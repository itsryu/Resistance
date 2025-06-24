# --- resistance_game/game_constants.py ---
# Define constantes e configurações globais do jogo.

import tkinter as tk
from typing import List, Dict, Any, Callable, Optional, Tuple

# Constantes de Estilo para a GUI
BG_DARK = "#1a1a1a"
BG_MEDIUM = "#0d0d0d"
TEXT_PRIMARY = "#00ff99"
TEXT_ACCENT = "#00bfff"
BUTTON_BG = "#00bfff"
BUTTON_FG = "white"
ERROR_COLOR = "#ff4444"
FONT_TITLE = ("Helvetica", 24, "bold")
FONT_DEFAULT = ("Helvetica", 12)
FONT_LOG = ("Courier", 10)
BORDER_RADIUS = 10 # Para simular cantos arredondados em Tkinter, precisaria de Canvas ou ttk.Style

# Configurações do Jogo
NUM_PLAYERS = 5
NUM_SPIES = 2
MISSION_SIZES = [2, 3, 2, 3, 3] # Tamanhos das missões para 5 jogadores

# Configurações de Rede
SERVER_HOST = '127.0.0.1' # Endereço IP do servidor. Use '0.0.0.0' para aceitar de qualquer IP na rede local.
SERVER_PORT = 12345       # Porta do servidor
BUFFER_SIZE = 4096        # Tamanho do buffer para mensagens de rede

# Tipos de Mensagem do Protocolo (mantidos)
MSG_TYPE_CONNECT_ACK = "CONNECT_ACK"
MSG_TYPE_GAME_STATE_UPDATE = "GAME_STATE_UPDATE"
MSG_TYPE_START_GAME = "START_GAME"
MSG_TYPE_PLAYER_ROLE = "PLAYER_ROLE" # Usado para enviar o papel específico a um cliente
MSG_TYPE_REQUEST_TEAM_SELECTION = "REQUEST_TEAM_SELECTION"
MSG_TYPE_TEAM_PROPOSED = "TEAM_PROPOSED" # Cliente -> Servidor
MSG_TYPE_REQUEST_VOTE = "REQUEST_VOTE"
MSG_TYPE_VOTE_CAST = "VOTE_CAST"     # Cliente -> Servidor
MSG_TYPE_REQUEST_SABOTAGE = "REQUEST_SABOTAGE"
MSG_TYPE_SABOTAGE_CHOICE = "SABOTAGE_CHOICE" # Cliente -> Servidor
MSG_TYPE_MISSION_OUTCOME = "MISSION_OUTCOME" # Servidor -> Cliente (para log ou eventos específicos)
MSG_TYPE_GAME_OVER = "GAME_OVER"
MSG_TYPE_LOG_MESSAGE = "LOG_MESSAGE" # Servidor -> Cliente (para mensagens gerais no log)