import tkinter as tk
from tkinter import messagebox, Toplevel, Label, Button
from typing import List, Any, Callable, Optional
from src.utils.settings import BG_DARK, BG_MEDIUM, TEXT_PRIMARY, TEXT_ACCENT, FONT_TITLE, FONT_DEFAULT, BUTTON_BG, BUTTON_FG, BUTTON_HOVER_BG, GAME_TITLE, BORDER_RADIUS, BG_LIGHT, ERROR_COLOR

class CustomDialog(tk.Toplevel):
    """
    Classe base para diálogos personalizados, fornecendo estilos comuns
    e um mecanismo para capturar a resposta.
    """
    def __init__(self, parent: tk.Tk, title: str, message: str):
        super().__init__(parent)
        self.transient(parent)
        self.grab_set()
        self.title(f"{GAME_TITLE} - {title}")
        self.configure(bg=BG_DARK, padx=20, pady=20)
        self.resizable(False, False)

        self.result: Any = None

        Label(self, text=title, font=FONT_TITLE, fg=TEXT_ACCENT, bg=BG_DARK).pack(pady=10)
        Label(self, text=message, font=FONT_DEFAULT, fg=TEXT_PRIMARY, bg=BG_DARK).pack(pady=10)

    def _on_confirm(self):
        """Método de callback padrão para confirmação do diálogo."""
        self.destroy()
        self.grab_release()


class TeamSelectionDialog(CustomDialog):
    """
    Diálogo para o líder selecionar os membros da missão, utilizando botões para seleção.
    """
    def __init__(self, parent: tk.Tk, leader_id: int, mission_size: int,
                 available_players_ids: List[int], callback: Callable[[List[int]], None]):
        super().__init__(parent, f"Seleção de Equipe - Jogador {leader_id}",
                         f"Jogador {leader_id}, clique nos jogadores para selecionar {mission_size} para a missão.")
        self.leader_id = leader_id
        self.mission_size = mission_size
        self.available_players_ids = available_players_ids
        self.callback = callback
        self.selected_team_ids: List[int] = []
        self.player_buttons: Dict[int, tk.Button] = {}

        self._create_player_selection_ui()

        self.selected_count_label = Label(self, text=self._get_selected_count_text(), 
                                          font=FONT_DEFAULT, fg=TEXT_PRIMARY, bg=BG_DARK)
        self.selected_count_label.pack(pady=10)


        confirm_button = Button(self, text="Confirmar Equipe", font=FONT_DEFAULT, bg=BUTTON_BG, fg=BUTTON_FG, relief="flat", command=self._process_selection, activebackground=BUTTON_HOVER_BG, activeforeground=BUTTON_FG)
        confirm_button.pack(pady=10, ipadx=10, ipady=5)
        confirm_button.bind("<Enter>", self._on_enter_button)
        confirm_button.bind("<Leave>", self._on_leave_button)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_player_selection_ui(self):
        """Cria os botões para cada jogador disponível."""
        players_frame = tk.Frame(self, bg=BG_DARK)
        players_frame.pack(pady=10)

        for player_id in self.available_players_ids:
            button = Button(players_frame, text=f"JOGADOR {player_id}", font=FONT_DEFAULT,
                            bg=BG_MEDIUM, fg=TEXT_PRIMARY, relief="raised", bd=2,
                            command=lambda p_id=player_id: self._toggle_player_selection(p_id))
            button.pack(side=tk.LEFT, padx=5, pady=5)
            button.bind("<Enter>", self._on_enter_player_button)
            button.bind("<Leave>", self._on_leave_player_button)
            self.player_buttons[player_id] = button

    def _get_selected_count_text(self) -> str:
        """Retorna o texto para a label de contagem de jogadores selecionados."""
        return f"Jogadores selecionados: {len(self.selected_team_ids)}/{self.mission_size}"

    def _toggle_player_selection(self, player_id: int):
        """Adiciona ou remove um jogador da equipe selecionada."""
        if player_id in self.selected_team_ids:
            self.selected_team_ids.remove(player_id)
            self.player_buttons[player_id].config(bg=BG_MEDIUM, fg=TEXT_PRIMARY)
        else:
            if len(self.selected_team_ids) < self.mission_size:
                self.selected_team_ids.append(player_id)
                self.player_buttons[player_id].config(bg=TEXT_ACCENT, fg=BG_DARK)
            else:
                messagebox.showwarning("Atenção", f"Você já selecionou o máximo de {self.mission_size} jogadores para a missão.")
        
        self.selected_team_ids.sort()
        self.selected_count_label.config(text=self._get_selected_count_text())


    def _process_selection(self):
        """Processa a seleção do usuário e chama o callback."""
        if len(self.selected_team_ids) != self.mission_size:
            messagebox.showerror("Erro", f"Você deve escolher exatamente {self.mission_size} jogadores para a equipe.")
            return

        self.callback(self.selected_team_ids)
        self.destroy()
        self.grab_release()
    
    def _on_close(self):
        """Lida com o fechamento da janela sem uma seleção válida."""
        self.callback([])
        self.destroy()
        self.grab_release()

    def _on_enter_button(self, event):
        event.widget['background'] = BUTTON_HOVER_BG

    def _on_leave_button(self, event):
        event.widget['background'] = BUTTON_BG

    def _on_enter_player_button(self, event):
        if event.widget['bg'] != TEXT_ACCENT:
            event.widget['background'] = BG_LIGHT

    def _on_leave_player_button(self, event):
        if event.widget['bg'] != TEXT_ACCENT:
            event.widget['background'] = BG_MEDIUM


class YesNoDialog(CustomDialog):
    """
    Diálogo genérico para perguntas de Sim/Não, usado para votos e sabotagens.
    """
    def __init__(self, parent: tk.Tk, player_id: int, question: str, callback: Callable[[bool], None]):
        super().__init__(parent, f"Ação do Jogador {player_id}", question)
        self.player_id = player_id
        self.callback = callback

        button_frame = tk.Frame(self, bg=BG_DARK)
        button_frame.pack(pady=10)

        yes_button = Button(button_frame, text="✅ SIM", font=FONT_DEFAULT,
                            bg="#28a745", fg="white", relief="flat",
                            command=lambda: self._respond(True),
                            activebackground="#218838", activeforeground="white")
        yes_button.pack(side=tk.LEFT, padx=10, ipadx=10, ipady=5)
        yes_button.bind("<Enter>", lambda e: e.widget.config(bg="#218838"))
        yes_button.bind("<Leave>", lambda e: e.widget.config(bg="#28a745"))

        no_button = Button(button_frame, text="❌ NÃO", font=FONT_DEFAULT,
                           bg="#dc3545", fg="white", relief="flat",
                           command=lambda: self._respond(False),
                           activebackground="#c82333", activeforeground="white")
        no_button.pack(side=tk.RIGHT, padx=10, ipadx=10, ipady=5)
        no_button.bind("<Enter>", lambda e: e.widget.config(bg="#c82333"))
        no_button.bind("<Leave>", lambda e: e.widget.config(bg="#dc3545"))
        self.protocol("WM_DELETE_WINDOW", lambda: self._respond(False))


    def _respond(self, choice: bool):
        """Registra a escolha e chama o callback."""
        self.result = choice
        self.callback(choice)
        self.destroy()
        self.grab_release()