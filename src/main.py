import tkinter as tk
from tkinter import ttk, Canvas, messagebox # Adicionado messagebox aqui
import sys
import time # Para simular atrasos para animações

from src.views.view import GameView
from src.models.model import GameModel
from src.controllers.controller import GameController
from src.utils.network import GameServer, GameClient
from src.utils.settings import (
    GAME_TITLE, FONT_TITLE, FONT_SUBTITLE, FONT_DEFAULT, FONT_HEADING,
    BG_DARK, BG_MEDIUM, BG_MENU, TEXT_ACCENT, TEXT_PRIMARY,
    BUTTON_BG, BUTTON_FG, BUTTON_HOVER_BG, NUM_PLAYERS, NUM_SPIES,
    BORDER_COLOR
)

# Tentar importar winsound para feedback sonoro no Windows
try:
    import winsound
    _WINSOUND_AVAILABLE = True
except ImportError:
    _WINSOUND_AVAILABLE = False
    # print("winsound não disponível (apenas para Windows). Feedback sonoro desativado.")


class MainApplication(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(GAME_TITLE)
        self.geometry("900x750")
        self.configure(bg=BG_MENU)
        self.resizable(False, False) # Manter tamanho fixo para controle total do layout

        self.controller: Optional[GameController] = None
        self._current_frame: Optional[tk.Frame] = None # Frame que contém o conteúdo atual
        self._loading_screen: Optional[tk.Toplevel] = None
        self.sound_enabled = tk.BooleanVar(value=True) # Variável para controlar o som

        self._configure_ttk_style()
        self._show_main_menu()
        
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _configure_ttk_style(self):
        """Configura o estilo para os widgets ttk."""
        style = ttk.Style(self)
        style.theme_use('clam')

        # Estilo para Botões
        style.configure('TButton',
                        background=BUTTON_BG,
                        foreground=BUTTON_FG,
                        font=FONT_SUBTITLE,
                        relief='flat',
                        borderwidth=0,
                        padding=[20, 15], # Ajustar padding para evitar quebra de texto
                        focusthickness=0, 
                        focuscolor=BUTTON_BG)
        style.map('TButton',
                  background=[('active', BUTTON_HOVER_BG), ('pressed', BUTTON_HOVER_BG)],
                  foreground=[('active', BUTTON_FG)])

        # Estilo para Labels de título e subtítulo
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
        
        # Estilo para Frame (para as seções do menu)
        style.configure('Menu.TFrame',
                        background=BG_MENU)
        
        # Estilo para texto de descrição com quebra de linha
        style.configure('Description.TLabel',
                        background=BG_MENU,
                        foreground=TEXT_PRIMARY,
                        font=FONT_DEFAULT,
                        padding=[10, 5])
        
        # Estilo para botões pequenos de opção
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
        
        # Estilo para Checkbutton
        style.configure('TCheckbutton',
                        background=BG_MENU,
                        foreground=TEXT_PRIMARY,
                        font=FONT_DEFAULT,
                        focusthickness=0,
                        indicatorcolor=TEXT_PRIMARY) # Cor do indicador (checkbox)
        style.map('TCheckbutton',
                  background=[('active', BG_MENU)], # Evita mudança de cor ao clicar
                  foreground=[('active', TEXT_ACCENT)])

    def _clear_frame(self):
        """Limpa o frame atual para exibir um novo."""
        if self._current_frame:
            for widget in self._current_frame.winfo_children():
                widget.destroy()
            self._current_frame.destroy()
        
        self._current_frame = ttk.Frame(self, style='Menu.TFrame') # Usar ttk.Frame para consistência
        self._current_frame.pack(fill=tk.BOTH, expand=True, padx=40, pady=40)
        
        # Configurar grid para o novo frame para centralização e espaçamento flexível
        self._current_frame.grid_rowconfigure((0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11), weight=1) 
        self._current_frame.grid_columnconfigure(0, weight=1) # Coluna central flexível

    def _play_sound(self, sound_type: str):
        """Reproduz um som (apenas no Windows) se o som estiver ativado."""
        if self.sound_enabled.get() and _WINSOUND_AVAILABLE:
            if sound_type == "click":
                winsound.PlaySound("SystemExclamation", winsound.SND_ASYNC)
            elif sound_type == "start_game":
                winsound.PlaySound("SystemAsterisk", winsound.SND_ASYNC)

    def _show_main_menu(self):
        """Exibe a tela do menu principal."""
        self._clear_frame()

        # Título do Jogo Centralizado
        ttk.Label(self._current_frame, text=GAME_TITLE, style='Title.TLabel').grid(row=0, column=0, pady=(100, 40), sticky="n")

        # Botões de Ação Principal
        ttk.Button(self._current_frame, text="Jogar", command=self._show_play_options).grid(row=2, column=0, pady=10)
        ttk.Button(self._current_frame, text="Como Jogar", command=self._show_how_to_play).grid(row=3, column=0, pady=10)
        ttk.Button(self._current_frame, text="Configurações", command=self._show_settings_menu).grid(row=4, column=0, pady=10)
        ttk.Button(self._current_frame, text="Sair", command=self._on_closing).grid(row=5, column=0, pady=10)
        
        # Ajuste de pesos das linhas para centralizar os botões verticalmente
        self._current_frame.grid_rowconfigure(1, weight=1) # Espaço antes dos botões
        self._current_frame.grid_rowconfigure(6, weight=1) # Espaço depois dos botões
        self._current_frame.grid_rowconfigure((0, 2, 3, 4, 5), weight=0) # As linhas dos widgets não se expandem

    def _show_play_options(self):
        """Exibe as opções de jogar (Servidor/Cliente)."""
        self._play_sound("click")
        self._clear_frame()

        ttk.Label(self._current_frame, text="Escolha o Modo de Jogo", style='Heading.TLabel').grid(row=0, column=0, pady=(0, 30))

        ttk.Button(self._current_frame, text="🚀 Servidor (Host)", command=lambda: self._trigger_start_game(True), style='Option.TButton').grid(row=1, column=0, pady=15)
        ttk.Button(self._current_frame, text="💻 Cliente (Entrar)", command=lambda: self._trigger_start_game(False), style='Option.TButton').grid(row=2, column=0, pady=15)
        ttk.Button(self._current_frame, text="Voltar", command=self._show_main_menu, style='Option.TButton').grid(row=4, column=0, pady=20)
        
        self._current_frame.grid_rowconfigure(3, weight=1) # Espaçamento entre os botões de jogar e voltar

    def _show_how_to_play(self):
        """Exibe a tela detalhada de como jogar."""
        self._play_sound("click")
        self._clear_frame()

        ttk.Label(self._current_frame, text="Como Jogar: The Resistance", style='Title.TLabel').grid(row=0, column=0, pady=(0, 20), sticky="n")

        how_to_play_text = """
The Resistance é um jogo de dedução social e blefe, jogado por 5 a 10 pessoas. Dividido em dois grupos, a Resistência (maioria) e os Espiões (minoria), o jogo exige que a Resistência complete uma série de missões bem-sucedidas para vencer, enquanto os Espiões tentam sabotá-las para alcançar a vitória.

Papéis:
- RESISTÊNCIA: Trabalhadores leais que tentam completar missões. Eles sempre devem votar SUCESSO.
- ESPIÕES: Infiltrados que tentam sabotar missões. Eles podem votar SUCESSO ou FALHA (sabotagem).

Fases do Jogo:
1.  Início da Rodada e Líder: Um jogador é designado como o Líder da rodada. O Líder propõe uma equipe para a missão atual, selecionando um número específico de jogadores.
2.  Votação de Aprovação da Equipe: Todos os jogadores votam (sim ou não) para aprovar a equipe proposta.
    -   Se a maioria votar SIM: A equipe é aprovada e a missão prossegue.
    -   Se a maioria votar NÃO: A equipe é rejeitada. O Líder passa para o próximo jogador, e um novo processo de proposta de equipe começa. Se 5 equipes consecutivas forem rejeitadas, os Espiões vencem a partida.
3.  Execução da Missão (Voto Secreto): Os jogadores da equipe aprovada votam secretamente SUCESSO ou FALHA.
    -   Membros da Resistência devem votar SUCESSO.
    -   Espiões podem votar SUCESSO (para se disfarçar) ou FALHA (para sabotar a missão).
    -   Se houver **nenhum voto de FALHA** (ou apenas um em missões que permitem uma falha), a missão é um SUCESSO.
    -   Se houver **um ou mais votos de FALHA** (ou o número exigido para missões específicas), a missão é uma FALHA.

Condições de Vitória:
-   RESISTÊNCIA VENCE: Se 3 missões forem bem-sucedidas.
-   ESPIÕES VENCEM: Se 3 missões falharem OU se 5 propostas de equipe consecutivas forem rejeitadas.

Objetivo Final:
-   Resistência: Completar 3 missões.
-   Espiões: Causar 3 falhas em missões.
        """
        # Criando um Text widget para exibir o texto formatado com rolagem
        how_to_play_text_widget = tk.Text(self._current_frame, wrap=tk.WORD, bg=BG_MENU, fg=TEXT_PRIMARY,
                                         font=FONT_DEFAULT, relief="flat", padx=20, pady=20)
        how_to_play_text_widget.insert(tk.END, how_to_play_text)
        how_to_play_text_widget.config(state=tk.DISABLED) # Torna o texto somente leitura
        how_to_play_text_widget.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        scrollbar = ttk.Scrollbar(self._current_frame, command=how_to_play_text_widget.yview, style='Vertical.TScrollbar')
        scrollbar.grid(row=1, column=1, sticky="ns")
        how_to_play_text_widget.config(yscrollcommand=scrollbar.set)
        
        ttk.Button(self._current_frame, text="Voltar", command=self._show_main_menu, style='Option.TButton').grid(row=2, column=0, pady=20, sticky="s")
        
        self._current_frame.grid_rowconfigure(1, weight=1) # Faz a área de texto expandir
        self._current_frame.grid_columnconfigure(0, weight=1) # Faz a coluna de texto expandir

    def _show_settings_menu(self):
        """Exibe o menu de configurações."""
        self._play_sound("click")
        self._clear_frame()

        ttk.Label(self._current_frame, text="Configurações", style='Title.TLabel').grid(row=0, column=0, pady=(0, 30), sticky="n")

        # Opção de ativar/desativar som
        ttk.Checkbutton(self._current_frame, text="Ativar Som do Jogo", 
                        variable=self.sound_enabled, onvalue=True, offvalue=False,
                        style='TCheckbutton').grid(row=1, column=0, pady=10, sticky="w", padx=50)

        # Botões de ação
        ttk.Button(self._current_frame, text="Salvar", command=self._save_settings, style='Option.TButton').grid(row=3, column=0, pady=15)
        ttk.Button(self._current_frame, text="Voltar", command=self._show_main_menu, style='Option.TButton').grid(row=4, column=0, pady=10)
        
        self._current_frame.grid_rowconfigure(2, weight=1) # Espaço entre a opção e os botões

    def _save_settings(self):
        """Salva as configurações (por enquanto, apenas o estado da variável)."""
        self._play_sound("click")
        messagebox.showinfo("Configurações", "Configurações salvas com sucesso!")
        # Em um sistema real, você salvaria self.sound_enabled.get() em um arquivo de configuração.
        self._show_main_menu() # Volta ao menu principal

    def _trigger_start_game(self, is_server: bool):
        """Prepara e inicia o jogo, mostrando uma tela de carregamento."""
        self._play_sound("start_game") # Som ao iniciar jogo
        self._show_loading_screen()
        # Usar after para permitir que a tela de carregamento apareça antes de iniciar o controlador pesado
        self.after(100, lambda: self._start_game(is_server))

    def _show_loading_screen(self):
        """Exibe uma tela de carregamento."""
        self._loading_screen = tk.Toplevel(self)
        self._loading_screen.title("Carregando...")
        self._loading_screen.geometry("400x200")
        self._loading_screen.configure(bg=BG_DARK)
        self._loading_screen.transient(self) # Fica por cima da janela principal
        self._loading_screen.grab_set() # Bloqueia interações com a janela principal
        self._loading_screen.resizable(False, False)

        # Centralizar tela de carregamento
        self._loading_screen.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (self._loading_screen.winfo_width() // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (self._loading_screen.winfo_height() // 2)
        self._loading_screen.geometry(f"+{x}+{y}")

        ttk.Label(self._loading_screen, text="Iniciando Jogo...", style='Heading.TLabel', background=BG_DARK, foreground=TEXT_ACCENT).pack(pady=40)
        
    def _hide_loading_screen(self):
        """Esconde a tela de carregamento."""
        if self._loading_screen:
            self._loading_screen.grab_release()
            self._loading_screen.destroy()
            self._loading_screen = None

    def _start_game(self, is_server: bool):
        """Inicia a aplicação do jogo (GameController e GameView)."""
        self._clear_frame() # Limpa o menu
        self.controller = GameController(self, is_server)
        self._hide_loading_screen() # Esconde a tela de carregamento após a inicialização do controller

    def _on_closing(self):
        """Lida com o fechamento da janela, garantindo que as threads de rede sejam paradas."""
        self._play_sound("click") # Som ao sair
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