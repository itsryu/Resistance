# src/models/model.py
import random
from typing import List, Dict, Any, Callable, Optional

class Player:
    def __init__(self, player_id: int, role: str):
        self.player_id = player_id
        self.role = role # "Resistência" ou "Espião"
        self.is_spy = (role == "Espião")

    def to_dict(self):
        return {"player_id": self.player_id, "role": self.role}

    @staticmethod
    def from_dict(data: Dict[str, Any]):
        return Player(data["player_id"], data["role"])

class GameModel:
    def __init__(self, num_players: int, num_spies: int, mission_sizes: List[int]):
        self.num_players: int = num_players
        self.num_spies: int = num_spies
        self.mission_sizes: List[int] = mission_sizes
        self.player_ids: List[int] = list(range(1, num_players + 1)) # Lista de IDs dos jogadores

        self.game_started: bool = False
        self.players_roles: Dict[int, str] = {} # { 1: "Resistencia", 2: "Espiao" }
        self.resistance_wins: int = 0
        self.spy_wins: int = 0
        self.current_round: int = 0
        self.current_leader_index: int = 0 # Novo atributo para controlar o índice do líder
        self.current_leader_id: int = self.player_ids[self.current_leader_index] # Inicializa com o primeiro jogador
        self.current_mission_failures_count: int = 0 # Contador de falhas de aprovação de equipe
        self.mission_results: List[bool] = [] # True para sucesso, False para falha
        self.mission_sabotages: int = 0 # Sabotagens na missão atual

        self.proposed_team: Optional[List[int]] = None
        self.team_votes: Dict[int, bool] = {} # player_id -> vote_choice (True/False)
        self.sabotage_choices: Dict[int, bool] = {} # player_id -> sabotage_choice (True/False)

        self._state_changed_callback: Optional[Callable[[], None]] = None

    def set_state_changed_callback(self, callback: Callable[[], None]):
        """Define um callback a ser chamado quando o estado do modelo muda."""
        self._state_changed_callback = callback

    def _notify_state_change(self):
        """Notifica o Controller do servidor sobre uma mudança no estado do Modelo."""
        if self._state_changed_callback:
            self._state_changed_callback()

    def reset_game(self):
        """Reinicia o estado do jogo para um novo início."""
        self.game_started = True
        self.resistance_wins = 0
        self.spy_wins = 0
        self.current_round = 0
        self.current_leader_index = 0 # Reinicia o índice do líder
        self.current_leader_id = self.player_ids[self.current_leader_index]
        self.current_mission_failures_count = 0
        self.mission_results = []
        self.mission_sabotages = 0
        self.proposed_team = None
        self.team_votes = {} # Resetar para dicionário
        self.sabotage_choices = {} # Resetar para dicionário
        self.players_roles = {}
        self._notify_state_change()

    def assign_roles(self) -> Dict[int, str]:
        """Sorteia e atribui os papéis (Resistência ou Espião) aos jogadores."""
        roles_pool = ['Espião'] * self.num_spies + ['Resistência'] * (self.num_players - self.num_spies)
        random.shuffle(roles_pool)
        self.players_roles = {i + 1: roles_pool[i] for i in range(self.num_players)}
        self.game_started = True
        self._notify_state_change()
        return self.players_roles

    def get_player_role(self, player_id: int) -> str:
        """Retorna o papel de um jogador dado seu ID."""
        return self.players_roles.get(player_id, "Desconhecido")

    def get_current_mission_size(self) -> int:
        """Retorna o tamanho da missão para a rodada atual."""
        if 0 <= self.current_round < len(self.mission_sizes):
            return self.mission_sizes[self.current_round]
        return 0 # Valor padrão em caso de rodada inválida ou raise IndexError conforme necessidade

    def set_proposed_team(self, team_ids: List[int]):
        """Define o time proposto para a missão atual."""
        self.proposed_team = team_ids
        self.team_votes = {} # Reseta votos para a nova proposta (dicionário)
        self.current_mission_failures_count += 1 # Incrementa falhas de aprovação de equipe
        self._notify_state_change()

    def record_vote(self, player_id: int, vote_choice: bool):
        """Registra um voto para a aprovação do time, associado ao player_id."""
        self.team_votes[player_id] = vote_choice
        self._notify_state_change()

    def process_team_vote(self) -> bool:
        """Processa os votos do time proposto e limpa os votos registrados."""
        approved_votes = sum(1 for vote in self.team_votes.values() if vote)
        rejected_votes = sum(1 for vote in self.team_votes.values() if not vote)

        team_approved = approved_votes > rejected_votes
        
        # Se a equipe for aprovada, resetamos o contador de falhas de aprovação
        if team_approved:
            self.current_mission_failures_count = 0
        
        self.team_votes = {} # Limpar os votos após o processamento
        self._notify_state_change()
        return team_approved

    def record_sabotage(self, player_id: int, sabotaged: bool):
        """Registra uma sabotagem para a missão atual, associado ao player_id."""
        self.sabotage_choices[player_id] = sabotaged
        self._notify_state_change()

    def process_mission_outcome(self) -> bool:
        """Processa o resultado da missão e atualiza os contadores de sucesso/falha."""
        num_sabotages = sum(1 for choice in self.sabotage_choices.values() if choice)
        
        # Regra de 2 falhas para missão 4 e 5 em 7+ jogadores
        required_sabotages_for_failure = 2 if self.num_players >= 7 and self.current_round in [3, 4] else 1 
        
        mission_succeeded = num_sabotages < required_sabotages_for_failure
        
        self.mission_results.append(mission_succeeded)
        self.mission_sabotages = num_sabotages # Armazena o número de sabotagens para exibição

        if mission_succeeded:
            self.resistance_wins += 1
        else:
            self.spy_wins += 1
        
        # Avança para a próxima rodada somente se a missão foi concluída
        self.current_round += 1

        # Reseta escolhas de sabotagem e equipe proposta para a próxima rodada/tentativa de equipe
        self.sabotage_choices = {}
        self.proposed_team = None
        # team_votes já é resetado em process_team_vote()

        self._notify_state_change()
        return mission_succeeded

    def advance_leader(self):
        """Avança o líder para o próximo jogador, ciclicamente."""
        self.current_leader_index = (self.current_leader_index + 1) % self.num_players
        self.current_leader_id = self.player_ids[self.current_leader_index]
        self._notify_state_change()

    def is_game_over(self) -> bool:
        """Verifica se as condições de fim de jogo foram atingidas."""
        # Se 5 equipes forem rejeitadas em sequência, espiões vencem
        if self.current_mission_failures_count >= 5:
            return True
        return self.resistance_wins >= 3 or self.spy_wins >= 3

    def get_game_winner(self) -> Optional[str]:
        """Determina o vencedor do jogo."""
        if self.resistance_wins >= 3:
            return "Resistência"
        elif self.spy_wins >= 3:
            return "Espiões"
        elif self.current_mission_failures_count >= 5: # 5ª equipe rejeitada, espiões vencem
            return "Espiões (5 equipes rejeitadas)"
        return None

    def get_game_state_for_client(self) -> Dict[str, Any]:
        """Retorna uma representação serializável do estado atual do jogo para um cliente."""
        # Converta as chaves inteiras para strings, pois JSON usa strings para chaves de dicionário
        serializable_players_roles = {str(k): v for k, v in self.players_roles.items()}

        return {
            'num_players': self.num_players,
            'current_round': self.current_round,
            'mission_sizes': self.mission_sizes,
            'resistance_wins': self.resistance_wins, # Alterado para resistance_wins
            'spy_wins': self.spy_wins, # Alterado para spy_wins
            'current_leader_id': self.current_leader_id,
            'mission_results': self.mission_results,
            'is_game_over': self.is_game_over(),
            'game_started': self.game_started,
            'proposed_team': self.proposed_team,
            'mission_sabotages': self.mission_sabotages, # Adicionado para exibir sabotagens
            'current_mission_failures_count': self.current_mission_failures_count, # Adicionado para clientes
            'winner': self.get_game_winner() # Adicionado para clientes
        }

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializa o estado do GameModel para um dicionário Python.
        Isso permite salvar o estado em formatos como JSON.
        """
        return {
            "num_players": self.num_players,
            "num_spies": self.num_spies,
            "mission_sizes": self.mission_sizes,
            "players_roles": {str(k): v for k, v in self.players_roles.items()}, # Converta int keys para str
            "current_leader_index": self.current_leader_index,
            "current_leader_id": self.current_leader_id,
            "current_round": self.current_round,
            "resistance_wins": self.resistance_wins,
            "spy_wins": self.spy_wins,
            "mission_results": self.mission_results,
            "proposed_team": self.proposed_team,
            "team_votes": self.team_votes, # Dicionário de player_id -> voto
            "sabotage_choices": self.sabotage_choices, # Dicionário de player_id -> sabotagem
            "mission_sabotages": self.mission_sabotages,
            "game_started": self.game_started,
            "current_mission_failures_count": self.current_mission_failures_count
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GameModel':
        """
        Cria uma nova instância de GameModel a partir de um dicionário de estado.
        Usado para carregar o estado salvo.
        """
        # Tratar casos onde chaves podem não existir (novos atributos em salvamentos antigos)
        num_players = data.get("num_players", 5) # Default para evitar KeyError
        num_spies = data.get("num_spies", 2)
        mission_sizes = data.get("mission_sizes", [2, 3, 2, 3, 3])

        model = cls(num_players=num_players, num_spies=num_spies, mission_sizes=mission_sizes)

        model.players_roles = {int(k): v for k, v in data.get("players_roles", {}).items()}
        model.current_leader_index = data.get("current_leader_index", 0)
        model.current_leader_id = data.get("current_leader_id", model.player_ids[model.current_leader_index] if model.player_ids else 1)
        model.current_round = data.get("current_round", 0)
        model.resistance_wins = data.get("resistance_wins", 0)
        model.spy_wins = data.get("spy_wins", 0)
        model.mission_results = data.get("mission_results", [])
        model.proposed_team = data.get("proposed_team")
        model.team_votes = data.get("team_votes", {}) # Carrega como dicionário
        model.sabotage_choices = data.get("sabotage_choices", {}) # Carrega como dicionário
        model.mission_sabotages = data.get("mission_sabotages", 0)
        model.game_started = data.get("game_started", False)
        model.current_mission_failures_count = data.get("current_mission_failures_count", 0)
        return model