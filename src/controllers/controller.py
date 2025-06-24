# --- resistance_game/controller.py ---
# A camada de Controller, orquestra as interações entre Model e View.
# Gerencia o fluxo do jogo e as entradas/saídas de rede.

import threading
import queue
from typing import List, Dict, Any, Tuple, Optional, Callable
import time

from src.models.model import GameModel
from src.views.view import GameView
from src.models.player import Player
from src.utils.network import GameServer, GameClient
from src.utils.settings import (
    NUM_PLAYERS, NUM_SPIES, MISSION_SIZES,
    SERVER_HOST, SERVER_PORT,
    MSG_TYPE_CONNECT_ACK, MSG_TYPE_GAME_STATE_UPDATE, MSG_TYPE_START_GAME, MSG_TYPE_PLAYER_ROLE,
    MSG_TYPE_REQUEST_TEAM_SELECTION, MSG_TYPE_TEAM_PROPOSED, MSG_TYPE_REQUEST_VOTE, MSG_TYPE_VOTE_CAST,
    MSG_TYPE_REQUEST_SABOTAGE, MSG_TYPE_SABOTAGE_CHOICE, MSG_TYPE_MISSION_OUTCOME, MSG_TYPE_GAME_OVER,
    MSG_TYPE_LOG_MESSAGE
)

