# --- resistance_game/model.py ---
# Contém a lógica de negócio central e o estado do jogo.
# Este módulo é exclusivo do servidor em uma configuração LAN.

import random
from typing import List, Dict, Any, Callable, Optional

class GameModel:
    """
    O Modelo do jogo "A Resistência". Gerencia o estado do jogo e as regras de negócio.
    É completamente independente da interface do usuário (View) e do controlador (Controller).
    Em um jogo LAN, este Model reside **apenas no servidor**.
    """
    def __init__(self, num_players: int, num_spies: int, mission_sizes: List[int]):
        self.num_players: int = num_players
        self.num_spies: int = num_spies
        self.mission_sizes: List[int] = mission_sizes

        self.players_roles: Dict[int, str] = {} # {player_id: role}
        self.current_leader_id: int = 1
        self.current_round: int = 0
        self.successful_missions: int = 0
        self.failed_missions: int = 0
        self.mission_results: List[bool] = [] # True para sucesso, False para falha
        self.model_state_changed_callback: Optional[Callable[[], None]] = None # Callback para o Controller do servidor

        self.proposed_team: Optional[List[int]] = None
        self.team_votes: List[bool] = []
        self.mission_sabotages: int = 0
        self.game_started: bool = False # Novo estado para indicar se o jogo já começou

    def set_state_changed_callback(self, callback: Callable[[], None]):
        """Define um callback a ser chamado quando o estado do modelo muda."""
        self.model_state_changed_callback = callback

    def _notify_state_change(self):
        """Notifica o Controller do servidor sobre uma mudança no estado do Modelo."""
        if self.model_state_changed_callback:
            self.model_state_changed_callback()

    def reset_game(self):
        """Reinicia o estado do jogo para um novo início."""
        self.players_roles = {}
        self.current_leader_id = 1
        self.current_round = 0
        self.successful_missions = 0
        self.failed_missions = 0
        self.mission_results = []
        self.proposed_team = None
        self.team_votes = []
        self.mission_sabotages = 0
        self.game_started = False
        self._notify_state_change()

    def assign_roles(self) -> Dict[int, str]:
        """Sorteia e atribui os papéis (Resistência ou Espião) aos jogadores."""
        roles_pool = ['Espião'] * self.num_spies + ['Resistência'] * (self.num_players - self.num_spies)
        random.shuffle(roles_pool)
        # Converte o ID para string para consistência na serialização JSON e em dicts que vêm da rede
        self.players_roles = {i + 1: roles_pool[i] for i in range(self.num_players)}
        self.game_started = True # Marca o jogo como iniciado após atribuição de papéis
        self._notify_state_change()
        return self.players_roles

    def get_player_role(self, player_id: int) -> str:
        """Retorna o papel de um jogador dado seu ID."""
        return self.players_roles.get(player_id, "Desconhecido") # Assume player_id é int

    def get_current_mission_size(self) -> int:
        """Retorna o tamanho da missão para a rodada atual."""
        if self.current_round < len(self.mission_sizes):
            return self.mission_sizes[self.current_round]
        raise IndexError("Tentativa de acessar tamanho de missão além do número de rodadas definidas.")

    def set_proposed_team(self, team_ids: List[int]):
        """Define o time proposto para a missão atual."""
        self.proposed_team = team_ids
        self._notify_state_change()

    def record_vote(self, vote_choice: bool):
        """Registra um voto para a aprovação do time."""
        self.team_votes.append(vote_choice)
        self._notify_state_change()

    def process_team_vote(self) -> bool:
        """Processa os votos do time proposto e limpa os votos registrados."""
        approved_votes = self.team_votes.count(True)
        is_approved = approved_votes > self.num_players // 2
        self.team_votes = [] # Limpa votos para a próxima fase/rodada
        self._notify_state_change()
        return is_approved

    def record_sabotage(self, sabotaged: bool):
        """Registra uma sabotagem para a missão atual."""
        if sabotaged:
            self.mission_sabotages += 1
        self._notify_state_change()

    def process_mission_outcome(self) -> bool:
        """Processa o resultado da missão e atualiza os contadores de sucesso/falha."""
        mission_success = (self.mission_sabotages == 0)
        if mission_success:
            self.successful_missions += 1
        else:
            self.failed_missions += 1
        self.mission_results.append(mission_success)
        self.current_round += 1
        self.mission_sabotages = 0 # Reinicia para a próxima missão
        self._notify_state_change()
        return mission_success

    def advance_leader(self):
        """Move o líder para o próximo jogador."""
        self.current_leader_id = (self.current_leader_id % self.num_players) + 1
        self._notify_state_change()

    def is_game_over(self) -> bool:
        """Verifica se as condições de fim de jogo foram atingidas."""
        return self.successful_missions >= 3 or self.failed_missions >= 3

    def get_game_winner(self) -> str:
        """Determina o vencedor do jogo."""
        if self.successful_missions >= 3:
            return "Resistência"
        elif self.failed_missions >= 3:
            return "Espiões"
        return "Empate"

    def get_game_state_for_client(self) -> Dict[str, Any]:
        """Retorna uma representação serializável do estado atual do jogo para um cliente."""
        # Garante que os IDs dos jogadores em players_roles sejam strings para serialização JSON
        serializable_players_roles = {str(k): v for k, v in self.players_roles.items()}

        return {
            'num_players': self.num_players,
            'current_round': self.current_round,
            'mission_sizes': self.mission_sizes,
            'successful_missions': self.successful_missions,
            'failed_missions': self.failed_missions,
            'current_leader_id': self.current_leader_id,
            'mission_results': self.mission_results,
            'is_game_over': self.is_game_over(),
            'game_started': self.game_started,
            'proposed_team': self.proposed_team,
            'players_roles': serializable_players_roles # Enviado para clientes no início para que saibam os IDs
        }