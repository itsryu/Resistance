# --- resistance_game/main.py ---
# Ponto de entrada da aplicação. Inicializa as camadas MVC e inicia o loop principal.

import tkinter as tk
import sys
# Importações relativas para os módulos do jogo
from src.views.view import GameView
from src.models.model import GameModel
from src.controllers.controller import GameController
from src.utils.network import GameServer, GameClient # Para acesso no on_closing

def start_application():
    root = tk.Tk()
    
    # Prompt de escolha de modo (Servidor/Cliente)
    mode_selection_dialog = tk.Toplevel(root)
    mode_selection_dialog.title("Escolha o Modo de Jogo")
    mode_selection_dialog.configure(bg="#1a1a1a", padx=30, pady=30)
    mode_selection_dialog.transient(root)
    mode_selection_dialog.grab_set()
    mode_selection_dialog.resizable(False, False)

    tk.Label(mode_selection_dialog, text="Você quer ser o Servidor ou um Cliente?", 
             font=("Helvetica", 16, "bold"), fg="#00bfff", bg="#1a1a1a").pack(pady=20)

    is_server_choice = [False] # Usar lista para que o valor possa ser modificado por lambda

    def select_mode(is_server: bool):
        is_server_choice[0] = is_server
        mode_selection_dialog.destroy()
        # Não precisa grab_release aqui, destroy já faz isso automaticamente para Toplevel.

    server_button = tk.Button(mode_selection_dialog, text="🚀 Servidor", 
                              font=("Helvetica", 14), bg="#28a745", fg="white", 
                              relief="flat", command=lambda: select_mode(True))
    server_button.pack(side=tk.LEFT, padx=15, ipadx=10, ipady=8)

    client_button = tk.Button(mode_selection_dialog, text="💻 Cliente", 
                              font=("Helvetica", 14), bg="#007bff", fg="white", 
                              relief="flat", command=lambda: select_mode(False))
    client_button.pack(side=tk.RIGHT, padx=15, ipadx=10, ipady=8)

    # Espera até o usuário escolher o modo
    root.wait_window(mode_selection_dialog)

    # Agora que o modo foi escolhido, inicia o Controller
    controller = GameController(root, is_server_choice[0])
    
    # Define o protocolo de fechamento para garantir que as threads de rede parem
    root.protocol("WM_DELETE_WINDOW", lambda: on_closing(controller, root)) 

    root.mainloop()

def on_closing(controller: GameController, root: tk.Tk):
    """Lida com o fechamento da janela, garantindo que as threads de rede sejam paradas."""
    print("Fechando aplicação...")
    if controller.is_server and controller.server:
        controller.server.stop()
        print("Servidor de rede parado.")
    elif not controller.is_server and controller.client:
        controller.client.stop()
        print("Cliente de rede parado.")
    root.destroy()
    sys.exit(0) # Garante que todas as threads em background sejam encerradas

if __name__ == '__main__':
    start_application()