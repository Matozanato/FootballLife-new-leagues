# Criar suas próprias ligas e pacotes: cada clique, em ordem

> [English](../en/make-your-own-leagues.md) · [hrvatski](../hr/make-your-own-leagues.md) · [español](../es/make-your-own-leagues.md) · **português**

> O outro guia passo a passo: [Instalar um pacote pronto](install-a-pack.md)
> · cada página e opção explicada: [mod-studio-guide.md](mod-studio-guide.md)
> · perguntas: [faq.md](../../docs/faq.md) (em inglês) · ajuda: [Discord](https://discord.gg/StQqtk3G3M)

O programa não tem janela em português, então este guia escreve os nomes dos botões, campos,
páginas e opções em inglês, exatamente como o programa mostra.

Esta página te leva do zero até as suas próprias ligas no jogo: ligas reais com clubes e
jogadores reais do **NewLife Database**, configuradas do jeito que você quer, montadas, jogadas
e compartilhadas com outras pessoas. Ela diz o que clicar, o nome exato de cada botão e campo
como o Mod Studio mostra, e o que você deve ver depois de cada passo. Faça os passos na ordem.
Se você vir algo diferente do que um passo diz, pare ali e olhe em
[Se algo der errado](#se-algo-der-errado).

Três palavras que você vai encontrar o tempo todo:

- **Receita** (*recipe*): a sua lista de ligas e tudo o que você configurou para elas. Você
  muda ela nas páginas do **LEAGUE BUILDER**. É só um plano: nada chega ao jogo até você fazer
  o **Build**.
- **Mundo** (*world*): o que o Build faz a partir da receita, uma pasta cujo nome começa com
  `_FL26` (`_FL26MyWorld`, a não ser que você mude). O jogo lê ela enquanto ela está ligada.
- **Build**: o botão que transforma a receita num mundo e coloca ele no jogo.

**Conteúdo**

- [Antes de começar: a configuração de uma vez só](#antes-de-começar-a-configuração-de-uma-vez-só)
- [Passo 1. Pegue o NewLife Database](#passo-1-pegue-o-newlife-database)
- [Passo 2. Abra ele na página NewLife Database](#passo-2-abra-ele-na-página-newlife-database)
- [Passo 3. Escolha suas ligas](#passo-3-escolha-suas-ligas)
- [Passo 4. Escolha os clubes de uma liga](#passo-4-escolha-os-clubes-de-uma-liga)
- [Passo 5. Adicione à receita](#passo-5-adicione-à-receita)
- [Passo 6. A página Leagues: cada configuração de uma liga](#passo-6-a-página-leagues-cada-configuração-de-uma-liga)
- [Passo 7. Exemplo: um país com duas divisões](#passo-7-exemplo-um-país-com-duas-divisões)
- [Passo 8. A página New clubs: nomes, escudos, uniformes, clubes do jogo](#passo-8-a-página-new-clubs-nomes-escudos-uniformes-clubes-do-jogo)
- [Passo 9. A página Players](#passo-9-a-página-players)
- [Passo 10. Limites que barram um Build](#passo-10-limites-que-barram-um-build)
- [Passo 11. Salve a receita](#passo-11-salve-a-receita)
- [Passo 12. Faça o Build](#passo-12-faça-o-build)
- [Passo 13. Jogue: uma Master League NOVA, depois a conferência](#passo-13-jogue-uma-master-league-nova-depois-a-conferência)
- [Passo 14. Mudar algo depois](#passo-14-mudar-algo-depois)
- [Passo 15. Compartilhar o que você fez](#passo-15-compartilhar-o-que-você-fez)
- [Se algo der errado](#se-algo-der-errado)

---

## Antes de começar: a configuração de uma vez só

Faça antes os passos 1 a 5 do outro guia, uma vez:
[feche o jogo](install-a-pack.md#passo-1-feche-o-jogo),
[baixe o Mod Studio](install-a-pack.md#passo-2-baixe-o-mod-studio),
[diga onde está o seu jogo](install-a-pack.md#passo-3-diga-onde-está-o-seu-jogo),
[descompacte as tabelas do jogo](install-a-pack.md#passo-4-descompacte-as-tabelas-do-jogo) e
[instale os módulos do Mod Studio](install-a-pack.md#passo-5-instale-os-módulos-do-mod-studio).
Depois volte aqui.

Mantenha o jogo fechado o tempo todo em que você trabalha no Mod Studio.

---

## Passo 1. Pegue o NewLife Database

O NewLife Database é um download separado com clubes e jogadores reais: nomes, datas de
nascimento, posições, notas na escala do jogo, e as cores dos clubes. Ele não está no GitHub.

1. Abra o nosso [Discord](https://discord.gg/StQqtk3G3M) e vá para o canal **#newlife**.
2. Baixe as partes que você quer. Há uma parte por continente (um continente grande vem em
   mais de uma parte), mais *Free agents*. Cada parte é um arquivo `.zip` chamado `NewLife-...zip`.
3. Crie uma pasta para elas, por exemplo `Documents\NewLife`, e coloque **todas** as partes
   nessa mesma pasta.
4. **Não descompacte.** O Mod Studio lê os zips como estão. (O visualizador de zip do próprio
   Windows nem consegue abrir eles; isso é normal.)

Quando sair uma versão mais nova do NewLife, coloque as partes dela numa pasta **nova**. Nunca
misture duas versões numa pasta.

## Passo 2. Abra ele na página NewLife Database

1. Barra da esquerda, em **LEAGUE BUILDER**: clique em **NewLife Database**.
2. Clique em **Open NewLife Database...** em cima.
3. Escolha a pasta do Passo 1 (a pasta, não um zip dentro dela) e confirme.
4. Espere alguns segundos enquanto ele lê.

**Você deve ver:** em cima da lista, a versão do NewLife e a pasta, e embaixo delas
`Parts:` com as partes que ele encontrou. Abaixo disso, uma lista longa de ligas.

O Mod Studio lembra a pasta: na próxima vez a página abre ela sozinha.

**Busca.** A caixa em cima da lista, *Search leagues or countries*, deixa só as ligas cujo
nome ou país tem o que você digita. Digite `brazil` ou `liga`, digamos. Esvazie a caixa para
ver tudo de novo.

**As colunas.** Clique no título de uma coluna para ordenar por ela, clique de novo para
inverter a ordem.

| Coluna | O que ela diz |
|---|---|
| **League** | O nome da liga. Um `*` depois dele quer dizer que você mudou os clubes dela (Passo 4). |
| **Country** | Onde ela vai no jogo. |
| **Clubs** | Quantos clubes ela vai ter, do jeito que está configurada agora. |
| **In game** | Quantos dos clubes dela o jogo já tem (eles mantêm os próprios nomes, escudos, uniformes e jogadores). |
| **Players** | Quantos jogadores os clubes dela têm no NewLife. |
| **Level** | O quanto a liga é forte. Mais alto é mais forte. |
| (última coluna) | Por que uma liga cinza não pode ser adicionada. Vazia para uma liga que você pode adicionar. |

**Por que algumas ligas estão cinza.** Uma liga cinza não pode ser adicionada, e a última
coluna diz por quê:

- `a league takes 10 to 24 clubs`: uma liga no jogo tem de 10 a 24 clubes, os novos e os do
  jogo juntos. Esta tem menos ou mais. Você ainda pode consertar isso no Passo 4 (adicionar ou
  deixar clubes de fora) até ela caber.
- `the game's own league: Bring the game's leagues to this season`: o jogo já tem esta liga (a
  Premier League, o Championship ...). Ela não é adicionada uma segunda vez. O botão
  **Bring the game's leagues to this season...** em cima dá às ligas do próprio jogo os clubes
  e elencos desta temporada do NewLife no lugar; veja
  [8.4 no guia completo](mod-studio-guide.md#84-newlife-database-clubes-e-jogadores-reais).

Se a página disser que o Mod Studio não tem as tabelas do jogo e oferecer abrir o Settings:
clique em **Yes** e faça
[Descompacte as tabelas do jogo](install-a-pack.md#passo-4-descompacte-as-tabelas-do-jogo).

## Passo 3. Escolha suas ligas

1. Clique numa liga da lista para selecionar ela. A linha dela fica destacada.
2. Para mais de uma: segure **Ctrl** e clique em cada uma. (Ou clique na primeira, segure
   **Shift** e clique na última para pegar tudo o que está entre elas.)

**Você deve ver:** embaixo da página uma linha como
`New clubs in the recipe: 0 of the 793 the game takes.  Selected: 18 more.`

- O **primeiro** número é quantos clubes novos a sua receita já tem.
- O **segundo** é quantos clubes novos cabem no jogo ao todo. O Mod Studio calcula isso a
  partir das tabelas do seu jogo, então pode ser um pouco diferente em outra versão do jogo.
- **Selected** é quantos clubes novos as ligas que você escolheu adicionariam.

Se a receita e a seleção juntas passam do que o jogo aceita, **Add to the recipe** fica cinza:
escolha menos ligas.

## Passo 4. Escolha os clubes de uma liga

Este passo é opcional. Pule ele para pegar uma liga exatamente como o NewLife tem.

Selecione **uma** liga (só uma). A lista da direita mostra os clubes dela: **Club** e
**Players** (quantos jogadores o NewLife dá a ele). Um clube que o jogo já tem aparece cinza,
com `in the game` no lugar de um número.

- **Deixar um clube de fora:** clique na caixa de marcação dele para desmarcar.
- **Trazer um clube de outra liga** (a primeira divisão desta temporada é a da temporada passada
  com dois clubes que subiram, digamos): clique em **Add a club from another league...** embaixo
  da lista.
  1. Abre uma janela com todos os clubes das partes do NewLife que você abriu, cada um com a
     liga dele entre parênteses.
  2. Digite na caixa de busca para achar um clube ou uma liga.
  3. Marque um ou mais clubes. A linha embaixo da lista diz quantos você escolheu.
  4. Clique em **OK**.

  **Você deve ver:** o clube no fim da lista, com `from <its league>` ao lado.

**Você deve ver:** a linha da liga na lista agora tem um `*`, e o número em **Clubs** mudou.
Uma liga cinza que agora tem de 10 a 24 clubes volta ao normal.

Um clube só pode jogar em uma liga. Se você colocar ele em duas, o Mod Studio te barra no
Passo 5.

## Passo 5. Adicione à receita

Com a sua liga ou ligas selecionadas, clique em **Add to the recipe** em cima.

**Você deve ver:** uma linha verde embaixo do título da página. O que cada linha quer dizer:

| Linha verde | O que quer dizer |
|---|---|
| `Added: <leagues>. Change them on Leagues, New clubs and Players, then Build.` | As ligas estão na sua receita, cada uma como primeira divisão do país dela, todos contra todos duas vezes. Nada está no jogo ainda. |
| `<clubs> also play in a competition of the game: on New clubs pick each one and use Club of the game to choose the club that takes its place there.` | Esses clubes da sua liga nova são clubes que o jogo já tem, e eles também jogam em algum lugar no jogo (uma liga, uma copa, a Europa League ...). Um clube joga em uma liga só, então o lugar antigo dele precisa de outro clube. Você escolhe esse clube no [Passo 8](#clubes-que-o-jogo-já-tem). Até fazer isso, o Build para com um erro que diz o nome do clube. |
| `<n> players stay at their game club (their club would have too few players).` | Jogadores que o jogo já tem normalmente vão para o clube do NewLife. Esses ficam, para que o clube antigo deles mantenha pelo menos 18 jogadores. Nada a fazer. |
| `<n> players are not added: another league already has them.` | Uma liga que você adicionou antes já pegou esses jogadores. Nada a fazer. |

Se uma janela de erro disser `<club> would play in two leagues (<league> and <league>).`,
desmarque esse clube numa das duas ligas (Passo 4) e tente de novo.

Quer ligas de outros continentes? Selecione elas também e clique em **Add to the recipe** de
novo. Cada clique adiciona; ele nunca tira o que já está lá.

---

## Passo 6. A página Leagues: cada configuração de uma liga

1. Barra da esquerda: clique em **Leagues**.
2. Em cima da lista, clique em **Ours**: a lista mostra só as ligas da sua receita. (**All**
   mostra todas as ligas, as do jogo também; **Changed**, as ligas do jogo que você mudou.) As
   ligas ficam agrupadas por continente.
3. Clique na sua liga.

**Você deve ver:** à direita, `OURS`, o nome e o logo da liga, e as linhas **Country**,
**Clubs**, **Format**, **Division**, **Up / down**, **Europe** e **League ID** (`not built yet`
até o primeiro Build), depois os escudos dos clubes dela. Embaixo, os botões **Edit league...**,
**Add lower tier**, **Clubs and names**, **Players** e **Remove**.

Você pode arrastar uma liga para cima ou para baixo na lista para pôr as ligas de um continente
em ordem.

4. Clique em **Edit league...**.

**Você deve ver:** uma janela chamada **League** com os campos abaixo, de cima para baixo. Um
campo cinza não pode ser usado com o que você configurou acima dele (por exemplo uma copa numa
segunda divisão). O **?** ao lado de **OK** explica a janela em poucas palavras. Nada é
obrigatório: os padrões funcionam, e **Cancel** não muda nada.

| Campo | O que é, e o que fazer |
|---|---|
| **Name** | O nome da liga no jogo. Duas ligas não podem ter o mesmo nome. Mantenha abaixo de uns 38 caracteres: um nome mais longo aparece como uma linha vazia na lista de ligas do Kick Off. |
| **Country** | Digite algumas letras e escolha da lista (`korea` acha as duas Coreias). Ele dá a bandeira e onde a liga aparece na lista do jogo. |
| **Clubs** | 10 a 24. Para uma liga do NewLife, deixe como está: um número menor tira os últimos clubes, um maior adiciona clubes inventados no fim. |
| **Clubs in no league** | Deixe em `(no -- a league)`. As outras escolhas (*Other European teams* ...) são para um clube, ou alguns, sem uma liga em volta; eles entram nos grupos "Other ..." do jogo, e a maioria dos campos abaixo fica cinza. [Mais](mod-studio-guide.md#8-league-builder-novas-ligas-clubes-e-jogadores). |
| **Format** | Escolha um: **everyone plays everyone, times:** e o número (1 a 4; 2 é ida e volta); **splits in two (Scottish style)**, com `first` *n* `x, then groups` *6/6* *n* `x` (os grupos têm que somar a quantidade de clubes); ou **Apertura and Clausura, then playoffs of:** *8 clubs*, *4 clubs* ou *no playoffs* (dois torneios curtos por temporada, no máximo 18 clubes). |
| **Division** | `(top division)` = a melhor liga do país dela. Para uma segunda divisão, escolha a liga um nível acima: as suas ligas novas estão no topo da lista, depois as ligas do jogo com um número entre parênteses. `= division 2` ao lado mostra o nível. Uma liga que já tem uma liga embaixo fica cinza (`-- under it: ...`): uma liga pode ter uma liga abaixo dela. Veja o [Passo 7](#passo-7-exemplo-um-país-com-duas-divisões). |
| **Exhibition only -- not in Master League** | Deixe desligado. Ligado: a liga é só para Kick Off e partidas amistosas (lendas, uma temporada histórica); ela nunca joga uma temporada da Master League, e a divisão, as copas e a Europa ficam cinza. Não comece uma carreira com um dos clubes dela. |
| **Season** | Só primeira divisão: **August to May** (como a Europa) ou **February to December** (como o Brasil ou o Japão). Uma divisão abaixo acompanha a liga de cima. Fevereiro a dezembro ainda não pode ter divisão em dois, Apertura/Clausura nem as copas do país. |
| **Up / down** | 1 a 6: quantos clubes trocam de lugar com a liga de cima no fim da temporada. Só faz sentido numa divisão embaixo de outra. |
| **Logo** | **Pick picture...** um PNG ou JPG para a liga (um PNG com fundo transparente fica melhor). **Clear** tira. Vazio: `(made for you)`, um logo é desenhado no Build. |
| **Country flag** | Sua própria imagem da bandeira do país. Vazio: `(the game's own)`. Deixe vazio a não ser que o jogo não tenha uma bandeira boa. |
| **Cup** | Só primeira divisão. Marque **National cup** para dar ao país uma copa mata-mata (esta liga e a divisão abaixo dela). A caixa ao lado é o nome da copa; vazio = o nome da liga + Cup. |
| **Super cup (champion v cup winner)** | Um jogo no fim de julho. Precisa de **National cup** marcado. |
| **League cup** | Só primeira divisão. Uma segunda copa mata-mata, como a Carabao Cup da Inglaterra: esta liga e a de baixo, até 44 clubes. A caixa é o nome dela; vazio = o nome da liga + League Cup. |
| **Cup logos** | Uma imagem para cada: a **Cup**, a **Super cup**, a **League cup** e os **Playoffs**. Vazio: um emblema com as iniciais da copa. |
| **Formation** | Como os clubes da liga entram em campo. Escolha uma da lista, ou deixe vazio para o 4-2-3-1 padrão do jogo. Um clube sozinho pode ter a própria (Passo 8). |
| **Europe** | Só primeira divisão: qual posição da tabela vai para qual competição continental. O botão que começa com **Top flight:** preenche as vagas de sempre do continente do país (para a Europa: `Top flight: 1st UCL qualifying, 2nd UEL, 3rd UECL`). **Add place** adiciona uma linha: escolha a **League position** (abaixo de 1 fica **Cup winner**) e a **Competition**. O **✕** numa linha tira ela, **Clear** tira todas. Deixe vazio para uma segunda divisão. |

5. Clique em **OK**.

**Você deve ver:** a janela fecha e as linhas à direita mostram o que você configurou.

Uma liga do NewLife chega sem vagas europeias. Se você quer os clubes dela na Champions League
e nas outras, configure **Europe** agora; senão o **1. Check the plan** te lembra com
`no European places: the new leagues send nobody to Europe`.

O significado de cada formato, copa e vaga europeia em detalhe (datas, fases preliminares,
tamanhos das copas):
[seção 8 do guia completo](mod-studio-guide.md#8-league-builder-novas-ligas-clubes-e-jogadores)
e [8.2](mod-studio-guide.md#82-montar-ligar-jogar).

**More ▾** (em cima da página Leagues) tem as ferramentas para o mundo inteiro:
**Pre-season cups**, **Cups of the game's countries**, **European places of the game's leagues**,
**UEFA ranking**, **South American places**, **Competition names** (nomes e logos novos para
copas e competições continentais) e **World name and recipe...** (o nome da pasta do mundo; tem
que começar com `_FL26`). Você não precisa de nenhuma delas para um primeiro mundo.

**Uma liga sem clubes do NewLife.** **Add league** em cima da página Leagues abre a mesma
janela **League** para uma liga feita do zero: dê a ela um **Name**, um **Country** e uma
quantidade de **Clubs**, e o Build faz os clubes com elencos completos e um técnico. Você dá
nome a eles em **New clubs** (Passo 8), onde **NewLife club...** também pode colocar clubes
reais nela.

## Passo 7. Exemplo: um país com duas divisões

Digamos que as suas partes do NewLife têm a primeira e a segunda divisão de um país, aqui
chamadas *First League* e *Second League*. Você quer acesso e rebaixamento entre elas.

1. **NewLife Database**: selecione *First League* e clique em **Add to the recipe**. (A de cima
   primeiro.)
2. Selecione *Second League* e clique em **Add to the recipe**.

   **Você deve ver:** a linha verde `Added:` cada vez. As duas agora são primeiras divisões do
   mesmo país, o que ainda não é o que você quer.

3. **Leagues** → **Ours** → clique em *Second League* → **Edit league...**.
4. **Division**: abra a lista e escolha *First League* (as suas ligas estão no topo).

   **Você deve ver:** `= division 2` ao lado. **Cup**, **League cup**, **Season** e o botão
   **Top flight** ficam cinza: eles pertencem à primeira divisão.

5. **Up / down**: quantos clubes sobem e descem entre as duas, por exemplo `3`.
6. **Europe**: se tiver linhas, clique em **Clear**. Uma segunda divisão não manda ninguém para
   a Europa.
7. Clique em **OK**.

   **Você deve ver:** à direita, **Division** `2  (below First League)` e **Up / down**
   `3 with First League above`. Clique em *First League*: o **Up / down** dela diz
   `3 with Second League below`.

8. Clique em *First League* → **Edit league...** e configure o que pertence à primeira divisão:
   **Europe** (o botão **Top flight**), e se quiser **National cup**, **Super cup** e
   **League cup**. Clique em **OK**.

Uma terceira divisão funciona do mesmo jeito: a **Division** dela é *Second League*. O jogo vai
até a 7ª divisão.

**Uma liga embaixo de uma liga.** Duas ligas não podem ficar embaixo da mesma liga (três grupos
regionais embaixo de uma segunda divisão, digamos). A segunda aparece cinza na lista
**Division**.

**Embaixo de uma das ligas do jogo.** A sua liga nova também pode ir embaixo de uma liga que o
jogo tem: escolha a liga do jogo em **Division** (as que têm um número entre parênteses). Ela
então joga acesso e rebaixamento com ela.

**Sem o NewLife.** Em **Leagues**, clique na sua primeira divisão, depois em **Add lower tier**:
abre uma janela **League** com o país, os clubes, o formato e a divisão já preenchidos. Dê a ela
um **Name** e clique em **OK**.

---

## Passo 8. A página New clubs: nomes, escudos, uniformes, clubes do jogo

1. Barra da esquerda: clique em **New clubs** (ou em **Clubs and names** na página Leagues).
2. Em cima, **League**: escolha uma das suas ligas.

**Você deve ver:** os clubes dela com as colunas **#**, **Name**, **Short name**, **Team ID**
(`at Build` até o primeiro Build), **Crest** e **Players changed**. Os clubes do NewLife já
têm nomes, nomes curtos e escudos. Um clube sem nome aparece como `<league> 01`,
`<league> 02` ... em cinza.

### Nome, escudo, uniformes, técnico

1. Dê um clique duplo num clube (ou selecione ele e clique em **Edit club**).

**Você deve ver:** uma janela chamada **Club** com:

| Campo | O que fazer |
|---|---|
| **Name** | O nome do clube. Letras com acentos (Željezničar) funcionam. |
| **Short name** | Três letras ou dígitos. Vazio = feito a partir do nome. Č, Ž, Đ ... viram C, Z, D, como no jogo. |
| **Crest** | **Pick picture...** um PNG ou JPG. **Clear** tira. Um clube sem escudo ganha um distintivo numerado. |
| **Home stadium** | Só quando o Stadium Server está instalado: **Choose stadium...** do seu pacote de estádios, ou **Game's own**. |
| **Manager** | O nome do técnico. Vazio: um nome inventado a partir de jogadores do país do clube. |
| **Manager picture** | Um PNG ou JPG; o jogo mostra ele no Edit mode e na Master League. |
| **Formation** | `As the league (...)` mantém a formação da liga; ou escolha uma para este clube. |
| **Home kit colours**, **Away kit colours** | Clique nos dois quadrados de cor (camisa, segunda cor) para escolher as cores; **None** = o Build escolhe um uniforme sozinho. O Build dá ao clube o uniforme do jogo mais parecido com essas cores. |

2. Clique em **OK**.

**Você deve ver:** o nome e o escudo novos na lista.

**Uniformes.** Um clube novo pega emprestado um uniforme de um clube do jogo nas cores dele.
Duas opções na página **Build** mudam isso: **Make kits for the new clubs** (ligada por padrão,
precisa do Kit Server instalado: todo clube novo ganha uniformes de casa, fora, terceiro e de
goleiro feitos nas cores dele, com o escudo dele) e **Kits you can edit in the game** (cada
clube novo veste um uniforme simples que você pode mudar no Edit mode do jogo).
[Mais no guia completo](mod-studio-guide.md#8-league-builder-novas-ligas-clubes-e-jogadores).

**Muitos clubes de uma vez.** **More ▾** tem **Paste names...** e **Load names from file...**
(um nome por linha, na ordem) e **Import crests...** (uma pasta de imagens, ligadas aos clubes
pelo nome do arquivo). Ele também tem **Insert club**, **Remove club**, **New club here** e
**Move to another league...**.

### Clubes que o jogo já tem

Uma liga do NewLife pode incluir clubes que o jogo já tem. Eles aparecem na lista com o nome
do jogo, o **Team ID** deles, e `(the game's)` em **Crest**. Se a linha verde no Passo 5
disse que eles *also play in a competition of the game* (também jogam numa competição do jogo),
faça isto para **cada** um deles:

1. Clique no clube na lista.
2. Clique em **Club of the game...**.

**Você deve ver:** uma janela chamada **Club of the game**, com o clube selecionado e embaixo
da lista uma linha como `<club> plays in <competitions>. Every one of those competitions keeps its
number of clubs: pick who takes its place there.`

3. Escolha quem toma o lugar antigo dele:
   - **Its place goes to a club of the game that plays in nothing:** e escolha um clube da
     lista embaixo; ou
   - **Its place goes to a new club, named:** e digite um nome. O Build faz esse clube.
4. Se o clube joga uma competição continental (Champions League, Libertadores ...), também há
   **It keeps its places in continental competitions**. Marcado, ele continua jogando essa
   competição e ninguém precisa tomar o lugar dele ali.
5. Clique em **OK**.

O mesmo botão coloca qualquer clube do jogo num lugar da sua liga: selecione o lugar,
**Club of the game...**, busque pelo nome, nome curto ou team ID (**Only clubs in no league**
filtra a lista). **New club here** (em **More ▾**) devolve o lugar a um clube novo.

**NewLife club...** coloca clubes do NewLife, com os elencos deles, no lugar selecionado e nos
lugares seguintes: marque um ou mais na janela que abre, depois **OK**. É assim que uma liga que
você fez na mão ganha clubes reais.

## Passo 9. A página Players

Os clubes do NewLife vêm com elencos completos, então você não precisa mexer nesta página. Ela
está aí se você quiser mudar um elenco.

1. Barra da esquerda: clique em **Players** (ou selecione um clube em New clubs e clique em
   **Players**).
2. Em cima, escolha a **League** e o **Club**. (Ou digite em *Find a club...*.)

**Você deve ver:** o elenco com as colunas **Order**, **No.**, **Name**, **Pos**, **Age**,
**Rating**, **Foot**, **Changed** e **Player ID**, e os onze titulares num campo embaixo.
Clique num jogador: o lado direito mostra ele, nas abas **Basics**, **Positions**, **Abilities**
e **Skills**.

- Mude um nome, número, posição, nota ou habilidade à direita. A mudança fica guardada na hora.
- **Order up** / **Order down**: a ordem do elenco. Os primeiros onze começam a partida. Ou
  arraste um jogador para uma posição no campo. **Best eleven** coloca o jogador mais forte em
  cada posição.
- **Sign players...** traz jogadores de outros clubes; **Transfer to...** manda o jogador
  selecionado para outro clube.
- **Undo changes to this player** e **Undo all changes of this club** voltam atrás.

Tudo desta página está em [Jogadores no guia completo](mod-studio-guide.md#jogadores).

---

## Passo 10. Limites que barram um Build

| Limite | Onde você vê |
|---|---|
| Clubes novos ao todo: o número na linha `New clubs in the recipe: X of the Y the game takes.` | Página NewLife Database: **Add to the recipe** fica cinza. Build: `error: <n> new clubs, but the game has room for <m> more (a full squad each)`. |
| 10 a 24 clubes numa liga | NewLife Database: liga cinza, `a league takes 10 to 24 clubs`. New clubs: `A league has 10 to 24 clubs.` |
| Ligas novas por mundo (39 nos nossos testes) | Build: `error: <n> leagues, but the game has room for <m> ...` |
| Uma liga embaixo de uma liga | Lista **Division**: cinza. Build: `... are all under ...; the game follows one link down from a league ...` |
| Divisões até a 7ª | Build: `error: <league>: division 8 -- the rank field stops at 7`. |
| 2 ligas divididas por mundo; uma divisão em dois ou Apertura/Clausura por país | Build: `error: at most 2 split leagues for now ...`, `... only one league of a country can be split or Apertura/Clausura`. |
| Um clube em uma liga só | Build: `error: <club> is in <league> and in <league>: a club plays in one league`. |
| Um clube do jogo que joga em algum lugar precisa de um substituto | Build: `error: <league>, club <n>: <club> plays in <...> -- pick the club that takes its place there`. Faça [Clubes que o jogo já tem](#clubes-que-o-jogo-já-tem). |

Todos os números: [8.3 Limites](mod-studio-guide.md#83-limites).

## Passo 11. Salve a receita

1. Barra de cima: **File → Save recipe**.
2. Na primeira vez, abre uma janela **Save recipe as...**. Ela sugere o nome do mundo, por
   exemplo `_FL26MyWorld.json`. Escolha uma pasta que você vai achar de novo (por exemplo
   `Documents\FL26 Mod Studio\recipes`) e clique em **Save**.

**Você deve ver:** embaixo da janela, `Recipe saved: <file>`.

Depois disso, **File → Save recipe** salva no mesmo arquivo sem perguntar. **File → Save recipe
as...** salva uma cópia com outro nome. **File → Open recipe...** abre de novo uma receita salva
(ele avisa se você tem mudanças não salvas). **File → New recipe** começa uma vazia.

O Build também guarda uma cópia da receita sozinho, e o Mod Studio abre a última receita quando
inicia, então o que você montou nunca se perde. Salve mesmo assim: o seu próprio arquivo é o que
você consegue achar e copiar.

## Passo 12. Faça o Build

1. Barra da esquerda: clique em **Build**.

**Você deve ver:** o grande botão azul **Build and install**, a fileira **0. Install the
modules**, **1. Check the plan**, **2. Build the world**, **3. Switch it on**, **4. After a
start: check** e **Export the world...**, dois cartões (**European cups** e **New clubs**)
com opções, uma linha como `World _FL26MyWorld: not built yet · builder modules: installed`,
e uma caixa para o log embaixo.

2. Clique primeiro em **1. Check the plan**. Ele não muda nada; só lê a sua receita.

**Você deve ver:** na caixa, uma linha `world _FL26MyWorld: 2 new leagues, ...` e uma linha para
cada liga com os clubes, a divisão e o formato dela (`18 clubs x2` são 18 clubes, todos contra
todos duas vezes; `division 2  below ... (3 up/down)` é uma segunda divisão), e as
`European places:` dela. Uma linha começando com `error:` diz o que consertar primeiro; veja a
tabela no fim.

3. Clique em **Build and install**. Ele pergunta `Build _FL26MyWorld and make it the live world? ...`:
   clique em **Yes**.

   Se as tabelas do jogo forem mais antigas que o jogo, ele pergunta antes se deve
   descompactar elas de novo: clique em **Yes** (cerca de um minuto).

   Ele instala os módulos, monta o mundo e liga ele, tudo de uma vez. Leva de alguns segundos a
   alguns minutos.

**Você deve ver:** uma janela **Build finished** com uma marca em cada linha: **World built**,
**Leagues and clubs** (`2 leagues · 36 new clubs`), **Modules installed and switched on**,
**Switched on in sider.ini** e **Start the game to play it**. Em **Before you play**:
`Start a new Master League career: a career saved before keeps the old world.` Clique em **Done**.

Se ele disser **An Edit save from before this Build is in the game's save folder**: clique em
**Move the Edit save aside**. Um save Edit antigo esconde os nomes e elencos novos.

**Passo a passo em vez do botão grande** (o mesmo resultado):

1. **1. Check the plan**: como acima.
2. **2. Build the world**: monta ele. Se o mundo existe, ele pergunta
   `... exists. Build it again?`: **Yes**. O log termina com
   `Next: 3. Switch it on, then start the game.`
3. **3. Switch it on**: pergunta `Make _FL26MyWorld the live world in sider.ini?`: **Yes**. O log
   termina com `Start the game, then 4. check.`

**O que as linhas do log querem dizer:**

| Linha | Significado |
|---|---|
| `installing the modules ...`, `modules: ... copied, ... already there` | Os módulos do Mod Studio são colocados no lugar. |
| `world ...: N new leagues, changes to ... of the game's leagues and ... of its clubs` | O resumo da sua receita. |
| `<league>  reg ...  comp ...  division 1  18 clubs x2` | Uma liga: os ids dela no jogo, a divisão e o formato. |
| `European places: 1st Champions League qualifying, ...` | Para onde vão os clubes do topo dela. |
| `no European places: the new leagues send nobody to Europe` | Um aviso, não um erro: configure **Europe** numa primeira divisão se você quiser. |
| `building ...` | O mundo está sendo gravado. |
| `livecpk: _FL26MyWorld (... files), sider.ini loads it` | O mundo está ligado. |
| `error: ...` | O Build parou e nada mudou no jogo. Conserte o que ele diz (tabela no fim) e faça o Build de novo. |

As opções nos cartões (**Include the Conference League**, **Country cup draw**, **Make kits
for the new clubs** ...) são explicadas em [8.2](mod-studio-guide.md#82-montar-ligar-jogar). Os
padrões estão bons.

## Passo 13. Jogue: uma Master League NOVA, depois a conferência

1. Clique no botão verde **Play** no canto superior direito (ou **Game → Start the game**).
2. No jogo: **Master League** → **New game**. Não Continue: uma carreira salva antes mantém o
   mundo antigo.
3. Em **Select Team**, role a lista: as suas ligas estão nela, embaixo dos países delas.
4. Escolha um clube e jogue.

Depois deixe o Mod Studio conferir se o jogo pegou o mundo:

1. Feche o jogo (ou pelo menos inicie ele uma vez até o menu principal).
2. No Mod Studio: **Build** → **4. After a start: check**.

**Você deve ver:** uma linha por módulo dizendo quantas ligas ele leu do arquivo do mundo, e
no fim `the world works as built`. Uma linha `not loaded` ou `did NOT read the world file`, e
no fim `something is wrong -- see the lines above`, querem dizer que algo não funcionou: veja a
tabela no fim.

## Passo 14. Mudar algo depois

1. Feche o jogo.
2. Abra o Mod Studio. Ele abre a sua última receita sozinho (ou **File → Open recipe...**).
3. Mude o que quiser em **NewLife Database**, **Leagues**, **New clubs** ou **Players**.
4. **File → Save recipe**.
5. **Build** → **Build and install** → **Yes**.

**Você precisa de uma carreira nova?** Sim: comece uma Master League nova depois de cada mudança
que você monta. Uma carreira pega a própria cópia das ligas, clubes e elencos quando começa,
então uma carreira em que você já está mantém os antigos. E uma carreira salva com um mundo
precisa desse mesmo mundo para carregar, então mantenha o mundo ligado enquanto joga ela.

**Uma versão mais nova do NewLife.** Coloque as partes dela numa pasta nova,
**Open NewLife Database...** essa pasta, depois clique em **Update my leagues to this version**.
Cada liga mantém nome, divisão, formato, vagas europeias e copas; os clubes e elencos vêm da
versão nova (a caixa **Keep my clubs** mantém a sua própria formação de clubes). Faça o Build de
novo e comece uma carreira nova.
[Mais](mod-studio-guide.md#84-newlife-database-clubes-e-jogadores-reais).

**Tirar uma liga.** **Leagues** → **Ours** → clique nela → **Remove** → **Yes**. Os clubes dela
e as mudanças de jogadores deles vão junto.

## Passo 15. Compartilhar o que você fez

Há dois jeitos. Escolha um:

| | Pacote de liga (`.fl26pack`) | Mundo exportado (`.zip`) |
|---|---|---|
| O que ele guarda | As suas ligas como uma receita: clubes, nomes, escudos, logos, elencos, rostos, e se você quiser uniformes e placares. | O mundo exatamente como você montou. |
| A outra pessoa | Adiciona à própria receita e faz o Build, então funciona ao lado das ligas dela e de outros pacotes. | Instala e joga. Nada para montar, mas ele substitui qualquer outro mundo que ela tenha ligado. |
| Como ela instala | [Caminho C de Instalar um pacote pronto](install-a-pack.md#caminho-c-um-pacote-de-liga-fl26pack) | [Caminho A de Instalar um pacote pronto](install-a-pack.md#caminho-a-um-mundo-pronto-um-zip) |

### Um pacote de liga

1. Barra da esquerda: **League packages** → **Make a package...** (ou na barra de cima:
   **File → Make a league package...**).

**Você deve ver:** uma janela **Make a league package**.

2. Preencha **Name** (obrigatório), **Author**, **Version** (`1.0` para começar) e
   **Description**.
3. Em **Leagues**, marque as ligas que entram (**Select all** / **Select none**). Uma liga
   embaixo de outra liga tem que ir junto com ela.
4. **Also my changes to the game's own leagues, clubs and players** (só se você mudou alguma):
   marque para colocar essas mudanças também.
5. Em **What goes in**, vem tudo marcado: **Squads**, **Player faces and portraits**,
   **Crests and league logos**, **Managers**, **Kit colours**, **Kits**, **Scoreboards** e
   **Home stadiums**. Desmarque o que você não quer compartilhar. Uniformes somam uns 10 MB por
   liga e um placar uns 7 MB.
6. Clique em **Save the package...**. Abre uma janela de salvar **Save the package** com um nome
   como `<name>-1.0.fl26pack`. Escolha uma pasta que você vai achar de novo (Desktop,
   Documents ...) e clique em **Save**.

**Você deve ver:** `Saved <file>` com quantas ligas, clubes e rostos estão nele. Esse único
arquivo é o que você compartilha. Se passar de 10 MB, o Mod Studio avisa: o Discord não aceita,
então compartilhe pelo Google Drive, Dropbox, MEGA ou parecido, ou desmarque **Kits** e
**Scoreboards**, ou faça um pacote por liga.

Mais: [9. Pacotes de ligas](mod-studio-guide.md#9-pacotes-de-ligas-compartilhe-uma-liga-inteira).

### Um mundo inteiro (zip)

1. Faça o Build antes (Passo 12). O mundo tem que estar montado.
2. Barra da esquerda: **Build** → **Export the world...**.
3. Abre uma janela de salvar com o nome do mundo como nome do arquivo (`_FL26MyWorld.zip`), na
   sua pasta de usuário na primeira vez (depois disso, na pasta que você usou por último).
   Escolha uma pasta e clique em **Save**.

**Você deve ver:** depois de um momento, `Saved <file>` e quantos jogadores novos ganham um
rosto gerado. O zip guarda a pasta do mundo, o arquivo do mundo e um leia-me.

Quem instala precisa dos módulos do Mod Studio com o pacote de rostos (**Build → 0. Install
the modules**); sem eles todo jogador novo fica com a mesma cara. O leia-me no zip diz isso.

Mais: [9.1 Exportar o mundo](mod-studio-guide.md#91-exportar-o-mundo-um-mundo-pronto-para-outro-pc).

---

## Se algo der errado

As mensagens aparecem numa janela de erro, na linha verde ou vermelha embaixo do título de uma
página, ou no log do Build depois de `error:`. `<...>` representa um nome ou número.

| O que você vê | O que fazer |
|---|---|
| `no NewLife Database here: put the NewLife-....zip parts you downloaded in one folder (no need to unpack them) and open that folder` | Você escolheu a pasta errada, ou descompactou as partes. Abra a pasta que tem os próprios arquivos `NewLife-...zip`. |
| `the parts in this folder are of different versions (...): keep one version's parts only` | Duas versões do NewLife estão misturadas. Deixe na pasta só as partes de uma versão. |
| `<file> is not a NewLife part (...) -- download it again` | O download quebrou. Baixe essa parte de novo. |
| Uma liga cinza, `a league takes 10 to 24 clubs` | Adicione ou deixe clubes de fora (Passo 4) até ela ter de 10 a 24. |
| Uma liga cinza, `the game's own league: Bring the game's leagues to this season` | O jogo já tem ela. Use **Bring the game's leagues to this season...**. |
| **Add to the recipe** fica cinza | Nada que dá para adicionar está selecionado, ou a seleção passaria do limite de clubes novos (a linha embaixo). |
| `<club> would play in two leagues (<league> and <league>).` | Desmarque o clube numa delas. |
| `<league> has no country the game knows.` | Esta liga não pode ser adicionada. |
| `A league needs a name and a country.` / `Pick the country from the list.` | No **Edit league...**, preencha **Name**, e escolha o **Country** da lista em vez de digitar ele inteiro. |
| `There is already a league called <name>.` | Dê outro nome à liga. |
| `European places: position <n> -- the league has <m> clubs` | Uma linha em **Europe** aponta para depois do último clube. Mude ou tire ela. |
| `European places: position <n> is listed twice` | Duas linhas têm a mesma posição. Tire uma. |
| `European places: a cup winner's place, but the country has no cup` | Marque **National cup**, ou tire a linha **Cup winner**. |
| `Clubs, times and groups must be numbers.` | Em **splits in two**, digite os grupos como números, por exemplo `6/6`. |
| `A league playing February to December has no split, Apertura/Clausura, national cup or league cup yet.` | Ponha **Season** em **August to May**, ou tire a divisão em dois, o Apertura/Clausura ou as copas. |
| `This division plays February to December with the league above it, and a league playing February to December has no split or Apertura/Clausura yet.` | Dê a esta divisão **everyone plays everyone**. |
| `Clubs in no league are all new clubs: take the clubs of the game out first (Edit club).` | A liga tem clubes do jogo. Em **New clubs** selecione cada um e use **More ▾ → New club here**, depois configure **Clubs in no league** de novo. |
| `<league> is below this league; clubs in no league have none.` (ou `an exhibition league has none.`) | Outra liga tem esta como **Division**. Mude aquela liga primeiro. |
| `A league has 10 to 24 clubs.` (New clubs) | Insert club / Remove club deixaria a liga fora de 10 a 24. |
| `Open the NewLife Database on the NewLife page first.` | **NewLife club...** precisa da pasta do NewLife: abra ela em **NewLife Database** uma vez. |
| `Pick the club that takes its place.` / `Give the new club a name.` / `A club cannot take its own place.` | Em **Club of the game**, escolha um clube substituto, ou digite um nome para o novo. |
| `error: no game tables -- Settings > Unpack the game's tables` | **Settings → Unpack the game's tables**. |
| `error: no game folder -- Game > Choose the game folder` | **Game → Choose the game folder...**. |
| `error: the world name must start with _FL26` | **Leagues → More ▾ → World name and recipe...**: um nome começando com `_FL26`. |
| `error: nothing to build: add a league or change one of the game's ...` | A receita está vazia. Adicione ligas (Passos 3 a 5). |
| `error: <league>, club <n>: <club> plays in <...> -- pick the club that takes its place there` | Faça [Clubes que o jogo já tem](#clubes-que-o-jogo-já-tem) para esse clube. |
| `error: <league>, club <n>: the new club taking <club>'s place needs a name` | A mesma janela: digite um nome ao lado de **Its place goes to a new club, named:**. |
| `error: <club> is in <league> and in <league>: a club plays in one league` | Tire o clube de uma liga (**New club here** em New clubs, ou desmarque ele antes de adicionar). |
| `error: <n> new clubs, but the game has room for <m> more (a full squad each)` | Clubes novos demais. Tire uma liga, ou clubes. |
| `error: <n> leagues, but the game has room for <m> ...` | Ligas novas demais. Tire algumas. |
| `error: <league> has <n> leagues below it; the game follows one link` / `... are all under ...` | Só uma liga pode ficar embaixo de uma liga. Mude a **Division** das outras. |
| `error: <league>: division 8 -- the rank field stops at 7` | Um país vai até a 7ª divisão. |
| `error: at most 2 split leagues for now ...` / `... only one league of a country can be split or Apertura/Clausura` | Dê às outras ligas **everyone plays everyone**. |
| `The game's tables Mod Studio uses are older than the game: ... Unpack them again first?` | Clique em **Yes**. |
| `<world> is not built yet: 2. Build the world first.` (Export the world) | Faça o Build primeiro, depois exporte. |
| `Give the package a name.` / `Tick at least one league.` / `The recipe has no leagues yet.` | Em **Make a league package**, preencha **Name** e marque uma liga; a receita precisa ter ligas antes. |
| Nenhuma liga nova no Select Team | Comece uma Master League **nova**. Depois **Build → 4. After a start: check**. |
| `sider.log is older than the world switched on -- start the game to the main menu, then check again` | Inicie o jogo até o menu principal, feche, confira de novo. |
| `<module> not loaded` / `did NOT read the world file` | **Build → 0. Install the modules**, depois **3. Switch it on**, inicie o jogo de novo e confira de novo. Ainda errado: pergunte no Discord. |
| Os nomes dos clubes são os do jogo, não os seus | Um save Edit antigo esconde eles: **Move the Edit save aside** na janela **Build finished**, ou tire o `EDIT00000000` da pasta de saves do jogo. |
| Todos os jogadores novos têm o mesmo rosto | **Build → 0. Install the modules** (traz o pacote de rostos), depois inicie o jogo de novo. |

**Pedir ajuda:** no [Discord](https://discord.gg/StQqtk3G3M), mande uma captura de tela do
que você vê, o texto do log do Build, e o seu `sider.log` (**Game → Open sider.log**).
