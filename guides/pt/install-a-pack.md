# Instalar um pacote pronto: cada clique, em ordem

> [English](../en/install-a-pack.md) · [hrvatski](../hr/install-a-pack.md) · [español](../es/install-a-pack.md) · **português**

> O outro guia passo a passo: [Criar suas próprias ligas e pacotes](make-your-own-leagues.md)
> · cada página explicada: [mod-studio-guide.md](mod-studio-guide.md)
> · perguntas: [faq.md](../../docs/faq.md) (em inglês) · ajuda: [Discord](https://discord.gg/StQqtk3G3M)

Este guia escreve os nomes dos botões, páginas e opções em inglês, como o programa mostra na
primeira vez (em **Settings → Language** ele também fala português).

Esta página é para quem nunca abriu o Mod Studio e recebeu algo pronto para jogar: um mundo,
um modpack ou um pacote de ligas. Ela não explica como nada funciona. Ela só diz o que clicar,
em que ordem, e o que você deve ver depois de cada passo. Faça os passos na ordem e não pule
nenhum. Se você vir algo diferente do que um passo diz, pare ali e vá para
[Se algo der errado](#se-algo-der-errado).

Os passos 1 a 3 são iguais para todo mundo e você faz uma vez só. Depois escolha o caminho que
combina com o arquivo que você recebeu:

- **Caminho A: um mundo pronto**, como um `.zip` (um modpack, o mundo de um amigo). O jeito
  mais rápido: nada para montar.
- **Caminho C: um pacote de liga**, um arquivo `.fl26pack` que alguém fez. O Mod Studio monta
  ele para você.

Ninguém te passou nada, e você quer escolher ligas reais você mesmo (do NewLife Database) ou
criar as suas? Isso é o outro guia:
[Criar suas próprias ligas e pacotes](make-your-own-leagues.md). Faça antes os passos 1 a 3 daqui.

---

## Passo 1. Feche o jogo

O jogo tem que estar fechado enquanto você muda qualquer coisa. O Sider lê a configuração só
quando o jogo inicia. Olhe a barra de tarefas: nenhuma janela do Football Life, nenhum launcher.

## Passo 2. Baixe o Mod Studio

1. Abra a [versão mais recente](https://github.com/Matozanato/FootballLife-new-leagues/releases/latest).
2. Em **Assets**, clique em `FL26ModStudio-<version>.zip` (por exemplo `FL26ModStudio-0.2.1.zip`).
3. Clique com o botão direito no zip baixado → **Extract All...** → escolha uma pasta, por
   exemplo `Documents\FL26 Mod Studio` → **Extract**.

   Não rode o programa de dentro do zip. Não tire o `FL26ModStudio.exe` da pasta dele: as
   pastas `_internal` e `pack` ao lado dele têm que ficar junto.

4. Abra essa pasta e dê um clique duplo em `FL26ModStudio.exe`.

**Você deve ver:** uma janela escura. Em cima: **File, Game, Profiles, Language, Help,
Credits**, e um botão verde **Play** à direita. Na esquerda: **Home**, depois **YOUR WORLD**
(**Build your world**, **Import your world**, **Edit your world**, **NewLife Database**),
**GAME CONTENT**, **TOOLS** e, embaixo, **Settings**.

Se o Windows disser "Windows protected your PC": clique em **More info** → **Run anyway**.

Quer a janela em outro idioma? Barra de cima → **Language** → Hrvatski, Español ou Français.

## Passo 3. Diga onde está o seu jogo

1. Barra da esquerda, embaixo: clique em **Settings**.
2. Ao lado da pasta do jogo, clique em **Browse...**.
3. Escolha a pasta que tem o `FL_2026.exe` (por exemplo `C:\Football Life 2026`). Não a
   `SiderAddons`, nem uma subpasta: a pasta com o `FL_2026.exe` dentro.
4. Clique em **Use this folder**.

**Você deve ver:** embaixo da pasta, uma linha dizendo que o `SiderAddons\sider.ini` foi
encontrado.

(O mesmo está na barra de cima: **Game → Choose the game folder...**.)

Não tem mais nada para configurar. Quando sabe onde está o seu jogo, o Mod Studio descompacta
as tabelas do jogo (a lista de clubes, ligas e jogadores) sozinho, só na primeira vez. Os módulos
do Mod Studio entram com **Install the world** (caminho A) ou **Build and install** (caminho C).
As ligas novas só funcionam com esses módulos, e eles trazem o pacote de rostos que dá rosto aos
jogadores novos. Se a **Home** disser alguma vez que eles estão faltando ou são mais antigos,
clique em **Install now** ali.

Agora escolha o caminho que combina com o seu arquivo.

---

## Caminho A: um mundo pronto (um .zip)

Use este quando alguém te passou um mundo como zip (um modpack, um mundo exportado).

**A1.** Não descompacte você mesmo.

**A2.** Barra da esquerda, em **YOUR WORLD**: clique em **Import your world**.

**A3.** Clique em **Choose a file...** e escolha o zip. (Ou arraste o zip para essa página.)

**A4. Você deve ver:** uma linha dizendo o que é, por exemplo `a ready world to play
(_FL26Modpack)`, ou `a newer version of the world _FL26Modpack you have` quando você tem uma
versão mais antiga, e embaixo quantas ligas tem dentro. As partes (o mundo, uniformes,
placares ...) estão em **More options: which parts, name, order of the content folders, map
lines**, todas marcadas. Deixe assim. (Para instalar sem os uniformes, desmarque os uniformes ali.)

**A5.** Clique em **Install the world**. Se uma versão mais antiga do mesmo mundo já estiver
instalada (um Modpack anterior), ele pergunta se deve trocar: diga **Yes**. A antiga sai primeiro,
então nada dela fica para trás; os seus saves não são mexidos. Espere até dizer que terminou. O
Mod Studio instala os módulos (os desta versão), copia o mundo, coloca o arquivo do mundo onde os
módulos leem ele, e coloca o mundo no jogo.

**Você deve ver:** `✓ Ready to play: press Play and start a new Master League`, e uma janela
**Ready to play** com uma lista de marcas (o mundo, os módulos, o pacote de rostos ...). Se ela
disser **Almost ready**, ela lista o que corrigir.

Um mundo pronto não precisa de Build: ele já está montado. Enquanto ele está no jogo, os passos
do Build ficam desligados (0.2.4). Para montar ligas suas depois, coloque primeiro o seu próprio
mundo no jogo (**Home → Switch world...**). Vá para
[Passo 4](#passo-4-inicie-o-jogo).

---

## Caminho B: monte suas próprias ligas

Escolher ligas reais do NewLife Database, ou criar ligas suas, tem um guia próprio, com cada
campo explicado:
[Criar suas próprias ligas e pacotes](make-your-own-leagues.md).

---

## Caminho C: um pacote de liga (.fl26pack)

**C1.** Barra da esquerda, em **YOUR WORLD**: clique em **Build your world**, depois na aba
**League packages**.

**C2.** Clique em **Add a package...** e escolha o arquivo `.fl26pack`. (Ou na barra de cima:
**File → Add a league package...**.)

**C3. Você deve ver:** uma janela **Add a league package** com o que tem dentro: o nome, a
versão e o autor, depois as ligas, cada uma marcada. Um pacote com várias ligas tem
**Select all** / **Select none** em cima da lista: desmarque uma liga que você não quer. Em
**What to take** você pode desmarcar partes (por exemplo **Scoreboards ...**). Se não tiver
certeza, deixe tudo marcado. Clique em **OK**.

Se o pacote tem uma liga com um nome que você já tem, ele pergunta se deve adicionar com um
nome novo: clique em **Yes**.

**Você deve ver:** uma linha verde embaixo do título da página: "Added ... Build and install
puts its leagues in the game."

Não tem nada para salvar: o seu mundo se salva sozinho um instante depois de cada mudança (a
barra de baixo diz **Your world is saved**).

**C4.** Aba **Build** (ao lado de **League packages**) → o grande botão azul **Build and
install** → **Yes**.

Ele coloca os módulos do Mod Studio, monta o seu mundo e coloca ele no jogo, tudo de uma vez.
Leva de alguns segundos a alguns minutos.

(Soltar o `.fl26pack` em **Import your world** faz o mesmo: depois da janela do C3 o pacote
entra no seu mundo e o **Build and install** começa sozinho.)

**Você deve ver:** uma janela **Build finished** com marcas (World built, Leagues and clubs,
Modules installed and switched on, In the game). Clique em **Done**. Na caixa embaixo da página
Build não há nenhuma linha começando com `error:`.

---

## Passo 4. Inicie o jogo

Clique no botão verde **Play** no canto superior direito (ou **Game → Start the game**).
Espere o menu do jogo.

## Passo 5. Comece uma Master League NOVA

1. **Master League** → **New game** (não Continue: uma carreira antiga não recebe as ligas
   novas).
2. Em **Select Team**, role a lista: as ligas novas estão nela, embaixo dos países delas.
3. Escolha um clube e jogue.

As ligas novas também estão em **Kick Off** → League, e em **Database → Competition Info**.

## Passo 6. Deixe o Mod Studio conferir se funcionou

1. Feche o jogo.
2. No Mod Studio: **Build your world** → **Step by step, and Export the world** → **4. After a
   start: check**.

**Você deve ver:** uma linha por módulo dizendo quantas ligas ele leu do mundo, e no fim
`the world works as built`. Uma linha dizendo `not loaded` ou `did NOT read the world file`,
e a última linha `something is wrong -- see the lines above`, dizem o que está errado.

---

## Se algo der errado

| O que você vê | O que fazer |
|---|---|
| `error: no game tables -- Settings > Unpack the game's tables` | **Settings → Unpack the game's tables**. |
| Nenhuma liga nova no Select Team | Você começou uma Master League **nova**? Depois **4. After a start: check** ([Passo 6](#passo-6-deixe-o-mod-studio-conferir-se-funcionou)). Se o log dele diz `world file -- 0 leagues`, o seu mundo estava vazio: adicione o pacote de novo (Caminho C) e faça o Build de novo. |
| O mundo diz que foi montado com `0 leagues, 0 clubs` | O mesmo: o seu mundo não tinha ligas. Adicione algumas antes, depois Build. |
| `sider.log is older than the world switched on -- start the game to the main menu, then check again` | A conferência rodou antes de você iniciar o jogo. Inicie ele até o menu principal, feche, aperte **4. After a start: check** de novo. |
| Todos os jogadores novos têm o mesmo rosto | **Home → Install now** (quando a Home diz que os módulos estão faltando ou são mais antigos), ou **Build your world → Step by step, and Export the world → 0. Install the modules**: traz o pacote de rostos. Depois inicie o jogo de novo. |
| O jogo dá crash ao iniciar | Inicie ele mais uma vez pelo launcher (um crash nos primeiros 10 segundos também acontece sem mods). Se continuar dando crash: **Game → Start the game without mods (safe mode)...** e pergunte no Discord. |
| Você quer tudo de volta como era | **Import your world** → selecione ele em **In the game now** → **Remove** tira um mundo instalado. **TOOLS → Restore points → Put Sider back as before Mod Studio...** (também no menu **Game**) devolve cada arquivo que o Mod Studio mudou e tira o que ele trouxe. Nada é apagado: fica guardado em `SiderAddons\ModStudio\reset-<time>`, e **Undo the last reset** coloca de volta. |

**Pedir ajuda:** no [Discord](https://discord.gg/StQqtk3G3M), mande uma captura de tela do
que você vê e o seu `sider.log` (**Game → Open sider.log**, ou `SiderAddons\sider.log` na
pasta do jogo).
