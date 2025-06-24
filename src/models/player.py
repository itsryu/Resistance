# --- resistance_game/player.py ---
# Define a entidade Jogador, que representa um participante no jogo.

import threading
from typing import TYPE_CHECKING, Optional

# Importação para type-hinting, evita circular dependency em tempo de execução
if TYPE_CHECKING:
    from src.views.view import GameView 
    # from .controller import GameController # Pode ser necessário se Player precisar de Controller


class Player(threading.Thread):
    """
    Representa um jogador individual no jogo.
    Herda de threading.Thread. Em um ambiente LAN, esta thread
    pode ser usada para lógica de IA ou para gerenciar a comunicação
    específica de um jogador com o servidor (embora a comunicação
    geral seja feita pelo Controller/Network classes).
    """
    def __init__(self, player_id: int, role: str):
        super().__init__()
        self.player_id: int = player_id
        self.role: str = role
        self.is_spy: bool = (role == "Espião")
        # A referência à View aqui é mais conceitual para IA,
        # para players humanos, a View é gerenciada pelo Controller.
        self._view_reference: Optional['GameView'] = None 
        # self._controller_reference: Optional['GameController'] = None # Se Player precisar notificar Controller

    def set_view_reference(self, view: 'GameView'):
        """Define a referência da View para este jogador, usada para interações GUI."""
        self._view_reference = view

    # def set_controller_reference(self, controller: 'GameController'):
    #     """Define a referência do Controller para este jogador."""
    #     self._controller_reference = controller

    def run(self):
        """
        Método executado pela thread do jogador.
        Para jogadores humanos em um jogo LAN, esta thread pode permanecer inativa,
        pois as interações são controladas pelo Controller via callbacks da GUI.
        Se houvesse IA, a lógica da IA residiria aqui (e se comunicaria via filas).
        """
        pass