class GameController:
    """
    O Controlador do jogo "A Resistência". Atua como um intermediário entre
    o Model e a View, gerenciando o fluxo do jogo, as entradas do usuário
    e as interações de rede.
    """
    def __init__(self, root: tk.Tk, is_server: bool):
        self.root: tk.Tk = root
        self.is_server: bool = is_server
        self.view: GameView = GameView(root)
        self.view.set_controller(self)

        self.model: Optional[GameModel] = None # Apenas o servidor tem um Model
        self.server: Optional[GameServer] = None # Apenas o servidor tem uma instância de GameServer
        self.client: Optional[GameClient] = None # Apenas o cliente tem uma instância de GameClient

        self.players: List[Player] = [] # Lista de objetos Player (gerenciada no servidor)
        self.connected_player_ids: List[int] = [] # IDs dos jogadores conectados (apenas no servidor)
        self.local_player_id: Optional[int] = None # ID do jogador local (apenas no cliente)
        self.local_player_role: Optional[str] = None # Papel do jogador local (apenas no cliente)

        # Fila para mensagens de rede para o thread principal da GUI
        self.network_message_queue: queue.Queue[Dict[str, Any]] = queue.Queue()
        # Não precisamos de threads dedicadas para processar a fila aqui; root.after faz isso.
        # self._message_processing_thread: Optional[threading.Thread] = None 
        self._game_logic_thread: Optional[threading.Thread] = None # Thread para a lógica do jogo no servidor

        self._current_phase_lock = threading.Lock() # Para sincronizar o acesso a fases do jogo no servidor

        # Atributos de controle de fase do jogo (apenas servidor)
        self._current_player_voting_index_server: int = 0
        self._current_player_sabotaging_index_server: int = 0
        self._last_mission_outcome_log: str = "" # Para evitar logs duplicados no final da missão

        # Mapeamento de mensagens de rede para handlers no Controller
        self._message_handlers: Dict[str, Callable[[Dict[str, Any]], None]] = {
            MSG_TYPE_CONNECT_ACK: self._handle_connect_ack,
            MSG_TYPE_GAME_STATE_UPDATE: self._handle_game_state_update,
            MSG_TYPE_PLAYER_ROLE: self._handle_player_role_assignment, # Especificamente para o papel individual
            MSG_TYPE_LOG_MESSAGE: self._handle_log_message, # Para mensagens de log gerais do servidor
            MSG_TYPE_GAME_OVER: self._handle_game_over, # Para notificação de fim de jogo

            # Mensagens do cliente para o servidor
            MSG_TYPE_START_GAME: self._handle_start_game_request,
            MSG_TYPE_TEAM_PROPOSED: self._handle_team_proposed,
            MSG_TYPE_VOTE_CAST: self._handle_vote_cast,
            MSG_TYPE_SABOTAGE_CHOICE: self._handle_sabotage_choice,

            # Mensagens do servidor para o cliente (requerem ação do cliente)
            MSG_TYPE_REQUEST_TEAM_SELECTION: self._handle_request_team_selection,
            MSG_TYPE_REQUEST_VOTE: self._handle_request_vote,
            MSG_TYPE_REQUEST_SABOTAGE: self._handle_request_sabotage,
        }

        self._initialize_mode()

    def _initialize_mode(self):
        """Inicializa o Controller no modo servidor ou cliente."""
        if self.is_server:
            self.model = GameModel(NUM_PLAYERS, NUM_SPIES, MISSION_SIZES)
            self.model.set_state_changed_callback(self._on_model_state_changed)
            self.server = GameServer(SERVER_HOST, SERVER_PORT, self._on_client_connected)
            self.server.start()
            self.view.write_to_log(f"MODO SERVIDOR INICIADO em {SERVER_HOST}:{SERVER_PORT}")
            self.view.action_button.config(text="Aguardando jogadores...", command=self.request_start_game, state=tk.DISABLED)
            self.view.write_to_log("Aguardando " + str(NUM_PLAYERS) + " jogadores se conectarem...")
            
        else: # Cliente
            self.client = GameClient(SERVER_HOST, SERVER_PORT)
            self.view.write_to_log(f"MODO CLIENTE: Conectando a {SERVER_HOST}:{SERVER_PORT}...")
            self.view.action_button.config(text="Conectando...", state=tk.DISABLED)
            
            # Tenta conectar em uma thread separada para não bloquear a GUI
            threading.Thread(target=self._connect_client_loop, daemon=True).start()
        
        # Inicia o loop de processamento de mensagens de rede para AMBOS os modos
        self.root.after(100, self._process_network_messages)

    def _connect_client_loop(self):
        """Lógica de conexão do cliente em uma thread separada, com tentativas."""
        while not self.client.connect(): # type: ignore
            self.view.write_to_log("Falha ao conectar ao servidor. Tentando novamente em 5s...")
            time.sleep(5) # Espera antes de tentar novamente

        self.view.write_to_log("Conectado ao servidor.")
        # A view será atualizada após receber o CONNECT_ACK via network_message_queue.
        # O botão de ação no cliente será atualizado pelo handler de GAME_STATE_UPDATE.


    def _process_network_messages(self):
        """
        Processa mensagens da fila de rede no thread principal da GUI.
        Isso garante que as atualizações da GUI ocorram no thread correto.
        """
        if self.is_server:
            network_instance = self.server # type: ignore
        else:
            network_instance = self.client # type: ignore
        
        if network_instance:
            while not network_instance.message_queue.empty():
                message = network_instance.message_queue.get()
                self._dispatch_message(message)
            
        # Agende a próxima verificação
        self.root.after(100, self._process_network_messages)

    def _dispatch_message(self, message: Dict[str, Any]):
        """Despacha a mensagem para o handler apropriado."""
        msg_type = message.get("type")
        handler = self._message_handlers.get(msg_type)
        if handler:
            # print(f"Processando mensagem tipo: {msg_type} (no main thread)") # Debug
            try:
                handler(message)
            except Exception as e:
                self.view.write_to_log(f"Erro ao processar mensagem '{msg_type}': {e}")
                print(f"Erro ao processar mensagem '{msg_type}': {e}, Mensagem: {message}")
        else:
            self.view.write_to_log(f"Tipo de mensagem desconhecido: {msg_type}")

    # --- Handlers de Mensagens de Rede (Cliente e Servidor) ---
    def _handle_connect_ack(self, message: Dict[str, Any]):
        """Handler para o reconhecimento de conexão (apenas cliente)."""
        if not self.is_server:
            self.local_player_id = message.get("player_id")
            self.view.write_to_log(f"ID de jogador recebido do servidor: {self.local_player_id}")
            # O papel será setado via MSG_TYPE_PLAYER_ROLE ou GAME_STATE_UPDATE
            self.view.action_button.config(text="Aguardando Jogo Iniciar...", state=tk.DISABLED) 

    def _handle_game_state_update(self, message: Dict[str, Any]):
        """Handler para atualizações do estado do jogo (apenas cliente)."""
        if not self.is_server:
            game_state = message.get("state")
            if game_state:
                self.view.update_view(game_state)
                # Cliente agora sabe seu papel se 'players_roles' veio no estado completo
                if self.local_player_id and 'players_roles' in game_state:
                    # IDs de jogador vêm como string do JSON
                    role = game_state['players_roles'].get(str(self.local_player_id)) 
                    if role and self.local_player_role is None: # Atribui o papel apenas uma vez
                        self.local_player_role = role
                        self.view.set_local_player_info(self.local_player_id, self.local_player_role)
            else:
                self.view.write_to_log("Erro: Atualização de estado do jogo vazia.")

    def _handle_player_role_assignment(self, message: Dict[str, Any]):
        """Handler para atribuição de papel ao jogador (apenas cliente)."""
        if not self.is_server:
            player_id = message.get("player_id")
            role = message.get("role")
            if player_id == self.local_player_id:
                self.local_player_role = role
                self.view.set_local_player_info(self.local_player_id, self.local_player_role)


    def _handle_log_message(self, message: Dict[str, Any]):
        """Handler para mensagens de log do servidor (apenas cliente)."""
        if not self.is_server:
            log_text = message.get("text")
            if log_text:
                self.view.write_to_log(log_text)

    # --- Server-side message handlers (received from clients) ---
    def _handle_start_game_request(self, message: Dict[str, Any]):
        """Handler para solicitação de início de jogo (apenas servidor)."""
        if self.is_server and self.model:
            if not self.model.game_started:
                if len(self.connected_player_ids) < NUM_PLAYERS:
                    self.view.write_to_log(f"Não há jogadores suficientes ({len(self.connected_player_ids)}/{NUM_PLAYERS}) para iniciar o jogo.")
                    self.server.send_to_all_clients({ # type: ignore
                        "type": MSG_TYPE_LOG_MESSAGE,
                        "text": f"O servidor precisa de {NUM_PLAYERS - len(self.connected_player_ids)} mais jogadores para iniciar."
                    })
                    return

                self.view.write_to_log("Solicitação de início de jogo recebida. Iniciando...")
                self.server.send_to_all_clients({ # type: ignore
                    "type": MSG_TYPE_LOG_MESSAGE,
                    "text": "O jogo está prestes a começar!"
                })
                # Inicia o jogo em uma thread para não bloquear o thread principal do servidor
                self._game_logic_thread = threading.Thread(target=self._run_game_logic_server, daemon=True)
                self._game_logic_thread.start()
                self.model.game_started = True
                self.update_view_from_model() # Atualiza o botão do servidor
            else:
                self.view.write_to_log("Jogo já em andamento ou já iniciado.")

    def _handle_team_proposed(self, message: Dict[str, Any]):
        """Handler para time proposto pelo líder (apenas servidor)."""
        if self.is_server and self.model:
            team_ids = message.get("team")
            leader_id = message.get("player_id") # O ID do jogador que propôs o time

            with self._current_phase_lock: # Garante que apenas uma proposta de time seja processada por vez
                if leader_id == self.model.current_leader_id: # Apenas se for o líder correto
                    if not team_ids or \
                       len(team_ids) != self.model.get_current_mission_size() or \
                       not all(1 <= p_id <= self.model.num_players for p_id in team_ids) or \
                       len(set(team_ids)) != len(team_ids):
                        self.server.send_to_client(leader_id, { # type: ignore
                            "type": MSG_TYPE_LOG_MESSAGE,
                            "text": "❌ Seleção de time inválida. Tente novamente."
                        })
                        # Re-solicita a seleção ao mesmo líder
                        self.server.send_to_client(leader_id, { # type: ignore
                            "type": MSG_TYPE_REQUEST_TEAM_SELECTION,
                            "leader_id": leader_id,
                            "mission_size": self.model.get_current_mission_size(),
                            "available_players_ids": list(range(1, self.model.num_players + 1))
                        })
                        return # Não prossegue

                    self.model.set_proposed_team(team_ids)
                    self.server.send_to_all_clients({ # type: ignore
                        "type": MSG_TYPE_LOG_MESSAGE,
                        "text": f"👥 Jogador {leader_id} propôs o time: {team_ids}. Iniciando votação..."
                    })
                    # Agora, inicia o processo de votação em cada cliente.
                    self._start_vote_collection_server()
                else:
                    self.server.send_to_client(leader_id, { # type: ignore
                        "type": MSG_TYPE_LOG_MESSAGE,
                        "text": "Não é sua vez de propor um time."
                    })

    def _handle_vote_cast(self, message: Dict[str, Any]):
        """Handler para voto recebido (apenas servidor)."""
        if self.is_server and self.model:
            player_id = message.get("player_id")
            vote_choice = message.get("vote_choice")

            # Garantir que o voto vem de um jogador válido e ainda não votou nesta fase
            # (A fila e o lock ajudam a serializar, mas uma checagem de estado adicional é boa)
            # Para simplificar aqui, confiamos na ordem e no lock.
            with self._current_phase_lock:
                # O model.record_vote já adiciona ao team_votes.
                # Precisamos de um mecanismo para saber se todos já votaram e quem votou.
                # A abordagem atual de "contar o tamanho da lista team_votes" funciona
                # se garantirmos que só aceitamos votos de quem ainda não votou.
                # Para simplificar, assumiremos que os clientes só enviam voto quando solicitado.
                
                self.model.record_vote(vote_choice)
                vote_str = "✅ SIM" if vote_choice else "❌ NÃO"
                self.server.send_to_all_clients({ # type: ignore
                    "type": MSG_TYPE_LOG_MESSAGE,
                    "text": f"🗳 Jogador {player_id} votou {vote_str}"
                })
                # Checa se todos votaram
                if len(self.model.team_votes) == self.model.num_players:
                    self._process_all_votes_server()
                else:
                    # Pede o próximo voto se ainda faltam jogadores para votar
                    self._request_next_vote_server()


    def _handle_sabotage_choice(self, message: Dict[str, Any]):
        """Handler para escolha de sabotagem (apenas servidor)."""
        if self.is_server and self.model:
            player_id = message.get("player_id")
            sabotage_choice = message.get("sabotage_choice")

            with self._current_phase_lock:
                # Confirma se o jogador está na equipe da missão e se é um espião (se sabotou)
                is_on_mission = self.model.proposed_team and player_id in self.model.proposed_team
                is_spy = self.model.get_player_role(player_id) == "Espião"

                if is_on_mission:
                    # Se não é espião e tentou sabotar, ou se é espião e sabotou, registra.
                    # A lógica do model já lida com quem pode sabotar.
                    self.model.record_sabotage(sabotage_choice)
                    sabotage_str = "SABOTOU" if sabotage_choice else "NÃO sabotou"
                    self.server.send_to_all_clients({ # type: ignore
                        "type": MSG_TYPE_LOG_MESSAGE,
                        "text": f"💥 Jogador {player_id} {sabotage_str} a missão!"
                    })
                    
                    # Para saber se todos os membros da missão já enviaram sua escolha:
                    self._current_player_sabotaging_index_server += 1 # Incrementa após processar
                    if self._current_player_sabotaging_index_server == len(self.model.proposed_team):
                        self._process_mission_result_server()
                    else:
                        self._request_next_sabotage_server()
                else:
                    self.server.send_to_client(player_id, { # type: ignore
                        "type": MSG_TYPE_LOG_MESSAGE,
                        "text": "Você não está nesta missão ou sua escolha não é válida."
                    })


    # --- Lógica de Jogo do Servidor (executada em thread separada ou sequencialmente) ---
    def _run_game_logic_server(self):
        """Thread que orquestra o fluxo do jogo no servidor."""
        with self._current_phase_lock: # Garante que apenas uma instância de lógica de jogo roda
            self.model.reset_game() # type: ignore
            roles = self.model.assign_roles() # type: ignore
            self.players = [Player(i, roles[i]) for i in range(1, self.model.num_players + 1)] # type: ignore
            
            # Envia o estado inicial do jogo para todos os clientes
            self.server.send_to_all_clients({ # type: ignore
                "type": MSG_TYPE_GAME_STATE_UPDATE,
                "state": self.model.get_game_state_for_client() # type: ignore
            })
            # Opcional: enviar papéis específicos para cada cliente (se o state_update não for suficiente)
            for player_id, role in roles.items():
                 self.server.send_to_client(player_id, { # type: ignore
                     "type": MSG_TYPE_PLAYER_ROLE,
                     "player_id": player_id,
                     "role": role
                 })

            self.root.after(2000, self._start_new_round_server) # Inicia a primeira rodada após 2s

    def _on_client_connected(self, player_id: int):
        """Callback quando um novo cliente se conecta (apenas servidor)."""
        self.connected_player_ids.append(player_id)
        self.view.write_to_log(f"Jogador {player_id} conectado. Total: {len(self.connected_player_ids)}/{NUM_PLAYERS}")
        
        # Se todos os jogadores estiverem conectados e o jogo não começou, habilita o botão de início.
        if len(self.connected_player_ids) == NUM_PLAYERS and not self.model.game_started: # type: ignore
            self.view.action_button.config(state=tk.NORMAL, text="Iniciar Jogo (Todos Conectados)")
            self.server.send_to_all_clients({ # type: ignore
                "type": MSG_TYPE_LOG_MESSAGE,
                "text": "Todos os jogadores estão conectados. O servidor pode iniciar o jogo!"
            })
        elif self.model.game_started: # type: ignore
             # Se o jogo já começou, envia o estado atual para o novo cliente
             self.server.send_to_client(player_id, { # type: ignore
                 "type": MSG_TYPE_GAME_STATE_UPDATE,
                 "state": self.model.get_game_state_for_client() # type: ignore
             })
             self.server.send_to_client(player_id, { # type: ignore
                 "type": MSG_TYPE_PLAYER_ROLE,
                 "player_id": player_id,
                 "role": self.model.get_player_role(player_id) # type: ignore
             })


    def request_start_game(self):
        """Solicitação para iniciar o jogo (do botão do servidor ou do cliente de reinício)."""
        if self.is_server:
            if self.model.game_started: # type: ignore
                self.view.write_to_log("Jogo já iniciado ou em andamento. Reiniciando...")
                # Lógica de reinício no servidor: para o jogo atual e inicia um novo
                # Isso pode ser complexo. Para simplificar, vou resetar o modelo e notificar clientes.
                # Idealmente, haveria uma fase de "lobby" ou "reset" coordenada.
                self.server.send_to_all_clients({"type": MSG_TYPE_LOG_MESSAGE, "text": "Servidor reiniciando o jogo..."}) # type: ignore
                self.model.reset_game() # type: ignore
                self.view.action_button.config(state=tk.DISABLED, text="Reiniciando...")
                # A lógica de _run_game_logic_server será chamada após o reset
                self._game_logic_thread = threading.Thread(target=self._run_game_logic_server, daemon=True)
                self._game_logic_thread.start()
            elif len(self.connected_player_ids) < NUM_PLAYERS:
                self.view.write_to_log(f"Aguardando {NUM_PLAYERS - len(self.connected_player_ids)} jogadores para iniciar o jogo.")
                return
            else:
                self.view.write_to_log("Servidor iniciando o jogo...")
                self.server.send_to_all_clients({"type": MSG_TYPE_START_GAME}) # type: ignore
                # A lógica de início real (_run_game_logic_server) é chamada pelo handler do servidor
                # para garantir que todos os clientes recebam a mensagem de START_GAME primeiro.
        else: # Cliente quer reiniciar o jogo
            if self.client:
                self.client.send_message({"type": MSG_TYPE_START_GAME}) 
                self.view.write_to_log("Solicitação de reinício enviada ao servidor.")


    def _start_new_round_server(self):
        """Inicia uma nova rodada no servidor."""
        with self._current_phase_lock: # Garante que apenas uma rodada seja processada por vez
            if self.model.is_game_over(): # type: ignore
                self._end_game_server()
                return

            # Atualiza e envia o estado do jogo para todos os clientes
            self.server.send_to_all_clients({ # type: ignore
                "type": MSG_TYPE_GAME_STATE_UPDATE,
                "state": self.model.get_game_state_for_client() # type: ignore
            })
            self.server.send_to_all_clients({ # type: ignore
                "type": MSG_TYPE_LOG_MESSAGE,
                "text": f"\n📢 Rodada {self.model.current_round + 1} — Líder: Jogador {self.model.current_leader_id}" # type: ignore
            })

            # Solicita seleção de time ao líder atual
            leader_id = self.model.current_leader_id # type: ignore
            mission_size = self.model.get_current_mission_size() # type: ignore
            available_ids = list(range(1, self.model.num_players + 1)) # type: ignore

            self.server.send_to_client(leader_id, { # type: ignore
                "type": MSG_TYPE_REQUEST_TEAM_SELECTION,
                "leader_id": leader_id,
                "mission_size": mission_size,
                "available_players_ids": available_ids
            })
            self.view.write_to_log(f"Servidor solicitando seleção de time ao Jogador {leader_id}")

    # --- Server: Gerenciamento de Fases de Jogo ---

    def _start_vote_collection_server(self):
        """Inicia a coleta de votos no servidor, solicitando votos de cada cliente."""
        self._current_player_voting_index_server = 0
        self._request_next_vote_server()

    def _request_next_vote_server(self):
        """Solicita o voto do próximo jogador no servidor."""
        with self._current_phase_lock: # Proteger a lógica de avanço da fase
            if self._current_player_voting_index_server < self.model.num_players: # type: ignore
                player_id_to_vote = self.players[self._current_player_voting_index_server].player_id
                self.server.send_to_client(player_id_to_vote, { # type: ignore
                    "type": MSG_TYPE_REQUEST_VOTE,
                    "player_id": player_id_to_vote,
                    "team": self.model.proposed_team # type: ignore
                })
                # Não incrementa o índice aqui. Ele é incrementado APÓS o cliente enviar o voto
                # no _handle_vote_cast e chamarmos _request_next_vote_server novamente.
            else:
                # Todos os votos foram solicitados, agora o servidor aguarda os retornos via _handle_vote_cast
                pass # O processamento final é feito em _process_all_votes_server após todos os votos serem recebidos

    def _process_all_votes_server(self):
        """Processa os votos coletados no servidor e decide a aprovação do time."""
        with self._current_phase_lock:
            team_approved = self.model.process_team_vote() # type: ignore
            self.server.send_to_all_clients({ # type: ignore
                "type": MSG_TYPE_GAME_STATE_UPDATE,
                "state": self.model.get_game_state_for_client() # type: ignore
            })

            if team_approved:
                self.server.send_to_all_clients({ # type: ignore
                    "type": MSG_TYPE_LOG_MESSAGE,
                    "text": "✅ Time aprovado! Iniciando missão..."
                })
                self._current_player_sabotaging_index_server = 0
                self._request_next_sabotage_server()
            else:
                self.server.send_to_all_clients({ # type: ignore
                    "type": MSG_TYPE_LOG_MESSAGE,
                    "text": "❌ Time rejeitado. Novo líder será escolhido."
                })
                self._advance_leader_and_round_server()

    def _request_next_sabotage_server(self):
        """Solicita a escolha de sabotagem do próximo membro do time no servidor."""
        with self._current_phase_lock: # Proteger a lógica de avanço da fase
            if self.model.proposed_team and self._current_player_sabotaging_index_server < len(self.model.proposed_team): # type: ignore
                player_id_on_mission = self.model.proposed_team[self._current_player_sabotaging_index_server] # type: ignore
                player_obj = next((p for p in self.players if p.player_id == player_id_on_mission), None)

                if player_obj and player_obj.is_spy:
                    self.server.send_to_client(player_id_on_mission, { # type: ignore
                        "type": MSG_TYPE_REQUEST_SABOTAGE,
                        "player_id": player_id_on_mission
                    })
                elif player_obj: # É um jogador da Resistência na missão
                    self.server.send_to_all_clients({ # type: ignore
                        "type": MSG_TYPE_LOG_MESSAGE,
                        "text": f"🛡 Jogador {player_id_on_mission} (Resistência) não pode sabotar."
                    })
                    # Auto-registra o "não sabotar" para resistência e avança
                    self.model.record_sabotage(False) # type: ignore
                    self._current_player_sabotaging_index_server += 1
                    self.root.after(100, self._request_next_sabotage_server) # Chama o próximo membro da missão
                else: # Jogador não encontrado (erro)
                    self.view.write_to_log(f"Erro: Jogador {player_id_on_mission} não encontrado para sabotagem.")
                    self._current_player_sabotaging_index_server += 1 # Tenta avançar para não travar
                    self.root.after(100, self._request_next_sabotage_server)

            else:
                # Todos os membros da missão foram processados
                self._process_mission_result_server()

    def _process_mission_result_server(self):
        """Processa o resultado final da missão e atualiza o Model no servidor."""
        with self._current_phase_lock:
            mission_success = self.model.process_mission_outcome() # type: ignore
            sabotages_count = self.model.mission_sabotages # type: ignore
            
            if mission_success:
                self.server.send_to_all_clients({ # type: ignore
                    "type": MSG_TYPE_LOG_MESSAGE,
                    "text": "🎉 Missão bem-sucedida!"
                })
            else:
                self.server.send_to_all_clients({ # type: ignore
                    "type": MSG_TYPE_LOG_MESSAGE,
                    "text": f"💥 Missão FALHOU com {sabotages_count} sabotagem(ns)!"
                })

            self.server.send_to_all_clients({ # type: ignore
                "type": MSG_TYPE_GAME_STATE_UPDATE,
                "state": self.model.get_game_state_for_client() # type: ignore
            })
            self._advance_leader_and_round_server()

    def _advance_leader_and_round_server(self):
        """Avança o líder e a rodada, ou encerra o jogo no servidor."""
        self.model.advance_leader() # type: ignore
        self.root.after(1000, self._start_new_round_server)

    def _end_game_server(self):
        """Finaliza o jogo e envia o vencedor para todos os clientes."""
        winner = self.model.get_game_winner() # type: ignore
        results_display = [("✅" if r else "❌") for r in self.model.mission_results] # type: ignore
        self.server.send_to_all_clients({ # type: ignore
            "type": MSG_TYPE_LOG_MESSAGE,
            "text": f"\n🏁 FIM DE JOGO\n📜 Resultados das Missões: {', '.join(results_display)}"
        })
        self.server.send_to_all_clients({ # type: ignore
            "type": MSG_TYPE_GAME_OVER,
            "winner": winner
        })
        self.view.action_button.config(state=tk.NORMAL, text="Reiniciar Servidor") 
        self.model.game_started = False # type: ignore
        self.update_view_from_model() # Atualiza o estado da view do servidor

    # --- Cliente: Lógica para responder a requisições do servidor ---

    def _handle_request_team_selection(self, message: Dict[str, Any]):
        """Handler para solicitação de seleção de time (apenas cliente, se for o líder)."""
        if not self.is_server and self.local_player_id == message.get("leader_id"):
            leader_id = message.get("leader_id")
            mission_size = message.get("mission_size")
            available_players_ids = message.get("available_players_ids")
            
            self.view.show_team_selection_dialog(
                leader_id=leader_id,
                mission_size=mission_size,
                available_players_ids=available_players_ids,
                callback=self._on_team_selected_client_callback
            )
        else:
            self.view.write_to_log(f"Líder atual é Jogador {message.get('leader_id')}. Aguardando seleção de time...")


    def _on_team_selected_client_callback(self, team_ids: List[int]):
        """Callback do cliente quando o líder local seleciona um time."""
        if self.client and self.local_player_id:
            self.client.send_message({ # type: ignore
                "type": MSG_TYPE_TEAM_PROPOSED,
                "player_id": self.local_player_id,
                "team": team_ids
            })
            self.view.write_to_log("Time proposto enviado ao servidor.")
        
    def _handle_request_vote(self, message: Dict[str, Any]):
        """Handler para solicitação de voto (apenas cliente)."""
        if not self.is_server and self.local_player_id == message.get("player_id"):
            team = message.get("team")
            self.view.show_vote_dialog(
                player_id=self.local_player_id, # type: ignore
                team=team, # type: ignore
                callback=self._on_vote_cast_client_callback
            )
        else:
            self.view.write_to_log(f"Aguardando voto do Jogador {message.get('player_id')}...")

    def _on_vote_cast_client_callback(self, vote_choice: bool):
        """Callback do cliente quando um jogador local vota."""
        if self.client and self.local_player_id:
            self.client.send_message({ # type: ignore
                "type": MSG_TYPE_VOTE_CAST,
                "player_id": self.local_player_id,
                "vote_choice": vote_choice
            })
            self.view.write_to_log("Voto enviado ao servidor.")

    def _handle_request_sabotage(self, message: Dict[str, Any]):
        """Handler para solicitação de sabotagem (apenas cliente)."""
        if not self.is_server and self.local_player_id == message.get("player_id"):
            # Apenas espiões devem ser capazes de sabotar via diálogo interativo.
            if self.local_player_role == "Espião":
                self.view.show_sabotage_dialog(
                    player_id=self.local_player_id, # type: ignore
                    callback=self._on_sabotage_choice_client_callback
                )
            else:
                # Se não é espião, não pode sabotar. Envia False automaticamente.
                self.view.write_to_log("Você é Resistência, não pode sabotar. Enviando 'Não' ao servidor.")
                self._on_sabotage_choice_client_callback(False)
        else:
            self.view.write_to_log(f"Aguardando escolha de sabotagem do Jogador {message.get('player_id')}...")


    def _on_sabotage_choice_client_callback(self, sabotage_choice: bool):
        """Callback do cliente quando um jogador local decide sabotar."""
        if self.client and self.local_player_id:
            self.client.send_message({ # type: ignore
                "type": MSG_TYPE_SABOTAGE_CHOICE,
                "player_id": self.local_player_id,
                "sabotage_choice": sabotage_choice
            })
            self.view.write_to_log("Escolha de sabotagem enviada ao servidor.")

    def _handle_game_over(self, message: Dict[str, Any]):
        """Handler para fim de jogo (apenas cliente)."""
        if not self.is_server:
            winner = message.get("winner")
            self.view.show_game_over_dialog(winner)
            self.view.write_to_log(f"Fim de Jogo! Vencedor: {winner}")
            self.view.action_button.config(state=tk.NORMAL, text="🔄 Jogar Novamente")