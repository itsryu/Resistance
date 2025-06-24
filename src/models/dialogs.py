import tkinter as tk
from tkinter import messagebox, Toplevel, Label, Button
from typing import List, Any, Callable, Optional, Dict
from src.utils.settings import BG_DARK, BG_MEDIUM, TEXT_PRIMARY, TEXT_ACCENT, FONT_TITLE, FONT_DEFAULT, BUTTON_BG, BUTTON_FG, BUTTON_HOVER_BG, GAME_TITLE, FONT_SUBTITLE, BG_LIGHT, ERROR_COLOR


class CustomDialog(tk.Toplevel):
    """
    Classe base para diálogos personalizados, fornecendo estilos comuns
    e um mecanismo para capturar a resposta. Inclui um temporizador.
    """
    def __init__(self, parent: tk.Tk, title: str, message: str, timeout: int = 0, on_close_callback: Optional[Callable[[], None]] = None):
        super().__init__(parent)
        self.transient(parent)
        self.grab_set() 
        self.title(f"{GAME_TITLE} - {title}")
        self.configure(bg=BG_DARK, padx=20, pady=20)
        self.resizable(False, False)

        self.parent = parent
        self.result: Any = None
        self.timeout = timeout
        self._timer_id: Optional[str] = None 
        self._callback_executed: bool = False 
        self._on_close_callback = on_close_callback 

        Label(self, text=title, font=FONT_TITLE, fg=TEXT_ACCENT, bg=BG_DARK).pack(pady=10)
        Label(self, text=message, font=FONT_DEFAULT, fg=TEXT_PRIMARY, bg=BG_DARK).pack(pady=10)

        self.timer_label = Label(self, text="", font=FONT_DEFAULT, fg=TEXT_ACCENT, bg=BG_DARK)
        self.timer_label.pack(pady=5)

        self.update_idletasks()
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()

        self_width = self.winfo_width()
        self_height = self.winfo_height()

        x = parent_x + (parent_width // 2) - (self_width // 2)
        y = parent_y + (parent_height // 2) - (self_height // 2)
        self.geometry(f"+{x}+{y}")

        self._start_timer()
        self.protocol("WM_DELETE_WINDOW", self._on_close_dialog) 

    def _start_timer(self):
        """Inicia a contagem regressiva do temporizador."""
        if self.timeout > 0:
            self._update_timer_display(self.timeout)
            self._timer_countdown(self.timeout)
        else:
            self.timer_label.config(text="") 

    def _timer_countdown(self, remaining_time: int):
        """Atualiza a contagem regressiva e agenda a próxima atualização."""
        if remaining_time > 0 and self.winfo_exists():
            self._update_timer_display(remaining_time)
            self._timer_id = self.after(1000, self._timer_countdown, remaining_time - 1)
        elif self.winfo_exists() and not self._callback_executed: 
            self._update_timer_display(0)
            self._on_timeout() 

    def _update_timer_display(self, remaining_time: int):
        """Atualiza o texto da label do temporizador."""
        if remaining_time > 0:
            self.timer_label.config(text=f"Tempo restante: {remaining_time}s")
        else:
            self.timer_label.config(text="Tempo esgotado!")
            self.timer_label.config(fg=ERROR_COLOR) 

    def _on_timeout(self):
        """Ação a ser executada quando o temporizador atinge zero.
        Deve ser sobrescrito por classes filhas.
        """
        if not self._callback_executed:
            self._callback_executed = True
            
            
            self._finish_dialog()


    def _finish_dialog(self):
        """Finaliza o diálogo de forma controlada, cancelando o timer e liberando o grab."""
        if self._timer_id:
            self.after_cancel(self._timer_id)
            self._timer_id = None 
        
        if self.winfo_exists(): 
            self.destroy()
        self.grab_release()

        if self._on_close_callback and callable(self._on_close_callback):
            self._on_close_callback()

    def _on_close_dialog(self):
        """Lida com o fechamento do diálogo via botão X ou protocolo de janela."""
        if not self._callback_executed: 
            self._callback_executed = True
            
            self.callback(None) if hasattr(self, 'callback') and callable(self.callback) else None
        
        self._finish_dialog()


class TeamSelectionDialog(CustomDialog):
    """
    Diálogo para o líder selecionar os membros da missão, utilizando botões para seleção.
    """
    def __init__(self, parent: tk.Tk, leader_id: int, mission_size: int,
                 available_players_ids: List[int], callback: Callable[[Optional[List[int]]], None], timeout: int = 60):
        super().__init__(parent, f"Seleção de Equipe - Jogador {leader_id}",
                         f"Jogador {leader_id}, clique nos jogadores para selecionar {mission_size} para a missão.",
                         timeout)
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

        confirm_button = Button(self, text="Confirmar Equipe", font=FONT_DEFAULT,
                                bg=BUTTON_BG, fg=BUTTON_FG, relief="flat", command=self._process_selection,
                                activebackground=BUTTON_HOVER_BG, activeforeground=BUTTON_FG)
        confirm_button.pack(pady=10, ipadx=10, ipady=5)
        confirm_button.bind("<Enter>", self._on_enter_button)
        confirm_button.bind("<Leave>", self._on_leave_button)

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
        
        if not self._callback_executed: 
            self._callback_executed = True
            self.callback(self.selected_team_ids)
            self._finish_dialog() 
    
    
    def _on_timeout(self):
        if not self._callback_executed:
            self._callback_executed = True
            messagebox.showwarning("Tempo Esgotado", "Tempo para selecionar a equipe esgotado. Nenhuma equipe foi proposta.")
            self.callback([]) 
            self._finish_dialog()

    
    def _on_enter_button(self, event):
        event.widget['background'] = BUTTON_HOVER_BG

    def _on_leave_button(self, event):
        event.widget['background'] = BUTTON_BG

    def _on_enter_player_button(self, event):
        if event.widget['bg'] != str(TEXT_ACCENT): 
            event.widget['background'] = BG_LIGHT

    def _on_leave_player_button(self, event):
        if event.widget['bg'] != str(TEXT_ACCENT): 
            event.widget['background'] = BG_MEDIUM


class YesNoDialog(CustomDialog):
    """
    Diálogo genérico para perguntas de Sim/Não, usado para votos e sabotagens.
    """
    def __init__(self, parent: tk.Tk, player_id: int, question: str, callback: Callable[[bool], None], timeout: int = 30):
        super().__init__(parent, f"Ação do Jogador {player_id}", question, timeout)
        self.player_id = player_id
        self.callback = callback 

        button_frame = tk.Frame(self, bg=BG_DARK)
        button_frame.pack(pady=10)

        yes_button = Button(button_frame, text="✅ SIM", font=FONT_DEFAULT,
                            bg="#28a745", fg="white", relief="flat",
                            command=lambda: self._respond(True))
        yes_button.pack(side=tk.LEFT, padx=10, ipadx=10, ipady=5)
        yes_button.bind("<Enter>", lambda e: e.widget.config(bg="#218838"))
        yes_button.bind("<Leave>", lambda e: e.widget.config(bg="#28a745"))

        no_button = Button(button_frame, text="❌ NÃO", font=FONT_DEFAULT,
                           bg="#dc3545", fg="white", relief="flat",
                           command=lambda: self._respond(False))
        no_button.pack(side=tk.RIGHT, padx=10, ipadx=10, ipady=5)
        no_button.bind("<Enter>", lambda e: e.widget.config(bg="#c82333"))
        no_button.bind("<Leave>", lambda e: e.widget.config(bg="#dc3545"))

    def _respond(self, choice: bool):
        """Registra a escolha e chama o callback."""
        if not self._callback_executed: 
            self._callback_executed = True
            self.result = choice
            self.callback(choice)
            self._finish_dialog() 

    
    def _on_timeout(self):
        if not self._callback_executed:
            self._callback_executed = True
            messagebox.showwarning("Tempo Esgotado", "Tempo para responder esgotado. Voto/Escolha padrão (NÃO) será usado.")
            self.callback(False) 
            self._finish_dialog()




class MissionOutcomeDialog(CustomDialog):
    def __init__(self, parent: tk.Tk, success: bool, sabotages_count: int):
        title = "Missão Bem-Sucedida!" if success else "Missão Falhou!"
        message = ("A Resistência obteve sucesso na missão!" 
                   if success 
                   else f"Os Espiões sabotaram a missão com {sabotages_count} falha(s)!")
        
        super().__init__(parent, title, message, timeout=5) 

        ok_button = Button(self, text="OK", font=FONT_DEFAULT,
                           bg=BUTTON_BG, fg=BUTTON_FG, relief="flat", command=self._on_confirm_outcome)
        ok_button.pack(pady=10)
        ok_button.bind("<Enter>", lambda e: e.widget.config(bg=BUTTON_HOVER_BG))
        ok_button.bind("<Leave>", lambda e: e.widget.config(bg=BUTTON_BG))

        
        if not success:
            self.timer_label.config(fg=ERROR_COLOR) 

    def _on_confirm_outcome(self):
        """Callback para o botão OK do diálogo de resultado de missão."""
        if not self._callback_executed: 
            self._callback_executed = True
            self._finish_dialog()

    def _on_timeout(self):
        """Sobrescreve para fechar automaticamente após timeout."""
        if not self._callback_executed:
            self._callback_executed = True
            self._finish_dialog() 


class GameOverDetailsDialog(CustomDialog):
    def __init__(self, parent: tk.Tk, winner: str, mission_results: List[str], resistance_wins: int, spy_wins: int):
        
        super().__init__(parent, "Fim de Jogo", f"O vencedor é: {winner}!", timeout=0) 

        self.geometry("450x450") 

        winner_label = Label(self, text=f"Vencedor: {winner}", font=FONT_TITLE, fg=TEXT_ACCENT, bg=BG_DARK)
        winner_label.pack(pady=(0, 15))

        results_heading = Label(self, text="Resultados das Missões:", font=FONT_SUBTITLE, fg=TEXT_PRIMARY, bg=BG_DARK)
        results_heading.pack(pady=(10, 5))

        
        results_frame = tk.Frame(self, bg=BG_LIGHT, bd=1, relief="solid")
        results_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

        results_text_widget = tk.Text(results_frame, font=FONT_DEFAULT, fg=TEXT_PRIMARY, bg=BG_LIGHT,
                                       wrap=tk.WORD, height=len(mission_results) + 1, relief="flat", bd=0)
        results_text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        results_text_widget.insert(tk.END, "\n".join([f"Missão {i+1}: {res}" for i, res in enumerate(mission_results)]))
        results_text_widget.config(state=tk.DISABLED) 

        scrollbar = tk.Scrollbar(results_frame, command=results_text_widget.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        results_text_widget.config(yscrollcommand=scrollbar.set)

        score_label = Label(self, text=f"Placar: Resistência {resistance_wins} x {spy_wins} Espiões", font=FONT_SUBTITLE, fg=TEXT_PRIMARY, bg=BG_DARK)
        score_label.pack(pady=(15, 20))

        ok_button = Button(self, text="OK", font=FONT_DEFAULT,
                           bg=BUTTON_BG, fg=BUTTON_FG, relief="flat", command=self._on_confirm_game_over)
        ok_button.pack(pady=10)
        ok_button.bind("<Enter>", lambda e: e.widget.config(bg=BUTTON_HOVER_BG))
        ok_button.bind("<Leave>", lambda e: e.widget.config(bg=BUTTON_BG))

    def _on_confirm_game_over(self):
        """Callback para o botão OK do diálogo de fim de jogo."""
        if not self._callback_executed:
            self._callback_executed = True
            self._finish_dialog()

    def _on_timeout(self):
        """Diálogo de fim de jogo não deve ter timeout para fechamento automático."""
        pass 