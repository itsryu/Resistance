import socket
import threading
import json
import queue
from typing import Callable, Optional, Dict, Tuple, List
from src.utils.settings import BUFFER_SIZE
from src.models.messages import ConnectAckMessage, NetworkMessage, create_message_from_dict

class Network:
    def __init__(self):
        self._socket: Optional[socket.socket] = None
        self._is_running: bool = False
        self._receive_thread: Optional[threading.Thread] = None
        self.message_queue: queue.Queue[NetworkMessage] = queue.Queue()

    def _send_message(self, conn: socket.socket, message: NetworkMessage):
        try:
            message_str = json.dumps(message.to_dict())
            conn.sendall(message_str.encode('utf-8') + b'\n')
        except (socket.error, TypeError) as e:
            print(f"Erro ao enviar mensagem: {e}")
            self._is_running = False

    def _receive_messages(self, conn: socket.socket, client_address: Optional[Tuple[str, int]] = None):
        buffer = b''
        while self._is_running:
            try:
                data = conn.recv(BUFFER_SIZE)
                if not data:
                    print(f"Conexão encerrada pelo {client_address or 'remoto'}.")
                    self._is_running = False
                    break
                buffer += data
                while b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    try:
                        message_data = json.loads(line.decode('utf-8'))
                        message = create_message_from_dict(message_data)
                        if message:
                            self.message_queue.put(message)
                    except json.JSONDecodeError as e:
                        print(f"Erro ao decodificar JSON: {e}, Dados: {line.decode('utf-8')}")
            except socket.error as e:
                if self._is_running:
                    print(f"Erro no socket durante o recebimento: {e}")
                self._is_running = False
                break
            except Exception as e:
                print(f"Erro inesperado no recebimento de mensagens: {e}")
                self._is_running = False
                break
        print(f"Thread de recebimento para {client_address or 'socket'} encerrada.")

    def stop(self):
        self._is_running = False
        if self._socket:
            try:
                self._socket.shutdown(socket.SHUT_RDWR)
                self._socket.close()
            except OSError as e:
                print(f"Erro ao fechar socket: {e}")
        if self._receive_thread and self._receive_thread.is_alive():
            self._receive_thread.join(timeout=1)

class GameServer(Network):
    def __init__(self, host: str, port: int, client_connected_callback: Callable[[int], None]):
        super().__init__()
        self._host: str = host
        self._port: int = port
        self._client_connected_callback: Callable[[int], None] = client_connected_callback
        self.clients: Dict[int, socket.socket] = {}
        self._client_id_counter: int = 0
        self._lock = threading.Lock()
        self._max_concurrent_client_setup: int = 3 
        self._client_setup_semaphore = threading.Semaphore(self._max_concurrent_client_setup)

    def start(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.settimeout(0.5)
        
        try:
            self._socket.bind((self._host, self._port))
            self._socket.listen(5)
            print(f"Servidor ouvindo em {self._host}:{self._port}")
            self._is_running = True
            threading.Thread(target=self._accept_connections, daemon=True).start()
        except socket.error as e:
            print(f"Erro ao iniciar servidor: {e}")
            self._is_running = False

    def _accept_connections(self):
        while self._is_running:
            try:
                if self._socket is None:
                    print("Socket do servidor não está inicializado.")
                    break
                conn, addr = self._socket.accept()
                threading.Thread(target=self._handle_new_client_connection, args=(conn, addr), daemon=True).start()
            except socket.timeout:
                continue
            except socket.error as e:
                if self._is_running:
                    print(f"Erro ao aceitar conexão: {e}")
                break
            except Exception as e:
                print(f"Erro inesperado no _accept_connections: {e}")
                break
        print("Thread de aceitação de conexões encerrada.")

    def _handle_new_client_connection(self, conn: socket.socket, addr: Tuple[str, int]):
        """
        Lida com a configuração inicial de uma nova conexão de cliente.
        Esta função é executada em uma thread separada e adquire uma permissão do semáforo.
        """
        with self._client_setup_semaphore:
            player_id: Optional[int] = None
            try:
                with self._lock:
                    self._client_id_counter += 1
                    player_id = self._client_id_counter
                    self.clients[player_id] = conn
                print(f"Conexão aceita de {addr}, atribuído ID de jogador: {player_id}")
                
                self._send_message(conn, ConnectAckMessage(player_id=player_id))

                threading.Thread(target=self._receive_messages, args=(conn, addr), daemon=True).start()
                self._client_connected_callback(player_id)
            except Exception as e:
                print(f"Erro ao configurar nova conexão de cliente: {e}")
                if player_id is not None and player_id in self.clients:
                    self.remove_client(player_id)

    def send_to_all_clients(self, message: NetworkMessage):
        disconnected_clients = []
        with self._lock:
            for player_id, conn in list(self.clients.items()):
                try:
                    self._send_message(conn, message)
                except socket.error:
                    print(f"Cliente {player_id} desconectado (erro ao enviar).")
                    disconnected_clients.append(player_id)
            for player_id in disconnected_clients:
                self.remove_client(player_id)

    def send_to_client(self, player_id: int, message: NetworkMessage):
        with self._lock:
            conn = self.clients.get(player_id)
            if conn:
                try:
                    self._send_message(conn, message)
                except socket.error:
                    print(f"Erro ao enviar para cliente {player_id}. Desconectando.")
                    self.remove_client(player_id)
            else:
                print(f"Cliente {player_id} não encontrado ou já desconectado.")

    def remove_client(self, player_id: int):
        with self._lock:
            if player_id in self.clients:
                conn = self.clients.pop(player_id)
                try:
                    conn.shutdown(socket.SHUT_RDWR)
                    conn.close()
                except OSError as e:
                    print(f"Erro ao fechar socket do cliente {player_id}: {e}")
                print(f"Cliente {player_id} removido.")

    def get_connected_player_ids(self) -> List[int]:
        with self._lock:
            return list(self.clients.keys())

    def stop(self):
        super().stop()
        with self._lock:
            for player_id in list(self.clients.keys()):
                self.remove_client(player_id)
            self.clients.clear()
        print("Servidor parado.")

class GameClient(Network):
    def __init__(self, host: str, port: int):
        super().__init__()
        self._host: str = host
        self._port: int = port
        self.player_id: Optional[int] = None

    def connect(self) -> bool:
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self._socket.connect((self._host, self._port))
            self._is_running = True
            self._receive_thread = threading.Thread(target=self._receive_messages, args=(self._socket, None), daemon=True)
            self._receive_thread.start()
            print(f"Conectado ao servidor em {self._host}:{self._port}")
            return True
        except socket.error as e:
            print(f"Erro ao conectar ao servidor: {e}")
            return False

    def send_message(self, message: NetworkMessage):
        if self._socket and self._is_running:
            self._send_message(self._socket, message)
        else:
            print("Não conectado ao servidor para enviar mensagem.")