import tkinter as tk
from tkinter import messagebox
from typing import List, Callable, Optional, Dict, Any
from src.utils.settings import BG_DARK, BG_MEDIUM, TEXT_PRIMARY, TEXT_ACCENT, FONT_TITLE, FONT_DEFAULT, FONT_LOG, BUTTON_BG, BUTTON_FG, NUM_PLAYERS, MISSION_SIZES
from src.models.dialogs import TeamSelectionDialog, YesNoDialog # Importa os diálogos para uso na View

class GameView:
    """
    A View do jogo "A Resistência". É responsável por exibir a interface gráfica
    e por solicitar entrada do usuário. Ela notifica o Controller sobre interações do usuário.
    Em um jogo LAN, esta View é exclusiva do cliente.
    """
    def __init__(self, root: tk.Tk):
        self.root: tk.Tk = root
        self.root.title("🎲 Jogo da Resistência")
        self.root.configure(bg=BG_DARK)
        self.root.geometry("800x700")

        self.controller: Optional['GameController'] = None # Referência ao Controller
        self.game_state_data: Dict[str, Any] = {} # Dados do Model para exibir
        self.local_player_id: Optional[int] = None # ID do jogador local, atribuído pelo servidor
        self.local_player_role: Optional[str] = None # Papel do jogador local

        self._initialize_ui_components()

    def set_controller(self, controller: 'GameController'):
        """Define o Controller associado a esta View."""
        self.controller = controller

    def set_local_player_info(self, player_id: int, role: str):
        """Define o ID e papel do jogador local."""
        self.local_player_id = player_id
        self.local_player_role = role
        self.root.title(f"🎲 Jogo da Resistência - Jogador {self.local_player_id}")
        self.write_to_log(f"Seu ID de Jogador: {self.local_player_id}")
        role_str = "🕵️‍♂️ ESPIÃO" if self.local_player_role == "Espião" else "🛡 RESISTÊNCIA"
        self.write_to_log(f"Seu Papel: {role_str}")


    def _initialize_ui_components(self):
        """Cria e organiza todos os widgets da interface."""
        self.title_label = tk.Label(self.root, text="Jogo da Resistência", font=FONT_TITLE, fg=TEXT_ACCENT, bg=BG_DARK)
        self.title_label.pack(pady=10)

        # Frame para exibir o status do jogo (rodada, sucessos, falhas)
        self.status_frame = tk.Frame(self.root, bg=BG_MEDIUM, padx=10, pady=5, relief="groove", bd=2)
        self.status_frame.pack(pady=10, fill=tk.X, padx=20)

        self.round_label = tk.Label(self.status_frame, text="Rodada: 0/5", font=FONT_DEFAULT, fg=TEXT_PRIMARY, bg=BG_MEDIUM)
        self.round_label.pack(side=tk.LEFT, padx=10)

        self.success_label = tk.Label(self.status_frame, text="✅ Sucessos: 0", font=FONT_DEFAULT, fg=TEXT_PRIMARY, bg=BG_MEDIUM)
        self.success_label.pack(side=tk.LEFT, padx=10)

        self.fail_label = tk.Label(self.status_frame, text="❌ Falhas: 0", font=FONT_DEFAULT, fg=TEXT_PRIMARY, bg=BG_MEDIUM)
        self.fail_label.pack(side=tk.LEFT, padx=10)

        self.current_leader_label = tk.Label(self.status_frame, text="Líder Atual: N/A", font=FONT_DEFAULT, fg=TEXT_ACCENT, bg=BG_MEDIUM)
        self.current_leader_label.pack(side=tk.RIGHT, padx=10)


        self.log_text = tk.Text(self.root, width=80, height=20, bg=BG_MEDIUM, fg=TEXT_PRIMARY, font=FONT_LOG,
                                relief="flat", bd=0, padx=10, pady=10)
        self.log_text.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED) # Torna o log somente leitura

        # Botão de iniciar/conectar. Sua função depende do modo (servidor/cliente)
        # e é controlada pelo Controller.
        self.action_button = tk.Button(self.root, text="Aguardando Conexão...", font=("Helvetica", 16, "bold"),
                                   bg=BUTTON_BG, fg=BUTTON_FG, relief="flat", state=tk.DISABLED)
        self.action_button.pack(pady=15, ipadx=20, ipady=10)

        self.update_view({}) # Inicializa a View

    def write_to_log(self, text: str):
        """Escreve uma mensagem no log da interface."""
        self.log_text.config(state=tk.NORMAL) # Habilita escrita
        self.log_text.insert(tk.END, text + "\n")
        self.log_text.see(tk.END) # Rola para o final
        self.log_text.config(state=tk.DISABLED) # Desabilita escrita novamente

    def update_view(self, game_state: Dict[str, Any]):
        """
        Atualiza a View com o estado mais recente do Modelo recebido do servidor.
        """
        self.game_state_data = game_state

        # Atualiza labels de status
        current_round = self.game_state_data.get('current_round', 0)
        mission_sizes = self.game_state_data.get('mission_sizes', MISSION_SIZES)
        self.round_label.config(text=f"Rodada: {current_round + 1}/{len(mission_sizes)}")
        self.success_label.config(text=f"✅ Sucessos: {self.game_state_data.get('successful_missions', 0)}")
        self.fail_label.config(text=f"❌ Falhas: {self.game_state_data.get('failed_missions', 0)}")
        leader_id = self.game_state_data.get('current_leader_id', 'N/A')
        self.current_leader_label.config(text=f"Líder Atual: Jogador {leader_id}")

        is_game_over = self.game_state_data.get('is_game_over', False)
        game_started = self.game_state_data.get('game_started', False)

        if is_game_over:
            self.action_button.config(state=tk.NORMAL, text="🔄 Jogar Novamente")
            self.action_button.config(command=self.controller.request_start_game) # Permite ao Controller resetar
        elif game_started:
            self.action_button.config(state=tk.DISABLED, text="Jogo em Andamento...")
        else: # Jogo não começou, aguardando jogadores
             self.action_button.config(state=tk.DISABLED, text="Aguardando Outros Jogadores...")


    # --- Métodos que interagem com o Controller para obter input do usuário ---
    def show_team_selection_dialog(self, leader_id: int, mission_size: int,
                                   available_players_ids: List[int], callback: Callable[[List[int]], None]):
        """Exibe o diálogo de seleção de time e espera pelo input do líder local."""
        TeamSelectionDialog(self.root, leader_id, mission_size, available_players_ids, callback)

    def show_vote_dialog(self, player_id: int, team: List[int], callback: Callable[[bool], None]):
        """Exibe o diálogo de votação para o jogador local."""
        YesNoDialog(self.root, player_id, f"Você aprova o time {team}?", callback)

    def show_sabotage_dialog(self, player_id: int, callback: Callable[[bool], None]):
        """Exibe o diálogo de sabotagem para o jogador espião local."""
        YesNoDialog(self.root, player_id, "Você quer SABOTAR a missão?", callback)

    def show_game_over_dialog(self, winner: str):
        """Exibe o diálogo final de fim de jogo."""
        if winner == "Resistência":
            messagebox.showinfo("Fim de Jogo", "🏆 A RESISTÊNCIA VENCEU!")
        elif winner == "Espiões":
            messagebox.showinfo("Fim de Jogo", "🕵️‍♂️ OS ESPIÕES VENCERAM!")
        else:
            messagebox.showinfo("Fim de Jogo", "⚖️ EMPATE - Sem vencedor claro")