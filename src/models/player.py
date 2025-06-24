import threading
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from src.views.view import GameView


class Player(threading.Thread):
    def __init__(self, player_id: int, role: str):
        super().__init__()
        self.player_id: int = player_id
        self.role: str = role
        self.is_spy: bool = (role == "Espião")
        self._view_reference: Optional['GameView'] = None

    def set_view_reference(self, view: 'GameView'):
        self._view_reference = view

    def run(self):
        pass