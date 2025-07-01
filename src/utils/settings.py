from enum import Enum

BG_DARK = "#1a1a1a"          # Fundo principal
BG_MEDIUM = "#2a2a2a"         # Fundo secundários
BG_LIGHT = "#3a3a3a"          # Para detalhes mais claros
BG_MENU = "#0d0d0d"           # Fundo para menus, ainda mais escuro

TEXT_PRIMARY = "#00ff99"      # Verde neon para texto principal
TEXT_ACCENT = "#00bfff"       # Azul ciano para destaques e títulos
BUTTON_BG = "#00bfff"         # Cor de fundo dos botões
BUTTON_FG = "white"           # Cor do texto dos botões
BUTTON_HOVER_BG = "#0099cc"   # Cor do botão ao passar o mouse
ERROR_COLOR = "#ff4444"       # Vermelho para mensagens de erro
BORDER_COLOR = "#00ff99"      # Cor da borda para elementos importantes

FONT_FAMILY = "Consolas"
FONT_SUBTITLE = "Consolas"

FONT_TITLE = (FONT_FAMILY, 30, "bold")      # Títulos
FONT_SUBTITLE = (FONT_FAMILY, 18, "bold")   # Subtítulos
FONT_HEADING = (FONT_FAMILY, 14, "bold")    # Títulos de seção
FONT_DEFAULT = (FONT_FAMILY, 12)            # Texto geral
FONT_LOG = ("Courier New", 10)              # Fonte monoespaçada para logs

BORDER_RADIUS = 5

# Configurações do Jogo
GAME_TITLE = "The Resistance"
NUM_PLAYERS = 5
NUM_SPIES = 2
MISSION_SIZES = [2, 3, 2, 3, 3] # Tamanhos das missões para 5 jogadores

# Configurações de Rede
SERVER_HOST = 'localhost'
SERVER_PORT = 12345
BUFFER_SIZE = 4096

# Caminho do arquivo de salvamento do estado do jogo
SAVE_FILE_PATH = "game_state.json"

# Tipos de Mensagem do Protocolo como Enum
class MessageType(Enum):
    CONNECT_ACK = "CONNECT_ACK"
    GAME_STATE_UPDATE = "GAME_STATE_UPDATE"
    START_GAME = "START_GAME"
    PLAYER_ROLE = "PLAYER_ROLE"
    REQUEST_TEAM_SELECTION = "REQUEST_TEAM_SELECTION"
    TEAM_PROPOSED = "TEAM_PROPOSED"
    REQUEST_VOTE = "REQUEST_VOTE"
    VOTE_CAST = "VOTE_CAST"
    REQUEST_SABOTAGE = "REQUEST_SABOTAGE"
    SABOTAGE_CHOICE = "SABOTAGE_CHOOGE"
    MISSION_OUTCOME = "MISSION_OUTCOME"
    GAME_OVER = "GAME_OVER"
    LOG_MESSAGE = "LOG_MESSAGE"