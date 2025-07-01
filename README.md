<body>
    <h1>The Resistance</h1>
    <p>Este projeto é uma implementação do jogo de dedução social e blefe "The Resistance", adaptado para ser jogado em uma rede local (LAN). Ele proporciona uma experiência interativa onde os jogadores assumem papéis de Resistência ou Espiões e participam de diversas fases do jogo, como seleção de equipes, votação e sabotagem de missões.</p>
    <h2>O Jogo "The Resistance"</h2>
    <p>
        "The Resistance" é um jogo de dedução social e blefe para 5 jogadores. O objetivo é para a equipe da Resistência (maioria) completar missões, enquanto os Espiões (minoria) tentam sabotá-las.
        <br>
        <strong>Papéis:</strong>
        <ul>
            <li><strong>Resistência:</strong> Trabalhadores leais; votam SUCESSO.</li>
            <li><strong>Espiões:</strong> Infiltrados; podem votar SUCESSO ou FALHA.</li>
        </ul>
        <strong>Fases do Jogo:</strong>
        <ol>
            <li>O Líder propõe uma equipe.</li>
            <li>Os jogadores votam para aprovar ou rejeitar a equipe.</li>
            <li>Se a equipe for aprovada, os membros da equipe votam SUCESSO ou FALHA.</li>
        </ol>
        <strong>Condições de Vitória:</strong>
        <ul>
            <li><strong>Resistência:</strong> Vence se 3 missões forem bem-sucedidas.</li>
            <li><strong>Espiões:</strong> Vencem se 3 missões falharem OU se 5 propostas de equipe forem rejeitadas consecutivamente.</li>
        </ul>
    </p>
    <h2>Arquitetura do Código: Model-View-Controller (MVC)</h2>
    <p>O projeto segue o padrão arquitetural MVC para uma clara separação de responsabilidades, facilitando o desenvolvimento, a manutenção e a escalabilidade.</p>
    <ul>
        <li><strong>Modelo (<code>src/models/model.py</code>):</strong> Gerencia o estado do jogo e a lógica de negócios. Não possui conhecimento da interface do usuário ou da rede.</li>
        <li><strong>Visão (<code>src/views/view.py</code>, <code>src/models/dialogs.py</code>, <code>src/main.py</code>):</strong> Responsável pela interface gráfica do usuário, exibindo o estado do jogo e coletando entradas do jogador.</li>
        <li><strong>Controlador (<code>src/controllers/controller.py</code>):</strong> Atua como intermediário, processando entradas do usuário, atualizando o Modelo e a Visão, e gerenciando a comunicação de rede.</li>
        <li><strong>Rede (<code>src/utils/network.py</code>, <code>src/models/messages.py</code>):</strong> Camada responsável pela comunicação cliente-servidor, definindo o protocolo de mensagens.</li>
    </ul>
    <h2>Funcionalidades do Código</h2>
    <h3>1. Modelo (<code>src/models/model.py</code>)</h3>
    <p>A classe <code>GameModel</code> encapsula todo o estado do jogo e suas regras. É o coração lógico do sistema.</p>
    <ul>
        <li>Gerencia a atribuição de papéis (Resistência e Espião) aos jogadores.</li>
        <li>Controla o placar das missões (sucessos e falhas).</li>
        <li>Acompanha a rodada atual, o líder e o contador de propostas de equipe rejeitadas.</li>
        <li>Processa votos de aprovação de equipe e escolhas de sabotagem.</li>
        <li>Verifica as condições de vitória e determina o vencedor.</li>
        <li>Oferece métodos para serializar e desserializar o estado do jogo (<code>to_dict</code> e <code>from_dict</code>), permitindo persistência.</li>
    </ul>
    <h3>2. Visão (<code>src/views/view.py</code> e <code>src/models/dialogs.py</code>)</h3>
    <p>Utiliza a biblioteca <code>tkinter</code> para construir a interface gráfica.</p>
    <ul>
        <li><code>GameView</code> (<code>src/views/view.py</code>): Exibe o placar, a rodada atual, o líder e um log de eventos do jogo.</li>
        <li><code>src/models/dialogs.py</code>: Contém classes para diálogos modais interativos (<code>TeamSelectionDialog</code>, <code>YesNoDialog</code>, <code>MissionOutcomeDialog</code>, <code>GameOverDetailsDialog</code>) que permitem aos jogadores realizar ações como selecionar equipes, votar e decidir sobre sabotagens.</li>
        <li>As configurações de estilo (cores, fontes, etc.) são definidas em <code>src/utils/settings.py</code> e aplicadas aos widgets <code>tkinter</code> e <code>ttk</code>.</li>
    </ul>
    <h3>3. Controlador (<code>src/controllers/controller.py</code>)</h3>
    <p>Orquestra o fluxo do jogo, agindo como um ponto central de controle.</p>
    <ul>
        <li>Inicializa o Modelo e a Visão.</li>
        <li>Atua como servidor ou cliente de rede, dependendo da configuração.</li>
        <li>Despacha mensagens de rede para os manipuladores apropriados.</li>
        <li>Coordena as fases do jogo, solicitando entradas dos jogadores (via View) e atualizando o Modelo.</li>
        <li>Responsável por salvar e carregar o estado do jogo, permitindo a retomada de partidas.</li>
    </ul>
    <h3>4. Rede (<code>src/utils/network.py</code> e <code>src/models/messages.py</code>)</h3>
    <p>Gerencia a comunicação entre os diferentes jogadores (clientes) e o servidor.</p>
    <ul>
        <li><code>Network</code> (classe base): Define a funcionalidade comum para enviar e receber mensagens via sockets TCP.</li>
        <li><code>GameServer</code>: Responsável por ouvir conexões, aceitar novos clientes e enviar mensagens para todos ou para clientes específicos.</li>
        <li><code>GameClient</code>: Responsável por conectar-se ao servidor e enviar/receber mensagens.</li>
        <li><code>src/models/messages.py</code>: Define as dataclasses para os diferentes tipos de mensagens trocadas no protocolo (ex: <code>ConnectAckMessage</code>, <code>GameStateUpdateMessage</code>, <code>RequestTeamSelectionMessage</code>, etc.).</li>
        <li>As mensagens são serializadas/desserializadas em formato JSON para transmissão.</li>
    </ul>
    <h2>Uso de Threads para Concorrência e Responsividade</h2>
    <p>O projeto faz uso extensivo de threads para garantir que a aplicação permaneça responsiva e para lidar com operações de I/O bloqueantes (como rede) de forma assíncrona. Isso evita o congelamento da interface do usuário.</p>
    <ul>
        <li><strong>Recebimento de Mensagens (<code>Network._receive_messages</code>):</strong> Tanto o servidor quanto o cliente dedicam uma thread para ouvir continuamente por mensagens de entrada. Isso impede que a espera por dados de rede bloqueie a execução de outras partes do programa.</li>
        <li><strong>Aceitação de Conexões (<code>GameServer._accept_connections</code>):</strong> No servidor, uma thread separada é responsável por aceitar novas conexões de clientes e iniciar um thread para lidar com a configuração inicial de cada um. Isso permite que o servidor continue operando enquanto aguarda novos jogadores.</li>
        <li><strong>Lógica Principal do Jogo (<code>GameController._run_game_logic_server</code>):</strong> No lado do servidor, a orquestração das fases do jogo (proposta de equipe, votação, missão) ocorre em uma thread dedicada (<code>self._game_logic_thread</code>). Isso é crucial para que os timeouts e esperas por respostas dos jogadores não bloqueiem o thread principal da interface gráfica.</li>
        <li><strong>Conexão do Cliente (<code>GameClient._connect_client_loop</code>):</strong> A tentativa de conexão do cliente ao servidor também é realizada em uma thread separada para evitar que a GUI congele durante o processo de estabelecimento da conexão.</li>
        <li><strong>Atualizações da GUI (<code>root.after</code>):</strong> Embora a lógica e a rede rodem em threads separadas, todas as interações com a interface gráfica (widgets <code>tkinter</code>) são agendadas para serem executadas no thread principal da GUI usando <code>self.root.after()</code>. Isso garante a segurança e consistência das operações de UI, prevenindo erros de concorrência.</li>
    </ul>
    <h2>Mecanismos de Sincronização (Locks, Semaphores e Queues)</h2>
    <p>Para gerenciar o acesso a recursos compartilhados e garantir a integridade dos dados em um ambiente multithreaded, o projeto emprega locks, semáforos e filas (queues) thread-safe.</p>
    <ul>
        <li><strong><code>threading.Lock</code> (<code>GameServer._lock</code>):</strong> Utilizado em <code>src/utils/network.py</code> para proteger o dicionário <code>self.clients</code>, que armazena os sockets conectados. Isso impede condições de corrida quando múltiplos threads (ex: o thread que aceita conexões e o thread que envia mensagens) tentam modificar a lista de clientes simultaneamente, garantindo a integridade dos dados da conexão.</li>
        <li><strong><code>threading.Lock</code> (<code>GameController._current_phase_lock</code>):</strong> Em <code>src/controllers/controller.py</code>, este lock é fundamental para sincronizar o acesso e a modificação do <code>GameModel</code>. Ele garante que apenas uma operação (seja da thread de lógica do jogo ou de um manipulador de mensagens de rede) possa modificar o estado do jogo em um dado momento. Isso previne condições de corrida e garante a consistência lógica do jogo.</li>
        <li><strong><code>threading.Semaphore</code> (<code>GameServer._client_setup_semaphore</code>):</strong> Adicionado em <code>src/utils/network.py</code>, este semáforo é utilizado para limitar o número de threads que podem realizar a configuração inicial de novas conexões de clientes simultaneamente (definido por <code>_max_concurrent_client_setup</code>, por exemplo, 3). Cada thread que lida com uma nova conexão (<code>_handle_new_client_connection</code>) adquire uma permissão do semáforo antes de prosseguir com a configuração, bloqueando se o limite for atingido. Isso ajuda a prevenir a sobrecarga do servidor em caso de muitas conexões simultâneas.</li>
        <li><strong>Filas Thread-Safe (<code>queue.Queue</code>):</strong>
            <ul>
                <li><code>self.message_queue</code> (em <code>src/utils/network.py</code>): Usada por ambas as classes <code>GameServer</code> e <code>GameClient</code> para armazenar mensagens de rede recebidas de forma thread-safe.</li>
                <li><code>self.team_selection_response_queue</code>, <code>self.vote_response_queues</code>, <code>self.sabotage_response_queues</code> (em <code>src/controllers/controller.py</code>): Estas filas são usadas para coletar as respostas dos diálogos da GUI (que são executados no thread principal) e passá-las de volta para a thread de lógica do jogo. Elas garantem que as respostas sejam transmitidas de forma ordenada e thread-safe.</li>
            </ul>
        </li>
    </ul>
    <h2>Como Executar</h2>
    <p>Para executar o jogo, siga os passos abaixo:</p>
    <ol>
        <li>Certifique-se de ter Python 3.12 instalado.</li>
        <li>Navegue até o diretório raiz do projeto no terminal.</li>
        <li>
            <p><strong>Para iniciar o Servidor:</strong></p>
            <pre><code>python -m src.main</code></pre>
            <p>Selecione a opção "Servidor (Host)" no menu principal. O servidor ficará ouvindo na porta <code>12345</code> (definida em <code>src/utils/settings.py</code>).</p>
        </li>
        <li>
            <p><strong>Para conectar como Cliente:</strong></p>
            <pre><code>python -m src.main</code></pre>
            <p>Selecione a opção "Cliente (Entrar)" e digite o IP do servidor (Ex: <code>127.0.0.1</code> para jogar na mesma máquina, ou o IP da máquina host na rede). O cliente tentará conectar na porta <code>12345</code>.</p>
        </li>
        <li>O jogo requer 5 jogadores (definido em <code>NUM_PLAYERS</code> em <code>src/utils/settings.py</code>). Conecte os clientes necessários.</li>
        <li>No servidor, o botão "Iniciar Jogo" ficará ativo quando <code>NUM_PLAYERS</code> jogadores estiverem conectados.</li>
    </ol>
</body>