# --- resistance_game/dialogs.py ---
# Contém as classes para diálogos personalizados da GUI.

import tkinter as tk
from tkinter import messagebox, Toplevel, Label, Button, Entry
from typing import List, Any, Callable, Optional
from src.utils.settings import BG_DARK, BG_MEDIUM, TEXT_PRIMARY, TEXT_ACCENT, FONT_TITLE, FONT_DEFAULT, BUTTON_BG, BUTTON_FG

class CustomDialog(tk.Toplevel):
    """
    Classe base para diálogos personalizados, fornecendo estilos comuns
    e um mecanismo para capturar a resposta.
    """
    def __init__(self, parent: tk.Tk, title: str, message: str):
        super().__init__(parent)
        self.transient(parent)
        self.grab_set()  # Garante que o diálogo seja modal, bloqueando outras interações.
        self.title(title)
        self.configure(bg=BG_DARK, padx=20, pady=20)
        self.resizable(False, False)

        self.result: Any = None

        Label(self, text=title, font=FONT_TITLE, fg=TEXT_ACCENT, bg=BG_DARK).pack(pady=10)
        Label(self, text=message, font=FONT_DEFAULT, fg=TEXT_PRIMARY, bg=BG_DARK).pack(pady=10)

        # Permite fechar o diálogo com Enter em alguns casos, se a subclasse implementar.
        self.bind("<Return>", lambda event: self._on_confirm())

    def _on_confirm(self):
        """Método de callback padrão para confirmação do diálogo.
        Deve ser sobrescrito por subclasses se houver lógica específica.
        """
        self.destroy()
        self.grab_release() # Libera o foco do diálogo.


class TeamSelectionDialog(CustomDialog):
    """
    Diálogo para o líder selecionar os membros da missão.
    """
    def __init__(self, parent: tk.Tk, leader_id: int, mission_size: int,
                 available_players_ids: List[int], callback: Callable[[List[int]], None]):
        super().__init__(parent, "Seleção de Time",
                         f"Jogador {leader_id}, escolha {mission_size} jogadores (IDs de 1 a {len(available_players_ids)} separados por vírgula):\n\nJogadores disponíveis: {', '.join(map(str, available_players_ids))}")
        self.leader_id = leader_id
        self.mission_size = mission_size
        self.available_players_ids = available_players_ids
        self.callback = callback

        self.team_entry = Entry(self, font=FONT_DEFAULT, bg=BG_MEDIUM, fg=TEXT_PRIMARY,
                                insertbackground=TEXT_PRIMARY, relief="flat", justify="center")
        self.team_entry.pack(pady=10, ipadx=5, ipady=5)
        self.team_entry.focus_set()

        confirm_button = Button(self, text="Confirmar", font=FONT_DEFAULT,
                                bg=BUTTON_BG, fg=BUTTON_FG, relief="flat", command=self._process_selection)
        confirm_button.pack(pady=10, ipadx=10, ipady=5)
        self.protocol("WM_DELETE_WINDOW", self._on_close) # Garante que o callback seja chamado ao fechar a janela.


    def _process_selection(self):
        """Processa a entrada do usuário e chama o callback."""
        try:
            team_ids_str = self.team_entry.get().strip()
            if not team_ids_str: # Considera entrada vazia como cancelamento ou inválida
                self.callback([]) # Retorna uma lista vazia para indicar não seleção válida
                self.destroy()
                self.grab_release()
                return

            team_ids = [int(i.strip()) for i in team_ids_str.split(',')]
            if len(team_ids) != self.mission_size:
                messagebox.showerror("Erro", f"Você deve escolher exatamente {self.mission_size} jogadores.")
                return # Não fecha o diálogo
            if not all(1 <= player_id <= len(self.available_players_ids) for player_id in team_ids):
                messagebox.showerror("Erro", "IDs de jogador inválidos. Escolha IDs de 1 a 5.")
                return # Não fecha o diálogo
            if len(set(team_ids)) != len(team_ids):
                messagebox.showerror("Erro", "Não é permitido escolher o mesmo jogador mais de uma vez.")
                return # Não fecha o diálogo

            self.callback(team_ids)
            self.destroy()
            self.grab_release()
        except ValueError:
            messagebox.showerror("Erro", "Entrada inválida. Use números separados por vírgula (ex: 1,2,3).")
        except Exception as e:
            messagebox.showerror("Erro", f"Um erro inesperado ocorreu: {e}")
            self.callback([]) # Em caso de erro inesperado, retorna vazio
            self.destroy()
            self.grab_release()
    
    def _on_confirm(self):
        """Sobrescrito para permitir a confirmação com Enter no Entry."""
        self._process_selection()

    def _on_close(self):
        """Lida com o fechamento da janela sem uma seleção válida."""
        self.callback([]) # Indica que nenhuma seleção foi feita
        self.destroy()
        self.grab_release()


class YesNoDialog(CustomDialog):
    """
    Diálogo genérico para perguntas de Sim/Não, usado para votos e sabotagens.
    """
    def __init__(self, parent: tk.Tk, player_id: int, question: str, callback: Callable[[bool], None]):
        super().__init__(parent, f"Jogador {player_id}", question)
        self.player_id = player_id
        self.callback = callback

        button_frame = tk.Frame(self, bg=BG_DARK)
        button_frame.pack(pady=10)

        yes_button = Button(button_frame, text="✅ SIM", font=FONT_DEFAULT,
                            bg="#28a745", fg="white", relief="flat",
                            command=lambda: self._respond(True))
        yes_button.pack(side=tk.LEFT, padx=10, ipadx=10, ipady=5)

        no_button = Button(button_frame, text="❌ NÃO", font=FONT_DEFAULT,
                           bg="#dc3545", fg="white", relief="flat",
                           command=lambda: self._respond(False))
        no_button.pack(side=tk.RIGHT, padx=10, ipadx=10, ipady=5)
        self.protocol("WM_DELETE_WINDOW", lambda: self._respond(False)) # Assume "Não" se a janela for fechada


    def _respond(self, choice: bool):
        """Registra a escolha e chama o callback."""
        self.result = choice
        self.callback(choice)
        self.destroy()
        self.grab_release()