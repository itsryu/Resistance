
import threading
import queue
import time
import tkinter as tk
import json
import os
from collections import defaultdict
import traceback

from typing import List, Dict, Any, Tuple, Optional, Callable

from src.models.model import GameModel
from src.models.player import Player
from src.views.view import GameView
from src.utils.network import GameServer, GameClient
from src.utils.settings import (
    NUM_PLAYERS, NUM_SPIES, MISSION_SIZES,
    SERVER_HOST, SERVER_PORT, SAVE_FILE_PATH, GAME_TITLE,
    MessageType
)
from src.models.messages import (
    NetworkMessage, ConnectAckMessage, GameStateUpdateMessage, StartGameMessage,
    PlayerRoleMessage, RequestTeamSelectionMessage, TeamProposedMessage, RequestVoteMessage,
    VoteCastMessage, RequestSabotageMessage, SabotageChoiceMessage,
    GameOverMessage, LogMessage
)

class InvalidTeamProposedSignal:
    pass

INVALID_TEAM_PROPOSED_SIGNAL = InvalidTeamProposedSignal()

class GameController:
    """
    O Controlador do jogo "The Resistance". Atua como um intermediário entre
    o Model e a View, gerenciando o fluxo do jogo, as entradas do usuário
    e as interações de rede.
    """
    def __init__(self, root: tk.Tk, is_server: bool, server_ip: Optional[str] = None):
        self.root: tk.Tk = root
        self.is_server: bool = is_server
        self.view: GameView = GameView(root)
        self.view.set_controller(self)

        self.model: Optional[GameModel] = None
        self.server: Optional[GameServer] = None
        self.client: Optional[GameClient] = None
        self.server_target_ip = server_ip

        self.players: List[Player] = [] 
        self.connected_player_ids: List[int] = []
        self.local_player_id: Optional[int] = None
        self.local_player_role: Optional[str] = None

        self._game_logic_thread: Optional[threading.Thread] = None
        self._current_phase_lock = threading.Lock() 

        self.team_selection_response_queue: queue.Queue[List[int] | InvalidTeamProposedSignal] = queue.Queue()
        self.vote_response_queues: Dict[int, queue.Queue[bool]] = defaultdict(queue.Queue)
        self.sabotage_response_queues: Dict[int, queue.Queue[bool]] = defaultdict(queue.Queue)
        
        self._message_handlers: Dict[MessageType, Callable[[NetworkMessage], None]] = {
            MessageType.CONNECT_ACK: self._handle_connect_ack,
            MessageType.GAME_STATE_UPDATE: self._handle_game_state_update,
            MessageType.PLAYER_ROLE: self._handle_player_role_assignment,
            MessageType.LOG_MESSAGE: self._handle_log_message,
            MessageType.GAME_OVER: self._handle_game_over,

            MessageType.START_GAME: self._handle_start_game_request,
            MessageType.TEAM_PROPOSED: self._handle_team_proposed,
            MessageType.VOTE_CAST: self._handle_vote_cast,
            MessageType.SABOTAGE_CHOICE: self._handle_sabotage_choice,

            MessageType.REQUEST_TEAM_SELECTION: self._handle_request_team_selection,
            MessageType.REQUEST_VOTE: self._handle_request_vote,
            MessageType.REQUEST_SABOTAGE: self._handle_request_sabotage,
        }

        self._initialize_mode()

    def _initialize_mode(self):
        """Inicializa o Controller no modo servidor ou cliente."""
        if self.is_server:
            loaded_model = self._load_game_state()
            if loaded_model:
                self.model = loaded_model
                self.view.write_to_log("Estado do jogo carregado com sucesso!")
                
                self.players = [Player(int(p_id), role) for p_id, role in self.model.players_roles.items()]
            else:
                self.model = GameModel(NUM_PLAYERS, NUM_SPIES, MISSION_SIZES)
                self.view.write_to_log("Nenhum estado salvo encontrado ou falha ao carregar. Iniciando um novo jogo.")

            self.model.set_state_changed_callback(self._on_model_state_changed)

            self.server = GameServer('0.0.0.0', SERVER_PORT, self._on_client_connected)
            self.server.start()
            self.view.write_to_log(f"MODO SERVIDOR INICIADO em 0.0.0.0:{SERVER_PORT} (acessível via IP local da máquina)")

            if self.model.game_started and not self.model.is_game_over():
                self.view.action_button.config(text="Jogo em Andamento...", state=tk.DISABLED)
                self.view.write_to_log("Jogo já em andamento. Aguardando clientes se reconectarem e retomarem.")
                
                if not self._game_logic_thread or not self._game_logic_thread.is_alive():
                    self._game_logic_thread = threading.Thread(target=self._run_game_logic_server, daemon=True)
                    self._game_logic_thread.start()
            else:
                self.view.action_button.config(text="Aguardando Jogadores...", command=self.request_start_game, state=tk.DISABLED)
                self.view.write_to_log(f"Aguardando {NUM_PLAYERS} jogadores se conectarem...")

        else: 
            target_ip = self.server_target_ip if self.server_target_ip else SERVER_HOST
            self.client = GameClient(target_ip, SERVER_PORT)
            self.view.write_to_log(f"MODO CLIENTE: Conectando a {target_ip}:{SERVER_PORT}...")
            self.view.action_button.config(text="Conectando...", state=tk.DISABLED)

            threading.Thread(target=self._connect_client_loop, daemon=True).start()

        self.root.after(100, self._process_network_messages)

    def _save_game_state(self):
        """Salva o estado atual do Model em um arquivo JSON."""
        if self.model:
            try:
                with open(SAVE_FILE_PATH, 'w') as f:
                    json.dump(self.model.to_dict(), f, indent=4)
                self.view.write_to_log("Estado do jogo salvo em disco.")
            except Exception as e:
                self.view.write_to_log(f"Erro ao salvar estado do jogo: {e}")

    def _load_game_state(self) -> Optional[GameModel]:
        """Carrega o estado do jogo de um arquivo JSON."""
        if os.path.exists(SAVE_FILE_PATH):
            try:
                with open(SAVE_FILE_PATH, 'r') as f:
                    data = json.load(f)
                return GameModel.from_dict(data)
            except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
                self.view.write_to_log(f"Erro ao carregar estado do jogo: {e}. Iniciando um novo jogo.")
                try:
                    os.remove(SAVE_FILE_PATH)
                    self.view.write_to_log(f"Arquivo de salvamento corrompido ou inválido '{SAVE_FILE_PATH}' removido.")
                except OSError as ose:
                    self.view.write_to_log(f"Não foi possível remover arquivo corrompido: {ose}")
                return None
        return None

    def _on_model_state_changed(self):
        """
        Callback chamado pelo Model quando seu estado muda (apenas no servidor).
        Este método envia o estado atualizado do Model para todos os clientes
        e também atualiza a View do próprio servidor e salva o estado.
        """
        if self.is_server and self.model and self.server:
            game_state_for_clients = self.model.get_game_state_for_client()
            self.server.send_to_all_clients(GameStateUpdateMessage(state=game_state_for_clients))
            self.root.after(0, lambda: self.view.update_view(game_state_for_clients)) 
            self._save_game_state()


    def _on_client_connected(self, player_id: int):
        """
        Callback chamado pelo GameServer quando um novo cliente se conecta.
        """
        if player_id not in self.connected_player_ids: 
            self.connected_player_ids.append(player_id)
        self.view.write_to_log(f"Jogador {player_id} conectado. Total: {len(self.connected_player_ids)}/{NUM_PLAYERS}")

        if len(self.connected_player_ids) == NUM_PLAYERS and self.model and not self.model.game_started:
            self.root.after(0, lambda: self.view.action_button.config(state=tk.NORMAL, text="Iniciar Jogo (Todos Conectados)"))
            if self.server:
                self.server.send_to_all_clients(LogMessage(text="Todos os jogadores estão conectados. O servidor pode iniciar o jogo!"))
        elif self.model and self.model.game_started:
            
            if self.server:
                self.server.send_to_client(player_id, GameStateUpdateMessage(state=self.model.get_game_state_for_client()))
                role = self.model.get_player_role(player_id)
                if role:
                    self.server.send_to_client(player_id, PlayerRoleMessage(player_id=player_id, role=role))


    def _connect_client_loop(self):
        """Lógica de conexão do cliente em uma thread separada, com tentativas."""
        if self.client is None:
            self.view.write_to_log("Erro: Cliente de rede não inicializado.")
            return

        while not self.client.connect():
            self.view.write_to_log("Falha ao conectar ao servidor. Tentando novamente em 5s...")
            time.sleep(5)

        self.view.write_to_log("Conectado ao servidor.")
        self.root.after(0, lambda: self.view.action_button.config(text="Aguardando Início do Jogo...", state=tk.DISABLED))


    def _process_network_messages(self):
        """
        Processa mensagens da fila de rede no thread principal da GUI.
        Isso garante que as atualizações da GUI ocorram no thread correto.
        """
        network_instance = None
        if self.is_server and self.server:
            network_instance = self.server
        elif not self.is_server and self.client:
            network_instance = self.client

        if network_instance:
            while not network_instance.message_queue.empty():
                message = network_instance.message_queue.get()
                self._dispatch_message(message)

        self.root.after(100, self._process_network_messages)

    def _dispatch_message(self, message: NetworkMessage):
        """Despacha a mensagem para o handler apropriado."""
        handler = self._message_handlers.get(message.type)
        if handler:
            try:
                handler(message)
            except Exception as e:
                self.view.write_to_log(f"Erro ao processar mensagem '{message.type.value}': {e}")
                print(f"Erro ao processar mensagem '{message.type.value}': {e}, Mensagem: {message}")
                traceback.print_exc() 
        else:
            self.view.write_to_log(f"Tipo de mensagem desconhecido: {message.type.value}")

    
    def _handle_connect_ack(self, message: NetworkMessage):
        """Handler para o reconhecimento de conexão (apenas cliente)."""
        if not self.is_server and isinstance(message, ConnectAckMessage):
            self.local_player_id = message.player_id
            self.view.write_to_log(f"ID de Jogador recebido do servidor: {self.local_player_id}")
            self.root.after(0, lambda: self.view.action_button.config(text="Aguardando Início do Jogo...", state=tk.DISABLED))

    def _handle_game_state_update(self, message: NetworkMessage):
        """Handler para atualizações do estado do jogo (apenas cliente)."""
        if not self.is_server and isinstance(message, GameStateUpdateMessage):
            game_state = message.state
            if game_state:
                self.root.after(0, lambda: self.view.update_view(game_state))
                if self.local_player_id and 'players_roles' in game_state:
                    
                    role = game_state['players_roles'].get(str(self.local_player_id))
                    if role:
                        self.local_player_role = role
                        self.root.after(0, lambda: self.view.set_local_player_info(self.local_player_id, self.local_player_role))
            else:
                self.view.write_to_log("Erro: Atualização de estado do jogo vazia.")

    def _handle_player_role_assignment(self, message: NetworkMessage):
        """Handler para atribuição de papel ao jogador (apenas cliente)."""
        if not self.is_server and isinstance(message, PlayerRoleMessage):
            player_id = message.player_id
            role = message.role
            if player_id == self.local_player_id:
                self.local_player_role = role
                self.root.after(0, lambda: self.view.set_local_player_info(self.local_player_id, self.local_player_role))

    def _handle_log_message(self, message: NetworkMessage):
        """Handler para mensagens de log do servidor (apenas cliente)."""
        if not self.is_server and isinstance(message, LogMessage):
            log_text = message.text
            if log_text:
                self.view.write_to_log(log_text)

    def request_start_game(self):
        """
        Gerencia a solicitação para iniciar ou reiniciar o jogo.
        No servidor, isso envia uma mensagem START_GAME para todos os clientes (incluindo ele próprio via processamento de mensagem).
        No cliente, isso envia uma mensagem START_GAME para o servidor (ex: para "Jogar Novamente").
        """
        if self.is_server and self.server:
            self.view.write_to_log("Servidor: Iniciando processo de início/reinício do jogo...")
            start_msg = StartGameMessage()
            self.server.send_to_all_clients(start_msg)
            
            self._dispatch_message(start_msg)
        elif not self.is_server and self.client:
            self.view.write_to_log("Cliente: Solicitando reinício do jogo ao servidor (Jogar Novamente)...")
            self.client.send_message(StartGameMessage())

    
    def _handle_start_game_request(self, message: NetworkMessage):
        """Handler para solicitação de início de jogo (apenas servidor)."""
        if self.is_server and self.model and self.server and isinstance(message, StartGameMessage):
            with self._current_phase_lock: 
                if not self.model.game_started or self.model.is_game_over():
                    if len(self.connected_player_ids) < NUM_PLAYERS:
                        self.view.write_to_log(f"Número insuficiente de jogadores ({len(self.connected_player_ids)}/{NUM_PLAYERS}) para iniciar o jogo.")
                        self.server.send_to_all_clients(LogMessage(text=f"O servidor precisa de mais {NUM_PLAYERS - len(self.connected_player_ids)} jogadores para iniciar."))
                        return

                    self.view.write_to_log("Solicitação de início de jogo recebida. Iniciando...")
                    self.server.send_to_all_clients(LogMessage(text="O jogo está prestes a começar!"))

                    
                    self.model.reset_game()
                    roles = self.model.assign_roles()
                    self.players = [Player(i, roles[i]) for i in range(1, self.model.num_players + 1)] 
                    
                    
                    for p in self.players:
                        self.server.send_to_client(p.player_id, PlayerRoleMessage(player_id=p.player_id, role=p.role))
                    
                    self.view.write_to_log("Jogo iniciado! Papéis atribuídos e enviados aos jogadores.")

                    
                    if not self._game_logic_thread or not self._game_logic_thread.is_alive():
                        self._game_logic_thread = threading.Thread(target=self._run_game_logic_server, daemon=True)
                        self._game_logic_thread.start()
                    else:
                        self.view.write_to_log("Thread de lógica do jogo já em execução. Não reiniciando.")

                else:
                    self.view.write_to_log("Jogo já em andamento. Ignorando solicitação de início.")
                    self.server.send_to_all_clients(LogMessage(text="O jogo já está em andamento. Por favor, aguarde o fim da rodada atual ou o servidor reiniciar."))


    def _handle_team_proposed(self, message: NetworkMessage):
        """Handler para time proposto pelo líder (apenas servidor)."""
        if self.is_server and self.model and self.server and isinstance(message, TeamProposedMessage):
            team_ids = message.team
            leader_id = message.player_id

            with self._current_phase_lock:
                
                if leader_id == self.model.current_leader_id:
                    
                    mission_size = self.model.get_current_mission_size()
                    if not team_ids or \
                       len(team_ids) != mission_size or \
                       not all(1 <= p_id <= self.model.num_players for p_id in team_ids) or \
                       len(set(team_ids)) != len(team_ids):
                        self.server.send_to_client(leader_id, LogMessage(text="Seleção de equipe inválida. Por favor, selecione exatamente "
                                                                             f"{mission_size} jogadores válidos e únicos. Tente novamente."))
                        self.team_selection_response_queue.put(INVALID_TEAM_PROPOSED_SIGNAL) 
                        return

                    
                    self.model.set_proposed_team(team_ids)
                    self.server.send_to_all_clients(LogMessage(text=f"Jogador {leader_id} propôs a equipe: {sorted(team_ids)}. Iniciando votação..."))
                    self.team_selection_response_queue.put(team_ids) 
                else:
                    self.server.send_to_client(leader_id, LogMessage(text="Não é sua vez de propor uma equipe."))

    def _handle_vote_cast(self, message: NetworkMessage):
        """Handler para voto recebido (apenas servidor)."""
        if self.is_server and self.model and self.server and isinstance(message, VoteCastMessage):
            player_id = message.player_id
            vote_choice = message.vote_choice

            if player_id in self.connected_player_ids and player_id not in self.model.team_votes: 
                
                self.vote_response_queues[player_id].put(vote_choice)
                
                with self._current_phase_lock:
                    self.model.record_vote(player_id, vote_choice) 
                
                vote_str = "APROVAR" if vote_choice else "REJEITAR"
                self.server.send_to_all_clients(LogMessage(text=f"Jogador {player_id} votou: {vote_str}"))
            else:
                self.server.send_to_client(player_id, LogMessage(text="Você já votou ou não é sua vez de votar."))


    def _handle_sabotage_choice(self, message: NetworkMessage):
        """Handler para escolha de sabotagem (apenas servidor)."""
        if self.is_server and self.model and self.server and isinstance(message, SabotageChoiceMessage):
            player_id = message.player_id
            sabotage_choice = message.sabotage_choice

            with self._current_phase_lock:
                is_on_proposed_team = self.model.proposed_team and player_id in self.model.proposed_team
                has_voted_sabotage = player_id in self.model.sabotage_choices
                
                
                player_obj = next((p for p in self.players if p.player_id == player_id), None)
                is_spy = player_obj and player_obj.is_spy

                if not is_on_proposed_team:
                    self.server.send_to_client(player_id, LogMessage(text="Você não está na equipe da missão."))
                    return
                if not is_spy:
                    self.server.send_to_client(player_id, LogMessage(text="Apenas espiões podem sabotar. Sua escolha não foi registrada como sabotagem."))
                    self.sabotage_response_queues[player_id].put(False) 
                    return
                if has_voted_sabotage:
                    self.server.send_to_client(player_id, LogMessage(text="Você já fez sua escolha de sabotagem para esta missão."))
                    return

                
                if player_id in self.sabotage_response_queues: 
                    self.sabotage_response_queues[player_id].put(sabotage_choice)
                    self.model.record_sabotage(player_id, sabotage_choice) 
                else:
                    self.server.send_to_client(player_id, LogMessage(text="Não é sua vez de escolher sabotagem ou estado inválido."))


    
    def _run_game_logic_server(self):
        """Thread que orquestra o fluxo do jogo no servidor."""
        try:
            if self.model is None or self.server is None:
                self.view.write_to_log("ERRO: Modelo ou Servidor não inicializado. Lógica do jogo não pode rodar.")
                return

            self.view.write_to_log(f"Thread de lógica do jogo ativa. Iniciando loop do jogo. Rodada atual: {self.model.current_round + 1}")

            while not self.model.is_game_over():
                self.root.after(0, lambda: self.view.write_to_log(f"\n--- INÍCIO DA RODADA {self.model.current_round + 1} ({self.model.current_mission_failures_count + 1}ª tentativa de equipe) ---"))
                self.root.after(0, lambda: self.view.write_to_log(f"Líder da Rodada: Jogador {self.model.current_leader_id}"))

                
                self._request_team_selection_server_sync()

                team_response: Optional[List[int] | InvalidTeamProposedSignal] = None
                try:
                    
                    self.root.after(0, lambda: self.view.update_timer(60))
                    team_response = self.team_selection_response_queue.get(timeout=60)
                except queue.Empty:
                    self.view.write_to_log(f"Tempo esgotado: Jogador {self.model.current_leader_id} (Líder) não propôs equipe.")
                    self.server.send_to_all_clients(LogMessage(text=f"Tempo esgotado para o Jogador {self.model.current_leader_id}. Avançando líder."))
                    with self._current_phase_lock:
                        self.model.advance_leader()
                    self.root.after(0, lambda: self.view.update_timer(0)) 
                    continue 

                if team_response is INVALID_TEAM_PROPOSED_SIGNAL:
                    self.view.write_to_log("Proposta de equipe inválida recebida. Líder atual terá outra chance (sem avançar líder).")
                    self.root.after(0, lambda: self.view.update_timer(0)) 
                    continue 

                team_ids = team_response
                self.view.write_to_log(f"Lógica do servidor: Equipe Selecionada: {team_ids}")
                self.root.after(0, lambda: self.view.update_timer(0)) 

                
                self.view.write_to_log("Lógica do servidor iniciando coleta de votos...")
                self.model.team_votes = {} 
                votes_collected = 0
                total_players = self.model.num_players

                
                for player_to_vote_obj in self.players:
                    player_id = player_to_vote_obj.player_id
                    
                    self.vote_response_queues[player_id] = queue.Queue()
                    self.root.after(0, lambda p_id=player_id, team=team_ids: self._request_next_vote_server(p_id, team))
                
                
                self.root.after(0, lambda: self.view.update_timer(30)) 
                for player_to_vote_obj in self.players:
                    player_id = player_to_vote_obj.player_id
                    try:
                        vote_choice = self.vote_response_queues[player_id].get(timeout=30) 
                        self.view.write_to_log(f"Voto recebido do Jogador {player_id}: {'SIM' if vote_choice else 'NÃO'}.")
                        
                    except queue.Empty:
                        self.view.write_to_log(f"Tempo esgotado: Jogador {player_id} não votou. Assumindo NÃO.")
                        with self._current_phase_lock:
                            self.model.record_vote(player_id, False) 
                self.root.after(0, lambda: self.view.update_timer(0)) 

                with self._current_phase_lock:
                    team_approved = self.model.process_team_vote()

                self.root.after(0, lambda: self.server.send_to_all_clients(
                    GameStateUpdateMessage(state=self.model.get_game_state_for_client())
                ))

                if team_approved:
                    self.server.send_to_all_clients(LogMessage(text="Equipe aprovada! Missão em andamento..."))
                    self.view.write_to_log("Lógica do servidor: Equipe aprovada! Iniciando coleta de sabotagem...")

                    
                    self.model.sabotage_choices = {} 
                    
                    
                    for player_on_mission_id in team_ids:
                        player_obj_on_mission = next((p for p in self.players if p.player_id == player_on_mission_id), None)
                        if player_obj_on_mission and player_obj_on_mission.is_spy:
                            self.sabotage_response_queues[player_obj_on_mission.player_id] = queue.Queue() 
                            self.root.after(0, lambda p_id=player_obj_on_mission.player_id: self._request_next_sabotage_server(p_id, True))
                    
                    
                    self.root.after(0, lambda: self.view.update_timer(30)) 
                    for player_on_mission_id in team_ids:
                        player_obj_on_mission = next((p for p in self.players if p.player_id == player_on_mission_id), None)
                        if player_obj_on_mission and player_obj_on_mission.is_spy:
                            try:
                                sabotage_choice = self.sabotage_response_queues[player_obj_on_mission.player_id].get(timeout=30)
                                self.view.write_to_log(f"Escolha de sabotagem recebida do Jogador {player_obj_on_mission.player_id}: {sabotage_choice}.")
                                
                            except queue.Empty:
                                self.view.write_to_log(f"Tempo esgotado: Espião Jogador {player_obj_on_mission.player_id} não escolheu sabotar. Assumindo NÃO.")
                                with self._current_phase_lock:
                                    self.model.record_sabotage(player_obj_on_mission.player_id, False)
                        elif player_obj_on_mission: 
                            self.view.write_to_log(f"Jogador {player_obj_on_mission.player_id} (Resistência) não pode sabotar. Assumindo NÃO.")
                            with self._current_phase_lock:
                                self.model.record_sabotage(player_obj_on_mission.player_id, False)
                    self.root.after(0, lambda: self.view.update_timer(0)) 

                    with self._current_phase_lock:
                        self.model.process_mission_outcome() 
                    
                    
                    self.root.after(0, self._process_mission_result_server_sync)

                else: 
                    self.view.write_to_log("Lógica do servidor: Equipe rejeitada. Avançando líder.")
                    self.server.send_to_all_clients(LogMessage(text=f"A equipe foi REJEITADA! Total de rejeições nesta rodada: {self.model.current_mission_failures_count}"))
                    with self._current_phase_lock:
                        self.model.advance_leader() 
                    self.root.after(0, lambda: self.server.send_to_all_clients(GameStateUpdateMessage(state=self.model.get_game_state_for_client())))

                self.view.write_to_log("Fim da iteração do loop de jogo atual. Verificando condição de fim de jogo.")
                self.root.after(0, lambda: self.view.update_timer(0)) 

            self.root.after(0, self._end_game_server)
        except Exception as e:
            self.view.write_to_log(f"ERRO FATAL na thread de lógica do jogo: {e}")
            traceback.print_exc()


    
    def _request_team_selection_server_sync(self):
        """Solicita a seleção de equipe do líder atual no servidor, sincronizado com a thread de lógica."""
        if self.model is None or self.server is None: return

        
        

        leader_id = self.model.current_leader_id
        mission_size = self.model.get_current_mission_size()
        available_ids = list(range(1, self.model.num_players + 1))

        if leader_id == self.local_player_id: 
            self.view.write_to_log(f"Servidor (atuando como Jogador {leader_id}): Solicitando sua seleção de equipe localmente.")
            self.root.after(0, lambda: self.view.show_team_selection_dialog(
                leader_id=leader_id,
                mission_size=mission_size,
                available_players_ids=available_ids,
                callback=self._on_team_selected_server_local_callback,
                timeout=60
            ))
        else: 
            self.server.send_to_client(leader_id, RequestTeamSelectionMessage(
                leader_id=leader_id,
                mission_size=mission_size,
                available_players_ids=available_ids
            ))
            self.view.write_to_log(f"Servidor solicitando seleção de equipe do Jogador {leader_id} (remoto).")


    def _process_mission_result_server_sync(self):
        """Processa o resultado final da missão e atualiza o Model no servidor, sincronizado."""
        if self.model is None or self.server is None: return

        
        mission_success = self.model.mission_results[-1]
        sabotages_count = self.model.mission_sabotages

        if mission_success:
            self.server.send_to_all_clients(LogMessage(text="Missão bem-sucedida! A Resistência marcou um ponto!"))
        else:
            self.server.send_to_all_clients(LogMessage(text=f"Missão FALHOU com {sabotages_count} sabotagem(ns)! Os Espiões marcaram um ponto!"))

        self.server.send_to_all_clients(GameStateUpdateMessage(state=self.model.get_game_state_for_client()))
        
        
        with self._current_phase_lock:
            self.model.advance_leader() 
        self.server.send_to_all_clients(LogMessage(text=f"Próximo líder: Jogador {self.model.current_leader_id}"))


    def _request_next_vote_server(self, player_id_to_vote: int, team_ids: List[int]):
        """Solicita o voto de um jogador específico."""
        if self.model is None or self.server is None: return

        if player_id_to_vote == self.local_player_id: 
            self.view.write_to_log(f"Servidor (atuando como Jogador {player_id_to_vote}): Solicitando seu voto localmente.")
            self.root.after(0, lambda: self.view.show_vote_dialog(
                player_id=player_id_to_vote,
                team=team_ids,
                callback=self._on_vote_cast_server_local_callback,
                timeout=30
            ))
        else: 
            self.server.send_to_client(player_id_to_vote, RequestVoteMessage(
                player_id=player_id_to_vote,
                team=team_ids
            ))

    def _request_next_sabotage_server(self, player_id_on_mission: int, is_spy: bool):
        """Solicita a escolha de sabotagem de um membro da equipe específico."""
        if self.model is None or self.server is None: return

        if player_id_on_mission == self.local_player_id: 
            if is_spy:
                self.view.write_to_log(f"Servidor (atuando como Jogador {player_id_on_mission}): Solicitando sua escolha de sabotagem localmente.")
                self.root.after(0, lambda: self.view.show_sabotage_dialog(
                    player_id=player_id_on_mission,
                    callback=self._on_sabotage_choice_server_local_callback,
                    timeout=30
                ))
            else: 
                self.view.write_to_log(f"Servidor (atuando como Jogador {player_id_on_mission}, Resistência): Não pode sabotar. Escolha local é Falso.")
                if player_id_on_mission in self.sabotage_response_queues:
                    self.sabotage_response_queues[player_id_on_mission].put(False)
        else: 
            if is_spy:
                self.server.send_to_client(player_id_on_mission, RequestSabotageMessage(
                    player_id=player_id_on_mission
                ))
                self.view.write_to_log(f"Servidor solicitando escolha de sabotagem do Espião Jogador {player_id_on_mission}.")
            else:
                
                
                self.view.write_to_log(f"Jogador {player_id_on_mission} (Resistência) não pode sabotar. Escolha assumida como 'NÃO'.")
                
                if player_id_on_mission in self.sabotage_response_queues:
                    self.sabotage_response_queues[player_id_on_mission].put(False)


    def _end_game_server(self):
        """Finaliza o jogo e envia o vencedor para todos os clientes."""
        if self.model is None or self.server is None: return

        winner = self.model.get_game_winner()
        results_display = [("Sucesso" if r else "Falha") for r in self.model.mission_results]
        self.server.send_to_all_clients(LogMessage(text=f"\n--- FIM DE JOGO ---"))
        self.server.send_to_all_clients(LogMessage(text=f"Resultados das Missões: {', '.join(results_display)}"))
        self.server.send_to_all_clients(GameOverMessage(winner=winner))
        self.view.write_to_log(f"Jogo finalizado! Vencedor: {winner}")
        self.root.after(0, lambda: self.view.action_button.config(state=tk.NORMAL, text="Reiniciar Servidor"))
        
        with self._current_phase_lock:
            self.model.game_started = False
            self.model.reset_game()
        self._on_model_state_changed()

    def _on_team_selected_server_local_callback(self, team_ids: List[int]):
        """Callback acionado quando o líder (servidor local) seleciona um time."""
        self.team_selection_response_queue.put(team_ids)
        self.view.write_to_log(f"Servidor (local): Equipe proposta {team_ids} para a missão.")

    def _on_vote_cast_server_local_callback(self, vote_choice: bool):
        """Callback acionado quando um jogador (servidor local) vota."""
        if self.local_player_id: 
            
            if self.local_player_id in self.vote_response_queues:
                self.vote_response_queues[self.local_player_id].put(vote_choice)
                self.view.write_to_log(f"Servidor (local Jogador {self.local_player_id}): Votou {vote_choice}.")
                
            else:
                self.view.write_to_log("Erro: Fila de voto não encontrada para callback de voto local. Tentando recriar.")
                self.vote_response_queues[self.local_player_id] = queue.Queue()
                self.vote_response_queues[self.local_player_id].put(vote_choice)
                with self._current_phase_lock:
                    if self.model: self.model.record_vote(self.local_player_id, vote_choice)


    def _on_sabotage_choice_server_local_callback(self, sabotage_choice: bool):
        """Callback acionado quando um jogador (servidor local) escolhe sabotar."""
        if self.local_player_id:
            
            if self.local_player_id in self.sabotage_response_queues:
                self.sabotage_response_queues[self.local_player_id].put(sabotage_choice)
                self.view.write_to_log(f"Servidor (local Jogador {self.local_player_id}): Escolha de sabotagem: {sabotage_choice}.")
                
            else:
                self.view.write_to_log("Erro: Fila de sabotagem não encontrada para callback de sabotagem local. Tentando recriar.")
                self.sabotage_response_queues[self.local_player_id] = queue.Queue()
                self.sabotage_response_queues[self.local_player_id].put(sabotage_choice)
                with self._current_phase_lock:
                    if self.model: self.model.record_sabotage(self.local_player_id, sabotage_choice)


    

    def _handle_request_team_selection(self, message: NetworkMessage):
        """Manipulador para solicitação de seleção de equipe (apenas lado do cliente, se o jogador local for o líder)."""
        if not self.is_server and isinstance(message, RequestTeamSelectionMessage) and self.local_player_id == message.leader_id:
            leader_id = message.leader_id
            mission_size = message.mission_size
            available_players_ids = message.available_players_ids

            self.root.after(0, lambda: self.view.show_team_selection_dialog(
                leader_id=leader_id,
                mission_size=mission_size,
                available_players_ids=available_players_ids,
                callback=self._on_team_selected_client_callback,
                timeout=60
            ))
            self.root.after(0, lambda: self.view.update_timer(60)) 
        else:
            if not self.is_server and isinstance(message, RequestTeamSelectionMessage):
                self.view.write_to_log(f"O líder atual é o Jogador {message.leader_id}. Aguardando seleção da equipe...")
                self.root.after(0, lambda: self.view.update_timer(60)) 


    def _on_team_selected_client_callback(self, team_ids: List[int]):
        """Callback do cliente quando o líder local seleciona uma equipe."""
        if self.client and self.local_player_id:
            self.client.send_message(TeamProposedMessage(
                player_id=self.local_player_id,
                team=team_ids
            ))
            self.view.write_to_log("Equipe proposta enviada ao servidor.")
        self.root.after(0, lambda: self.view.update_timer(0)) 

    def _handle_request_vote(self, message: NetworkMessage):
        """Manipulador para solicitação de voto (apenas lado do cliente)."""
        if not self.is_server and isinstance(message, RequestVoteMessage) and self.local_player_id == message.player_id:
            team = message.team
            self.root.after(0, lambda: self.view.show_vote_dialog(
                player_id=self.local_player_id,
                team=team,
                callback=self._on_vote_cast_client_callback,
                timeout=30
            ))
            self.root.after(0, lambda: self.view.update_timer(30)) 
        else:
            if not self.is_server and isinstance(message, RequestVoteMessage):
                self.view.write_to_log(f"Aguardando voto do Jogador {message.player_id}...")
                self.root.after(0, lambda: self.view.update_timer(30)) 


    def _on_vote_cast_client_callback(self, vote_choice: bool):
        """Callback do cliente quando um jogador local vota."""
        if self.client and self.local_player_id:
            self.client.send_message(VoteCastMessage(
                player_id=self.local_player_id,
                vote_choice=vote_choice
            ))
            self.view.write_to_log("Voto enviado ao servidor.")
        self.root.after(0, lambda: self.view.update_timer(0)) 

    def _handle_request_sabotage(self, message: NetworkMessage):
        """Manipulador para solicitação de sabotagem (apenas lado do cliente)."""
        if not self.is_server and isinstance(message, RequestSabotageMessage) and self.local_player_id == message.player_id:
            if self.local_player_role == "Espião":
                self.root.after(0, lambda: self.view.show_sabotage_dialog(
                    player_id=self.local_player_id,
                    callback=self._on_sabotage_choice_client_callback,
                    timeout=30
                ))
                self.root.after(0, lambda: self.view.update_timer(30)) 
            else:
                self.view.write_to_log("Você é Resistência, você não pode sabotar. Enviando 'Não' ao servidor.")
                self._on_sabotage_choice_client_callback(False) 
        else:
            if not self.is_server and isinstance(message, RequestSabotageMessage):
                self.view.write_to_log(f"Aguardando escolha de sabotagem do Jogador {message.player_id}...")
                self.root.after(0, lambda: self.view.update_timer(30)) 


    def _on_sabotage_choice_client_callback(self, sabotage_choice: bool):
        """Callback do cliente quando um jogador local decide sabotar."""
        if self.client and self.local_player_id:
            self.client.send_message(SabotageChoiceMessage(
                player_id=self.local_player_id,
                sabotage_choice=sabotage_choice
            ))
            self.view.write_to_log("Escolha de sabotagem enviada ao servidor.")
        self.root.after(0, lambda: self.view.update_timer(0)) 


    def _handle_game_over(self, message: NetworkMessage):
        """Manipulador para fim de jogo (apenas lado do cliente)."""
        if not self.is_server and isinstance(message, GameOverMessage):
            winner = message.winner
            self.root.after(0, lambda: self.view.show_game_over_dialog(winner))
            self.view.write_to_log(f"Fim de Jogo! Vencedor: {winner}")
            self.root.after(0, lambda: self.view.action_button.config(state=tk.NORMAL, text="Jogar Novamente"))