import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sys
import os

from src.controllers.controller import GameController
from src.utils.settings import (
    GAME_TITLE, FONT_TITLE, FONT_SUBTITLE, FONT_DEFAULT, FONT_HEADING,
    BG_DARK, BG_MEDIUM, BG_MENU, TEXT_ACCENT, TEXT_PRIMARY,
    BUTTON_BG, BUTTON_FG, BUTTON_HOVER_BG, BORDER_COLOR
)
from typing import Optional

try:
    import winsound
    _WINSOUND_AVAILABLE = True
except ImportError:
    _WINSOUND_AVAILABLE = False


class MainApplication(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(GAME_TITLE)
        self.geometry("900x750")
        self.configure(bg=BG_MENU)
        self.resizable(False, False)

        self.controller: Optional[GameController] = None
        self._current_frame: Optional[tk.Frame] = None
        self._loading_screen: Optional[tk.Toplevel] = None
        self.sound_enabled = tk.BooleanVar(value=True)
        self.how_to_play_text_content: str = self._load_how_to_play_text()

        self._configure_ttk_style()
        self._show_main_menu()
        
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _load_how_to_play_text(self) -> str:
        """Carrega o texto de como jogar de um arquivo .txt."""
        script_dir = os.path.dirname(__file__)
        file_path = os.path.join(script_dir, 'how_to_play.txt')
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return "Erro: Arquivo 'how_to_play.txt' não encontrado. Certifique-se de que ele está em src/how_to_play.txt."
        except Exception as e:
            return f"Erro ao carregar o texto de como jogar: {e}"

    def _configure_ttk_style(self):
        style = ttk.Style(self)
        style.theme_use('clam')

        style.configure('TButton',
                        background=BUTTON_BG,
                        foreground=BUTTON_FG,
                        font=FONT_SUBTITLE,
                        relief='flat',
                        borderwidth=0,
                        padding=[20, 15],
                        focusthickness=0,
                        focuscolor=BUTTON_BG)
        style.map('TButton',
                  background=[('active', BUTTON_HOVER_BG), ('pressed', BUTTON_HOVER_BG)],
                  foreground=[('active', BUTTON_FG)])

        style.configure('TLabel',
                        background=BG_MENU,
                        foreground=TEXT_PRIMARY,
                        font=FONT_DEFAULT)
        style.configure('Title.TLabel',
                        background=BG_MENU,
                        foreground=TEXT_ACCENT,
                        font=FONT_TITLE)
        style.configure('Heading.TLabel',
                        background=BG_MENU,
                        foreground=TEXT_PRIMARY,
                        font=FONT_HEADING)
        
        style.configure('Menu.TFrame',
                        background=BG_MENU)
        
        style.configure('Description.TLabel',
                        background=BG_MENU,
                        foreground=TEXT_PRIMARY,
                        font=FONT_DEFAULT,
                        padding=[10, 5])
        
        style.configure('Option.TButton',
                        background=BG_MEDIUM,
                        foreground=TEXT_PRIMARY,
                        font=FONT_DEFAULT,
                        relief='flat',
                        borderwidth=1,
                        bordercolor=BORDER_COLOR,
                        padding=[15, 10])
        style.map('Option.TButton',
                  background=[('active', TEXT_ACCENT), ('pressed', TEXT_ACCENT)],
                  foreground=[('active', BG_DARK), ('pressed', BG_DARK)])
        
        style.configure('TCheckbutton',
                        background=BG_MENU,
                        foreground=TEXT_PRIMARY,
                        font=FONT_DEFAULT,
                        focusthickness=0,
                        indicatorcolor=TEXT_PRIMARY)
        style.map('TCheckbutton',
                  background=[('active', BG_MENU)],
                  foreground=[('active', TEXT_ACCENT)])

    def _clear_frame(self):
        if self._current_frame:
            for widget in self._current_frame.winfo_children():
                widget.destroy()
            self._current_frame.destroy()
        
        self._current_frame = ttk.Frame(self, style='Menu.TFrame')
        self._current_frame.pack(fill=tk.BOTH, expand=True, padx=40, pady=40)
        
        self._current_frame.grid_rowconfigure((0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11), weight=1) 
        self._current_frame.grid_columnconfigure(0, weight=1)

    def _play_sound(self, sound_type: str):
        if self.sound_enabled.get() and _WINSOUND_AVAILABLE:
            if sound_type == "click":
                winsound.PlaySound("SystemExclamation", winsound.SND_ASYNC)
            elif sound_type == "start_game":
                winsound.PlaySound("SystemAsterisk", winsound.SND_ASYNC)

    def _show_main_menu(self):
        self._clear_frame()

        ttk.Label(self._current_frame, text=GAME_TITLE, style='Title.TLabel').grid(row=0, column=0, pady=(100, 40), sticky="n")

        ttk.Button(self._current_frame, text="Jogar", command=self._show_play_options).grid(row=2, column=0, pady=10)
        ttk.Button(self._current_frame, text="Como Jogar", command=self._show_how_to_play).grid(row=3, column=0, pady=10)
        ttk.Button(self._current_frame, text="Configurações", command=self._show_settings_menu).grid(row=4, column=0, pady=10)
        ttk.Button(self._current_frame, text="Sair", command=self._on_closing).grid(row=5, column=0, pady=10)
        
        self._current_frame.grid_rowconfigure(1, weight=1)
        self._current_frame.grid_rowconfigure(6, weight=1)
        self._current_frame.grid_rowconfigure((0, 2, 3, 4, 5), weight=0)

    def _show_play_options(self):
        self._play_sound("click")
        self._clear_frame()

        ttk.Label(self._current_frame, text="Escolha o Modo de Jogo", style='Heading.TLabel').grid(row=0, column=0, pady=(0, 30))

        ttk.Button(self._current_frame, text="🚀 Servidor (Host)", command=lambda: self._trigger_start_game(True, None)).grid(row=1, column=0, pady=15)
        ttk.Button(self._current_frame, text="💻 Cliente (Entrar)", command=self._prompt_client_ip).grid(row=2, column=0, pady=15)
        ttk.Button(self._current_frame, text="Voltar", command=self._show_main_menu).grid(row=4, column=0, pady=20)
        
        self._current_frame.grid_rowconfigure(3, weight=1)

    def _prompt_client_ip(self):
        """Pede ao usuário o IP do servidor antes de iniciar como cliente."""
        self._play_sound("click")
        server_ip = simpledialog.askstring("Conectar ao Servidor", "Digite o IP do servidor (Ex: 192.168.1.100):",
                                           parent=self, initialvalue="127.0.0.1")
        if server_ip:
            self._trigger_start_game(False, server_ip)
        else:
            messagebox.showwarning("Conexão", "IP do servidor não fornecido. Não foi possível iniciar como cliente.")


    def _show_how_to_play(self):
        self._play_sound("click")
        self._clear_frame()

        ttk.Label(self._current_frame, text="Como Jogar: The Resistance", style='Title.TLabel').grid(row=0, column=0, pady=(0, 20), sticky="n")

        how_to_play_text_widget = tk.Text(self._current_frame, wrap=tk.WORD, bg=BG_MENU, fg=TEXT_PRIMARY,
                                         font=FONT_DEFAULT, relief="flat", padx=20, pady=20)
        how_to_play_text_widget.insert(tk.END, self.how_to_play_text_content)
        how_to_play_text_widget.config(state=tk.DISABLED)
        how_to_play_text_widget.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        scrollbar = ttk.Scrollbar(self._current_frame, command=how_to_play_text_widget.yview, style='Vertical.TScrollbar')
        scrollbar.grid(row=1, column=1, sticky="ns")
        how_to_play_text_widget.config(yscrollcommand=scrollbar.set)
        
        ttk.Button(self._current_frame, text="Voltar", command=self._show_main_menu, style='Option.TButton').grid(row=2, column=0, pady=20, sticky="s")
        
        self._current_frame.grid_rowconfigure(1, weight=1)
        self._current_frame.grid_columnconfigure(0, weight=1)

    def _show_settings_menu(self):
        self._play_sound("click")
        self._clear_frame()

        ttk.Label(self._current_frame, text="Configurações", style='Title.TLabel').grid(row=0, column=0, pady=(0, 30), sticky="n")

        ttk.Checkbutton(self._current_frame, text="Ativar Som do Jogo", 
                        variable=self.sound_enabled, onvalue=True, offvalue=False,
                        style='TCheckbutton').grid(row=1, column=0, pady=10, sticky="w", padx=50)

        ttk.Button(self._current_frame, text="Salvar", command=self._save_settings).grid(row=3, column=0, pady=15)
        ttk.Button(self._current_frame, text="Voltar", command=self._show_main_menu).grid(row=4, column=0, pady=10)
        
        self._current_frame.grid_rowconfigure(2, weight=1)

    def _save_settings(self):
        self._play_sound("click")
        messagebox.showinfo("Configurações", "Configurações salvas com sucesso!")
        self._show_main_menu()

    def _trigger_start_game(self, is_server: bool, server_ip: Optional[str] = None):
        """Prepara e inicia o jogo, mostrando uma tela de carregamento."""
        self._play_sound("start_game")
        self._show_loading_screen()
        self.after(100, lambda: self._start_game(is_server, server_ip))

    def _show_loading_screen(self):
        self._loading_screen = tk.Toplevel(self)
        self._loading_screen.title("Carregando...")
        self._loading_screen.geometry("400x200")
        self._loading_screen.configure(bg=BG_DARK)
        self._loading_screen.transient(self)
        self._loading_screen.grab_set()
        self._loading_screen.resizable(False, False)

        self._loading_screen.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (self._loading_screen.winfo_width() // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (self._loading_screen.winfo_height() // 2)
        self._loading_screen.geometry(f"+{x}+{y}")

        ttk.Label(self._loading_screen, text="Iniciando Jogo...", style='Heading.TLabel', background=BG_DARK, foreground=TEXT_ACCENT).pack(pady=40)
        
    def _hide_loading_screen(self):
        if self._loading_screen:
            self._loading_screen.grab_release()
            self._loading_screen.destroy()
            self._loading_screen = None

    def _start_game(self, is_server: bool, server_ip: Optional[str] = None):
        """Inicia a aplicação do jogo (GameController e GameView)."""
        self._clear_frame()
        self.controller = GameController(self, is_server, server_ip)
        self._hide_loading_screen()

    def _on_closing(self):
        self._play_sound("click")
        print("Fechando aplicação...")
        if self.controller:
            if self.controller.is_server and self.controller.server:
                self.controller.server.stop()
                print("Servidor de rede parado.")
            elif not self.controller.is_server and self.controller.client:
                self.controller.client.stop()
                print("Cliente de rede parado.")
        self.destroy()
        sys.exit(0)

if __name__ == '__main__':
    app = MainApplication()
    app.mainloop()