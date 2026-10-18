# Instalar um pacote pronto: cada clique, em ordem

> [English](../en/install-a-pack.md) · [hrvatski](../hr/install-a-pack.md) · [español](../es/install-a-pack.md) · **português** · [français](../fr/install-a-pack.md)

> O outro guia passo a passo: [Criar suas próprias ligas e pacotes](make-your-own-leagues.md)
> · cada página explicada: [mod-studio-guide.md](mod-studio-guide.md)
> · perguntas: [faq.md](../../docs/faq.md) (em inglês) · ajuda: [Discord](https://discord.gg/StQqtk3G3M)

Esta página é para quem nunca abriu o Mod Studio e recebeu algo pronto para jogar: um mundo,
um modpack ou um pacote de ligas. Ela não explica como nada funciona. Ela só diz o que clicar,
em que ordem, e o que você deve ver depois de cada passo. Faça os passos na ordem e não pule
nenhum. Se você vir algo diferente do que um passo diz, pare ali e vá para
[Se algo der errado](#se-algo-der-errado).

Os passos 1 a 3 são iguais para todo mundo e você faz uma vez só. Depois escolha o caminho que
combina com o arquivo que você recebeu:

- **Caminho A: um mundo pronto**, como um `.zip` (um modpack, o mundo de um amigo). O jeito
  mais rápido: nada para construir.
- **Caminho C: um pacote de liga**, um arquivo `.fl26pack` que alguém fez. O Mod Studio constrói
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
2. Em **Assets**, clique em `FL26ModStudio-<version>.zip` (por exemplo `FL26ModStudio-0.2.4.zip`).
3. Clique com o botão direito no zip baixado → **Extrair Tudo...** → escolha uma pasta, por
   exemplo `Documents\FL26 Mod Studio` → **Extrair**.

   Não rode o programa de dentro do zip. Não tire o `FL26ModStudio.exe` da pasta dele: as
   pastas `_internal` e `pack` ao lado dele têm que ficar junto.

4. Abra essa pasta e dê um clique duplo em `FL26ModStudio.exe`.

**Você deve ver:** uma janela escura. Em cima: os menus **Arquivo, Jogo, Perfis, Idioma (Language),
Ajuda**, o botão **Créditos**, e um botão verde **Iniciar o jogo** à direita. Embaixo deles,
caixas com o que está no jogo agora (**PASTA DO JOGO**, **SIDER**, **MUNDO ATIVO** ...), depois as
seções **1. Início**, **2. Meu mundo**, **3. Conteúdo do jogo**, **4. Ferramentas** e
**5. Configurações**.

Na primeira vez, um pequeno cartão mostra a janela em dez passos (o tour rápido). Leia com
**Próximo**, ou feche com **Pular o tour**. Ele não muda nada. **Ajuda → Tour rápido** mostra
ele de novo.

Se o Windows disser "O Windows protegeu o computador": clique em **Mais informações** →
**Executar assim mesmo**.

A janela começa em inglês, e este guia escreve os nomes como o programa mostra em português.
Para trocar: barra de cima → **Idioma (Language)** (em inglês o menu se chama *Language*) →
Português, depois abra o Mod Studio de novo. Ali também estão Hrvatski, Español e Français.

## Passo 3. Diga onde está o seu jogo

1. Clique em **5. Configurações**.
2. Ao lado da pasta do jogo, clique em **Procurar...**.
3. Escolha a pasta que tem o `FL_2026.exe` (por exemplo `D:\Games\Football Life 2026`). Não a
   `SiderAddons`, nem uma subpasta: a pasta com o `FL_2026.exe` dentro.
4. Clique em **Usar esta pasta**.

**Você deve ver:** embaixo da pasta, uma linha que começa com `Encontrado: FL_2026.exe` e diz a
pasta do Sider e o `sider.ini`.

(O mesmo está na barra de cima: **Jogo → Escolher a pasta do jogo...**.)

Não tem mais nada para configurar. Quando sabe onde está o seu jogo, o Mod Studio extrai as
tabelas do jogo (a lista de clubes, ligas e jogadores) sozinho, só na primeira vez. Isso leva um
ou dois minutos. Os módulos do Mod Studio entram com **Instalar o mundo** (caminho A) ou
**Construir e instalar** (caminho C). As ligas novas só funcionam com esses módulos, e eles trazem
o pacote de rostos que dá rosto aos jogadores novos. Se o **1. Início** disser alguma vez que eles
estão faltando ou são mais antigos, clique em **Instalar agora** ali.

Agora escolha o caminho que combina com o seu arquivo.

---

## Caminho A: um mundo pronto (um .zip)

Use este quando alguém te passou um mundo como zip (um modpack, um mundo exportado).

**A1.** Não descompacte você mesmo.

**A2.** Clique em **2. Meu mundo**, depois em **+ Adicionar...** (à direita, ao lado das abas).

**A3.** Clique em **Escolher um arquivo...** e escolha o zip. (Ou arraste o zip para essa
janela.) Uma linha verde começa com `Encontrado: um zip de mundo`. Clique em **Adicionar**: a
página **Importe seu mundo** abre com o zip.

(Dois outros caminhos para a mesma página: **1. Início → Importar um zip de mundo**, ou
**2. Meu mundo → Mais ▾ → Importar um zip de mundo**, depois escolha o zip.)

**A4. Você deve ver:** uma linha dizendo o que é, por exemplo `um mundo pronto para jogar
(_FL26Modpack)`, ou `uma versão mais nova do mundo _FL26Modpack que você tem` quando você tem uma
versão mais antiga, e embaixo quantas ligas tem dentro. As partes (o mundo, uniformes,
placares ...) estão em **Mais opções: quais partes, nome, ordem das pastas de conteúdo, linhas
dos map**, todas marcadas. Deixe assim. (Para instalar sem os uniformes, desmarque os uniformes ali.)

**A5.** Clique em **Instalar o mundo**. Se uma versão mais antiga do mesmo mundo já estiver
instalada (um Modpack anterior), ele pergunta se deve trocar: diga **Sim**. A antiga sai primeiro,
então nada dela fica para trás; os seus saves não são mexidos. Espere até dizer que terminou. O
Mod Studio instala os módulos (os desta versão), copia o mundo, coloca o arquivo do mundo onde os
módulos leem ele, e coloca o mundo no jogo.

**Você deve ver:** `✓ Pronto para jogar: aperte Iniciar o jogo e comece uma Master League nova`, e uma janela **Pronto para jogar** com uma lista de marcas (o
mundo, os módulos, o pacote de rostos ...). Se ela disser **Quase pronto**, ela lista o que
corrigir.

Em **2. Meu mundo** o mundo agora tem um cartão verde que diz **● NO JOGO AGORA**, com a etiqueta
**De um zip**.

Um mundo pronto não precisa ser construído: ele já está construído. Enquanto ele está no jogo, os
passos de construção ficam desligados. Para construir ligas suas depois, coloque primeiro o seu
próprio mundo no jogo (**Ativar** no cartão dele em **2. Meu mundo**). Vá para o
[Passo 4](#passo-4-inicie-o-jogo).

---

## Caminho B: monte suas próprias ligas

Escolher ligas reais do NewLife Database, ou criar ligas suas, tem um guia próprio, com cada
campo explicado:
[Criar suas próprias ligas e pacotes](make-your-own-leagues.md).

---

## Caminho C: um pacote de liga (.fl26pack)

**C1.** Clique em **2. Meu mundo**, depois em **+ Adicionar...** (à direita, ao lado das abas).

**C2.** Clique em **Escolher um arquivo...** e escolha o arquivo `.fl26pack`. (Ou arraste ele
para essa janela.)

**C3. Você deve ver:** uma linha verde `Encontrado: pacote de campeonatos "..."` com quantas
ligas e clubes ele tem, e as ligas dele numa lista, cada uma marcada. Desmarque uma liga que você
não quer. Embaixo da lista: quantas competições o seu mundo vai ter (o jogo tem lugar para 255),
e que nada chega ao jogo antes de **Construir e instalar**. Clique em **Adicionar**.

(Os outros caminhos: **2. Meu mundo → Mais ▾ → Pacotes de campeonatos → Adicionar um
pacote...**, ou **Arquivo → Adicionar um pacote de campeonatos...**. Eles mostram uma janela
**Adicionar um pacote de campeonatos**: ali você também pode desmarcar partes em **O que pegar**,
por exemplo os placares. Se não tiver certeza, deixe tudo marcado e clique em **OK**.)

Se o pacote tem uma liga com um nome que você já tem, ele pergunta se deve adicionar com um
nome novo: clique em **Sim**.

**Você deve ver:** a aba **Campeonatos**, com as ligas do pacote na lista, e embaixo da janela:
"... adicionado. Construir e instalar coloca os campeonatos dele no jogo."

Não tem nada para salvar: o seu mundo se salva sozinho um instante depois de cada mudança (a
barra de baixo diz **Seu mundo está salvo**).

**C4.** Aba **Construção** (a primeira aba de **2. Meu mundo**) → o botão grande **Construir e
instalar** → **Sim**.

Ele coloca os módulos do Mod Studio, constrói o seu mundo e coloca ele no jogo, tudo de uma vez.
Leva de alguns segundos a alguns minutos; a barra de baixo mostra quanto falta.

(Soltar o `.fl26pack` em **Importe seu mundo** faz o mesmo: depois da janela **Adicionar um
pacote de campeonatos** o pacote entra no seu mundo e o **Construir e instalar** começa sozinho.)

**Você deve ver:** uma janela **Construção concluída** com marcas (Mundo construído, Campeonatos
e clubes, Módulos instalados e ativados, No jogo). Clique em **Pronto**. Na caixa embaixo da aba
Construção não há nenhuma linha começando com `error:`.

---

## Passo 4. Inicie o jogo

Clique no botão verde **Iniciar o jogo** no canto superior direito (ou **Jogo → Iniciar o
jogo**). Espere o menu do jogo.

## Passo 5. Comece uma Master League NOVA

1. **Master League** → **New game** (não Continue: uma carreira antiga não recebe as ligas
   novas).
2. Em **Select Team**, role a lista: as ligas novas estão nela, embaixo dos países delas.
3. Escolha um clube e jogue.

As ligas novas também estão em **Kick Off** → League, e em **Database → Competition Info**.

Cada mundo guarda as próprias carreiras. Quando você coloca outro mundo no jogo, o Mod Studio
guarda as suas carreiras junto com o mundo a que pertencem, e traz elas de volta quando esse
mundo estiver no jogo de novo. Nada é apagado.

## Passo 6. Deixe o Mod Studio conferir se funcionou

1. Feche o jogo.
2. No Mod Studio: **2. Meu mundo** → aba **Construção** → **Passo a passo, e Exportar o mundo** →
   **4. Depois de iniciar: conferir**.

**Você deve ver:** uma linha por módulo dizendo quantas ligas ele leu do mundo, e no fim
`the world works as built`. Uma linha dizendo `not loaded` ou `did NOT read the world file`,
e a última linha `something is wrong -- see the lines above`, dizem o que está errado.

---

## Se algo der errado

| O que você vê | O que fazer |
|---|---|
| `error: não há tabelas do jogo -- Configurações > Extrair as tabelas do jogo` | **5. Configurações → Extrair as tabelas do jogo**. |
| Nenhuma liga nova no Select Team | Você começou uma Master League **nova**? Depois **4. Depois de iniciar: conferir** ([Passo 6](#passo-6-deixe-o-mod-studio-conferir-se-funcionou)). Se o log dele diz `world file -- 0 leagues`, o seu mundo estava vazio: adicione o pacote de novo (Caminho C) e construa de novo. |
| O mundo diz que foi construído com `0 leagues, 0 clubs` | O mesmo: o seu mundo não tinha ligas. Adicione algumas antes, depois construa. |
| `sider.log is older than the world switched on -- start the game to the main menu, then check again` | A conferência rodou antes de você iniciar o jogo. Inicie ele até o menu principal, feche, aperte **4. Depois de iniciar: conferir** de novo. |
| **Construir e instalar** está cinza | Um mundo pronto de um zip está aberto (Caminho A). Ele não precisa ser construído. Para construir suas próprias ligas, clique antes em **Ativar** no cartão do seu próprio mundo em **2. Meu mundo**. |
| A minha carreira antiga sumiu | Ela fica guardada com o mundo em que foi feita. Clique em **Ativar** no cartão desse mundo em **2. Meu mundo** e ela volta. |
| Todos os jogadores novos têm o mesmo rosto | **1. Início → Instalar agora** (quando o Início diz que os módulos estão faltando ou são mais antigos), ou **2. Meu mundo → Construção → Passo a passo, e Exportar o mundo → 0. Instalar os módulos**: traz o pacote de rostos. Depois inicie o jogo de novo. |
| O jogo dá crash ao iniciar | Inicie ele mais uma vez pelo launcher (um crash nos primeiros 10 segundos também acontece sem mods). Se continuar dando crash: **Jogo → Iniciar o jogo sem mods (modo seguro)...** e pergunte no Discord. |
| Você quer tudo de volta como era | **Importe seu mundo** (**2. Meu mundo → Mais ▾ → Importar um zip de mundo**) → selecione ele em **No jogo agora** → **Remover** tira um mundo instalado. **4. Ferramentas → Pontos de restauração → Voltar o Sider para antes do Mod Studio...** (também no menu **Jogo**) devolve cada arquivo que o Mod Studio mudou e tira o que ele trouxe. Nada é apagado: fica guardado em `SiderAddons\ModStudio\reset-<time>`, e **Desfazer a última volta** coloca de volta. |

**Pedir ajuda:** no [Discord](https://discord.gg/StQqtk3G3M), mande uma captura de tela do
que você vê e o seu `sider.log` (**Jogo → Abrir sider.log**, ou `SiderAddons\sider.log` na
pasta do jogo).
