# Criar suas próprias ligas e pacotes: cada clique, em ordem

> [English](../en/make-your-own-leagues.md) · [hrvatski](../hr/make-your-own-leagues.md) · [español](../es/make-your-own-leagues.md) · **português** · [français](../fr/make-your-own-leagues.md)

> O outro guia passo a passo: [Instalar um pacote pronto](install-a-pack.md)
> · cada página e opção explicada: [mod-studio-guide.md](mod-studio-guide.md)
> · perguntas: [faq.md](../../docs/faq.md) (em inglês) · ajuda: [Discord](https://discord.gg/StQqtk3G3M)

Esta página te leva do zero até as suas próprias ligas no jogo: ligas reais com clubes e
jogadores reais do **NewLife Database**, configuradas do jeito que você quer, construídas,
jogadas e compartilhadas com outras pessoas. Ela diz o que clicar, o nome exato de cada botão e
campo como o Mod Studio mostra, e o que você deve ver depois de cada passo. Faça os passos na
ordem. Se você vir algo diferente do que um passo diz, pare ali e olhe em
[Se algo der errado](#se-algo-der-errado).

O Mod Studio começa em inglês. Este guia usa os nomes que ele mostra em português: barra de cima
→ **Idioma (Language)** (em inglês o menu se chama *Language*) → Português, depois abra o Mod
Studio de novo.

Três palavras que você vai ver o tempo todo:

- **Seu mundo**: a sua lista de ligas e tudo o que você configurou para elas. Você muda ele nas
  abas de **2. Meu mundo**, e ele se salva sozinho um instante depois de cada mudança. Ele é só um
  plano: nada chega ao jogo antes de você **construir**.
- **Pasta do mundo**: o que a construção faz do seu mundo, uma pasta cujo nome começa com `_FL26`
  (`_FL26MyWorld`, se você não mudar). O jogo lê ela enquanto ela está no jogo (a caixa
  **MUNDO ATIVO** no topo da janela mostra o nome dela).
- **Construir** (Build): o botão que transforma o seu mundo nessa pasta e coloca ela no jogo.

**Conteúdo**

- [Antes de começar: a configuração de uma vez só](#antes-de-começar-a-configuração-de-uma-vez-só)
- [Passo 1. Pegue o NewLife Database](#passo-1-pegue-o-newlife-database)
- [Passo 2. Abra ele na página NewLife Database](#passo-2-abra-ele-na-página-newlife-database)
- [Passo 3. Escolha suas ligas](#passo-3-escolha-suas-ligas)
- [Passo 4. Escolha os clubes de uma liga](#passo-4-escolha-os-clubes-de-uma-liga)
- [Passo 5. Adicione ao seu mundo](#passo-5-adicione-ao-seu-mundo)
- [Passo 6. A página Campeonatos: cada configuração de uma liga](#passo-6-a-página-campeonatos-cada-configuração-de-uma-liga)
- [Passo 7. Exemplo: um país com duas divisões](#passo-7-exemplo-um-país-com-duas-divisões)
- [Passo 8. A aba Clubes: nomes, escudos, uniformes, clubes do jogo](#passo-8-a-aba-clubes-nomes-escudos-uniformes-clubes-do-jogo)
- [Passo 9. A página Jogadores](#passo-9-a-página-jogadores)
- [Passo 10. Limites que impedem a construção](#passo-10-limites-que-impedem-a-construção)
- [Passo 11. O seu mundo se salva sozinho](#passo-11-o-seu-mundo-se-salva-sozinho)
- [Passo 12. Construir](#passo-12-construir)
- [Passo 13. Jogue: uma Master League NOVA, depois a conferência](#passo-13-jogue-uma-master-league-nova-depois-a-conferência)
- [Passo 14. Mudar algo depois](#passo-14-mudar-algo-depois)
- [Passo 15. Compartilhar o que você fez](#passo-15-compartilhar-o-que-você-fez)
- [Se algo der errado](#se-algo-der-errado)

---

## Antes de começar: a configuração de uma vez só

Faça antes os passos 1 a 3 do outro guia, uma vez:
[feche o jogo](install-a-pack.md#passo-1-feche-o-jogo),
[baixe o Mod Studio](install-a-pack.md#passo-2-baixe-o-mod-studio) e
[diga onde está o seu jogo](install-a-pack.md#passo-3-diga-onde-está-o-seu-jogo).
Depois volte para cá. O Mod Studio extrai as tabelas do jogo sozinho, e **Construir e instalar**
(Passo 12) coloca os módulos dele.

Deixe o jogo fechado o tempo todo enquanto você trabalha no Mod Studio.

Se um mundo pronto de um zip (um Modpack) está no jogo agora, tudo bem: você pode construir o seu
próprio mundo ao lado dele. A construção pergunta antes, e tira o mundo pronto do jogo enquanto o
seu estiver nele. O cartão dele em **2. Meu mundo** continua lá, e **Ativar** coloca ele de volta.

---

## Passo 1. Pegue o NewLife Database

O NewLife Database é um download separado com clubes e jogadores reais: nomes, datas de
nascimento, posições, overalls na escala do jogo, e as cores dos clubes. Ele não está no GitHub.

1. Abra o nosso [Discord](https://discord.gg/StQqtk3G3M) e vá para o canal **#newlife**.
2. Baixe as partes que você quer. Há uma parte por continente (um continente grande vem em mais
   de uma parte), mais *Free agents*. Cada parte é um arquivo `.zip` chamado `NewLife-...zip`.
3. Crie uma pasta para elas, por exemplo `Documents\NewLife`, e coloque **todas** as partes
   nessa mesma pasta.
4. **Não descompacte.** O Mod Studio lê os zips como estão. (O visualizador de zip do próprio
   Windows não consegue abrir eles mesmo; isso é normal.)

Quando sair uma versão mais nova do NewLife, coloque as partes dela numa pasta **nova**. Nunca
misture duas versões numa pasta.

## Passo 2. Abra ele na página NewLife Database

1. Clique em **2. Meu mundo**, depois em **NewLife Database** (o botão à direita, ao lado das abas).
2. Clique em **Abrir NewLife Database...** no topo.
3. Escolha a pasta do Passo 1 (a pasta, não um zip dentro dela) e confirme.
4. Espere alguns segundos enquanto ele lê.

(Ou: **2. Meu mundo → + Adicionar...**, **Escolher uma pasta...**, escolha a pasta, depois
**Adicionar**.)

**Você deve ver:** acima da lista, a versão do NewLife e a pasta, e embaixo delas `Partes:` com
as partes que ele encontrou. Embaixo disso, uma lista longa de ligas.

O Mod Studio lembra da pasta: na próxima vez a página abre ela sozinha.

**Busca.** A caixa acima da lista, *Buscar campeonatos ou países*, deixa só as ligas cujo nome
ou país tem o que você digitar. Digite `brazil` ou `liga`, por exemplo. Esvazie a caixa para ver
todas de novo.

**As colunas.** Clique no cabeçalho de uma coluna para ordenar por ela, clique de novo para
inverter a ordem.

| Coluna | O que ela diz |
|---|---|
| **Campeonato** | O nome da liga. Um `*` depois dele quer dizer que você mudou os clubes dela (Passo 4). |
| **País** | Onde ela fica no jogo. |
| **Clubes** | Quantos clubes ela vai ter, do jeito que está configurada agora. |
| **No jogo** | Quantos clubes dela o jogo já tem (eles mantêm os próprios nomes, escudos, uniformes e jogadores). |
| **Jogadores** | Quantos jogadores os clubes dela têm no NewLife. |
| **Nível** | O quanto a liga é forte. Mais alto é mais forte. |
| (última coluna) | Por que uma liga cinza não pode ser adicionada. Vazia para uma liga que você pode adicionar. |

**Por que algumas ligas estão cinza.** Uma liga cinza não pode ser adicionada, e a última coluna
diz por quê:

- `um campeonato tem de 10 a 24 clubes`: uma liga no jogo tem de 10 a 24 clubes, os novos e os
  do jogo juntos. Esta tem menos ou mais. Você ainda pode corrigir isso no Passo 4 (adicionar ou
  deixar clubes de fora) até ela caber.
- `campeonato do próprio jogo: Levar os campeonatos do jogo para esta temporada`: o jogo já tem
  esta liga (a Premier League, o Championship ...). Ela não é adicionada uma segunda vez.
  **Mais ▾ → Levar os campeonatos do jogo para esta temporada...** no topo dá às ligas do próprio
  jogo os clubes e elencos desta temporada do NewLife; veja
  [8.4 no guia completo](mod-studio-guide.md#84-newlife-database-clubes-e-jogadores-reais).

Se a página disser que o Mod Studio não tem as tabelas do jogo e oferecer abrir as
Configurações: clique em **Sim**, depois em **Extrair as tabelas do jogo** ali.

## Passo 3. Escolha suas ligas

1. Clique numa liga da lista para selecionar ela. A linha dela fica destacada.
2. Para mais de uma: segure **Ctrl** e clique em cada uma. (Ou clique na primeira, segure
   **Shift** e clique na última para pegar tudo o que está entre elas.)

**Você deve ver:** embaixo da página, uma linha como
`Clubes novos no seu mundo: 0 dos 1544 que o jogo aceita.  Selecionados: mais 18.`

- O **primeiro** número é quantos clubes novos o seu mundo já tem.
- O **segundo** é quantos clubes novos cabem no jogo ao todo (cerca de 1.500). O Mod Studio
  calcula isso a partir das tabelas do seu jogo, então pode ser um pouco diferente em outra versão
  do jogo.
- **Selecionados** é quantos clubes novos as ligas que você escolheu adicionariam.

Se o seu mundo e a seleção juntos passam do que o jogo aceita, **Adicionar ao seu mundo** fica
cinza: escolha menos ligas.

## Passo 4. Escolha os clubes de uma liga

Este passo é opcional. Pule ele para pegar uma liga exatamente como o NewLife tem.

Selecione **uma** liga (só uma). A lista à direita mostra os clubes dela: **Clube** e
**Jogadores** (quantos jogadores o NewLife dá a ele). Um clube que o jogo já tem aparece cinza,
com `no jogo` no lugar de um número.

- **Deixar um clube de fora:** clique na caixinha dele para desmarcar.
- **Trazer um clube de outra liga** (a primeira divisão desta temporada é a da temporada passada
  com dois clubes que subiram, por exemplo): clique em **Adicionar um clube de outro
  campeonato...** embaixo da lista.
  1. Abre uma janela com todos os clubes das partes do NewLife que você abriu, cada um com a liga
     dele entre parênteses.
  2. Digite na caixa de busca para achar um clube ou uma liga.
  3. Marque um ou mais clubes. A linha embaixo da lista diz quantos você escolheu.
  4. Clique em **OK**.

  **Você deve ver:** o clube no fim da lista, com `de: <a liga dele>` ao lado.

**Você deve ver:** a linha da liga na lista agora tem um `*`, e o número em **Clubes** mudou. Uma
liga cinza que agora tem de 10 a 24 clubes volta ao normal.

Um clube só pode jogar numa liga. Se você adicionar ele a duas, o Mod Studio te para no Passo 5.

## Passo 5. Adicione ao seu mundo

Com a sua liga ou ligas selecionadas, clique em **Adicionar ao seu mundo** no topo.

**Você deve ver:** uma linha verde embaixo do título da página. O que cada linha quer dizer:

| Linha verde | O que quer dizer |
|---|---|
| `Adicionado: <ligas>. Altere-os em Campeonatos, Clubes e Jogadores, depois construa.` | As ligas estão no seu mundo, cada uma como primeira divisão do seu país, todos contra todos em turno e returno. Nada está no jogo ainda. |
| `<clubes> também jogam uma competição do jogo: em Clubes escolha cada um e use Clube do jogo para escolher o clube que fica com o lugar dele lá.` | Esses clubes da sua liga nova são clubes que o jogo já tem, e eles também jogam em algum lugar do jogo (uma liga, uma copa, a Europa League ...). Um clube só joga numa liga, então o lugar antigo dele precisa de outro clube. Você escolhe esse clube no [Passo 8](#clubes-que-o-jogo-já-tem). Até fazer isso, a construção para com um erro que diz o nome do clube. |
| `<n> jogadores ficam no clube deles no jogo (o clube ficaria com poucos jogadores).` | Jogadores que o jogo já tem normalmente vão para o clube do NewLife. Estes ficam, para que o clube antigo mantenha pelo menos 18 jogadores. Nada a fazer. |
| `<n> jogadores não são adicionados: outro campeonato já tem eles.` | Uma liga que você adicionou antes já pegou esses jogadores. Nada a fazer. |

Se uma janela de erro disser `<clube> jogaria em dois campeonatos (<liga> e <liga>).`, desmarque
esse clube numa das duas ligas (Passo 4) e tente de novo.

Quer ligas de outros continentes? Selecione elas também e clique em **Adicionar ao seu mundo** de
novo. Cada clique adiciona; nunca tira o que já está lá.

---

## Passo 6. A página Campeonatos: cada configuração de uma liga

1. **2. Meu mundo**, aba **Campeonatos**.
2. Acima da lista, clique em **Nossos**: a lista mostra só as ligas do seu mundo. (**Todos**
   mostra todas as ligas, as do jogo também; **Alterado**, as ligas do jogo que você mudou.) As
   ligas estão agrupadas por continente.
3. Clique na sua liga.

**Você deve ver:** à direita, `NOSSO`, o nome e o logo da liga, e as linhas **País**, **Clubes**,
**Formato**, **Divisão**, **Acesso / rebaix.**, **Europa** e **ID do campeonato**
(`ainda não construído` até a primeira construção), depois os escudos dos clubes dela. Embaixo
deles os botões **Editar campeonato...**, **Adicionar divisão inferior**, **Clubes e nomes**,
**Jogadores** e **Remover**.

A lista vai por país, as divisões de cada país de cima para baixo (Bundesliga, 2. Bundesliga,
3. Liga). Você pode arrastar uma liga para cima ou para baixo na lista para colocar as ligas de um
continente em ordem.

4. Clique em **Editar campeonato...**.

**Você deve ver:** uma janela chamada **Campeonato** com os campos abaixo, de cima para baixo. Um
campo cinza não pode ser usado com o que você configurou acima dele (por exemplo uma copa numa
segunda divisão). O **?** ao lado de **OK** explica a janela em poucas palavras. Nada é
obrigatório: os valores padrão funcionam, e **Cancelar** não muda nada.

| Campo | O que é, e o que fazer |
|---|---|
| **Nome** | O nome da liga no jogo. Duas ligas não podem ter o mesmo nome. Deixe ele abaixo de uns 38 caracteres: um nome mais longo aparece como uma linha vazia na lista de ligas do Kick Off. |
| **País** | Digite algumas letras e escolha na lista (`korea` acha as duas Coreias). Ele dá a bandeira e onde a liga aparece no jogo. |
| **Clubes** | De 10 a 24. Para uma liga do NewLife, deixe como está: um número menor tira os últimos clubes, um maior adiciona clubes inventados no fim. |
| **Clubes sem campeonato** | Deixe em `(não -- um campeonato)`. As outras opções (*Other European teams* ...) são para um clube, ou alguns, sem liga em volta; eles vão para os grupos "Other ..." do jogo, e a maioria dos campos abaixo fica cinza. [Mais](mod-studio-guide.md#8-league-builder-novas-ligas-clubes-e-jogadores). |
| **Formato** | Escolha um: **todos contra todos, turnos:** e o número (1 a 4; 2 é turno e returno); **divide-se em dois (estilo escocês)**, com `primeiro` *n* `x, depois grupos` *6/6* *n* `x` (os grupos têm que somar o número de clubes); ou **Apertura e Clausura, depois playoffs com:** *8 clubes*, *4 clubes* ou *sem playoffs* (dois torneios curtos por temporada, no máximo 18 clubes). A divisão em dois e Apertura e Clausura são **experimentais**: funcionam, mas ainda têm mais bugs do que todos contra todos, o formato totalmente testado. A janela diz isso embaixo dos formatos. Para um primeiro mundo, escolha todos contra todos. |
| **Divisão** | `(primeira divisão)` = a melhor liga do país. Para uma segunda divisão, escolha a liga um nível acima: as suas ligas novas estão no topo da lista, depois as ligas do jogo com um número entre parênteses. `= divisão 2` ao lado mostra o nível. Uma liga que já tem uma liga embaixo dela fica cinza (`-- abaixo dele: ...`): uma liga pode ter uma liga abaixo dela. Veja o [Passo 7](#passo-7-exemplo-um-país-com-duas-divisões). |
| **Só amistosos -- fora da Master League** | Deixe desligado. Ligado: a liga é só para o Kick Off e amistosos (lendas, uma temporada histórica); ela nunca joga uma temporada da Master League, e a divisão, as copas e a Europa ficam cinza. Não comece uma carreira com um dos clubes dela. |
| **Temporada** | Só na primeira divisão: **agosto a maio** (como na Europa) ou **fevereiro a dezembro** (como no Brasil ou no Japão). Uma divisão abaixo segue a liga de cima. Fevereiro a dezembro ainda não pode ter divisão em dois, Apertura/Clausura nem copa da liga; uma copa nacional pode. |
| **Acesso / rebaix.** | De 1 a 6: quantos clubes trocam de lugar com a liga de cima no fim da temporada. Só faz sentido para uma divisão abaixo de outra. |
| **Logo** | **Escolher imagem...**: um PNG ou JPG para a liga (um PNG com fundo transparente fica melhor). **Limpar** tira ele. Vazio: `(feito automaticamente)`, um logo é desenhado na construção. |
| **Bandeira do país** | A sua própria imagem da bandeira do país. Vazio: `(a do jogo)`. Deixe vazio, a não ser que o jogo não tenha uma bandeira boa. |
| **Copa** | Só na primeira divisão. Marque **Copa nacional** para dar ao país uma copa eliminatória (esta liga e a divisão abaixo dela). A caixa ao lado é o nome da copa; vazia = o nome da liga + Cup. |
| **Supercopa (campeão contra campeão da copa)** | Um jogo antes da temporada. Precisa de **Copa nacional** marcada. |
| **Copa da liga** | Só na primeira divisão. Uma segunda copa eliminatória, como a Carabao Cup da Inglaterra: esta liga e a de baixo, até 44 clubes. A caixa é o nome dela; vazia = o nome da liga + League Cup. |
| **Logos das copas** | Uma imagem para cada uma: a **Copa**, a **Supercopa**, a **Copa da liga** e os **Playoffs**. Vazio: um emblema com as iniciais da copa. |
| **Formação** | Como os clubes da liga entram em campo. Escolha uma da lista, ou deixe vazio e a construção escolhe a que melhor combina com o elenco de cada clube. Um clube pode ter a sua própria (Passo 8). |
| **Europa** | Só na primeira divisão: qual posição da tabela vai para qual competição continental. O botão que começa com **Primeira divisão:** preenche as vagas de costume do continente do país (para a Europa: `Primeira divisão: 1.º fase preliminar da UCL, 2.º UEL, 3.º UECL`). **Adicionar vaga** adiciona uma linha: escolha a **Posição no campeonato** (abaixo de 1 ela vira **Campeão da copa**) e a **Competição**. O **✕** numa linha tira ela, **Limpar** tira todas. Deixe vazio para uma segunda divisão. |

5. Clique em **OK**.

**Você deve ver:** a janela fecha e as linhas à direita mostram o que você configurou.

Uma liga do NewLife entra sem vagas europeias. Se você quer os clubes dela na Champions League e
nas outras, configure **Europa** agora; senão **1. Conferir o plano** te lembra com
`no European places: the new leagues send nobody to Europe`.

O que cada formato, copa e vaga europeia quer dizer em detalhe (datas, fases preliminares,
tamanho das copas):
[seção 8 do guia completo](mod-studio-guide.md#8-league-builder-novas-ligas-clubes-e-jogadores)
e [8.2](mod-studio-guide.md#82-construir-ativar-jogar).

**Mais ▾** (no topo da aba Campeonatos) tem as ferramentas para o mundo todo: **Torneios de
pré-temporada**, **Taças dos nossos países** (as copas de todas as suas ligas numa tabela),
**Copas dos países do jogo**, **Vagas continentais dos campeonatos do jogo**, **Clubes europeus
da primeira temporada**, **Ranking da UEFA**, **Vagas sul-americanas**, **Nomes das
competições** (nomes e logos novos para copas e competições continentais), **IDs das
competições**, **Ordem dos campeonatos**, **Temporadas dos campeonatos do jogo** e **Nome do
mundo e arquivo...** (o nome da pasta do mundo; tem que começar com `_FL26`). Você não precisa de
nenhuma delas para um primeiro mundo. As janelas das copas também estão em **Copas ▾**, ao lado
das abas.

**Uma liga sem clubes do NewLife.** **Adicionar campeonato** no topo da aba Campeonatos abre a
mesma janela **Campeonato** para uma liga feita do zero: dê a ela um **Nome**, um **País** e um
número de **Clubes**, e a construção cria os clubes com elencos completos e um técnico. Você dá
nome a eles na aba **Clubes** (Passo 8), onde **Clube NewLife...** também pode colocar clubes
reais nela.

## Passo 7. Exemplo: um país com duas divisões

Digamos que as suas partes do NewLife têm a primeira e a segunda divisão de um país, aqui
chamadas *First League* e *Second League*. Você quer acesso e rebaixamento entre elas.

1. **NewLife Database**: selecione *First League* e clique em **Adicionar ao seu mundo**. (A de
   cima primeiro.)
2. Selecione *Second League* e clique em **Adicionar ao seu mundo**.

   **Você deve ver:** a linha verde `Adicionado:` cada vez. As duas agora são primeiras divisões
   do mesmo país, o que ainda não é o que você quer.

3. **Campeonatos** → **Nossos** → clique em *Second League* → **Editar campeonato...**.
4. **Divisão**: abra a lista e escolha *First League* (as suas ligas estão no topo).

   **Você deve ver:** `= divisão 2` ao lado. **Copa**, **Copa da liga**, **Temporada** e o botão
   **Primeira divisão** ficam cinza: eles são da primeira divisão.

5. **Acesso / rebaix.**: quantos clubes sobem e descem entre as duas, por exemplo `3`.
6. **Europa**: se tiver linhas, clique em **Limpar**. Uma segunda divisão não manda ninguém para
   a Europa.
7. Clique em **OK**.

   **Você deve ver:** à direita, **Divisão** `2  (abaixo de First League)` e **Acesso / rebaix.**
   `3 com First League acima`. Clique em *First League*: o **Acesso / rebaix.** dela diz
   `3 com Second League abaixo`.

8. Clique em *First League* → **Editar campeonato...** e configure o que é da primeira divisão:
   **Europa** (o botão **Primeira divisão**), e se quiser **Copa nacional**, **Supercopa** e
   **Copa da liga**. Clique em **OK**.

Uma terceira divisão funciona do mesmo jeito: a **Divisão** dela é *Second League*. O jogo vai até
a 7.ª divisão.

**Uma liga abaixo de uma liga.** Duas ligas não podem ficar abaixo da mesma liga (três grupos
regionais abaixo de uma segunda divisão, por exemplo). A segunda aparece cinza na lista de
**Divisão**.

**Abaixo de uma das ligas do jogo.** A sua liga nova também pode ficar abaixo de uma liga que o
jogo tem: escolha a liga do jogo em **Divisão** (as que têm um número entre parênteses). Ela então
joga acesso e rebaixamento com essa liga.

**Sem NewLife.** Em **Campeonatos**, clique na sua liga de cima, depois em **Adicionar divisão
inferior**: abre uma janela **Campeonato** com o país, os clubes, o formato e a divisão já
preenchidos. Dê um **Nome** e clique em **OK**.

---

## Passo 8. A aba Clubes: nomes, escudos, uniformes, clubes do jogo

1. **2. Meu mundo**, aba **Clubes** (ou **Clubes e nomes** na aba Campeonatos).
2. No topo, **Campeonato**: escolha uma das suas ligas.

**Você deve ver:** os clubes dela com as colunas **#**, **Nome**, **Sigla** e **Jogadores
alterados**; deixe o mouse sobre um nome para ver o **ID do clube** dele (`no Build` até a
primeira construção) e o arquivo do escudo. Os clubes do NewLife já têm nomes, siglas e escudos.
Um clube sem nome mostra `<liga> 01`, `<liga> 02` ... em cinza. Acima da lista: **Editar clube** e
**Mais ▾**.

### Nome, escudo, uniformes, técnico

1. Dê um clique duplo num clube (ou selecione ele e clique em **Editar clube**).

**Você deve ver:** uma janela chamada **Clube** com:

| Campo | O que fazer |
|---|---|
| **Nome** | O nome do clube. Letras com acentos (Željezničar) estão ok. |
| **Sigla** | Três letras ou números. Vazio = feita a partir do nome. Č, Ž, Đ ... viram C, Z, D, como no jogo. |
| **Escudo** | **Escolher imagem...**: um PNG ou JPG. **Limpar** tira ele. Um clube sem escudo ganha um emblema numerado. |
| **Estádio do mandante** | Só quando o Stadium Server está instalado: **Escolher estádio...** do seu pack de estádios, ou **Do jogo**. |
| **Técnico** | O nome do técnico. Vazio: um nome inventado a partir de jogadores do país do clube. |
| **Foto do técnico** | Um PNG ou JPG; o jogo mostra ela no modo Edit e na Master League. |
| **Formação** | `Como o campeonato (...)` mantém a formação da liga; ou escolha uma para este clube. |
| **Cores do uniforme titular**, **Cores do uniforme reserva** | Clique nos dois quadrados de cor (camisa, segunda cor) para escolher as cores; **Nenhuma** = a construção escolhe um uniforme sozinha. A construção dá ao clube o uniforme do jogo mais próximo dessas cores. |

2. Clique em **OK**.

**Você deve ver:** o nome e o escudo novos na lista.

**Uniformes.** Um clube novo pega emprestado o uniforme de um clube do jogo nas cores dele. Duas
opções na aba **Construção**, em **Opções do mundo**, mudam isso: **Uniformes nas cores dos
clubes** (ligada por padrão, precisa do Kit Server instalado: cada clube novo ganha uniformes
titular, reserva, terceiro e de goleiro feitos nas cores dele, com o escudo dele) e **Uniformes
simples para o modo Edição** (cada clube novo usa um uniforme simples que você pode mudar no modo
Edit do jogo).
[Mais no guia completo](mod-studio-guide.md#8-league-builder-novas-ligas-clubes-e-jogadores).

**Capitão e bolas paradas.** Você não precisa escolher: a construção dá a cada clube um capitão e
jogadores que batem os pênaltis, as faltas e os escanteios.

**Muitos clubes de uma vez.** **Mais ▾** tem **Colar nomes...** e **Carregar nomes de um
arquivo...** (um nome por linha, em ordem) e **Importar escudos...** (uma pasta de imagens,
ligadas aos clubes pelo nome do arquivo). Ele também tem **Jogadores**, **Clube do jogo...**,
**Clube NewLife...**, **Clube novo aqui**, **Inserir clube**, **Remover clube** e **Mover para
outro campeonato...**.

### Clubes que o jogo já tem

Uma liga do NewLife pode incluir clubes que o jogo já tem. Eles aparecem na lista com o nome do
jogo (o mouse sobre ele mostra o **ID do clube**). Se a linha verde do Passo 5 disse que eles
*também jogam uma competição do jogo*, faça isto para **cada** um deles:

1. Clique no clube na lista.
2. Clique em **Mais ▾ → Clube do jogo...**.

**Você deve ver:** uma janela chamada **Clube do jogo**, com o clube selecionado e embaixo da
lista uma linha como `<clube> joga em <competições>. Cada uma dessas competições mantém o número
de clubes: escolha quem fica com o lugar dele lá.`

3. Escolha quem fica com o lugar antigo dele:
   - **O lugar dele vai para um clube do jogo que não joga nada:** e escolha um clube na lista
     embaixo; ou
   - **O lugar dele vai para um clube novo, chamado:** e digite um nome. A construção cria esse
     clube.
4. Se o clube joga uma competição continental (Champions League, Libertadores ...), também há
   **Mantém suas vagas em competições continentais**. Marcado, ele continua jogando essa
   competição e ninguém precisa ficar com o lugar dele lá.
5. Clique em **OK**.

O mesmo item do menu coloca qualquer clube do jogo num lugar da sua liga: selecione o lugar,
**Mais ▾ → Clube do jogo...**, busque pelo nome, sigla ou ID do clube (**Só clubes sem
campeonato** encurta a lista). **Clube novo aqui** (em **Mais ▾**) devolve o lugar a um clube
novo; ele fica cinza a não ser que um clube do jogo esteja no lugar.

**Clube NewLife...** (em **Mais ▾**) coloca clubes do NewLife, com os elencos deles, no lugar
selecionado e nos lugares depois dele: marque um ou mais na janela que abre, depois **OK**. É
assim que uma liga que você fez à mão ganha clubes reais.

## Passo 9. A página Jogadores

Os clubes do NewLife vêm com elencos completos, então você não precisa mexer nesta página. Ela
está aí se você quiser mudar um elenco.

1. **2. Meu mundo**, aba **Jogadores** (ou selecione um clube na aba **Clubes** e clique em
   **Mais ▾ → Jogadores**).
2. No topo, escolha o **Campeonato** e o **Clube**. (Ou digite em *Procurar um clube...*.)

**Você deve ver:** o elenco com as colunas **Ordem**, **N.º**, **Nome**, **Pos.**, **Idade**,
**Overall**, **Pé**, **Alterado** e **ID do jogador**, e os onze titulares num campo embaixo.
Clique num jogador: o lado direito mostra ele, nas abas **O básico**, **Posições**,
**Habilidades** e **Habilidades especiais**.

- Mude um nome, número, posição, overall ou habilidade à direita. A mudança fica guardada na
  hora.
- **Subir na ordem** / **Descer na ordem**: a ordem do elenco. Os onze primeiros começam o jogo.
  Ou arraste um jogador para um lugar no campo. **Melhor time** coloca o jogador mais forte em
  cada lugar.
- **Contratar jogadores...** traz jogadores de outros clubes; **Transferir para...** manda o
  jogador selecionado para outro clube.
- **Desfazer as alterações deste jogador** e **Desfazer todas as alterações deste clube**
  voltam atrás.

Tudo nesta página está em [Jogadores no guia completo](mod-studio-guide.md#jogadores).

---

## Passo 10. Limites que impedem a construção

| Limite | Onde você vê |
|---|---|
| Clubes novos ao todo (cerca de 1.500): o número na linha `Clubes novos no seu mundo: X dos Y que o jogo aceita.` | Página NewLife Database: **Adicionar ao seu mundo** fica cinza. Construção: `error: <n> new clubs, but the game has room for <m> more (a full squad each)`. |
| De 10 a 24 clubes numa liga | NewLife Database: liga cinza, `um campeonato tem de 10 a 24 clubes`. Aba Clubes: `Um campeonato tem de 10 a 24 clubes.` |
| Ligas novas por mundo: sem número fixo. Cada liga e cada copa ocupa uma das 255 competições do jogo; **2. Meu mundo** mostra quantas estão em uso (**Competições**). O nosso mundo de teste joga 86 ligas novas. | Construção: `error: <n> leagues, but the game has room for <m> ...` |
| Uma liga abaixo de uma liga | Lista **Divisão**: cinza. Construção: `... are all under ...; the game follows one link down from a league ...` |
| Divisões até a 7.ª | Construção: `error: <league>: division 8 -- the rank field stops at 7`. |
| 2 ligas divididas em dois por mundo; uma divisão em dois ou Apertura/Clausura por país | Construção: `error: at most 2 split leagues for now ...`, `... only one league of a country can be split or Apertura/Clausura`. |
| Um clube só numa liga | Construção: `error: <club> is in <league> and in <league>: a club plays in one league`. |
| Um clube do jogo que joga em algum lugar precisa de um substituto | Construção: `error: <league>, club <n>: <club> plays in <...> -- pick the club that takes its place there`. Faça [Clubes que o jogo já tem](#clubes-que-o-jogo-já-tem). |

Todos os números: [8.3 Limites](mod-studio-guide.md#83-limites).

## Passo 11. O seu mundo se salva sozinho

Não tem nada para salvar à mão: o Mod Studio salva o seu mundo um instante depois de cada
mudança.

**Você deve ver:** embaixo da janela, **Seu mundo está salvo**.

**Arquivo → Salvar seu mundo como...** salva uma cópia com outro nome, numa pasta que você
escolhe (por exemplo `Documents\FL26 Mod Studio`): esse arquivo é um que você consegue achar e
copiar. **Arquivo → Abrir um mundo...** abre de novo um mundo salvo. **Arquivo → Mundo novo**
começa um vazio.

O Mod Studio abre o seu mundo de novo quando inicia, então o que você fez nunca se perde.

## Passo 12. Construir

1. **2. Meu mundo**, aba **Construção** (a primeira aba).

**Você deve ver:** um aviso de que a construção é para modders, depois o botão grande **Construir
e instalar** e duas partes que abrem embaixo dele: **Opções do mundo: copas europeias, copas
nacionais, uniformes e rostos dos clubes novos** (dois cartões, **Copas europeias** e **Clubes
novos**, com opções) e **Passo a passo, e Exportar o mundo** (a linha **0. Instalar os módulos**,
**1. Conferir o plano**, **2. Construir o mundo**, **3. Ativar**, **4. Depois de iniciar:
conferir** e **Exportar o mundo...**). Depois uma linha como
`Mundo _FL26MyWorld: ainda não construído · módulos do Mod Studio: instalados`, e uma caixa para o
log embaixo. Enquanto o mundo é construído, a linha no topo de **2. Meu mundo** e a barra de baixo
mostram o tempo até agora e o passo em que ele está (`Construindo... 3:12 · squads: filling
them`).

2. Abra **Passo a passo, e Exportar o mundo** e clique primeiro em **1. Conferir o plano**. Ele
   não muda nada; só lê o seu mundo.

**Você deve ver:** na caixa, uma linha `world _FL26MyWorld: 2 new leagues, ...` e uma linha para
cada liga com os clubes, a divisão e o formato dela (`18 clubs x2` são 18 clubes, todos contra
todos em turno e returno; `division 2  below ... (3 up/down)` é uma segunda divisão), e as
`European places:` dela. Uma linha começando com `error:` diz o que corrigir primeiro; veja a
tabela no fim.

3. Clique em **Construir e instalar**. Ele pergunta `Montar _FL26MyWorld e colocar no jogo? ...`:
   clique em **Sim**.

   Se as tabelas do jogo forem mais antigas que o jogo, ele pergunta antes se deve extrair elas de
   novo: clique em **Sim** (um ou dois minutos).

   Ele coloca os módulos do Mod Studio, constrói o seu mundo e coloca ele no jogo, tudo de uma
   vez. Leva de alguns segundos a alguns minutos. Quando só imagens mudaram desde a última
   construção (um logo, um escudo, uma bandeira), leva alguns segundos.

**Você deve ver:** uma janela **Construção concluída** com uma marca em cada linha: **Mundo
construído**, **Campeonatos e clubes** (`2 campeonatos · 36 clubes novos`), **Módulos instalados e
ativados**, **No jogo** e **Inicie o jogo para jogar**. Em **Antes de jogar**:
`Comece uma carreira nova na Master League: uma carreira salva antes continua com o mundo antigo.`
Clique em **Pronto**.

Se ela disser **Há um save do Edit de antes deste Build na pasta de saves do jogo**: clique em
**Tirar o save do Edit do caminho**. Um save antigo do Edit esconde os nomes e elencos novos.

Em **2. Meu mundo** o cartão do seu mundo agora está verde: **● NO JOGO AGORA**.

**Passo a passo em vez do botão grande** (o mesmo resultado, em **Passo a passo, e Exportar o
mundo**):

1. **1. Conferir o plano**: como acima.
2. **2. Construir o mundo**: constrói ele. Se o mundo já existe, ele pergunta
   `... já existe. Construir de novo?`: **Sim**. O log termina com
   `Próximo: 3. Ativar, depois inicie o jogo.`
3. **3. Ativar**: pergunta `Colocar _FL26MyWorld no jogo (ligar no sider.ini)?`: **Sim**. O log
   termina com `Inicie o jogo, depois 4. conferir.`

**O que as linhas do log querem dizer:**

| Linha | Significado |
|---|---|
| `installing the modules ...`, `modules: ... copied, ... already there` | Os módulos do Mod Studio são colocados no lugar. |
| `world ...: N new leagues, changes to ... of the game's leagues and ... of its clubs` | O resumo do seu mundo. |
| `<league>  reg ...  comp ...  division 1  18 clubs x2` | Uma liga: os ids dela no jogo, a divisão e o formato. |
| `European places: 1st Champions League qualifying, ...` | Para onde vão os clubes do topo dela. |
| `no European places: the new leagues send nobody to Europe` | Um aviso, não um erro: configure **Europa** numa primeira divisão se você quiser. |
| `building ...` | O mundo está sendo escrito. |
| `livecpk: _FL26MyWorld (... files), sider.ini loads it` | O mundo está no jogo. |
| `error: ...` | A construção parou e nada mudou no jogo. Corrija o que ele diz (tabela no fim) e construa de novo. |

As opções em **Opções do mundo** (**Incluir a Conference League**, **Sorteio da copa nacional**,
**Uniformes nas cores dos clubes** ...) estão explicadas em
[8.2](mod-studio-guide.md#82-construir-ativar-jogar). Os valores padrão estão bons.

## Passo 13. Jogue: uma Master League NOVA, depois a conferência

1. Clique no botão verde **Iniciar o jogo** no canto superior direito (ou **Jogo → Iniciar o
   jogo**).
2. No jogo: **Master League** → **New game**. Não Continue: uma carreira salva antes continua com
   o mundo antigo.
3. Em **Select Team**, role a lista: as suas ligas estão nela, embaixo dos países delas.
4. Escolha um clube e jogue.

Cada mundo guarda as próprias carreiras: quando outro mundo entra no jogo, o Mod Studio guarda as
carreiras deste mundo, e traz elas de volta quando este mundo estiver no jogo de novo. Nada é
apagado. ([Mais](mod-studio-guide.md#31-meu-mundo).)

Depois deixe o Mod Studio conferir se o jogo pegou o mundo:

1. Feche o jogo (ou pelo menos inicie ele uma vez até o menu principal).
2. No Mod Studio: **2. Meu mundo** → aba **Construção** → **Passo a passo, e Exportar o mundo** →
   **4. Depois de iniciar: conferir**.

**Você deve ver:** uma linha por módulo dizendo quantas ligas ele leu do arquivo do mundo, e no
fim `the world works as built`. Uma linha `not loaded` ou `did NOT read the world file`, e no fim
`something is wrong -- see the lines above`, querem dizer que algo não funcionou: veja a tabela
no fim.

## Passo 14. Mudar algo depois

1. Feche o jogo.
2. Abra o Mod Studio. Ele abre o seu mundo sozinho (ou **Arquivo → Abrir um mundo...**).
3. Mude o que você quiser na página **NewLife Database**, ou nas abas de **2. Meu mundo**:
   **Campeonatos**, **Clubes** ou **Jogadores**. Ele se salva sozinho.
4. **Construir e instalar** (aba **Construção**) → **Sim**.

**Você precisa de uma carreira nova?** Sim: comece uma Master League nova depois de cada mudança
que você constrói. Uma carreira pega a sua própria cópia das ligas, clubes e elencos quando
começa, então uma carreira em que você já está continua com os antigos. E uma carreira salva com
um mundo precisa desse mesmo mundo para carregar, então deixe o mundo no jogo enquanto você joga
ela.

**Depois de atualizar o Mod Studio.** Construa o seu mundo mais uma vez com a versão nova e
comece uma carreira nova. Com a 0.2.4 isso importa: um mundo construído antes dela tem o goleiro
como capitão de todos os clubes. A construção agora dá a cada clube um capitão e batedores de
bola parada.

**Uma versão mais nova do NewLife.** Coloque as partes dela numa pasta nova, use **Abrir NewLife
Database...** nessa pasta, depois **Mais ▾ → Atualizar meus campeonatos para esta versão**. Cada
liga mantém o nome, a divisão, o formato, as vagas europeias e as copas; os clubes e os elencos
vêm da versão nova (a caixa **Manter meus clubes** mantém a sua própria escolha de clubes).
Construa de novo e comece uma carreira nova.
[Mais](mod-studio-guide.md#84-newlife-database-clubes-e-jogadores-reais).

**Tirar uma liga.** **Campeonatos** → **Nossos** → clique nela → **Remover** → **Sim**. Os clubes
dela e as mudanças nos jogadores deles vão junto.

## Passo 15. Compartilhar o que você fez

Há dois jeitos. Escolha um:

| | Pacote de liga (`.fl26pack`) | Mundo exportado (`.zip`) |
|---|---|---|
| O que ele tem | As suas ligas, prontas para adicionar a outro mundo: clubes, nomes, escudos, logos, elencos, rostos, e se você quiser uniformes e placares. | O mundo exatamente como você construiu. |
| A outra pessoa | Adiciona ele ao próprio mundo e constrói, então ele funciona ao lado das ligas e dos outros pacotes dela. | Instala e joga. Nada para construir, mas ele substitui qualquer outro mundo que ela tenha no jogo. |
| Como ela instala | [Caminho C de Instalar um pacote pronto](install-a-pack.md#caminho-c-um-pacote-de-liga-fl26pack) | [Caminho A de Instalar um pacote pronto](install-a-pack.md#caminho-a-um-mundo-pronto-um-zip) |

### Um pacote de liga

1. **2. Meu mundo → Mais ▾ → Pacotes de campeonatos → Criar um pacote...** (ou na barra de cima:
   **Arquivo → Criar um pacote de campeonatos...**).

**Você deve ver:** uma janela **Criar um pacote de campeonatos**.

2. Preencha **Nome** (obrigatório), **Autor**, **Versão** (`1.0` para começar) e **Descrição**.
3. Em **Campeonatos**, marque as ligas que entram (**Selecionar tudo** / **Não selecionar
   nada**). Uma liga abaixo de outra liga tem que ir junto com ela.
4. **Também minhas alterações nos campeonatos, clubes e jogadores do próprio jogo** (só se você
   mudou algum): marque para colocar essas mudanças também.
5. Em **O que entra**, está tudo marcado: **Elencos**, **Rostos e retratos de jogadores**,
   **Escudos e logos de campeonatos**, **Técnicos**, **Cores dos uniformes**, **Uniformes**,
   **Placares** e **Estádios dos mandantes**. Desmarque o que você não quer compartilhar. Os
   uniformes somam cerca de 10 MB por liga e um placar cerca de 7 MB.
6. Clique em **Salvar o pacote...**. Abre uma janela **Salvar o pacote** com um nome como
   `<nome>-1.0.fl26pack`. Escolha uma pasta que você vai achar de novo (Área de Trabalho,
   Documentos ...) e clique em **Salvar**.

**Você deve ver:** `Salvo: <arquivo>` com quantas ligas, clubes e rostos estão nele. Esse único
arquivo é o que você compartilha. Se ele passar de 10 MB, o Mod Studio avisa: o Discord não
aceita, então compartilhe pelo Google Drive, Dropbox, MEGA ou algo parecido, ou desmarque
**Uniformes** e **Placares**, ou faça um pacote por liga.

Mais: [9. Pacotes de ligas](mod-studio-guide.md#9-pacotes-de-ligas-compartilhe-uma-liga-inteira).

### Um mundo inteiro (zip)

1. Construa primeiro (Passo 12). O mundo tem que estar construído.
2. **2. Meu mundo** → **Exportar...** no cartão do mundo. (Ou aba **Construção** → **Passo a
   passo, e Exportar o mundo** → **Exportar o mundo...**.)
3. Abre uma janela de salvar com o nome do mundo como nome do arquivo (`_FL26MyWorld.zip`), na sua
   pasta de usuário na primeira vez (depois disso, na pasta que você usou por último). Escolha uma
   pasta e clique em **Salvar**.

**Você deve ver:** depois de um instante, `Salvo: <arquivo>` e quantos jogadores novos ganham um
rosto gerado. O zip tem a pasta do mundo, o arquivo do mundo e um leia-me.

Quem instala precisa dos módulos do Mod Studio com o pacote de rostos; instalar o zip em
**Importe seu mundo** coloca eles. Sem eles todos os jogadores novos ficam com a mesma cara. O
leia-me no zip diz isso.

Mais: [9.1 Exportar o mundo](mod-studio-guide.md#91-exportar-o-mundo-um-mundo-construído-para-outro-pc).

---

## Se algo der errado

As mensagens aparecem numa janela de erro, na linha verde ou vermelha embaixo do título de uma
página, ou no log da construção depois de `error:`. `<...>` quer dizer um nome ou um número.

| O que você vê | O que fazer |
|---|---|
| `no NewLife Database here: put the NewLife-....zip parts you downloaded in one folder (no need to unpack them) and open that folder` | Você escolheu a pasta errada, ou descompactou as partes. Abra a pasta que tem os próprios arquivos `NewLife-...zip`. |
| `the parts in this folder are of different versions (...): keep one version's parts only` | Duas versões do NewLife estão misturadas. Deixe na pasta só as partes de uma versão. |
| `<file> is not a NewLife part (...) -- download it again` | O download quebrou. Baixe essa parte de novo. |
| Uma liga cinza, `um campeonato tem de 10 a 24 clubes` | Adicione ou deixe clubes de fora (Passo 4) até ela ter de 10 a 24. |
| Uma liga cinza, `campeonato do próprio jogo: Levar os campeonatos do jogo para esta temporada` | O jogo já tem ela. Use **Levar os campeonatos do jogo para esta temporada...**. |
| **Adicionar ao seu mundo** fica cinza | Nada que pode ser adicionado está selecionado, ou a seleção passaria do limite de clubes novos (a linha embaixo). |
| `<clube> jogaria em dois campeonatos (<liga> e <liga>).` | Desmarque o clube numa delas. |
| `<liga> não tem um país que o jogo conheça.` | Esta liga não pode ser adicionada. |
| `Um campeonato precisa de um nome e de um país.` / `Escolha o país na lista.` | Em **Editar campeonato...**, preencha **Nome**, e escolha o **País** na lista em vez de digitar ele inteiro. |
| `Já existe um campeonato chamado <nome>.` | Dê outro nome à liga. |
| `European places: position <n> -- the league has <m> clubs` | Uma linha em **Europa** aponta para depois do último clube. Mude ou tire ela. |
| `European places: position <n> is listed twice` | Duas linhas têm a mesma posição. Tire uma. |
| `European places: a cup winner's place, but the country has no cup` | Marque **Copa nacional**, ou tire a linha **Campeão da copa**. |
| `Clubes, turnos e grupos precisam ser números.` | Em **divide-se em dois**, digite os grupos como números, por exemplo `6/6`. |
| `Uma liga de fevereiro a dezembro ainda não tem fase final, Apertura/Clausura nem copa da liga.` | Coloque **Temporada** em **agosto a maio**, ou tire a divisão em dois, Apertura/Clausura ou a copa da liga. |
| `Esta divisão joga de fevereiro a dezembro com o campeonato de cima, e um campeonato que joga de fevereiro a dezembro ainda não tem divisão em grupos nem Apertura/Clausura.` | Dê a esta divisão **todos contra todos**. |
| `Clubes sem campeonato são todos clubes novos: tire antes os clubes do jogo (Editar clube).` | A liga tem clubes do jogo. Na aba **Clubes** selecione cada um e use **Mais ▾ → Clube novo aqui**, depois configure **Clubes sem campeonato** de novo. |
| `<liga> fica abaixo deste campeonato; clubes sem campeonato não têm nada abaixo.` (ou `um campeonato de amistosos não tem nenhum.`) | Outra liga tem esta como **Divisão**. Mude aquela liga primeiro. |
| `Um campeonato tem de 10 a 24 clubes.` (aba Clubes) | Inserir clube / Remover clube deixaria a liga fora de 10 a 24. |
| `Abra antes a NewLife Database na página NewLife.` | **Clube NewLife...** precisa da pasta do NewLife: abra ela em **NewLife Database** uma vez. |
| `Escolha o clube que fica com o lugar dele.` / `Dê um nome ao clube novo.` / `Um clube não pode ficar com o próprio lugar.` | Em **Clube do jogo**, escolha um clube substituto, ou digite um nome para o novo. |
| `error: não há tabelas do jogo -- Configurações > Extrair as tabelas do jogo` | **5. Configurações → Extrair as tabelas do jogo**. |
| `error: não há pasta do jogo -- Jogo > Escolher a pasta do jogo` | **Jogo → Escolher a pasta do jogo...**. |
| `error: o nome do mundo precisa começar com _FL26` | **Campeonatos → Mais ▾ → Nome do mundo e arquivo...**: um nome que comece com `_FL26`. |
| `error: nada para construir: adicione um campeonato ou altere um do jogo ...` | O seu mundo está vazio. Adicione ligas (Passos 3 a 5). |
| `error: <league>, club <n>: <club> plays in <...> -- pick the club that takes its place there` | Faça [Clubes que o jogo já tem](#clubes-que-o-jogo-já-tem) para esse clube. |
| `error: <league>, club <n>: the new club taking <club>'s place needs a name` | Mesma janela: digite um nome ao lado de **O lugar dele vai para um clube novo, chamado:**. |
| `error: <club> is in <league> and in <league>: a club plays in one league` | Tire o clube de uma das ligas (**Clube novo aqui** na aba Clubes, ou desmarque ele antes de adicionar). |
| `error: <n> new clubs, but the game has room for <m> more (a full squad each)` | Clubes novos demais. Tire uma liga, ou clubes. |
| `error: <n> leagues, but the game has room for <m> ...` | Ligas novas demais. Tire algumas. |
| `error: <league> has <n> leagues below it; the game follows one link` / `... are all under ...` | Só uma liga pode ficar abaixo de uma liga. Mude a **Divisão** das outras. |
| `error: <league>: division 8 -- the rank field stops at 7` | Um país vai até a 7.ª divisão. |
| `error: at most 2 split leagues for now ...` / `... only one league of a country can be split or Apertura/Clausura` | Dê às outras ligas **todos contra todos**. |
| `As tabelas do jogo que o Mod Studio usa são mais antigas que o jogo: ... Extrair de novo primeiro?` | Clique em **Sim**. |
| Os passos da construção e **Construir e instalar** estão cinza | O mundo aberto é um mundo pronto de um zip: ele já está construído. Abra ou crie um mundo seu (**+ Mundo novo** em **2. Meu mundo**, ou **Ativar** no cartão do seu mundo), ou transforme o mundo pronto num mundo seu com **Torná-lo editável...**. |
| `<mundo> ainda não foi construído: primeiro 2. Construir o mundo.` (Exportar o mundo) | Construa primeiro, depois exporte. |
| `Dê um nome ao pacote.` / `Marque pelo menos um campeonato.` / `Seu mundo ainda não tem campeonatos.` | Em **Criar um pacote de campeonatos**, preencha **Nome** e marque uma liga; o seu mundo precisa de ligas antes. |
| Nenhuma liga nova no Select Team | Comece uma Master League **nova**. Depois **4. Depois de iniciar: conferir** (Passo 13). |
| `sider.log is older than the world switched on -- start the game to the main menu, then check again` | Inicie o jogo até o menu principal, feche, confira de novo. |
| `<module> not loaded` / `did NOT read the world file` | **2. Meu mundo → Construção → Passo a passo, e Exportar o mundo → 0. Instalar os módulos**, depois **3. Ativar**, inicie o jogo de novo e confira de novo. Continua errado: pergunte no Discord. |
| Os nomes dos clubes são os do jogo, não os seus | Um save antigo do Edit esconde eles: **Tirar o save do Edit do caminho** na janela **Construção concluída**, ou tire `EDIT00000000` da pasta de saves do jogo. |
| O goleiro é o capitão de todos os clubes novos | O mundo foi construído antes da 0.2.4. Construa de novo e comece uma carreira nova. |
| Todos os jogadores novos têm o mesmo rosto | **1. Início → Instalar agora** (quando o Início diz que os módulos estão faltando ou são mais antigos), ou **2. Meu mundo → Construção → Passo a passo, e Exportar o mundo → 0. Instalar os módulos**: traz o pacote de rostos. Depois inicie o jogo de novo. |

**Pedir ajuda:** no [Discord](https://discord.gg/StQqtk3G3M), mande uma captura de tela do que
você vê, o texto do log da construção, e o seu `sider.log` (**Jogo → Abrir sider.log**).
