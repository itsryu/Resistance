import tkinter as tk

from tkinter import Canvas, ttk
from typing import List, Callable, Optional, Dict, Any
from src.utils.settings import (
    BG_DARK, BG_MEDIUM, BG_LIGHT, TEXT_PRIMARY, TEXT_ACCENT, BORDER_COLOR,
    FONT_TITLE, FONT_SUBTITLE, FONT_DEFAULT, FONT_LOG, FONT_HEADING,
    BUTTON_BG, BUTTON_FG, BUTTON_HOVER_BG, BORDER_RADIUS, GAME_TITLE, MISSION_SIZES
)
from src.models.dialogs import TeamSelectionDialog, YesNoDialog, MissionOutcomeDialog, GameOverDetailsDialog


class GameView:
    """
    A View do jogo "The Resistance". É responsável por exibir a interface gráfica
    e por solicitar entrada do usuário. Ela notifica o Controller sobre interações do usuário.
    Em um jogo LAN, esta View é exclusiva do cliente.
    """
    def __init__(self, root: tk.Tk):
        self.root: tk.Tk = root
        self.root.title(GAME_TITLE)
        self.root.configure(bg=BG_DARK)
        self.root.geometry("900x750") 
        self.root.resizable(False, False)

        self.controller: Optional['GameController'] = None 
        self.game_state_data: Dict[str, Any] = {} 
        self.local_player_id: Optional[int] = None 
        self.local_player_role: Optional[str] = None 

        self._player_info_label_canvas_item: Optional[int] = None 

        self._configure_ttk_style()
        self._initialize_ui_components()

    def _configure_ttk_style(self):
        """Configura o estilo para os widgets ttk."""
        style = ttk.Style()
        style.theme_use('clam')

        # Configurações para botões gerais
        style.configure('TButton',
                        background=BUTTON_BG,
                        foreground=BUTTON_FG,
                        font=FONT_DEFAULT,
                        relief='flat',
                        borderwidth=0,
                        padding=10)
        
        style.map('TButton',
                  background=[('active', BUTTON_HOVER_BG), ('pressed', BUTTON_HOVER_BG)],
                  foreground=[('active', BUTTON_FG)])
        
        # Configurações para Text widget (para tk.Text)
        style.configure('TText',
                        background=BG_LIGHT, 
                        foreground=TEXT_PRIMARY, 
                        font=FONT_LOG, 
                        relief='flat',
                        borderwidth=0)
        
        # Configurações para Scrollbar
        style.configure('Vertical.TScrollbar',
                        background=BG_DARK,
                        troughcolor=BG_MEDIUM,
                        gripcount=0,
                        bordercolor=BG_DARK,
                        arrowcolor=TEXT_PRIMARY)
        
        style.map('Vertical.TScrollbar',
                  background=[('active', TEXT_ACCENT)],
                  arrowcolor=[('active', BG_DARK)])

        # Estilo para TFrame
        style.configure('TFrame',
                        background=BG_MEDIUM, 
                        relief='flat',
                        borderwidth=0)


    def set_controller(self, controller: 'GameController'):
        """Define o Controller associado a esta View."""
        self.controller = controller

    def set_local_player_info(self, player_id: int, role: str):
        """Define o ID e papel do jogador local e atualiza a interface."""
        self.local_player_id = player_id
        self.local_player_role = role
        self.root.title(f"{GAME_TITLE} - Jogador {self.local_player_id}")
        
        role_str = "ESPIÃO" if self.local_player_role == "Espião" else "RESISTÊNCIA"
        role_color = TEXT_ACCENT if self.local_player_role == "Espião" else TEXT_PRIMARY
        self.player_info_label.config(text=f"Você é o Jogador {self.local_player_id} - {role_str}",fg=role_color)
        self.write_to_log(f"Seu ID de Jogador: {self.local_player_id}")
        self.write_to_log(f"Seu Papel: {role_str}")

    def _initialize_ui_components(self):
        """Cria e organiza todos os widgets da interface, com melhorias de design."""
        main_frame = tk.Frame(self.root, bg=BG_DARK) 
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Definindo as linhas do grid
        main_frame.grid_rowconfigure(0, weight=0) # Título
        main_frame.grid_rowconfigure(1, weight=0) # Espaçamento abaixo do título
        main_frame.grid_rowconfigure(2, weight=0) # Informações do Jogador
        main_frame.grid_rowconfigure(3, weight=0) # Espaçamento
        main_frame.grid_rowconfigure(4, weight=0) # Status do Jogo
        main_frame.grid_rowconfigure(5, weight=0) # Espaçamento
        main_frame.grid_rowconfigure(6, weight=0) # Botão de Ação
        main_frame.grid_rowconfigure(7, weight=1) # Área de Log (expansível)
        main_frame.grid_rowconfigure(8, weight=0) # Espaçamento no final

        # Definindo a única coluna central
        main_frame.grid_columnconfigure(0, weight=1) 

        # Título do Jogo
        self.title_label = tk.Label(main_frame, text=GAME_TITLE, font=FONT_TITLE, fg=TEXT_ACCENT, bg=BG_DARK)
        self.title_label.grid(row=0, column=0, pady=(0, 10), sticky="n")

        # Espaçamento abaixo do título
        tk.Frame(main_frame, height=10, bg=BG_DARK).grid(row=1, column=0)

        # Frame de Informações do Jogador (com borda arredondada simulada)
        player_info_container = tk.Frame(main_frame, bg=BG_DARK)
        player_info_container.grid(row=2, column=0, pady=5, padx=10, sticky="ew")
        player_info_container.grid_columnconfigure(0, weight=1)

        self.player_info_canvas = Canvas(player_info_container, bg=BG_DARK, highlightthickness=0, relief='flat', height=60)
        self.player_info_canvas.grid(row=0, column=0, sticky="nsew")
        self.player_info_canvas.bind("<Configure>", self._resize_player_info_canvas)
        
        self.player_info_label = tk.Label(self.player_info_canvas, text="ID do Jogador: N/A - Papel: Desconhecido", font=FONT_SUBTITLE, fg=TEXT_PRIMARY, bg=BG_MEDIUM)
        self._player_info_label_canvas_item = self.player_info_canvas.create_window(0, 0, window=self.player_info_label, anchor="center")

        # Espaçamento
        tk.Frame(main_frame, height=15, bg=BG_DARK).grid(row=3, column=0)

        # Frame de Status do Jogo
        self.status_frame = tk.Frame(main_frame, bg=BG_MEDIUM, padx=20, pady=10, relief="flat", bd=0)
        self.status_frame.grid(row=4, column=0, pady=10, padx=10, sticky="ew")
        self.status_frame.grid_columnconfigure(0, weight=1)
        self.status_frame.grid_columnconfigure(1, weight=1)
        self.status_frame.grid_columnconfigure(2, weight=1)
        self.status_frame.grid_columnconfigure(3, weight=1)

        self.round_label = tk.Label(self.status_frame, text="Rodada: 0/5", font=FONT_HEADING, fg=TEXT_PRIMARY, bg=BG_MEDIUM)
        self.round_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        self.success_label = tk.Label(self.status_frame, text="Sucessos: 0", font=FONT_HEADING, fg=TEXT_PRIMARY, bg=BG_MEDIUM)
        self.success_label.grid(row=0, column=1, padx=10, pady=5, sticky="w")

        self.fail_label = tk.Label(self.status_frame, text="Falhas: 0", font=FONT_HEADING, fg=TEXT_PRIMARY, bg=BG_MEDIUM)
        self.fail_label.grid(row=0, column=2, padx=10, pady=5, sticky="w")

        self.current_leader_label = tk.Label(self.status_frame, text="Líder Atual: N/A", font=FONT_HEADING, fg=TEXT_ACCENT, bg=BG_MEDIUM)
        self.current_leader_label.grid(row=0, column=3, padx=10, pady=5, sticky="e")

        # Espaçamento
        tk.Frame(main_frame, height=15, bg=BG_DARK).grid(row=5, column=0)

        # Botão de Ação Principal (usando ttk.Button)
        self.action_button = ttk.Button(main_frame, text="Aguardando Conexão...", command=self._on_action_button_click, style='TButton')
        self.action_button.grid(row=6, column=0, pady=(15, 25), ipadx=30, ipady=15)
        self.action_button.config(state=tk.DISABLED) 

        # Área de Log
        self.log_frame = ttk.Frame(main_frame) 
        self.log_frame.grid(row=7, column=0, padx=10, pady=10, sticky="nsew")
        self.log_frame.grid_rowconfigure(0, weight=1)
        self.log_frame.grid_columnconfigure(0, weight=1)

        self.log_text = tk.Text(self.log_frame, bg=BG_LIGHT, fg=TEXT_PRIMARY, font=FONT_LOG, relief="flat", bd=0, padx=15, pady=15, wrap=tk.WORD) 
        self.log_text.grid(row=0, column=0, sticky="nsew")
        self.log_text.config(state=tk.DISABLED) 

        self.log_scrollbar = ttk.Scrollbar(self.log_frame, command=self.log_text.yview, style='Vertical.TScrollbar')
        self.log_scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.config(yscrollcommand=self.log_scrollbar.set)

        # Espaçamento no final
        tk.Frame(main_frame, height=10, bg=BG_DARK).grid(row=8, column=0)

        # Timer Label (Adicionado para exibir o tempo restante)
        self.timer_label = tk.Label(self.root, text="", font=FONT_SUBTITLE, fg=TEXT_ACCENT, bg=BG_DARK)
        self.timer_label.place(relx=0.5, rely=0.03, anchor="n")

        self.update_view({})
        
        self.root.update_idletasks()
        self._resize_player_info_canvas(None)

    def show_mission_outcome_dialog(self, success: bool, sabotages_count: int):
        """Exibe um diálogo modal com o resultado da missão e o número de sabotagens."""
        if self.local_player_id:
            title = "Missão Bem-Sucedida!" if success else "Missão Falhou!"
            message = "A Resistência obteve sucesso na missão!" if success else f"Os Espiões sabotaram a missão com {sabotages_count} falha(s)!"
            MissionOutcomeDialog(self.root, title, message)

    def _on_action_button_click(self):
        """Callback para o botão de ação principal, com feedback visual."""
        if self.controller:
            original_text = self.action_button['text']
            self.action_button.config(text="Processando...", state=tk.DISABLED)
            
            style = ttk.Style()
            style.map('TButton', background=[('active', TEXT_ACCENT), ('!active', TEXT_ACCENT)],foreground=[('active', BG_DARK), ('!active', BG_DARK)])
            self.root.after(300, lambda: style.map('TButton', background=[('active', BUTTON_HOVER_BG), ('!active', BUTTON_BG)], foreground=[('active', BUTTON_FG), ('!active', BUTTON_FG)]))
            self.root.after(500, lambda: self.action_button.config(text=original_text, state=tk.NORMAL))
            self.root.after(500, self.controller.request_start_game)


    def _round_rectangle(self, canvas: Canvas, x1, y1, x2, y2, radius=25, **kwargs):
        """Desenha um retângulo com cantos arredondados."""
        points = [x1+radius, y1,
                  x2-radius, y1,
                  x2, y1,
                  x2, y1+radius,
                  x2, y2-radius,
                  x2, y2,
                  x2-radius, y2,
                  x1+radius, y2,
                  x1, y2,
                  x1, y2-radius,
                  x1, y1+radius,
                  x1, y1]
        
        return canvas.create_polygon(points, smooth=True, **kwargs)

    def _resize_player_info_canvas(self, event):
        """Redimensiona o retângulo arredondado no canvas de informações do jogador."""
        canvas_width = self.player_info_canvas.winfo_width()
        canvas_height = self.player_info_canvas.winfo_height()

        if canvas_width > 10 and canvas_height > 10:
            self.player_info_canvas.delete("round_rect")
            self._round_rectangle(self.player_info_canvas, 5, 5, canvas_width-5, canvas_height-5, radius=BORDER_RADIUS, fill=BG_MEDIUM, outline=BORDER_COLOR, width=2, tags="round_rect")
            if self._player_info_label_canvas_item:
                self.player_info_canvas.coords(self._player_info_label_canvas_item, canvas_width/2, canvas_height/2)
        
        self.player_info_canvas.tag_lower("round_rect")


    def write_to_log(self, text: str):
        """Escreve uma mensagem no log da interface."""
        self.log_text.config(state=tk.NORMAL) 
        self.log_text.insert(tk.END, text + "\n")
        self.log_text.see(tk.END) 
        self.log_text.config(state=tk.DISABLED) 

    def update_view(self, game_state: Dict[str, Any]):
        """Atualiza a View com o estado mais recente do Modelo recebido do servidor."""
        self.game_state_data = game_state

        current_round = self.game_state_data.get('current_round', 0)
        mission_sizes = self.game_state_data.get('mission_sizes', MISSION_SIZES) 
        self.round_label.config(text=f"Rodada: {current_round + 1}/{len(mission_sizes)}")
        self.success_label.config(text=f"Sucessos: {self.game_state_data.get('successful_missions', 0)}")
        self.fail_label.config(text=f"Falhas: {self.game_state_data.get('failed_failures', 0)}")
        leader_id = self.game_state_data.get('current_leader_id', 'N/A')
        self.current_leader_label.config(text=f"Líder Atual: Jogador {leader_id}")

        is_game_over = self.game_state_data.get('is_game_over', False)
        game_started = self.game_state_data.get('game_started', False)

        if is_game_over:
            self.action_button.config(state=tk.NORMAL, text="Jogar Novamente")
        elif game_started:
            self.action_button.config(state=tk.DISABLED, text="Jogo em Andamento...")
        else: 
            self.action_button.config(state=tk.DISABLED, text="Aguardando Outros Jogadores...")


    def show_team_selection_dialog(self, leader_id: int, mission_size: int, available_players_ids: List[int], callback: Callable[[List[int]], None], timeout: int = 60):
        """Exibe o diálogo de seleção de time e espera pelo input do líder local."""
        TeamSelectionDialog(self.root, leader_id, mission_size, available_players_ids, callback, timeout)

    def show_vote_dialog(self, player_id: int, team: List[int], callback: Callable[[bool], None], timeout: int = 30):
        """Exibe o diálogo de votação para o jogador local."""
        YesNoDialog(self.root, player_id, f"Você aprova a equipe {team}?", callback, timeout) 
        

    def show_sabotage_dialog(self, player_id: int, callback: Callable[[bool], None], timeout: int = 30):
        """Exibe o diálogo de sabotagem para o jogador espião local."""
        YesNoDialog(self.root, player_id, "Você quer SABOTAR a missão?", callback, timeout) 
        

    def show_game_over_dialog(self, winner: str):
        """
        Exibe o diálogo final de fim de jogo com mais detalhes,
        incluindo os resultados de todas as missões.
        """
        if self.local_player_id:
            mission_results = self.game_state_data.get('mission_results', [])
            resistance_wins = self.game_state_data.get('resistance_wins', 0)
            spy_wins = self.game_state_data.get('spy_wins', 0)
        
            formatted_results = [("Sucesso" if r else "Falha") for r in mission_results]
            
            GameOverDetailsDialog(
                self.root,
                winner,
                formatted_results,
                resistance_wins,
                spy_wins
            )


    def update_timer(self, remaining_time: int):
        """Atualiza a label do temporizador na View principal."""
        if remaining_time > 0:
            self.timer_label.config(text=f"Tempo: {remaining_time}s")
        else:
            self.timer_label.config(text="")