import socket
import threading
import json
import queue

from typing import Callable, Optional, Dict, Any, Tuple, List
from src.utils.settings import SERVER_HOST, SERVER_PORT, BUFFER_SIZE, MSG_TYPE_GAME_STATE_UPDATE, MSG_TYPE_CONNECT_ACK

class Network:
    """
    Classe base para funcionalidades de rede, fornecendo métodos comuns
    para enviar e receber dados.
    """
    def __init__(self):
        self._socket: Optional[socket.socket] = None
        self._is_running: bool = False
        self._receive_thread: Optional[threading.Thread] = None
        self.message_queue: queue.Queue[Dict[str, Any]] = queue.Queue() # Fila para mensagens recebidas

    def _send_message(self, conn: socket.socket, message: Dict[str, Any]):
        """Envia uma mensagem JSON através do socket."""
        try:
            message_str = json.dumps(message)
            conn.sendall(message_str.encode('utf-8') + b'\n') # Adiciona um terminador para leitura
        except (socket.error, json.JSONEncodeError) as e:
            print(f"Erro ao enviar mensagem: {e}")
            self._is_running = False # Sinaliza para parar a thread de recebimento

    def _receive_messages(self, conn: socket.socket, client_address: Optional[Tuple[str, int]] = None):
        """Thread que recebe mensagens continuamente e as coloca na fila."""
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
                        message = json.loads(line.decode('utf-8'))
                        self.message_queue.put(message)
                    except json.JSONDecodeError as e:
                        print(f"Erro ao decodificar JSON: {e}, Dados: {line.decode('utf-8')}")
            except socket.error as e:
                if self._is_running: # Só imprime erro se ainda deveria estar rodando
                    print(f"Erro no socket durante o recebimento: {e}")
                self._is_running = False
                break
            except Exception as e:
                print(f"Erro inesperado no recebimento de mensagens: {e}")
                self._is_running = False
                break
        print(f"Thread de recebimento para {client_address or 'socket'} encerrada.")

    def stop(self):
        """Para a operação de rede e fecha o socket."""
        self._is_running = False
        if self._socket:
            try:
                self._socket.shutdown(socket.SHUT_RDWR)
                self._socket.close()
            except OSError as e:
                print(f"Erro ao fechar socket: {e}")
        if self._receive_thread and self._receive_thread.is_alive():
            self._receive_thread.join(timeout=1) # Espera a thread terminar

class GameServer(Network):
    """
    O servidor do jogo. Aceita conexões de clientes e gerencia a comunicação.
    """
    def __init__(self, host: str, port: int, client_connected_callback: Callable[[int], None]):
        super().__init__()
        self._host: str = host
        self._port: int = port
        self._client_connected_callback: Callable[[int], None] = client_connected_callback
        self.clients: Dict[int, socket.socket] = {} # {player_id: socket}
        self._client_id_counter: int = 0
        self._lock = threading.Lock() # Para proteger o acesso a self.clients e _client_id_counter

    def start(self):
        """Inicia o servidor e começa a escutar por conexões."""
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.settimeout(0.5) # Tempo limite para accept() para verificar _is_running
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
        """Loop que aceita novas conexões de clientes."""
        while self._is_running:
            try:
                conn, addr = self._socket.accept() # type: ignore
                conn.setblocking(True) # Conexões clientes são bloqueantes para recv
                with self._lock:
                    self._client_id_counter += 1
                    player_id = self._client_id_counter
                    self.clients[player_id] = conn
                print(f"Conexão aceita de {addr}, atribuído ID de jogador: {player_id}")
                
                # Envia o ID do jogador de volta para o cliente recém-conectado
                self._send_message(conn, {"type": MSG_TYPE_CONNECT_ACK, "player_id": player_id})

                # Inicia uma thread para receber mensagens deste cliente
                threading.Thread(target=self._receive_messages, args=(conn, addr), daemon=True).start()
                self._client_connected_callback(player_id) # Notifica o Controller
            except socket.timeout:
                continue # Continua o loop se não houver conexão no timeout
            except socket.error as e:
                if self._is_running:
                    print(f"Erro ao aceitar conexão: {e}")
                break
            except Exception as e:
                print(f"Erro inesperado no _accept_connections: {e}")
                break
        print("Thread de aceitação de conexões encerrada.")

    def send_to_all_clients(self, message: Dict[str, Any]):
        """Envia uma mensagem para todos os clientes conectados."""
        disconnected_clients = []
        with self._lock:
            for player_id, conn in list(self.clients.items()): # Usa list() para permitir modificação durante iteração
                try:
                    self._send_message(conn, message)
                except socket.error:
                    print(f"Cliente {player_id} desconectado.")
                    disconnected_clients.append(player_id)
            for player_id in disconnected_clients:
                del self.clients[player_id]

    def send_to_client(self, player_id: int, message: Dict[str, Any]):
        """Envia uma mensagem para um cliente específico."""
        with self._lock:
            conn = self.clients.get(player_id)
            if conn:
                try:
                    self._send_message(conn, message)
                except socket.error:
                    print(f"Erro ao enviar para cliente {player_id}. Desconectando.")
                    del self.clients[player_id]
            else:
                print(f"Cliente {player_id} não encontrado ou já desconectado.")

    def get_connected_player_ids(self) -> List[int]:
        """Retorna os IDs dos jogadores atualmente conectados."""
        with self._lock:
            return list(self.clients.keys())

    def stop(self):
        """Para o servidor, fechando todas as conexões de clientes."""
        super().stop()
        with self._lock:
            for conn in self.clients.values():
                try:
                    conn.shutdown(socket.SHUT_RDWR)
                    conn.close()
                except OSError:
                    pass # Ignora erros de socket já fechado
            self.clients.clear()
        print("Servidor parado.")

class GameClient(Network):
    """
    O cliente do jogo. Conecta-se ao servidor e gerencia a comunicação.
    """
    def __init__(self, host: str, port: int):
        super().__init__()
        self._host: str = host
        self._port: int = port
        self.player_id: Optional[int] = None # ID atribuído pelo servidor

    def connect(self) -> bool:
        """Tenta conectar ao servidor."""
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

    def send_message(self, message: Dict[str, Any]):
        """Envia uma mensagem para o servidor."""
        if self._socket and self._is_running:
            self._send_message(self._socket, message)
        else:
            print("Não conectado ao servidor para enviar mensagem.")