# FL26 Mod Studio — guia de uso

> [English](../en/mod-studio-guide.md) · [hrvatski](../hr/mod-studio-guide.md) · [español](../es/mod-studio-guide.md) · **português** · [français](../fr/mod-studio-guide.md)

> **Novo no Mod Studio?** Dois guias passo a passo, cada clique em ordem: [Instalar um pacote pronto](install-a-pack.md)
> (alguém te passou um mundo, um modpack ou um `.fl26pack`) · [Criar suas próprias ligas e pacotes](make-your-own-leagues.md)
> (você escolhe as ligas e constrói elas). Este guia explica cada página e opção em detalhe.

> Perguntas comuns (atualizar, crash ao iniciar, copas, acesso, o que mandar quando algo dá
> errado): [faq.md](../../docs/faq.md) (em inglês) · perguntas e ajuda no [Discord](https://discord.gg/StQqtk3G3M)

O FL26 Mod Studio é um programa só para tudo o que você adiciona ao Football Life 2026:

- os **mods** que você baixa: estádios, uniformes, bolas, placares, narração, música, rostos,
  módulos Lua;
- os **servidores de conteúdo** que servem esses mods (Stadium Server, Ball Server, Kit Server e
  os outros), com os arquivos map editados como tabelas em vez de à mão;
- a própria **configuração do Sider**: quais pastas de conteúdo e módulos estão ligados, e em que
  ordem;
- **ligas e clubes novos** (o League Builder), as suas mudanças nas ligas, clubes e **jogadores**
  do próprio jogo, e **pacotes de ligas** que um modder faz uma vez e qualquer pessoa adiciona ao
  jogo dela.

Nada do jogo é sobrescrito. Antes de mudar um arquivo o programa guarda uma cópia, e cada mod que
ele instala pode ser removido de novo.

---

## 1. Antes de começar

- **Football Life 2026** instalado, com a pasta `SiderAddons` (o FL26 vem com o Sider).
- Descompacte o programa onde quiser, por exemplo `Documents\FL26 Mod Studio`. Deixe a pasta
  inteira junta: as pastas `_internal` e `pack` e os arquivos `README` ficam ao lado do
  `FL26ModStudio.exe`.
- **Feche o jogo** enquanto muda as coisas. O Sider lê a configuração quando o jogo inicia.

A janela está em inglês. **Idioma (Language)** na barra de cima (ou **Configurações → Idioma
(Language)**; em inglês ele se chama *Language*) troca para croata (Hrvatski), espanhol (Español),
português do Brasil (Português) ou francês (Français). O idioma novo aparece na próxima vez que
você abrir o Mod Studio. Este guia usa os nomes que o programa mostra em português.

## 2. Primeira execução

**O tour rápido.** Na primeira vez que você abre a 0.2.4, um pequeno cartão mostra onde tudo está
agora, um lugar por vez, com uma moldura laranja em volta do que ele está explicando: o idioma, as
caixas do que está no jogo, **Iniciar o jogo**, depois de **1. Início** até **5. Configurações**
e **Ajuda**. Dez passos. Nada é mudado enquanto ele roda. **Próximo** e **Voltar** andam por ele,
**Pular o tour** fecha, e **Ajuda → Tour rápido** mostra ele de novo a qualquer hora. O último
cartão tem **Me mostre como instalar um Modpack**: um segundo cartão que leva você pela instalação de
um Modpack (um zip de mundo), clique por clique (também em **Ajuda → Instalar um Modpack, passo a
passo**).

1. **5. Configurações → Pasta do jogo**: aperte **Procurar...**, escolha a pasta que tem o
   `FL_2026.exe`, depois **Usar esta pasta**. A linha embaixo diz o que foi encontrado, por
   exemplo `Encontrado: FL_2026.exe, Sider em SiderAddons, sider.ini.`
2. As tabelas do jogo: o Mod Studio extrai elas sozinho na primeira vez (ele lê os clubes, ligas
   e jogadores do jogo para uma pasta de trabalho; isso leva um ou dois minutos, e a barra de
   baixo avisa). Depois de uma atualização do jogo, a construção percebe e oferece extrair elas
   de novo antes; **Configurações → As tabelas do jogo → Extrair as tabelas do jogo** faz isso à
   mão. **Usar outra pasta de tabelas...** é para uma base de dados sua, como uma pasta `pesdb`
   no livecpk: extraia antes as tabelas do jogo, depois escolha essa pasta. Os arquivos dela vão
   por cima dos do jogo, que dão o que ela não tem. Um mod de base de dados que move as ligas do
   jogo para os lugares de outras ligas (UML 2026 e parecidos) funciona: cada liga do jogo pega o
   país da maioria dos clubes dela, e o NewLife Database só conta um clube como do jogo quando
   essas tabelas têm ele (0.2.4).
3. Abra **1. Início**. Ele mostra o mundo que está no jogo (**NO JOGO AGORA**, com **Abrir os
   campeonatos dele** e **Trocar de mundo...**, que abre **2. Meu mundo**), um cartão que diz se o
   seu mundo tem mudanças que o jogo ainda não tem (**Ir para Construção** e **Só as copas
   europeias...**), e a **Verificação geral**: uma tabela com uma linha por verificação (jogo,
   Sider, módulos, pastas de conteúdo ...). Quando algo está errado, uma barra vermelha diz o
   problema e tem o botão que resolve. Quando os módulos do Mod Studio estão faltando, são mais
   antigos ou estão desligados, a linha diz quais, e **Instalar agora** coloca eles. À direita:
   **Ações rápidas** (**Instalar os módulos**, **Construir o mundo de novo**, **Importar um zip
   de mundo**, **Adicionar um pacote de campeonatos**) e **Últimas alterações** (os pontos de
   restauração mais novos, **Todos os pontos de restauração**).

**Atualizações.** Alguns segundos depois de abrir, o programa pergunta ao GitHub se saiu um FL26
Mod Studio mais novo, e só avisa quando há um. **Baixar e instalar** baixa o zip novo, confere ele
com o checksum da versão, fecha o programa, coloca os arquivos novos por cima dos antigos e abre
ele de novo. As suas configurações, mundos, pontos de restauração e o jogo não são mexidos.
**Ajuda → Procurar atualizações...** pergunta a qualquer hora; desmarque **Ajuda → Procurar
atualizações ao iniciar** e o programa só pergunta nessa hora. Se o programa estiver numa pasta
onde o Windows não deixa ele escrever (como Arquivos de Programas), ele abre a página da versão:
descompacte o zip você mesmo, ou mova o programa para uma pasta sua.

**Carreiras de antes da 0.2.0.** A 0.2.0 deixa um dia do calendário ter 792 jogos em vez de 280,
e isso muda as tabelas com que uma carreira é salva: **uma carreira salva com uma versão mais
antiga não carrega** (ela fica na tela de carregamento). Comece uma carreira nova depois da
atualização. Os seus mundos e os dados do Edit não são afetados.

**A 0.2.4 e a sua carreira.** Uma carreira salva com a 0.2.2 ou a 0.2.3 continua funcionando, e
uma copa salva antes da 0.2.4 também carrega. Uma correção precisa de uma construção nova: até a
0.2.4 o goleiro era o capitão de todos os clubes de um mundo feito com o Mod Studio. A
**construção** agora dá a cada clube e seleção que não tem um capitão e jogadores que batem os
pênaltis, as faltas e os escanteios. Para ter isso, **construa** o seu mundo de novo e comece uma
carreira nova.

**Jogar.** O botão **Iniciar o jogo** no canto superior direito (ou **Jogo → Iniciar o jogo**)
inicia o jogo e avisa antes quando há módulos na ordem errada. Ao lado dele, uma etiqueta diz se
está tudo pronto: **PRONTO PARA JOGAR**, **NÃO ESTÁ PRONTO** ou **AINDA SEM MUNDO**. **Jogo →
Iniciar o jogo sem mods (modo seguro)...** coloca de volta a configuração que o Mod Studio
encontrou na primeira vez.

**Créditos.** O botão **Créditos** ao lado de **Ajuda** lista todos que ajudaram a fazer o Mod
Studio: os testadores, as pessoas que mandaram relatórios e logs, e aquelas cujas ideias estão
nele.

**Mais de uma pasta do Sider?** O Sider não precisa se chamar `SiderAddons`. O programa procura,
ao lado do `FL_2026.exe`, a pasta que tem um `sider.ini`, e também um nível mais abaixo
(`sider\patch 1`, `sider\patch 2` ... quando uma pasta tem algumas cópias do Sider). Se houver
várias, **Configurações → Pasta do Sider** escolhe em qual ele trabalha; as outras não são
mexidas.

**Jogo dentro de Arquivos de Programas.** O Windows só deixa um programa rodando como
administrador mudar arquivos ali. Quando o Mod Studio não consegue escrever na pasta do jogo, ele
avisa (no **Início** também) e oferece **Reiniciar como administrador**. Ou mova o jogo para uma
pasta sua.

## 3. As páginas

No topo da janela, da esquerda para a direita:

- os menus **Arquivo**, **Jogo**, **Perfis**, **Idioma (Language)** e **Ajuda**, e **Créditos**;
- o botão **Iniciar o jogo** com a etiqueta de pronto ao lado;
- embaixo deles, caixas com o que está no jogo agora: **PASTA DO JOGO**, **SIDER**, **MUNDO
  ATIVO**, **MÓDULOS**, **CAMPEONATOS** e **PACK**. Uma caixa vermelha diz o problema; clique numa
  caixa para ir à página onde ele se resolve;
- depois as seções numeradas, e embaixo da janela uma barra de status (pronto ou o problema, o
  que o programa está fazendo, **Seu mundo está salvo**, o número de pontos de restauração).

| Seção | O que tem nela |
|---|---|
| **1. Início** | O mundo que está no jogo, a verificação geral, ações rápidas |
| **2. Meu mundo** | Os seus mundos como cartões, e as abas **Construção**, **Campeonatos**, **Clubes**, **Jogadores**, **Uniformes**, **Estádios** e **Copas** (seção 3.1) |
| **3. Conteúdo do jogo** ▾ | **Bolas**, **Narração**, **Música**, **Outro conteúdo** |
| **4. Ferramentas** ▾ | **Módulos Lua**, **Pastas de conteúdo**, **Perfis**, **Pontos de restauração**, **Diagnóstico** |
| **5. Configurações** | Pasta do jogo, pasta do Sider, idioma, carreiras da Master League, as tabelas do jogo |

**Arquivo** tem **Mundo novo**, **Abrir um mundo...**, **Salvar seu mundo como...**, **Mudanças
neste mundo...** (tudo o que o seu mundo muda no jogo numa lista só; escolha linhas e aperte
**Desfazer as mudanças escolhidas** para voltar atrás nelas), **Adicionar um pacote de
campeonatos...** e **Criar um pacote de campeonatos...**. **Jogo** abre a pasta do jogo, a pasta
do Sider, o `sider.ini` e o `sider.log`, e inicia o jogo. **Ajuda** tem **Guia de uso**, **Tour
rápido**, **Instalar um Modpack, passo a passo**, **Editar um Modpack, passo a passo**, **Procurar atualizações...** e **Sobre o FL26 Mod
Studio**.

### 3.1 Meu mundo

**2. Meu mundo** é o lugar dos seus mundos. Um **mundo** é uma pasta de conteúdo chamada
`_FL26...` que tem ligas, clubes e jogadores novos; o jogo lê um por vez (seção 8).

**No topo**: **Competições** (quantas competições, ligas e copas juntas, o mundo que está no jogo
tem; o jogo tem espaço para 255), **Países novos** (quantos países ele adiciona; espaço para 99),
um lembrete de que **as mudanças pedem uma Master League nova**, e o estado do mundo aberto.
**▾ Mundos** recolhe a fila de cartões para dar espaço, e mostra ela de novo.

**Os cartões**: um cartão para cada mundo no disco. O mundo que está no jogo vem primeiro, depois
os mais novos; a roda do mouse move a fila para a esquerda e para a direita.

- O mundo que está no jogo é verde, com **● NO JOGO AGORA** e **● Ativo**. Um mundo instalado de
  um zip tem a etiqueta **De um zip**.
- Cada outro mundo construído (**NÃO ESTÁ NO JOGO**) tem **▶ Ativar**: coloca esse mundo no jogo
  (ligado no `sider.ini`) e tira o que estava no jogo. Nada é apagado: o outro mundo fica no disco
  com as próprias carreiras. Comece uma Master League nova depois.
- Todo cartão tem **Exportar...** (um `.zip` do mundo para outro PC, seção 9.1), **Renomear** e
  **Apagar**. **Apagar** tira o mundo do jogo e do disco, mas guarda ele inteiro em **Pontos de
  restauração** (seção 5). O mundo que está no jogo não pode ser apagado: ative outro mundo antes.
- **+ Mundo novo** no fim começa um mundo vazio seu (o mesmo que **Arquivo → Mundo novo**);
  depois adicione as ligas dele em **Campeonatos**.

Se dois mundos estiverem ligados ao mesmo tempo, o cartão verde diz **▶ Manter só este**: ele
mantém esse mundo no jogo e desliga os outros.

**As abas** embaixo dos cartões mudam o mundo aberto: **Construção** (seção 8.2),
**Campeonatos**, **Clubes** e **Jogadores** (seção 8), **Uniformes** e **Estádios** (seção 6).
**Copas ▾** abre as janelas das copas: **Torneios de pré-temporada**, **Taças dos nossos países**,
**Copas dos países do jogo** e **Nomes das competições**. À direita:

- **NewLife Database** abre a página do NewLife (seção 8.4);
- **+ Adicionar...** é uma janela só para três coisas: um zip de mundo (um Modpack), um pacote de
  liga (`.fl26pack`) e o NewLife Database (uma pasta ou os zips dele). Solte o arquivo nela ou use
  **Escolher um arquivo...** / **Escolher uma pasta...**. Ela diz numa linha verde o que
  encontrou; para um pacote de liga ela lista as ligas para marcar e quantas competições o mundo
  vai ter. **Adicionar** entrega para a página certa: um zip de mundo para **Importe seu mundo**
  (seção 4), um pacote para dentro do seu mundo, o NewLife Database para a página dele. Nada chega
  ao jogo antes de **Construir e instalar**;
- **Mais ▾** tem **Pacotes de campeonatos** (seção 9), **Importar um zip de mundo** (seção 4),
  **NewLife Database** e **Pastas de conteúdo** (seção 5).

**Um mundo de um zip** (um Modpack) já está construído, então a **construção** fica desligada para
ele (seção 8.2). Para mudar ele mesmo assim, **Torná-lo editável...** no topo de Meu mundo
transforma ele num mundo seu, no mesmo lugar e com o próprio nome. Ele é copiado inteiro para
**Pontos de restauração** antes. Depois de construir, comece uma Master League nova.
**Ajuda → Editar um Modpack, passo a passo** mostra isso clique a clique.

**Cada mundo guarda as próprias carreiras da Master League** (0.2.4). Uma carreira é feita para um
mundo: em outro mundo as ligas e os clubes dela não existem. Por isso, cada vez que o mundo do jogo
muda (**Ativar**, **Construir e instalar** de outro mundo, Importe seu mundo, Pastas de conteúdo,
um perfil), o Mod Studio troca junto a pasta de saves do jogo. As carreiras do mundo que sai ficam
guardadas em `save_<mundo>`, ao lado de `save`, em `Documents\KONAMI\eFootball PES 2021 SEASON
UPDATE\2026`. As carreiras do mundo que entra voltam para `save`; um mundo que ainda não tem
nenhuma começa com uma vazia. A pasta inteira vai com o mundo (carreiras, Become a Legend, os
dados do Edit), menos as configurações do jogo, que vão com você para todos os mundos.

Nada é apagado: antes da primeira troca o Mod Studio copia a sua pasta de saves inteira para
`SiderAddons\ModStudio\backups\saves\<data>` (**Pontos de restauração** lista ela), e na primeira
vez ele diz para onde as suas carreiras foram. Ele não troca enquanto o jogo está rodando, nem
quando já existe uma pasta `save_<mundo>` com esse nome: ele diz por quê e não muda nada.
**Renomear** renomeia também o `save_<mundo>` do mundo; **Apagar** deixa ele em paz (as carreiras
são suas). Não quer isso? Desmarque **Configurações → Cada mundo guarda as próprias carreiras (a
pasta de saves troca junto com o mundo)**.

**Campeonatos** (uma aba de Meu mundo) lista todas as ligas, as do jogo e as suas, embaixo do
continente delas; as divisões de cada país ficam juntas, de cima para baixo (Bundesliga, 2.
Bundesliga, 3. Liga), até você arrastar uma liga para outro lugar. Filtros **Todos**, **Nossos** e
**Alterado**, e uma caixa de busca. Escolha uma: uma liga sua tem **Editar campeonato...**,
**Adicionar divisão inferior**, **Clubes e nomes**, **Jogadores** e **Remover**; uma liga do jogo
tem o nome, o logo e os clubes dela (seção 8, "As ligas do jogo"). **Adicionar campeonato** cria
uma nova. **Lugares em Select Team** mostra onde a última construção colocou cada uma das suas
ligas. **Mais ▾** tem **Torneios de pré-temporada**, **Taças dos nossos países**, **Copas dos
países do jogo**, **Vagas continentais dos campeonatos do jogo**, **Clubes europeus da primeira
temporada**, **Ranking da UEFA**, **Vagas sul-americanas**, **Nomes das competições**, **IDs das
competições**, **Ordem dos campeonatos**, **Temporadas dos campeonatos do jogo** e **Nome do
mundo e arquivo...**. Este último abre a página com o nome do mundo e a lista das suas ligas
(guias mais antigos chamam ela de *Campeonatos novos*).

## 4. Importe seu mundo

**Importe seu mundo** é a página que instala um pacote baixado. Chegue nela com **2. Meu mundo →
Mais ▾ → Importar um zip de mundo**, com **Importar um zip de mundo** em **Ações rápidas** no
**Início** (abre a escolha de arquivo na hora), ou com **+ Adicionar...** em Meu mundo.

Solte o pacote nela (`.zip`, `.7z`, uma pasta, `.lua`, `.cpk` ou `.fl26pack`), ou use **Escolher
um arquivo...** / **Escolher uma pasta...**. Quando o Mod Studio roda como administrador, o
Windows bloqueia o arrastar e soltar; a página avisa: use os dois botões.

O programa olha dentro e diz numa linha o que é: uma versão mais nova de um mundo que você tem, um
mundo pronto para jogar, um pacote de liga ou um mod, com as ligas que tem dentro. Depois, um
botão só: **Instalar** (**Instalar o mundo** para um mundo). Uma versão mais nova de um mundo que
você tem substitui a mais antiga: ele pergunta uma vez, a antiga sai primeiro para que nada dela
fique para trás, os seus saves não são mexidos, e você começa uma Master League nova com a nova.
Se um mundo com o mesmo nome foi construído neste PC, ele avisa antes de você apertar Instalar e
pede para renomear esse mundo no cartão dele em Meu mundo antes.

As partes, e para onde cada uma vai, estão na parte que abre **Mais opções: quais partes, nome,
ordem das pastas de conteúdo, linhas dos map**:

| Parte | O que acontece |
|---|---|
| Pasta de conteúdo (livecpk) | Copiada para `SiderAddons\livecpk\<nome>` e adicionada ao `sider.ini`. |
| Arquivos de servidor de conteúdo | Copiados para a pasta `content` do servidor. O **arquivo map dele é juntado com o seu**: as suas linhas ficam e as linhas novas do mod são adicionadas. Para um clube que você já mapeou, a escolha em **Mais opções** decide: *use the mod's* (usar a do mod), ou *keep mine, add the mod's after* (manter a minha, adicionar a do mod depois). Um pack de placar ou de menu feito para outro mundo vai para a competição que o nome dele diz no seu mundo, e a página diz qual liga o seu mundo não tem. |
| Módulo Lua | Copiado para `SiderAddons\modules` e ligado no lugar certo da ordem. |
| .cpk empacotado | Descompactado numa pasta de conteúdo na instalação. |
| Pacote de liga | Adicionado ao seu mundo (seção 9). Um `.fl26pack` solto aqui entra, e **Construir e instalar** começa sozinho. |
| Mundo pronto | Um mundo construído vindo de **Exportar o mundo** (seção 9.1), ou uma pasta `SiderAddons` copiada com `modules\fl26world.txt`. A pasta do mundo é copiada com o próprio nome, o arquivo do mundo vai para `SiderAddons\modules`, e o mundo é colocado no jogo com os módulos do Mod Studio. Termina com **✓ Pronto para jogar: aperte Iniciar o jogo e comece uma Master League nova** e uma lista final de verificação: o mundo, ligado, os módulos, o pacote de rostos, os servidores de conteúdo que o mundo usa, os estádios dos mandantes. Se faltar algo ele diz **Quase pronto** e o que corrigir; a linha vermelha embaixo da instalação (*see what to fix*) mostra a lista de novo. |
| DLL | **Não é instalada.** Uma DLL roda com os direitos do jogo; instale uma só de uma fonte em que você confia, à mão. |

Na mesma parte você pode desmarcar uma parte que não quer (os uniformes, por exemplo, para
instalar um mundo sem uniformes), dar um nome ao mod, e escolher se as pastas de conteúdo novas vão
para o topo (elas ganham) ou para o fim. **No jogo agora** lista cada pacote instalado com o
programa. **Remover** apaga os arquivos que ele adicionou e coloca de volta os arquivos que ele
substituiu.

A instalação copia todos os arquivos primeiro e escreve as linhas dos map por último, então uma
instalação que para no meio não deixa nenhuma linha apontando para um arquivo que falta. Se isso
aconteceu com uma versão mais antiga, o **Diagnóstico** diz o nome do zip ou do mundo: instale ele
de novo (um mundo construído no seu PC: construa ele de novo).

## 5. Pastas de conteúdo e módulos Lua

**Pastas de conteúdo** (**4. Ferramentas**) lista as linhas `cpk.root` do `sider.ini`; os mundos
(`_FL26...`) aparecem quando você marca **Mostrar os mundos (_FL26...)**, e **Só ativadas**
esconde o resto. O mundo que o jogo usa agora fica numa linha verde, com o nome em negrito e
**NO JOGO AGORA** na coluna Nota. O Sider procura um arquivo de cima para baixo, então a pasta mais
alta na lista ganha quando duas têm o mesmo arquivo.

- Marque ou desmarque uma pasta para ligar ou desligar ela (a linha vira comentário, nunca é
  apagada).
- **Para o topo**, **Subir**, **Descer** mudam a ordem; **Adicionar pasta...** adiciona uma pasta
  que você já tem.
- O tamanho e o que tem dentro (rostos, uniformes, estádios...) aparecem para cada pasta.
- **Escanear de novo**, **Remover da lista** e **Apagar do disco...** também estão ali.
- Nada é escrito até você apertar **Aplicar**. **Descartar** esquece as mudanças.

**Renomear mundo...** e **Apagar mundo...** (embaixo dos detalhes da pasta quando um mundo está
escolhido, ou com o botão direito no mundo) fazem o mesmo que **Renomear** e **Apagar** no cartão
de um mundo em Meu mundo:

- **Apagar mundo...** pergunta antes e não apaga nada para sempre. A pasta do mundo, os uniformes
  e placares dele, as linhas dele no `sider.ini` e nos map de uniformes e placares, e o registro
  da instalação vão para `SiderAddons\ModStudio\backups\worlds\<mundo>\<data> deleted`, e **Pontos
  de restauração → Restaurar esta cópia** traz tudo de volta exatamente como era. As 3 últimas
  cópias de cada mundo são guardadas. O mundo que está no jogo (o verde) não pode ser apagado. O
  seu mundo no Mod Studio (as ligas dele) não é apagado, então você pode construir ele de novo.
  **Apagar do disco...** numa linha de mundo faz o mesmo apagar seguro.
- **Renomear mundo...** muda o nome em todo lugar onde ele está escrito: a linha do `sider.ini`
  (mesmo lugar, ligada ou desligada como estava), as pastas de uniformes e placares e as linhas
  dos map delas, o arquivo do mundo, os seus perfis e o seu mundo no Mod Studio. O nome novo tem
  que começar com `_FL26` (letras, números, `-` e `_`). Um mundo grande é renomeado em segundo
  plano ("Renomeando ..." na barra de baixo e no cartão dele). Uma carreira continua funcionando
  depois de renomear: o jogo nunca vê o nome do mundo, só os arquivos dentro dele.

**Módulos Lua** (**4. Ferramentas**) é o mesmo para as linhas `lua.module`. A linha no topo diz se
os módulos do próprio Mod Studio estão instalados, atualizados e ligados; quando não estão, ela diz
quais faltam, são mais antigos ou estão desligados, e **Instalar agora** resolve. O programa sabe a
ordem certa dos módulos comuns (os servidores de conteúdo depois dos módulos que eles usam) e avisa
quando um módulo está no lugar errado. Alguns módulos precisam de uma configuração do Sider (por
exemplo o Goal Song Server precisa de `match-stats.enabled = 1`); o programa diz qual. Os módulos
`fl26...` do próprio Mod Studio ficam escondidos até você desmarcar **Esconder os módulos
próprios do Mod Studio (fl26...)**; **Adicionar módulo...** adiciona um módulo que você tem.

Os módulos do próprio Mod Studio mantêm a ordem em que foram instalados, juntos num bloco do
`sider.ini` com um título próprio. Linhas antigas deixadas por uma instalação à mão (um conjunto
caps antigo, um módulo listado duas vezes) são desligadas por **Instalar agora** e pela
construção.

Desde a 0.2.0 as doze pequenas proteções contra crash entram como dois arquivos,
`fl26guards.lua` (as oito `fl26nullguard`) e `fl26lateguards.lua` (`fl26superguard`,
`fl26resultsguard`, `fl26ctlguard`, `fl26kitguard`), então a lista fica mais curta. O sider.log
ainda diz o nome de cada proteção numa linha própria. A construção desliga as linhas antigas
separadas; não há nada para fazer à mão.

**Sem cópias ao lado dos seus arquivos** (0.2.4). Quando Construir, Ativar ou Instalar os módulos
mudam um arquivo, a cópia de antes vai para `SiderAddons\ModStudio\backups` e aparece em **Pontos
de restauração**, não ao lado do arquivo (acabaram os `map.txt.before-builder` ou
`modules\before-builder-<n>`).

**Desligar os regens** (0.2.0): o `fl26regen` dá aos regens nomes novos, um potencial novo e um
rosto do pack de rostos de regens. Para jogar sem ele, desmarque **Esconder os módulos próprios do
Mod Studio (fl26...)** para os nossos aparecerem, desmarque `fl26regen` e aperte **Aplicar**. O
Mod Studio anota isso em `modules\fl26-off.txt` na pasta do Sider, então a construção, **Instalar
os módulos** e a troca de mundos deixam ele desligado em vez de ligar de novo, como fazem com
qualquer outro módulo. O jogo então faz os próprios regens: o próprio potencial e nomes, sem
rostos do pack de rostos de regens. Marque de novo e **Aplicar** para ligar ele de volta. Só o
`fl26regen` pode ficar desligado desse jeito.

## 6. Conteúdo do jogo: os servidores de conteúdo

Cada uma destas páginas pertence a um servidor de conteúdo. **Uniformes** e **Estádios** são abas
de **2. Meu mundo**; **Bolas**, **Narração**, **Música** e **Outro conteúdo** estão em **3.
Conteúdo do jogo**. **Outro conteúdo** tem uma aba para cada: **Placares**, **Menus**,
**Uniformes de arbitragem**, **Patches de manga** e **Clima**, e **Módulos de visual**. Os
módulos próprios do SPFL26 para uniformes, estádios e placares (`common\kits.lua`,
`common\stadiums.lua`, `common\scoreboards.lua`) leem os mesmos arquivos de `content\kits`,
`content\stadiums` e `content\scoreboards`; quando o servidor em si não está instalado, a página
dele edita esses arquivos (uniformes desde a 0.1.7, estádios e placares desde a 0.1.8). Toda
página tem:

- uma **linha de status**: o módulo está ligado, a pasta de conteúdo dele existe;
- uma aba por **arquivo map**, mostrado como tabela: qual competição, clube ou estádio recebe o
  quê. **Adicionar...**, **Mudar...**, **Copiar**, **Ativ. / desativ.** (a linha vira comentário)
  e **Remover**; escolha itens da biblioteca em vez de digitar ids. **Salvar** escreve o arquivo;
  a cópia de antes vai para os Pontos de restauração;
- a **Biblioteca**: o que está na pasta de conteúdo do servidor, com imagens onde houver. Itens que
  nenhuma linha do map usa e linhas do map que apontam para itens que faltam ficam marcados;
- as **Configurações** do servidor onde ele tiver (estádio, bola, placar favorito ...).

O programa confere as tabelas antes de salvar: um número onde vai um número, nenhuma vírgula
dentro de um nome, um item que existe. Uma linha com problema fica colorida: **deixe o mouse sobre
ela para ver por quê**. **Só linhas com problemas** mostra só essas. Um clube listado duas vezes
também fica marcado: só a primeira linha dele conta. O problema mais comum, "... não está na
biblioteca", quer dizer que a linha aponta para uma pasta que não está na pasta de conteúdo do
servidor, e o jogo não mostra nada ali (um estádio preto, o uniforme antigo do clube): aponte ela
para uma pasta que a aba **Biblioteca** lista, ou tire a linha. **Módulos de visual** (em **Outro
conteúdo**) liga ou desliga módulos que não têm arquivos map.

Uma linha de competição é ligada a uma **fase** da competição, não à competição: o jogo diz aos
servidores de conteúdo a fase que está jogando (a Conference League é 186, 1210, 187, 189 e as
rodadas seguintes 1213 ... 8381; a Champions League 2, 3, 4 e as dela), então uma linha com o
número da própria competição (174) nunca é usada. A escolha de competição lista cada competição
mais uma vez como **(todas as fases: N)**: escolha essa e uma linha é escrita para cada fase
(0.1.9). Uma linha ligada a um número de competição fica marcada como problema.

**Placares de um mundo de um zip.** Um mundo pronto (o Modpack) traz os placares das ligas dele.
Enquanto outro mundo está no jogo, as linhas deles ficam em **Outro conteúdo → Placares**,
desligadas, e voltam a ligar com o mundo delas. O mesmo vale para os temas de menu que um mundo
trouxe.

**Importar uniformes...** (0.1.8, na aba *Uniformes*): uniformes para muitos clubes de uma vez.
Escolha uma pasta de uniformes prontos de kit-server -- uma pasta por clube, com `p1`, `p2`, `g1`
... e `order.ini`, com o nome do clube (`Dinamo Zagreb`) ou o ID do clube (`2215`). **Ligar a**
escolhe *Todos os clubes* ou *Os clubes novos do mundo do jogo*. Ligações de 60% ou mais ficam
marcadas; confira as desmarcadas e a coluna *Ligação* antes de **OK** (uma pasta sem ligação diz
"nenhum clube encontrado"). Os uniformes são copiados para a biblioteca do kit-server
(`League\Club`, como a pasta tinha) e cada clube ganha uma linha no `map.txt`; **Salvar** escreve
ela. Um clube que já tem uma linha mantém ela, a não ser que **Substituir uniformes já definidos**
esteja marcado. Os uniformes de um clube novo vão pelo ID do clube que a construção deu a ele,
então construa o mundo e deixe ele no jogo antes. Uma pasta de clube pode ter, em vez disso,
imagens simples de uniforme (0.2.0): `p1.png`, `p2.png` ... para os uniformes e `g1.png` para o
goleiro (2048 x 2048 é o melhor; `.jpg` e `.dds` também funcionam). O Mod Studio transforma elas em
uniformes de kit-server; os números das costas, os números do calção e a fonte do nome são
texturas próprias, então vêm de um uniforme que já está na biblioteca, escolhido em **Números e
nomes de** (começa no primeiro uniforme da biblioteca que tem eles; *nenhum*: o jogo mantém os do
próprio clube). As cores no `config.txt` são lidas da imagem. A conversão das imagens é do
Xxspedd, da ferramenta de uniformes dele. O Mod Studio não desenha uniformes: as imagens vêm de
você ou de quem faz uniformes.

Se o seu mundo foi construído com **Uniformes simples para o modo Edição** (seção 8), o Kit Server
não veste os clubes novos, então os uniformes importados não aparecem neles; **Importar
uniformes** avisa. Desmarque essa opção na aba **Construção** e construa de novo.

## 7. Perfis

Um perfil lembra quais pastas de conteúdo e módulos estão ligados, e em que ordem. Tenha um para a
Master League, um para jogar online, um para testes (**4. Ferramentas → Perfis**, ou o menu
**Perfis**):

- **Salvar a configuração atual...** guarda o que está ligado agora com um nome.
- **Trocar para este** coloca essa configuração no `sider.ini` (o `sider.ini` antigo vai para os
  Pontos de restauração).
- **Atualizar com a configuração atual** sobrescreve o perfil; **Apagar** tira ele.
- **Exportar...** / **Importar...** levam um perfil para outro PC (`.fl26profile.json`).

## 8. League Builder: novas ligas, clubes e jogadores

O League Builder adiciona ligas novas ao jogo e muda as do próprio jogo. O que ele faz é um
**mundo**: uma pasta de conteúdo chamada `_FL26...` que o jogo lê enquanto ela está no jogo. Você
trabalha nas abas de **2. Meu mundo**.

**Remover** (Campeonatos) apaga a liga selecionada com os clubes dela. Para apagar várias de uma
vez, abra **Mais → Nome do mundo e arquivo...**, escolha elas com Ctrl+clique, Shift+clique ou
Ctrl+A, depois **Remover** ou a tecla Delete.

**Campeonatos → Adicionar campeonato**

| Campo | O que quer dizer |
|---|---|
| **Nome** | O nome da liga no jogo. Não pode haver duas iguais. |
| **País** | Dá a bandeira e onde a liga aparece. Um país para o qual o jogo não tem liga ganha um título próprio. |
| **Clubes** | De 10 a 24 (de 1 a 24 para clubes sem campeonato). |
| **Clubes sem campeonato** | Para um clube, ou alguns, sem liga em volta (0.1.8): digamos só o BATE Borisov da Bielorrússia. Escolha o grupo em que eles entram: *Other European teams*, *Other Latin American teams*, *Other Asia-Oceania teams*, *Other Africa teams* ou *Classic Teams* -- onde o jogo guarda os próprios clubes que não jogam liga nenhuma (Dynamo Kyiv, Wydad Casablanca ...). No Select Team eles aparecem embaixo desse grupo. Eles ganham nomes, escudos, uniformes, um técnico, uma formação, jogadores e um estádio como qualquer clube novo (**Editar clube**, **Jogadores**); o nome acima é só como o Mod Studio lista eles. Eles não jogam liga, copa nem competição europeia, e todo o resto desta janela fica cinza. Em *Campeonatos* um grupo desses mostra *sem campeonato (...)* em vez de um ID de liga. |
| **Formato** | *Todos contra todos*, de 1 a 4 turnos, *divide-se em dois (estilo escocês)*, ou *Apertura e Clausura*: dois torneios por temporada (setembro ao começo de janeiro, janeiro a maio), cada um começando do zero, depois playoffs com 8 ou 4 clubes (ou nenhum). A tabela da temporada inteira decide o acesso e o rebaixamento. No máximo 18 clubes. Uma liga dividida em dois tem no máximo 46 rodadas, antes e depois da divisão juntas (16 clubes em dois turnos são 30, então o maior grupo em dois turnos pode ter 8 clubes, 14 rodadas). Por enquanto, uma liga por país pode ser dividida em dois ou Apertura/Clausura. **A divisão em dois e Apertura e Clausura são experimentais** (0.2.4): funcionam, mas ainda têm mais bugs em aberto do que todos contra todos, o formato totalmente testado. A janela diz isso embaixo dos formatos. Por favor, continue reportando o que encontrar. |
| **Divisão** | *(primeira divisão)*, ou a liga de cima: outra liga nova, ou uma do jogo. Para colocar uma liga nova embaixo de outra liga nova num passo só: selecione ela e aperte **Adicionar divisão inferior** (pega o país, o número de clubes, o formato e o acesso/rebaixamento da liga de cima; só falta o nome). Uma liga que já tem outra liga nova embaixo fica cinza (0.1.9): o jogo segue um único elo para baixo a partir de uma liga, então grupos de uma divisão (três grupos da Serie C embaixo da Serie B) ainda não são possíveis. |
| **Acesso / rebaix.** | Quantos clubes trocam de lugar com a liga de cima no fim da temporada. |
| **Temporada** | Só na primeira divisão de um país novo: *agosto a maio* (o padrão) ou *fevereiro a dezembro*, como no Brasil, no Japão ou na Arábia Saudita: os clubes sobem e descem no Ano Novo, e as divisões abaixo seguem ela. Ainda não com divisão em dois, Apertura/Clausura nem copa da liga -- nem divisão em dois ou Apertura/Clausura numa divisão abaixo de uma liga de fevereiro a dezembro, incluindo a Liga BetPlay e a J1 League do jogo. |
| **Europa** | Só na primeira divisão: qual posição na liga vai para qual competição europeia. **Primeira divisão: 1.º fase preliminar da UCL, 2.º UEL, 3.º UECL** preenche as três de costume (*... fase preliminar* são os playoffs de agosto, veja 8.2); **Adicionar vaga**, o ✕ numa linha e **Limpar** para todo o resto. Cada posição uma vez, e só posições que a liga tem. Abaixo de 1 a posição vira **Campeão da copa** (0.1.7): o campeão da copa do país (um país novo precisa de **Copa nacional**) -- e quando o campeão já tem uma vaga europeia pela liga, a vaga desce na liga para o próximo clube, como a UEFA faz. Desde a 0.2.0 o campeão da copa também pode ir para as copas que o Mod Studio constrói (Copa Sul-Americana, CAF Confederation Cup, AFC Champions League Two ...); numa carreira nova, antes de alguém ganhar a copa, essa vaga também vai para o próximo clube da liga. Uma liga do jogo também pode ter uma (*Vagas continentais dos campeonatos do jogo*). Deixe vazio para uma divisão inferior. A predefinição segue o país: a Ásia ganha a AFC Champions League e a AFC Champions League Two, a América do Sul a Libertadores e a Copa Sul-Americana, a África a CAF Champions League e a CAF Confederation Cup, a América do Norte e Central a CONCACAF Champions Cup, a Oceania a OFC Champions League. A **AFC Challenge League** (0.2.0) é a terceira copa da AFC, abaixo da AFC Champions League Two como a Conference League na Europa; escolha ela com **Adicionar vaga** (*AFC CHL* na lista de Campeonatos). Essas sete copas que o jogo não tem são construídas com o mundo (seção 8.2). Uma vaga *Libertadores (fase preliminar)* fica com o lugar de um clube do jogo na fase preliminar (o último do país com mais clubes nela), no máximo seis das oito vagas dela; **1. Conferir o plano** diz quais ligas ficam de fora depois disso. |
| **Logo** | Qualquer imagem (um PNG com fundo transparente fica melhor). Vazio: um é desenhado para você. |
| **Bandeira do país** | A sua própria imagem da bandeira do país, esticada na moldura de bandeira do jogo. Ela substitui a bandeira do jogo desse país em todo lugar (Select Team, nacionalidade dos jogadores, o título do país em Database > Competition Info) enquanto o mundo está ligado. Vazio: a bandeira do próprio jogo. |
| **Copa** | Só na primeira divisão. **Copa nacional**: o país ganha a própria copa, com o nome que você der (vazio: `<liga> Cup`). O jogo preenche a copa de um país com a primeira divisão e a divisão abaixo dela, e o tamanho da copa segue a linha Copa nacional dos Limites (8.3): o maior tamanho que a tela da copa desenha e que cabe, então 22 clubes dão uma copa de 20, a primeira divisão primeiro. Passando de 44 clubes a copa fica só com a primeira divisão. Uma segunda divisão nova embaixo de um país que o jogo já tem (Alemanha, Rússia ...) também entra na copa desse país, depois dos clubes da primeira divisão, quando as fases da copa cabem no número de clubes. Uma terceira divisão nova ou mais baixa (a League One embaixo do Championship) deixa a copa do país para as duas primeiras divisões do jogo, como no jogo. **Supercopa (campeão contra campeão da copa)**: também uma supercopa de jogo único antes da temporada. Precisa da copa nacional. |
| **Copa da liga** | Só na primeira divisão. Um mata-mata desta liga e da de baixo, do jeito que a Carabao Cup é jogada (0.2.0): um jogo por fase, a semifinal e a final também, nas semanas da Carabao Cup: 27 de agosto, 23 de setembro, 28 de outubro, as quartas de final em 23 de dezembro, a semifinal em 14 de janeiro e a final no domingo 15 de março, em dias próprios, nunca num dia de copa nacional ou europeu. Entram tantos clubes das duas divisões quantos a tela da copa desenha, até 44 (20 + 24: a Premier League e o Championship inteiros); onde isso não dá 16 ou 32, os clubes desta liga ficam com as folgas e começam na segunda fase. Cada confronto é sorteado. Dê um nome ou deixe vazio (`<liga> League Cup`). Um mundo construído antes da 0.2.0 mantém a copa antiga de 16 em ida e volta com a fase prévia até você construir ele de novo; uma carreira começada antes dessa construção joga a copa antiga. |
| **Logos das copas** | Uma imagem para a copa nacional, a supercopa, a copa da liga e os playoffs de Apertura/Clausura, cada uma separada. Vazio: um emblema com as iniciais da copa é desenhado para ela. |
| **Só amistosos -- fora da Master League** | Para o Kick Off e amistosos: uma liga histórica, lendas e coisas assim. Os clubes dela nunca jogam uma temporada da Master League, então a liga fica sozinha: sem divisão acima ou abaixo, sem vagas europeias, sem copas. Ela ainda aparece na lista de times da Master League; escolha o seu clube de outra liga. |
| **Formação** | Como os clubes da liga entram em campo. Escolha uma das formações que os clubes do jogo usam (4-2-3-1, 4-1-2-3, 4-3-3, 5-3-2 ...; a lista diz quantos clubes do jogo jogam nela): cada clube novo ganha uma cópia da tática de um clube do jogo com essa formação, e o melhor time dele é escalado na construção. Vazio: a construção escolhe para cada clube a formação que melhor combina com o elenco (0.2.4; antes, um 4-2-3-1 fixo): dois atacantes fortes jogam com dois na frente, bons pontas com três atacantes, três zagueiros com três ou cinco atrás. O log da construção diz quais formações foram escolhidas. Um clube pode ter a sua própria (**Editar clube**). |

**Nome do mundo** (Campeonatos → Mais → **Nome do mundo e arquivo...**) tem que começar com
`_FL26`. Essa página também lista as suas ligas: depois da **construção** a coluna **ID do
campeonato** mostra o id de competição de cada liga no jogo, o que o arquivo do logo dela leva. A
coluna **#** é o lugar da liga na ordem (**Subir** / **Descer**), e **Select Team** diz onde a
última construção colocou ela: *sim*, *no lugar de* um dos grupos do jogo, ou *sem lugar (é
jogado)*. Um `*` ali quer dizer que a ordem mudou desde então: construa de novo para ver onde ela
fica. Arrastar na aba **Campeonatos** move uma liga só entre os lugares que as ligas do continente
dela já ocupam aqui (0.2.0; antes, colocava a ordem inteira na ordem dos continentes, então as
ligas da América do Norte e da Oceania sempre ficavam por último).

**Torneios de pré-temporada** (Campeonatos → Mais, ou Meu mundo → Copas): mata-matas amistosos de
4 ou 8 clubes convidados em julho, antes da temporada, em pares na ordem que você der (primeiro
contra segundo ...). Um clube é de uma liga nova ou um clube do jogo (o id dele); pelo menos um tem
que ser de uma liga nova, e o país dele recebe a copa. Uma carreira começa em agosto, então o
primeiro é jogado na segunda temporada. Cada copa pode ter um **Logo**; vazio: um é desenhado para
ela.

**Taças dos nossos países** (Campeonatos → Mais, ou Meu mundo → Copas, 0.2.4): as copas das suas
próprias ligas numa tabela. Para cada primeira divisão: a copa nacional, a supercopa e a copa da
liga, cada uma com o nome e o logo. São os mesmos campos de **Editar campeonato...**, sem abrir
cada liga.

**Copas dos países do jogo** (Campeonatos → Mais, ou Meu mundo → Copas): uma copa da liga -- a
Carabao Cup, por exemplo -- para ligas do jogo. Marque **Copa da liga** ao lado de uma liga: ela e
a liga de baixo, até 44 clubes, um jogo por fase do fim de agosto até a final em meados de março,
sorteada, com os clubes da própria liga folgando até a segunda fase (0.2.0; a mesma copa de uma
liga nova), em dias que o calendário de liga e copa do jogo deixa livres. **Supercopa**, o campeão
contra o campeão da copa, só onde o jogo não tem uma (Brasil, Chile, Escócia, Grécia, EUA). É uma
supercopa de jogo único entre dois clubes (0.2.4; antes, saía como um mata-mata de 16). Ela é
jogada no fim de julho; num país de fevereiro a dezembro (a Supercopa de Chile, a Supercopa Rei)
ela é jogada no fim de janeiro, entre o campeão e o campeão da copa da temporada que acabou de
terminar. Quando ainda não há campeão da copa (o primeiro verão de uma carreira nova), ou o campeão
também ganhou a copa, joga o vice da liga. Nome vazio: o nome da liga e *League Cup* / *Super Cup*.
**Logo** ao lado de cada nome (0.2.0): uma imagem para essa copa; sem nenhuma, um emblema com as
iniciais da copa. Mudanças aqui precisam de **Instalar os módulos** (ou Construir e instalar), uma
construção nova e uma carreira nova.

**Vagas continentais dos campeonatos do jogo** (Campeonatos → Mais): quais posições da Premier
League, LaLiga, Serie A ... vão para qual competição europeia. A lista mostra as vagas do próprio
jogo; marque **Vagas próprias para este campeonato** para mudar elas. Uma liga não marcada mantém
as vagas do jogo, uma liga marcada sem linhas não manda ninguém.

**Ranking da UEFA** (Campeonatos → Mais, 0.1.7): todas as ligas europeias do mundo -- as do jogo e
as suas primeiras divisões novas -- numa lista, o país mais forte primeiro. Arraste uma liga (ou
**Subir** / **Descer**) para mudar a ordem, desmarque uma para não dar vaga europeia a ela, **Ordem
da UEFA** coloca a lista de volta no ranking de associações da UEFA para 2026-27. O lado direito
mostra o que cada liga ganha, e **OK** escreve: as vagas da chave da UEFA para 2024-27 -- o 1.º do
ranking tem cinco vagas na Champions League, o 6.º duas e uma vaga nos playoffs, o 30.º uma vaga na
segunda fase preliminar da Champions League e três na da Conference League, e assim por diante,
incluindo a vaga na Europa League do campeão da copa. Um mundo nunca tem os 55 países da UEFA,
então as vagas das posições do ranking que ele não tem vão para os próximos clubes das ligas mais
fortes, uma de cada vez, uma rodada por vez, e toda competição fica cheia: com doze ligas, o 6.º,
o 7.º e o 8.º da Inglaterra vão para a fase preliminar da Champions League, por exemplo. Depois da
31.ª liga não sobra vaga, e a lista avisa. Cada fase preliminar tem dezesseis clubes: com as 31
posições num mundo, as vagas das posições mais baixas que passam desses dezesseis não ganham nada
(as notas dizem quais; as posições 26 e abaixo na verdade começam na primeira fase preliminar, que
o Mod Studio não tem). As vagas das fases preliminares vão para as fases na ordem da chave, o país
mais forte para a fase mais próxima da fase de liga. Depois você ainda pode mudar à mão as vagas de
qualquer liga (*Europa* na liga, *Vagas continentais dos campeonatos do jogo*): a construção usa as
vagas, não o ranking.

**Vagas sul-americanas** (Campeonatos → Mais, 0.1.7, só leitura): para cada liga sul-americana, as
quatro do jogo e as suas, quais posições vão para a Copa Libertadores, a fase preliminar dela e a
Copa Sul-Americana. As vagas da Libertadores do jogo são as dele (Brasil do 1.º ao 4.º e o campeão
da Copa do Brasil, fase preliminar 5.º e 6.º, e assim por diante -- as mesmas que o Competition Info
do jogo mostra); a Copa Sul-Americana é do Mod Studio, então a lista mostra quantos clubes cada
liga do jogo manda para ela com as suas vagas incluídas: as suas ligas primeiro, depois Brasil,
Argentina, Chile e Colômbia, um clube cada, alternando até 32. Um clube que já está na Libertadores
ou na fase preliminar dela dá lugar ao próximo da liga dele. **1. Conferir o plano** mostra a mesma
lista sempre que o mundo tem uma vaga na Libertadores ou na Sul-Americana.

**Nomes das competições** (Campeonatos → Mais, ou Meu mundo → Copas): um nome e um logo novos para
as copas, supercopas e competições continentais do jogo -- a FA Cup, a Champions League, a
Libertadores ... -- e para as copas continentais que o mundo constrói (CAF Champions League,
Confederation Cup, AFC Champions League Two, Copa Sul-Americana, CONCACAF Champions Cup, OFC
Champions League, AFC Challenge League, Supercopa da CAF). Cada fase de uma competição pega o nome.
Vazio: o do próprio jogo. As ligas do jogo são renomeadas em *Campeonatos* (escolha uma liga do
jogo).

**IDs das competições** (Campeonatos → Mais): cada competição do mundo que está no jogo, ligas e
copas, com o id dela. O jogo tem espaço para 255; Meu mundo mostra quantas estão em uso.

**Ordem dos campeonatos** (Campeonatos → Mais, 0.2.0): a ordem dos países no Select Team da Master
League e na lista de times do Kick Off / Edit. *By continent* é a ordem do jogo (Europa, as
Américas, Ásia, depois África, cada uma de A a Z). *Todos os países de A a Z* coloca todos numa
sequência só em ordem alfabética, e *Minha própria ordem* deixa você colocar do jeito que quiser
(arrastando, ou Subir / Descer). As ligas de um país ficam juntas, primeira divisão primeiro, e as
competições de clubes, os grupos "Other" e os Classic Teams vêm depois dos países. Alemanha, EUA e
Japão ficam nos grupos "Other" do Select Team, então eles só mudam de lugar no Kick Off. Construa o
mundo de novo depois.

**Temporadas dos campeonatos do jogo** (Campeonatos → Mais, 0.2.0, experimental): Japão, China,
Brasil, Chile e Arábia Saudita jogam de fevereiro a dezembro no jogo. Marque um e as ligas dele
jogam de agosto a maio como na Europa: a temporada começa em agosto, o acesso e o rebaixamento
acontecem no verão europeu, as copas dele vão para datas de agosto a maio e as vagas continentais
dele vêm da tabela que terminou em maio. Uma divisão sua embaixo de uma dessas ligas segue ela.
Colômbia e EUA jogam Apertura e Clausura e não podem mudar. Construa o mundo de novo e comece uma
carreira nova.

**Clubes europeus da primeira temporada** (Campeonatos → Mais, 0.1.8): escolha à mão os clubes da
fase de liga da Champions League, da Europa League e da Conference League na primeira temporada de
uma carreira nova. Os seus clubes entram primeiro e o jogo completa o resto; a partir da segunda
temporada as vagas europeias decidem.

**Clubes** (uma aba de Meu mundo): escolha a liga, depois **Editar clube** (nome, sigla, escudo; ou
dê um clique duplo no clube). Todo o resto está em **Mais ▾**: **Jogadores**, **Clube do
jogo...**, **Clube NewLife...**, **Clube novo aqui**, **Inserir clube**, **Remover clube**,
**Mover para outro campeonato...**, **Colar nomes...**, **Carregar nomes de um arquivo...** e
**Importar escudos...**. Um nome vazio vira `<liga> 01`, `<liga> 02` ...; um clube sem escudo ganha
um emblema numerado. Os uniformes são emprestados dos próprios clubes do jogo. Um uniforme desses é
licenciado, e o modo Edit não muda ele ("You cannot edit this strip"): marque **Uniformes simples
para o modo Edição** na aba Construção (Opções do mundo) e os clubes novos não pegam nenhum
emprestado, cada um usa um uniforme simples que Edit > Teams > Strip muda como o de qualquer outro
clube, Paste Image incluído. Com o Kit Server instalado, **Uniformes nas cores dos clubes** (aba
Construção, Opções do mundo, ligada a não ser que você desmarque, 0.2.1) faz para cada clube novo
uniformes titular, reserva, terceiro e de goleiro nas cores da camisa dele (as do NewLife, ou as
do escudo quando não tem), com o escudo no peito e no calção, para ligas inteiras de uma vez quando
o mundo entra no jogo. Um escudo que você coloca depois (Importar escudos) vai para os uniformes na
próxima ativação. Um clube com um uniforme próprio do Kit Server, ou só com um emblema numerado,
não ganha nenhum. Uma linha de uniforme sua no `map.txt` (uma que você definiu na aba *Uniformes*,
para um uniforme que está na biblioteca) sempre ganha: a construção não faz uniforme para esse
clube, não coloca nele o uniforme de um pacote e deixa a sua linha ligada (0.2.4; a 0.2.3
desligava ela por causa do uniforme de um pacote de liga em toda construção). Os nomes mantêm as
letras (FK Željezničar); a sigla de três letras não tem acentos, como no jogo, então Č, Ž, Đ viram
C, Z, D ali. A ordem de A a Z de uma liga nos arquivos do jogo coloca Đakovo no D e Šibenik no S
(0.2.4). Depois da **construção**, o mouse sobre o nome de um clube mostra o id dele no jogo
(**ID do clube**).

**Rostos do pack de rostos para os jogadores novos** (aba Construção, Opções do mundo, ligada por
padrão): cada jogador novo sem rosto próprio ganha um rosto do pack de rostos de regens que combina
com a nacionalidade dele. Desligada: os jogadores novos mantêm a aparência que o jogo dá a eles, ou
a que você definiu no modo Edit do jogo. Vale a partir da próxima construção.

**Técnico**: em **Editar clube** de um clube novo você pode dar nome ao técnico dele. Vazio: um nome
inventado a partir de jogadores do país do clube (um clube croata ganha um nome como `Tomislav
Krovinović`; o mesmo em toda construção), ou um numerado (`FL M0001` ...) para um país de que o
jogo tem poucos jogadores. **Foto do técnico** embaixo dá ao técnico um retrato (o mesmo que
**Retrato do técnico...** na aba Jogadores); *Campeonatos* (uma liga do jogo) > **Editar clube**
tem isso para os clubes do jogo também.

**Cores dos uniformes**: **Cores do uniforme titular** e **Cores do uniforme reserva** em **Editar
clube**: a construção empresta o uniforme do jogo mais próximo delas, e **Uniformes nas cores dos
clubes** usa elas.

**Formação**: em **Editar clube** de um clube novo você pode dar a ele uma formação própria; *Como
o campeonato* mantém a da liga. O campo embaixo da lista mostra onde cada um joga.

**Capitão e batedores de bola parada** (0.2.4): a construção dá a cada clube e seleção que não tem
um capitão (um jogador com a habilidade Captaincy, senão o mais forte e mais experiente) e os
batedores de pênaltis, faltas e escanteios, entre os jogadores de linha dos onze titulares. Um
clube do jogo que tem os próprios mantém eles. Um mundo construído antes da 0.2.4 tem o goleiro
como capitão em todo lugar: construa de novo e comece uma carreira nova.

**Estádio do mandante** (0.1.7): em **Editar clube**, um estádio da biblioteca do Stadium Server
para o clube; o slot e o nome são preenchidos a partir da pasta, mude o nome se quiser. Ele é
escrito no `map_teams.txt` do Stadium Server quando o mundo entra no jogo (e quando o mundo que está
no jogo é construído de novo), então o id de um clube novo nunca precisa ser procurado. Uma linha
sua para o mesmo clube fica desligada nesse meio tempo, e liga de novo quando o clube não tiver mais
uma aqui. *Campeonatos* (uma liga do jogo) > **Editar clube** tem isso para os clubes do jogo
também. O Stadium Server tem que estar instalado (a aba *Estádios*), ou o próprio módulo de
estádios do SPFL26 (`common\stadiums.lua` com a pasta `content\stadiums`): desde a 0.1.8 o Mod
Studio escreve ali quando o Stadium Server não está instalado. Um estádio do jogo escolhido como
estádio do mandante fica bem iluminado no jogo (0.2.4; antes, podia ficar todo escuro): construa
de novo um mundo feito antes.

**Clubes que o jogo já tem.** Um lugar de uma liga nova pode ter um dos clubes do jogo em vez de um
novo: selecione o lugar, depois **Mais → Clube do jogo...**, e busque pelo nome, sigla ou ID do
clube (**Só clubes sem campeonato** encurta a lista). A janela **Clube do jogo** diz embaixo da
lista onde o clube joga. O clube mantém o nome, escudo, uniformes, técnico e jogadores, e joga só
na sua liga. Quando ele joga em algum lugar do jogo (uma liga, uma copa, a Europa League ...), você
escolhe quem fica com o lugar dele lá: **O lugar dele vai para um clube do jogo que não joga
nada:** (escolha um da lista), ou **O lugar dele vai para um clube novo, chamado:** (digite um
nome). **Mantém suas vagas em competições continentais** (0.1.8, #84) deixa ele continuar jogando
a Champions League, a Libertadores ou a AFC Champions League em que está: um clube que no jogo só
joga a competição continental então simplesmente muda, e um que também joga uma liga do jogo
passa só a liga e as copas para o clube que você escolher. A partir da segunda temporada as vagas
da sua liga decidem quem vai. Um torneio de pré-temporada (as *Pre-season friendly Cups* do
SPFL26) não conta: o clube continua jogando ele, como fazem os clubes da Premier League (0.1.7).
**Editar clube** num clube do jogo muda o nome, o escudo, o retrato do técnico e o estádio dele,
como em *Campeonatos* para uma liga do jogo (0.1.7). Desse jeito nenhuma competição do jogo muda o
número de clubes; as ligas do jogo só mantêm as datas com o número para o qual foram feitas.
Seleções, os times clássicos e padrão e clubes com menos de 18 jogadores não podem ser escolhidos.
**Clube novo aqui** (em **Mais**) devolve o lugar a um clube novo; ele fica cinza a não ser que o
clube escolhido seja um clube do jogo nesse lugar (0.2.4). O clube deixa de aparecer nos grupos
*Other ... clubs* da Master League.

**Clube NewLife...** (0.1.8, #83, em **Mais**) coloca clubes do NewLife Database, com os elencos
deles, no lugar selecionado e nos lugares depois dele: marque um ou mais clubes (busque por clube ou
por liga) e cada um fica com o seu lugar na ordem. Uma liga que você fez à mão ganha clubes reais
desse jeito. Ele usa a pasta do NewLife que você abriu por último; na primeira vez, abra ela na
página *NewLife Database*.

**Inserir clube** e **Remover clube** adicionam um lugar antes do clube selecionado ou tiram um (de
10 a 24 clubes); nomes, escudos, técnicos e mudanças de jogadores vão junto com os clubes deles.
Confira as vagas europeias da liga, depois **construa** de novo. Qualquer mudança nos clubes de uma
liga precisa de uma **carreira nova**.

**Mover para outro campeonato...** (0.1.7) leva o clube novo selecionado para o fim de outra liga
nova, com nome, sigla, escudo, técnico, formação, uniformes, id do NewLife e mudanças de jogadores;
a liga que ele deixa fica com um clube a menos. Um clube do jogo muda com **Clube do jogo**: tire
ele de uma liga e coloque na outra.

**As ligas do jogo** (escolha uma em *Campeonatos*): um nome ou logo novo, depois **Manter
alterações do campeonato** (**Desfazer alterações do campeonato** volta atrás); **Editar clube**
para o escudo, o nome, o retrato do técnico e o estádio de um clube. A lista de Clubes mostra
quantos jogadores cada clube vai ter: o elenco dele, menos os jogadores tirados ou contratados por
outro clube, mais os adicionados e contratados. Uma mudança dessas fica guardada no arquivo do seu
mundo na hora, como qualquer outra mudança.

**Importar escudos...** (0.1.8, *Clubes* → Mais; para as ligas do jogo *Campeonatos* → Mais):
escudos para muitos clubes de uma vez. Escolha uma pasta de imagens; cada uma é ligada a um clube
pelo nome do arquivo -- o nome do clube (`Alianza Lima.png`, `alianza_lima_r_l.png`) ou o ID do
clube (`2287.png`, o `e_2287_r.png` dos packs de escudos). Um nome só combina com palavras inteiras,
e uma seleção só pega uma imagem pelo ID do clube (0.2.4; antes, "termalica" podia ir para o Mali).
A lista mostra cada ligação com uma marca; desmarque uma errada antes de **OK**. **Ligar a** também pode ser uma liga do seu mundo: só os clubes dela são ligados, e uma pasta com o nome de uma liga do seu mundo (`Torneo DIMAYOR II`) escolhe ela sozinha, então um clube de mesmo nome em outra liga não recebe nada. Um clube que já
tem escudo mantém ele, a não ser que **Substituir escudos já definidos** esteja marcado. As imagens
ficam nessa pasta e a construção lê elas dali, então guarde a pasta. (Ligar pelo nome é uma ideia
do script de escudos do Xxspedd.)

**Trocar de campeonato com um clube...** (0.1.7, *Campeonatos*, uma liga do jogo → Mais): dois
clubes das ligas do jogo trocam de lugar -- um clube que subiu por um que caiu, um clube da liga de
um país por um de outro. Cada um fica com os lugares do outro na liga, nas copas e nas competições
europeias, então toda liga do jogo mantém o número de clubes. Um clube numa liga nova do seu mundo
não pode trocar também. **Desfazer alterações do clube** desfaz a troca. Depois **construa** de
novo e comece uma carreira nova.

> **Arquivo do Edit.** Se a pasta de saves do jogo tem um arquivo do Edit (`EDIT00000000`), ele
> passa por cima dos nomes dos clubes. Mova ele para outro lugar para ver os seus nomes.

### Jogadores

**Jogadores** (uma aba de Meu mundo) muda o elenco de qualquer clube: os clubes novos do seu mundo
e os do próprio jogo. Escolha um clube (ou **Mais → Jogadores** em Clubes), depois um jogador:

- **Nome**, **número da camisa**, **posição** e as posições em que ele pode jogar (A = natural,
  B = consegue jogar ali), pé preferido, altura, peso, idade, nacionalidade, estilo de jogo;
- todas as **habilidades** e **habilidades especiais** (os nomes são os do próprio jogo);
- **Overall**: o overall que o jogo mostra, calculado como no jogo a partir das habilidades, com
  pesos próprios para cada posição (no máximo um ou dois pontos de diferença). Mudar ele move todas
  as habilidades do jogador pelo mesmo tanto e as poucas que mais contam para a posição dele uma a
  mais, para cair no número digitado. Um jogador de um clube novo não tem nome até a
  construção numerar ele (FL P00001 ...); digite um em **Nome** para dar o seu; desde a 0.2.0 um
  elenco desses começa no nível da divisão dele (cerca de 72 numa primeira divisão, descendo até
  57 da quinta divisão para baixo);
- **Rosto**: **Escolher...** uma pasta de rosto (seção 8.1). **Limpar** devolve o rosto do jogo. Um
  jogador novo sem rosto ganha um rosto do pack de rostos de regens que combina com a
  nacionalidade dele, com o retrato (0.1.5.5, com os módulos instalados e o `fl26regen` ligado,
  seção 5). Um rosto feito para outro jogador traz também a aparência do corpo desse jogador,
  então os braços e as pernas ficam com a cor de pele do rosto (0.1.9);
- **Retrato**: **Escolher...** uma imagem (PNG ou JPG) para o retrato pequeno do jogador nas
  listas do elenco, sem um rosto próprio. A construção deixa ela em 180 x 180; ela ganha do
  retrato de uma pasta de rosto;
- **Subir na ordem / Descer na ordem**: a ordem do elenco. Os onze primeiros começam o jogo;
- **Adicionar jogador** (uma cópia do jogador que você escolher, com um id novo; só clubes do
  jogo), **Remover do clube** (aperte de novo para desfazer). Um clube novo mantém pelo menos 18
  jogadores, contando os contratados para ele; os clubes do jogo não têm mínimo;
- **Melhor time** coloca o jogador mais forte em cada lugar (um jogador que também pode jogar no
  lugar, mas está registrado em outra posição, conta com 6 a menos, e ele fica para o próprio
  lugar quando esse ficaria sem ninguém); **Nível do elenco...** (em **Mais**) sobe ou desce todas
  as habilidades do elenco inteiro;
- o campo (clubes novos): os onze titulares na formação do clube. Arraste um jogador da lista para
  um lugar, ou arraste um lugar para outro para trocar os dois; um clique num lugar seleciona o
  jogador que está ali. A formação que a construção escolheu para o clube aparece aqui; quando você
  muda a ordem dela, o clube mantém essa formação;
- **Exportar CSV... / Importar CSV...** (em **Mais**): edite um elenco numa planilha. Exporte
  primeiro, mude as células, importe as mesmas colunas de volta.
- **Importar um elenco de uma tabela...** (em **Mais**): qualquer tabela de jogadores vira o
  elenco do clube -- uma digitada à mão, uma lista de elenco copiada de um site, ou uma exportação
  de outro jogo de futebol. As colunas são reconhecidas pelos nomes (nome, posição, idade ou data
  de nascimento, nacionalidade, altura, pé, número da camisa, overall, e quaisquer notas) e
  mostradas para você corrigir uma que estiver errada. O que a tabela não tem vem dos próprios
  jogadores do jogo da mesma posição e overall; notas numa escala de 1 a 20 são esticadas para os
  40-99 do jogo. Os jogadores da tabela ficam com os lugares do clube na ordem do elenco: um clube
  novo mantém os 30 lugares (menos jogadores = o resto sai, até 18), um clube do jogo ganha ou
  perde jogadores para combinar.

Cada mudança é escrita no mundo quando você **constrói**; os arquivos do jogo ficam como estão.
**Desfazer as alterações deste jogador** e **Desfazer todas as alterações deste clube** voltam ao
que o jogo tem.

A lista de clubes também tem **Seleções** e **Outros clubes (sem campeonato)**: os times que o jogo
guarda fora de qualquer liga (seleções, clubes que só jogam uma copa ou uma competição
continental). Os jogadores deles são editados do mesmo jeito.

#### Transferências, seleções, ids, o retrato do técnico

- **Contratar jogadores...** (um clube): uma lista de todos os jogadores do jogo e dos seus clubes
  novos, com um filtro de nacionalidade e uma busca por nome; escolha vários com Ctrl ou Shift.
  Eles vão para este clube: o clube antigo perde eles (uma transferência). **Transferir para...**
  faz o mesmo pelo outro lado: o jogador selecionado vai para o clube que você escolher. A lista
  mostra *from ...* no clube que recebe ele e *to ...* no clube que ele deixa; **Remover do clube**
  em qualquer uma das linhas cancela a transferência. Um clube tem no máximo 40 jogadores. Se um
  clube acabar com mais de 40 (uma seleção com mais de 26), a construção mantém os 40 primeiros e
  segue, e o log da construção diz o nome do clube e dos jogadores que ficaram de fora; quando o
  clube está duas vezes no seu mundo, ele diz as duas ligas.
- **Convocar jogadores...** (uma seleção: escolha *Seleções* na lista de ligas): a lista abre no
  país da seleção. Os jogadores entram no elenco da seleção **e continuam nos clubes deles**, como
  no jogo. **Remover do clube** tira um jogador da seleção (não do clube dele). Uma seleção tem no
  máximo 26 jogadores; um jogador está numa seleção por vez. O seu elenco é escrito nos dados do
  jogo, mas numa carreira da Master League o jogo escolhe as próprias convocações, então ali as
  suas convocações não ficam.
- Um jogador que chega vai para o fim da ordem do elenco com um número de camisa livre; o elenco
  que ele deixou fecha a ordem.
- Coluna **ID do jogador**: o id de cada jogador -- o do próprio jogo, o que você digitou, ou o que
  a última **construção** deu a um jogador novo (construa uma vez antes de fazer minifaces ou
  rostos para jogadores novos). **Exportar CSV...** escreve ele como `player_id`; Importar CSV
  ignora essa coluna.
- **ID do clube** (ao lado do clube) e **ID do jogador** (aba O básico): só para os seus clubes e
  jogadores **novos**. Vazio = o próximo id livre na construção. Digite um quando um uniforme,
  escudo ou pack de rostos foi feito para um certo id. Ids de clube: do primeiro id depois dos
  clubes do jogo (71578) até 81919; ids de jogador: acima do maior do jogo até 399999; nunca um
  que o jogo ou outro clube ou jogador novo já tem. O id é usado em todo lugar onde o mundo se
  refere ao clube ou jogador (elencos, competições, uniformes, escudos, técnico, rostos). Os
  próprios clubes e jogadores do jogo mantêm os ids: os uniformes, os rostos e os seus saves estão
  presos a eles.
- **Os jogadores mantêm os ids quando você constrói de novo** (0.2.4). A construção acha cada
  jogador do próprio mundo por quem ele é (o id do NewLife, senão o nome e a data de nascimento)
  antes do lugar dele no elenco, então um jogador que subiu no elenco ou mudou de clube mantém o
  id, e uma carreira antiga não mostra ele como outra pessoa.
- **Retrato do técnico...**: um PNG ou JPG para o técnico do clube. A construção deixa ele em
  256 x 256 e coloca em `common/render/symbol/coach/coach_<id do técnico>.png`, o lugar do próprio
  jogo para retratos de técnicos. Aperte de novo para tirar a imagem.

### 8.1 Rostos

Um mod de rosto é uma pasta assim (do jeito que quem faz rostos compartilha):

```
<qualquer nome>\
    #Win\face.fpk
    #Win\face.fpkd
    sourceimages\#windx11\*.ftex
    portrait.dds            (ou <id>.dds, opcional)
```

Escolha essa pasta para um jogador. Na **construção** o rosto é copiado para o mundo e apontado
para o jogador, então funciona para um jogador novo cujo id não existia quando o rosto foi feito,
e nunca substitui um rosto do jogo. Sem retrato, a pequena foto do jogador nos menus fica o
contorno vazio; o rosto em si continua aparecendo. Uma pasta com mais de um rosto dentro é
recusada: escolha o rosto que você quer.

### 8.2 Construir, ativar, jogar

**Mantenha o Team.bin próprio do mundo.** Ele está na pasta do mundo e tem os clubes do mundo e os
playoffs dele. Trocar ele pelo Team.bin do próprio jogo derruba os dois, e as escalações só parecem
consertadas porque os clubes do mundo sumiram (GitHub #75). Construa o mundo de novo em vez disso.

**Construção** é a primeira aba de **2. Meu mundo**. Um aviso no topo diz que ela é para modders:
para jogar um modpack pronto você não precisa dela. Embaixo: o arquivo em que o seu mundo é
guardado, os botões **Mundo novo**, **Abrir um mundo...** e **Adicionar ligas** (para um mundo
seu), e o botão grande **Construir e instalar**.

**Construir e instalar** faz o 0, o 2 e o 3 abaixo de uma vez, depois mostra o que falta fazer:
uma janela **Construção concluída** com uma marca para **Mundo construído**, **Campeonatos e
clubes**, **Módulos instalados e ativados** e **No jogo**, e em **Antes de jogar** um lembrete
para começar uma Master League nova. Ela também pode **Tirar o save do Edit do caminho** (um save
do Edit de antes da construção esconde os nomes e elencos novos) e **Fechar o jogo**. O cartão do
Início tem um botão **Ir para Construção** que te traz aqui. Enquanto o mundo é construído, a linha
de estado de Meu mundo e a barra de baixo mostram o tempo até agora e o passo em que ele está
(`Construindo... 3:12 · squads: filling them`), e a janela continua livre para usar. Ou passo a
passo, em **Passo a passo, e Exportar o mundo** na aba **Construção**:

0. **Instalar os módulos** — uma vez, e de novo depois de uma versão nova do programa. Os arquivos
   que ele substitui ficam guardados em **Pontos de restauração**.
1. **Conferir o plano** — o que vai ser feito; nada é escrito.
2. **Construir o mundo**.
3. **Ativar** — coloca ele no jogo (o mundo ativo no `sider.ini`).
4. Inicie o jogo, volte e aperte **Depois de iniciar: conferir**. Ele lê o `sider.log` e diz,
   módulo por módulo, se o mundo foi carregado.

**Ativar** no cartão de outro mundo em Meu mundo faz o passo 3 para esse mundo (e troca a pasta de
saves, seção 3.1). O mundo que está no jogo mostra **● Ativo** no lugar. Comece uma Master League
nova depois de ativar um mundo diferente.

**Um logo ou escudo novo constrói em segundos** (0.2.4). Quando só imagens mudaram desde a última
construção (o logo de uma liga ou copa, o escudo de um clube, a bandeira de um país), a construção
desenha de novo só essas e deixa o resto do mundo como está. Qualquer outra mudança (um nome, um
clube, um jogador) é uma construção completa. Um mundo de um zip é construído por inteiro uma vez
no seu PC; depois disso as mudanças de imagem dele também são rápidas.

**Um mundo pronto não é construído aqui** (0.2.4). Um mundo instalado de um zip já está construído,
e a construção substituiria ele pelo mundo aberto no Mod Studio. Por isso, enquanto um mundo pronto
está no jogo, os passos da construção ficam cinza com um aviso, o Início diz **Pronto para jogar**,
e a Construção explica o que fazer: aperte **Iniciar o jogo**, ou coloque antes o seu próprio mundo
no jogo (**Ativar** no cartão dele). Outro mundo (NewLife, um mundo novo) ainda pode ser construído
enquanto o pronto está ligado: a construção pergunta antes e avisa que desliga o mundo pronto;
**Ativar** no cartão dele traz ele de volta, com as carreiras dele. Para mudar o próprio mundo
pronto: **Torná-lo editável...** (seção 3.1).

**Incluir a Conference League** (aba Construção, em Opções do mundo, ligada por padrão) também
constrói a Conference League: uma fase de liga de 36 clubes e um playoff em fevereiro, como as
outras duas. A Champions League e a Europa League ganham a fase de liga de 36 e o playoff de
fevereiro de qualquer jeito. Desligada: sem Conference League. (O Mod Studio 0.1.3 e anteriores
deixavam a Champions League e a Europa League nos grupos de quatro do jogo quando isso estava
desligado, o que o mod não consegue rodar -- elas quebravam; as Verificações marcam um mundo assim:
construa ele de novo.) **Logo da Conference League** ao lado: a sua própria imagem para ela; vazio:
um emblema da UECL é desenhado (o jogo não tem nenhum para ela). **Nome da Conference League**
embaixo: como o jogo chama ela, *FL Conference League* quando vazio (digite *UEFA Conference
League* se quiser); um nome novo precisa que o mundo seja construído de novo. Os dois também são
usados por **Construir só as copas europeias...**.

> **Vagas europeias.** As vagas que você dá às suas ligas vêm depois das que as próprias ligas do
> jogo têm. Cada competição tem 36 clubes; vagas depois do 36.º não ganham nada, e **1. Conferir o
> plano** avisa. Ligas novas sem vagas não mandam ninguém para a Europa, e o Início avisa sobre
> isso. Os campeões vêm primeiro: os campeões da Champions League e da Europa League ficam com duas
> das vagas diretas da Champions League, o campeão da Conference League com uma da Europa League. O
> sorteio da fase de liga segue as regras da UEFA: nenhum clube enfrenta um clube do próprio país,
> e no máximo dois dos adversários dele vêm de um mesmo outro país.
>
> **As fases preliminares de agosto.** Uma vaga de *fase preliminar* coloca o clube nas fases
> preliminares de agosto dessa competição: até três fases (0.1.7) -- a segunda fase preliminar
> (dias 220 e 225), a terceira (229 e 236) e o playoff (243 e 250; os da Champions League 244 e
> 251) -- cada uma de 16 clubes em ida e volta, os oito elencos mais fortes como cabeças de chave
> (segundo jogo em casa), dois clubes de um mesmo país mantidos separados. Os vencedores vão para a
> fase seguinte, do playoff para a fase de liga. Os perdedores caem como os da UEFA: os perdedores
> do playoff da *Champions League (fase preliminar)* para a Europa League, os da terceira fase para
> o playoff da Europa League, os da segunda fase para a terceira fase da Europa League; *Europa
> League (fase preliminar)* do mesmo jeito para a Conference League; os perdedores da *Conference
> League (fase preliminar)* estão fora. As primeiras vagas da lista vão para o playoff, as
> seguintes para as fases anteriores. Quantas fases um mundo ganha depende das vagas dele, e cada
> fase da Conference League precisa de 8 clubes a mais: 116 vagas na Europa só para os três
> playoffs, 132 para todas as nove fases. Com as vagas do próprio jogo são só os playoffs; o resumo
> da construção diz quais fases um mundo ganha (*August qualifying*). Cada playoff tira 8 vagas dos
> clubes que entram direto nas competições para onde vão os vencedores e perdedores dele: com os
> três, a Champions League pega 28 clubes direto, a Europa League e a Conference League 20 cada.
> Uma vaga além dessas é jogada na fase preliminar dessa competição. As vagas de fase preliminar
> das suas ligas vêm antes das do jogo (Portugal, Escócia, Grécia, Dinamarca ...).

Depois **comece uma carreira nova na Master League** (ou Become a Legend). As ligas novas estão
embaixo do país delas no Select Team e no Kick Off. Nas listas do Kick Off e do Edit um país
asiático novo vem antes de *Other Clubs (Asia)*, um sul-americano junto com os do jogo (depois da
Colômbia, antes da MLS, 0.1.7), um da CONCACAF depois da MLS, e os africanos e da Oceania (o jogo
não tem seção para eles) depois da Ásia.

> **Copas de outros continentes.** Quando as suas ligas mandam clubes para a CAF Champions League,
> a CAF Confederation Cup, a AFC Champions League Two, a AFC Challenge League, a Copa
> Sul-Americana, a CONCACAF Champions Cup ou a OFC Champions League (as três últimas novas na
> 0.2.0), a **construção** faz essas copas também. Cada uma ganha 32, 16, 8 ou 4 clubes: primeiro
> as vagas das suas ligas, depois as próprias ligas do jogo desse continente (Ásia, América do Sul,
> e a MLS para a da CONCACAF) completam; para a AFC Challenge League são do 11.º ao 14.º da J1
> League, do 10.º ao 13.º da Chinese Super League e do 11.º ao 14.º da Saudi Pro League. Com 8 ou
> mais ela joga grupos de quatro e depois um mata-mata; com menos de 8, só mata-mata. A CONCACAF
> Champions Cup é sempre mata-mata, de no máximo 16 clubes, como a de verdade, e dois clubes de uma
> mesma liga não se enfrentam na primeira fase dela quando isso pode ser evitado. Elas são
> preenchidas no fim de agosto, a partir das tabelas das ligas. Um clube que já está na Copa
> Libertadores, na fase preliminar dela ou na AFC Champions League não é sorteado para elas. Uma
> copa da CAF ou da OFC com menos de 4 vagas pega primeiro as vagas da próxima copa da CAF (com duas
> e duas, a CAF Champions League fica com as quatro), depois as próximas posições das suas ligas.
> **Supercopa da CAF** (aba Construção, Opções do mundo, ligada por padrão) faz os campeões das duas
> copas da CAF se enfrentarem uma vez no fim de julho, a partir da segunda temporada de uma
> carreira.
>
> Uma liga que pode mandar um clube para a Copa Libertadores, a AFC Champions League ou o Mundial
> de Clubes fica longe dos dias de jogo deles (0.2.4): nenhuma rodada da liga no dia antes ou
> depois.

> **Sorteio da copa nacional** (aba Construção, Opções do mundo) decide como as copas nacionais
> das suas ligas são sorteadas. *Seeded* (o padrão): os clubes da primeira divisão ficam com as
> folgas e as fases finais, são espalhados por igual nas duas metades da chave, e enfrentam os
> clubes das ligas de baixo em vez de se enfrentarem nas primeiras fases. *Random*: um sorteio às
> cegas. *Off*: o jogo preenche a chave na ordem da lista, o que coloca todos os clubes de cima de
> um lado só. No arquivo do mundo é a linha `cupdraw seeded|random|off`;
> `cupdraw <cup regulation> seeded|random|off` define uma copa só.

> **Os saves pertencem a um mundo.** Uma carreira salva com um mundo no jogo precisa desse mesmo
> mundo para carregar. Com **Cada mundo guarda as próprias carreiras** ligado (o padrão, seção
> 3.1), o Mod Studio mantém as carreiras de cada mundo separadas para você.

**O seu mundo se salva sozinho** um instante depois de cada mudança (a barra de baixo diz **Seu
mundo está salvo**): no próprio arquivo `.json` quando ele tem um, senão em
`%APPDATA%\FL26ModStudio\recipes\<mundo>.json`, e o Mod Studio abre ele de novo quando inicia.
**Arquivo → Salvar seu mundo como...** salva uma cópia com outro nome, **Arquivo → Abrir um
mundo...** traz um de volta e **Arquivo → Mundo novo** começa um vazio.

**Construir só as copas europeias...** (aba Construção, Opções do mundo; **Só as copas
europeias...** no Início) constrói um mundo só com a Champions League e a Europa League novas --
fase de liga de 36 e o playoff de fevereiro -- e a Conference League quando **Incluir a Conference
League** está marcada. Sem ligas novas; os clubes e as ligas do jogo ficam como estão, e o seu
mundo não é mudado. Ele pede um nome de mundo (`_FL26Euro` por padrão), constrói e oferece ativar.
Só um mundo pode estar no jogo, então ele é no lugar de um mundo com ligas novas: um mundo com
ligas novas já tem o formato novo.

> **Ligas de amistosos e Master League.** Uma liga marcada como *Só amistosos* nunca joga uma
> temporada da Master League, mas o jogo tem uma lista só de times para o Kick Off e a Master
> League, então os clubes dela ainda aparecem quando você escolhe o seu clube para uma carreira
> nova. Não comece uma carreira com um deles. **1. Conferir o plano** e a construção avisam.

### 8.3 Limites

| | |
|---|---|
| Ligas novas por mundo | Sem número fixo. Cada liga, copa e supercopa do mundo ocupa uma das 255 competições do jogo (o próprio jogo usa umas 90); **2. Meu mundo** mostra quantas estão em uso. O nosso mundo de teste joga 86 ligas novas. |
| Países novos | 99 |
| Clubes por liga | 10 – 24 |
| Clubes novos ao todo | cerca de 1.500 (a linha embaixo da página NewLife Database diz quantos cabem no seu jogo) |
| Vezes que os clubes se enfrentam | 1 – 4 |
| Ligas divididas em dois | 2 por mundo |
| Divisões num país | até a 7.ª |
| Jogadores por clube novo | 30 no começo (um mundo muito grande ganha elencos menores, nunca abaixo de 22); tire até 18; jogadores contratados levam até 40 |
| Jogadores por seleção | 26 |
| Copa nacional | a primeira divisão e a de baixo, até 44 clubes. Até 32 os tamanhos são 2-16, 18, 20, 24, 28, 30 e 32 -- o maior que cabe (22 clubes dão uma copa de 20); de 33 a 43 viram 32; 44, ou um tamanho que uma copa do jogo tem, fica; mais de 44: só a primeira divisão |

### 8.4 NewLife Database: clubes e jogadores reais

O NewLife Database é um download separado com clubes e jogadores reais para ligas novas: nomes,
datas de nascimento, posições e overalls na escala do jogo, e as cores dos clubes. Cada clube e
jogador nele tem um id próprio que fica igual em todas as versões da base. Ele não está no GitHub:
pegue ele no canal do NewLife do nosso [Discord](https://discord.gg/StQqtk3G3M). Ele vem em
partes, uma por continente (um grande em mais de uma), mais *Free agents*, cada uma com menos de
10 MB. Baixe só as partes que você quer.

1. Coloque as partes que você baixou numa pasta. Não descompacte: o Mod Studio lê os zips como
   estão. (São zips LZMA: o 7-Zip abre, o visualizador de zip do próprio Windows não.)
2. **2. Meu mundo → NewLife Database** (o botão à direita das abas), depois **Abrir NewLife
   Database...** e escolha essa pasta. (Ou solte a pasta em **+ Adicionar...**.) A lista mostra
   cada liga dessas partes: país, clubes, clubes que o jogo já tem (*No jogo*), jogadores e nível.
   Clique numa liga para ver os clubes dela. Clique num cabeçalho de coluna (Campeonato, País,
   Clubes, Jogadores, Nível) para ordenar por ele, de novo para inverter a ordem (0.2.0); a lista
   abre ordenada por país.
3. Selecione uma ou mais ligas (Ctrl ou Shift para mais) e aperte **Adicionar ao seu mundo**. Cada
   uma vira uma liga nova com os clubes e os elencos deles, a primeira divisão do seu país. Mude a
   divisão, o formato, as vagas europeias e o resto em *Campeonatos*, como em qualquer outra liga.
4. **Construir e instalar** e comece uma carreira nova (seção 8.2).

- **A sua própria escolha de clubes** (0.1.7): desmarque um clube na lista à direita para deixar
  ele de fora, e **Adicionar um clube de outro campeonato...** para trazer clubes de qualquer liga
  da versão -- a primeira divisão desta temporada é a da temporada passada com dois clubes que
  subiram, por exemplo. A linha da liga ganha um `*`. Um clube só pode estar numa liga do seu
  mundo. Se ele já está numa das suas ligas com outro nome, a mensagem diz essa liga e o nome que
  o clube tem lá.
- Uma liga tem de 10 a 24 clubes, os novos e os do jogo juntos; as outras ficam cinza. Uma liga do
  próprio jogo (a Premier League, o Championship ...) também fica cinza (0.1.9): ela já está no
  jogo, leve ela para a temporada do NewLife com **Mais → Levar os campeonatos do jogo para esta
  temporada...** abaixo. A linha embaixo conta os clubes novos do seu mundo contra o número que o
  jogo aceita.
- Os clubes que o jogo já tem entram na liga nova como clubes do jogo (seção 8, *Clubes que o jogo
  já tem*), nos últimos lugares, com os próprios nomes, escudos, uniformes e jogadores. Um que
  também joga uma competição do jogo (o Basel e o Young Boys jogam a Europa League) precisa do
  clube que fica com o lugar dele lá: *Clubes*, escolha ele, **Mais → Clube do jogo...**. A
  construção diz quais até lá. Um clube cuja única competição do jogo é continental (o Ludogorets
  na fase preliminar da Champions League) continua jogando ela sozinho (0.1.9).
- Um jogador que o jogo já tem (o mesmo jogador com o mesmo nome, o Urbański no Górnik no jogo e
  no Legia no NewLife, por exemplo) vai para o clube do NewLife em vez de ser criado uma segunda
  vez (0.1.7): ele mantém o rosto, o nome e o id e pega a posição e os overalls do NewLife. Ele
  fica onde está quando o clube antigo dele cairia para menos de 18 jogadores, ou quando uma liga
  anterior já pegou ele; aí ele fica de fora do clube do NewLife, não é copiado (0.1.8).
- Um clube do NewLife ganha um id de mundo próprio (0.1.8), no bloco que o jogo lê para clubes,
  contando depois dos ids que o builder dá aos próprios clubes. O mouse sobre o nome dele em
  *Clubes* mostra ele (**ID do clube**), e o `map.txt` de um Kit Server usa ele como chave. Um
  mundo construído antes da 0.1.8 tem que ser construído de novo e a carreira começada do zero para
  os uniformes acompanharem. A partir da 0.1.8 um clube mantém o id da primeira construção dele
  (o seu mundo lembra): tirar, adicionar ou atualizar outra liga não muda mais ele.
- **Uma versão mais nova do NewLife** (0.1.8): coloque as partes dela numa pasta (sem misturar com
  as antigas), use **Abrir NewLife Database...** nessa pasta e aperte **Mais → Atualizar meus
  campeonatos para esta versão**. Cada liga que você adicionou de uma versão mais antiga aparece na
  lista com o que muda (*16 clubes agora, 18 no NewLife 1.3 (5 novos, 3 que não estão nele)*) e uma
  caixa **Manter meus clubes**: marcada, a liga mantém os clubes; desmarcada, ela pega os clubes
  que tem na versão nova. Nos dois casos os elencos vêm da versão nova, e a liga mantém o nome, a
  divisão, o formato, as vagas europeias e as copas; um clube que fica mantém o técnico e um escudo
  que você escolheu, e os clubes seus que você colocou na liga ficam. As habilidades, posições e o
  resto dos elencos vêm da versão nova; um rosto que você ligou ou um retrato que você escolheu em
  *Jogadores* fica com um jogador que ainda está no clube (0.2.0, #111). Um clube do jogo cujo
  lugar foi para outro clube continua um clube novo na sua liga (0.2.4). Depois construa e comece
  uma carreira nova.
- **As próprias ligas do jogo na temporada do NewLife** (0.1.8): com um NewLife Database aberto,
  aperte **Mais → Levar os campeonatos do jogo para esta temporada...**. Cada liga do jogo que a
  versão tem aparece na lista com o que acontece com ela, cada uma com uma caixa. Um clube que
  subiu ou caiu entre duas ligas do jogo troca de lugar com um que foi para o outro lado (o Burnley
  para o Championship, o Coventry para a Premier League), como faz *Trocar de campeonato com um
  clube...*. Um clube que caiu para fora das ligas do jogo (o Leicester para a League One) vira o
  clube que subiu no lugar dele (o Bolton): o nome, a sigla, o escudo e o elenco dele; o uniforme,
  o estádio e o técnico ficam. Quando a base não tem escudo para esse clube, o lugar ganha o escudo
  em forma de brasão da camisa do clube novo (0.2.4). Cada clube das ligas marcadas ganha o elenco
  do NewLife: os jogadores que o jogo tem chegam do clube antigo, os que ele não tem são
  adicionados, e os jogadores que o NewLife tem em outro clube saem. Um jogador que o NewLife ainda
  tem neste clube fica, enquanto o clube tiver espaço (no máximo 40; 0.2.4); o log da construção
  diz o nome de quem não coube. Os overalls são colocados na escala do jogo, medidos nos jogadores
  que os dois têm, então uma estrela fica onde o jogo avalia ela (0.2.0; antes, a ponta de cima
  ficava de 2 a 4 mais alta). As ligas mantêm o número de clubes, o formato e as copas. Os clubes
  que você já mudou à mão (uma troca, um nome novo, um clube de uma liga nova, mudanças de
  jogadores) ficam como estão. Fazer de novo com uma versão mais nova substitui o que a mais antiga
  fez; **Mais → Desfazer os campeonatos do jogo** desfaz tudo. Construa e comece uma carreira nova.
- Um clube do NewLife ganha um escudo em forma de brasão nas cores dele e o uniforme do jogo mais
  próximo das cores dele, até você dar os seus (**Editar clube**).

## 9. Pacotes de ligas: compartilhe uma liga inteira

Um modder faz uma liga uma vez — clubes, nomes, escudos, logos, elencos, rostos — e compartilha
**um arquivo `.fl26pack`**. Qualquer pessoa adiciona ele ao próprio mundo e constrói.

A página **Pacotes de campeonatos** está em **2. Meu mundo → Mais ▾ → Pacotes de campeonatos**. Ela
lista os pacotes do seu mundo, com **Adicionar um pacote...**, **Criar um pacote...** e **Remover
do seu mundo**.

**Criar um pacote** (**Criar um pacote...** nessa página, ou **Arquivo → Criar um pacote de
campeonatos...**):

1. Nome, autor, versão e uma descrição curta.
2. Marque as ligas que entram (**Selecionar tudo** / **Não selecionar nada** em cima da lista).
   Uma liga abaixo de outra liga nova tem que ir junto com ela.
3. Se quiser, **também minhas alterações nos campeonatos, clubes e jogadores do próprio jogo**.
4. **O que entra** (0.1.8): está tudo marcado; desmarque o que você não quer compartilhar --
   **Elencos**, **Rostos e retratos de jogadores**, **Escudos e logos de campeonatos**,
   **Técnicos**, **Cores dos uniformes**, **Estádios dos mandantes** (a linha do Stadium Server,
   não o estádio em si), e (0.2.1) **Uniformes** (os do Kit Server dos clubes) e **Placares** (o
   do Scoreboard Server de cada liga). Os uniformes e placares são pegos do seu jogo como o mundo
   está agora: o que o kit-server\map.txt e o scoreboard-server\map_competitions.txt dão aos clubes
   e ligas dele. Um pacote sem elencos vai por cima de uma base de elencos que é atualizada por
   conta própria, como o NewLife, sem colocar elencos antigos de volta.
5. **Salvar o pacote...**. O arquivo (`.fl26pack`) leva as imagens, os rostos, os uniformes e os
   placares, não caminhos do seu computador. Quem adiciona ele recebe os uniformes e placares no
   lugar com os próprios ids de clube e de liga quando constrói (o Kit Server / Scoreboard Server
   tem que estar instalado); um clube a que a pessoa deu uma linha de uniforme própria na aba
   *Uniformes* mantém esse uniforme (0.2.4), e um uniforme de pacote fica com o clube dele quando um
   clube é tirado, inserido ou movido, ou a liga é atualizada para um NewLife mais novo. Os
   uniformes somam cerca de 10 MB por liga e um placar cerca de 7 MB, então um pacote desses muitas
   vezes passa do limite de 10 MB do Discord: compartilhe por um serviço de nuvem (Google Drive,
   Dropbox, MEGA ...); o programa avisa quando o arquivo é maior.

**Adicionar um pacote** (**Adicionar um pacote...** nessa página, **Adicionar um pacote de
campeonatos** em **Ações rápidas** no Início, **Arquivo → Adicionar um pacote de campeonatos...**,
**+ Adicionar...** em Meu mundo, ou solte ele em **Importe seu mundo**, onde **Construir e
instalar** então começa sozinho):

1. O programa mostra o que tem dentro e pergunta. Um pacote de várias ligas lista elas, todas
   marcadas: desmarque as que você não quer (0.2.1). Uma liga abaixo de outra liga do pacote traz
   essa junto. Em **O que pegar** você também pode desmarcar partes dele (placares, uniformes,
   escudos, rostos ...), por exemplo para pegar os placares de outro pacote.
2. Uma liga com um nome que você já tem: o programa pergunta, e adiciona ela como `Nome (Pacote)`
   (não: nada é adicionado). Um pacote feito sem elencos vai para cima dessa liga em vez disso: os
   escudos e técnicos dele caem nos clubes com o mesmo nome, os seus jogadores ficam, e o programa
   diz quantos clubes encontrou. Um pacote que o seu mundo já tem (o mesmo nome) é substituído
   pela versão nova (0.1.7): as ligas, clubes e mudanças de jogadores do antigo saem, os novos
   entram.
3. **Construir e instalar**.

Os ids são dados quando cada pessoa constrói, a partir do que o próprio jogo dela tem, então um
pacote funciona ao lado de outros pacotes e ao lado das suas próprias ligas. **Remover do seu
mundo** tira um pacote de novo, incluindo as mudanças que ele fez nos clubes do jogo. Se um pacote
muda um clube que o seu mundo já muda (um clube do NewLife, por exemplo), um jogador que os dois
adicionam é adicionado uma vez, e as contratações e saídas do pacote vêm junto (0.2.4).

Uma liga colocada abaixo de uma das ligas do jogo funciona para todos com a mesma versão do jogo.

### 9.1 Exportar o mundo: um mundo construído para outro PC

Um pacote precisa que a outra pessoa construa. Para entregar o mundo exatamente como você
construiu, aperte **Exportar...** no cartão do mundo em **2. Meu mundo**, ou **Exportar o
mundo...** em **Passo a passo, e Exportar o mundo** na aba Construção (depois de o mundo estar
construído). Ele salva um `.zip`:

- `SiderAddons\livecpk\<mundo>\...`: a pasta inteira do mundo, com o **arquivo do mundo**
  `fl26world.txt`. As linhas `newfaces` / `faceapp` desse arquivo listam os jogadores novos que
  ganham um rosto gerado. Sem elas todos os jogadores novos ficam com a mesma cara.
- `SiderAddons\content\kit-server\<mundo>\...` e `...\scoreboard-server\<mundo>\...`: os
  **uniformes** do mundo (os do Kit Server dos clubes dele, também os feitos a partir de cores e
  escudos) e os **placares**, cada um com um `map.txt` / `map_competitions.txt` só com as linhas
  deste mundo. Importe seu mundo adiciona essas linhas aos map de quem recebe (uma linha dessa
  pessoa para o mesmo clube fica desligada e volta quando o mod é removido). Os uniformes vão para
  o Kit Server que o jogo de quem recebe carrega (`content\kits` para o do próprio SPFL26). Um
  clube do mundo que usa um uniforme de outro pack no seu PC (o Other Europe do SPFL26, um modpack)
  leva junto uma cópia desse uniforme, em `<mundo>\_kits\`, então quem recebe não precisa desse
  pack.
- `SiderAddons\content\scoreboard-server\<mundo>\_packs\...`: os **placares de outros packs** que
  as linhas de map ligadas no seu PC dão às competições do mundo (os placares de um modpack para
  as ligas, copas e supercopas dele). Eles vêm com as linhas de map deles, apontadas para
  `<mundo>\_packs\`, então quem recebe também não precisa desse pack. Os temas de menu não fazem
  parte de um zip de mundo: os menus do próprio jogo ficam, mesmo quando o tema de um pack está
  ligado no seu PC.
- `READ ME - FL26 world.txt` e `fl26worldpack.json`: o que quem recebe precisa.

**Quem recebe precisa dos módulos do Mod Studio com o pacote de rostos**
(`modules\fl26regen_faces.bin`): instalar o zip em **Importe seu mundo** coloca eles (ou **Início
→ Instalar agora**). Os rostos vêm desse pack, então o zip não leva eles.

Para instalar, solte o zip em **Importe seu mundo** e aperte **Instalar o mundo**. O Mod Studio
instala os módulos dele, copia o mundo, coloca o `fl26world.txt` em `SiderAddons\modules` (onde o
`fl26regen` lê ele) e coloca o mundo no jogo; uma versão mais nova de um mundo que você tem
substitui a mais antiga. Termina com **Pronto para jogar** e uma lista final de verificação.
Depois comece uma carreira nova na Master League. **Remover** (em **No jogo agora**) tira o mundo
de novo e coloca de volta o arquivo do mundo anterior.

Um modpack diz os estádios dos clubes dele pelas pastas do pack de estádios de quem fez. Quando o
seu pack de estádios guarda um estádio em outra pasta, o Mod Studio acha ele pelo nome; um estádio
que você não tem fica de fora (o clube joga onde o jogo coloca), e a verificação final diz quantos
clubes têm o seu.

**Mudar um mundo instalado.** O `fl26worldpack.json` só tem o nome do mundo e o que ele precisa, mas
a pasta do mundo leva o `leaguebuilder-plan.json`. Quando o Mod Studio inicia com esse mundo no
jogo e as tabelas do jogo extraídas, ele faz o seu mundo a partir desse plano e abre ele, para quem
recebe poder ver as ligas do mundo. Para mudar ele e construir de novo nas próprias tabelas, a
pessoa aperta antes **Torná-lo editável...** em Meu mundo (seção 3.1). Ele fica perto do original,
mas não igual: as ligas, clubes, nomes, escudos, Europa, copas, mudanças de jogadores e a
Conference League voltam; os torneios de pré-temporada, as copas dos países do jogo, os nomes das
competições, as vagas europeias das ligas do jogo, a ordem das ligas e os clubes europeus da
primeira temporada não. As imagens e os rostos apontam para o PC de quem mandou: a construção
desenha um emblema para uma imagem que falta e diz quais. O Mod Studio não instala por cima de um
mundo com o mesmo nome que foi construído nesse PC: renomeie esse mundo no cartão dele antes.

## 10. Ferramentas

**Diagnóstico** (**4. Ferramentas**) **— Rodar as verificações** olha a configuração inteira: pastas
de conteúdo que estão ligadas mas faltam, módulos na ordem errada ou ligados duas vezes, linhas de
map que apontam para nada, o mundo que está no jogo (aba **Seu mundo no jogo**; só um mundo deveria
estar ligado), e o último `sider.log`. **Copiar um relatório** coloca tudo na área de transferência
para colar num post de fórum ou num relatório de bug.

**Pontos de restauração** (**4. Ferramentas**): cada arquivo que o programa mudou, com a cópia de
antes. **Restaurar esta cópia** coloca ela de volta. As cópias ficam em
`SiderAddons\ModStudio\backups`. **Limpar...** tira as antigas, e sempre mantém a cópia mais antiga
de um arquivo (a de antes do Mod Studio). Os mundos apagados e renomeados e a cópia da sua pasta de
saves também aparecem aqui.

**Voltar o Sider para antes do Mod Studio...** (Pontos de restauração, e o menu **Jogo**) traz tudo
de volta: coloca cada arquivo que o Mod Studio mudou como era no começo (`sider.ini`, CommonLib, os
arquivos map) e tira o que ele trouxe (os módulos dele, o pacote de rostos, os mundos e mods
instalados com ele). Nada é apagado: fica guardado em `SiderAddons\ModStudio\reset-<hora>`, e
**Desfazer a última volta** coloca de volta.

**Configurações** (**5. Configurações**): **Pasta do jogo**, **Pasta do Sider** (quando há mais de
uma), **Idioma (Language)**, **Carreiras da Master League** (**Cada mundo guarda as próprias
carreiras (a pasta de saves troca junto com o mundo)**, seção 3.1), **As tabelas do jogo**
(**Extrair as tabelas do jogo**, **Usar outra pasta de tabelas...**, seção 2) e **Abrir a pasta de
configurações do programa**.

## 11. Quando algo dá errado

| O que você vê | O que fazer |
|---|---|
| *sider.ini not found* | Configurações → Pasta do jogo: escolha a pasta com o `FL_2026.exe`. |
| *não há tabelas do jogo* | Configurações → Extrair as tabelas do jogo. |
| *Acesso negado*, ou o Mod Studio diz que não consegue escrever na pasta do jogo | O jogo está em Arquivos de Programas: aperte **Reiniciar como administrador**, ou mova o jogo para uma pasta sua. |
| O Mod Studio diz que falta uma DLL dos módulos dele (`fl26swiss.dll` ...) | Um antivírus levou ela. Adicione a pasta `SiderAddons` como exceção no antivírus, depois **Instalar agora** de novo. |
| Um mod não aparece no jogo | Diagnóstico → Rodar as verificações. Uma pasta de conteúdo mais alta na lista pode ter o mesmo arquivo. |
| O jogo não inicia depois de uma mudança | Pontos de restauração → coloque o `sider.ini` de volta, ou troque para um perfil que funcionava. |
| A liga nova não está no Select Team | Comece uma carreira *nova*; carreiras antigas mantêm as ligas antigas. |
| As minhas carreiras sumiram depois de trocar de mundo | Elas estão em `save_<mundo>` ao lado da pasta de saves: ative esse mundo de novo (seção 3.1). |
| O goleiro é o capitão de todos os clubes novos | O mundo foi construído antes da 0.2.4: construa de novo e comece uma carreira nova. |
| O escudo no calção de um uniforme desenhado aparece de lado | O uniforme foi desenhado antes da 0.2.4. Apague os arquivos `kitmaker.txt` em `SiderAddons\content\kit-server\<seu mundo>` e aperte **Construir e instalar** de novo: os uniformes são desenhados de novo com o escudo na posição certa. |
| Os nomes dos clubes são os do jogo | Um arquivo do Edit passa por cima deles (seção 8). |
| *seus campeonatos não mandam ninguém para a Europa* | Campeonatos → escolha a primeira divisão → **Editar campeonato...** → Europa (o botão **Primeira divisão** preenche as três de costume), depois construa de novo. |
| *a Conference League está ativada, mas faltam as tabelas dela* | Construa o mundo de novo: ele foi construído antes da opção, ou com ela desligada. |
| Os passos da construção estão cinza | Um mundo pronto de um zip está no jogo. Antes use **Ativar** no seu próprio mundo, ou **Torná-lo editável...** (seção 8.2). |
| Um rosto não aparece | A pasta tem que ter `#Win\face.fpk`; construa de novo depois de escolher ela. |
| Qualquer outra coisa | Diagnóstico → **Copiar um relatório**, e poste ele com o `SiderAddons\sider.log`. |
