# FL26 Mod Studio — guia do usuário

> [English](../en/mod-studio-guide.md) · [hrvatski](../hr/mod-studio-guide.md) · [español](../es/mod-studio-guide.md) · **português** · [français](../fr/mod-studio-guide.md)

> **Novo no Mod Studio?** Dois guias passo a passo, cada clique na ordem: [Instalar um pacote pronto](install-a-pack.md)
> (alguém te passou um mundo, um modpack ou um `.fl26pack`) · [Criar suas próprias ligas e pacotes](make-your-own-leagues.md)
> (você escolhe as ligas e monta elas). Este guia explica cada página e cada opção em detalhe.

> Perguntas comuns (atualizar, crash ao iniciar, copas, acesso, o que mandar quando algo dá
> errado): [faq.md](../../docs/faq.md) (em inglês) · perguntas e ajuda no [Discord](https://discord.gg/StQqtk3G3M)

O FL26 Mod Studio é um programa só para tudo o que você adiciona ao Football Life 2026:

- os **mods** que você baixa: estádios, uniformes, bolas, placares, narração, música, rostos, módulos Lua;
- os **servidores de conteúdo** que entregam esses mods (Stadium Server, Ball Server, Kit Server e os demais),
  com os arquivos de mapeamento editados como tabelas em vez de na mão;
- a própria **configuração do Sider**: quais pastas de conteúdo e módulos estão ligados, e em que ordem;
- **novas ligas e clubes** (o League Builder), suas mudanças nas ligas, nos clubes e nos **jogadores**
  do próprio jogo, e **pacotes de ligas** que um modder faz uma vez e qualquer um adiciona ao jogo.

Nada do jogo é sobrescrito. Antes de mudar um arquivo, o programa guarda uma cópia, e todo mod
que ele instala pode ser removido de novo.

---

## 1. Antes de começar

- **Football Life 2026** instalado, com a pasta `SiderAddons` (o FL26 já vem com o Sider).
- Descompacte o programa onde quiser, por exemplo `Documents\FL26 Mod Studio`. Mantenha a pasta inteira: as
  pastas `_internal` e `pack` e os arquivos `README` ficam ao lado do `FL26ModStudio.exe`.
- **Feche o jogo** enquanto muda as coisas. O Sider lê a configuração quando o jogo inicia.

A janela está em inglês. **Settings → Language** troca para croata (Hrvatski), espanhol
(Español) ou francês (Français).

## 2. Primeira execução

1. **Settings → Game folder**: aperte **Browse...**, escolha a pasta que tem o `FL_2026.exe` e depois
   **Use this folder**.
   A linha embaixo diz se o `SiderAddons\sider.ini` foi encontrado.
2. Se você quer novas ligas ou mudanças em jogadores: **Settings → Unpack the game's tables**. Isso
   lê os clubes, ligas e jogadores do jogo para uma pasta de trabalho (alguns segundos). Faça
   de novo só depois de uma atualização do jogo; o Build percebe uma (0.1.9) e oferece descompactar de novo antes. É preciso fazer uma vez em cada PC (um
   pacote ou um mundo novo pede isso e oferece abrir o Settings). **Use another tables folder**
   serve para um banco de dados seu, como uma pasta `pesdb` no livecpk: descompacte primeiro as tabelas do jogo,
   depois escolha essa pasta. Os arquivos dela vão por cima dos do jogo, que fornecem tudo o que ela não tem.
3. Abra **Home** (a primeira página). Ela mostra o mundo ativo e sua configuração e lista os problemas;
   **Open** ao lado de um problema leva à página que resolve. A Home também tem **Build and install**
   (todo o Build com um clique), **Only the European cups...**, **Open its leagues** e
   **Switch world...**.

**Atualizações.** Alguns segundos depois de abrir, o programa pergunta ao GitHub se saiu um FL26 Mod
Studio mais novo, e só avisa quando existe um. **Download and install** baixa o zip novo,
confere com o checksum da versão, fecha o programa, coloca os arquivos novos por cima dos antigos
e abre de novo. Suas configurações, projetos, pontos de restauração e o jogo não são tocados.
**Help → Check for updates...** pergunta a qualquer hora; desmarque **Help → Check for updates at start** e
o programa só pergunta nesse caso. Se o programa estiver numa pasta onde o Windows não
deixa escrever (como Program Files), ele abre a página da versão: descompacte o zip
você mesmo, ou mova o programa para uma pasta sua.

**Carreiras de antes da 0.2.0.** A 0.2.0 deixa um dia do calendário ter 792 partidas em vez de 280, e isso muda as tabelas com que uma carreira é salva: **uma carreira salva com uma versão mais antiga não carrega** (fica parada na tela de carregamento). Comece uma carreira nova depois da atualização. Seus mundos, projetos e dados do Edit não são afetados.

A **0.2.1** corrige o crash ao criar uma carreira Master League ou Be a Legend: instale os
módulos uma vez (o Build faz isso, ou **Build → 0. Install the modules**); o sider.log então diz
`3502 patches`. Mundos e carreiras feitos com a 0.2.0 continuam como estão.

**Jogar.** O botão **▶ Play** no canto superior direito (ou **Game → Start the game**) inicia o jogo
e avisa antes quando os módulos estão na ordem errada. **Game → Start the game without mods (safe
mode)...** volta a configuração que o Mod Studio encontrou na primeira vez.

**Créditos.** O botão **Credits** ao lado de **Help** lista todo mundo que ajudou a fazer o Mod Studio:
os testers, quem mandou relatórios e logs, e aqueles cujas ideias estão nele.

**Mais de uma pasta do Sider?** O Sider não precisa se chamar `SiderAddons`. O programa
procura a pasta ao lado do `FL_2026.exe` que tem um `sider.ini`, e também um nível mais
abaixo (`sider\patch 1`, `sider\patch 2` ... quando uma pasta guarda várias cópias do Sider). Se
houver várias, **Settings → Sider folder** escolhe em qual ele trabalha; as outras não
são tocadas.

## 3. As páginas

A lista à esquerda começa com **Home**, depois vêm três grupos.

| Grupo | Páginas |
|---|---|
| **League Builder** | Leagues, New clubs, Players, NewLife Database, League packages, Build |
| **Game content** | Kits, Stadiums, Balls, Commentary, Music, Other content |
| **Manage** | Install mods, Lua modules, Content folders, Profiles, Restore points, Diagnostics, Settings |

**Leagues** lista todas as ligas por continente, as do jogo e as suas (filtros **All**, **Ours**,
**Changed**, e uma caixa de busca). Escolha uma: uma liga sua ganha **Edit league...**, **Add lower
tier**, **Clubs and names**, **Players** e **Remove**; uma liga do jogo ganha nome, logo
e clubes (seção 8, "As ligas do jogo"). **Add league** cria uma nova. **More ▾** tem
**Pre-season cups**, **Cups of the game's countries**, **European places of the game's leagues**,
**UEFA ranking**, **South American places**, **Competition names** e **World name and
recipe...**. Esse último abre a página com o nome do mundo e a lista das suas ligas
(guias mais antigos chamam de *New leagues*), com mais alguns botões: **First-season European clubs**,
**League order** e **Seasons of the game's leagues**.

## 4. Instalar mods

Arraste um mod baixado para **Install mods** (`.zip`, `.7z`, uma pasta, `.lua`, `.cpk` ou
`.fl26pack`), ou use **Choose a file...** / **Choose a folder...**.

O programa olha dentro e lista cada parte: o que ela é e para onde vai.

| Parte | O que acontece |
|---|---|
| Pasta de conteúdo (livecpk) | Copiada para `SiderAddons\livecpk\<name>` e adicionada ao `sider.ini`. |
| Arquivos de servidor de conteúdo | Copiados para a pasta `content` do servidor. O **arquivo de mapeamento dele é mesclado ao seu**: suas linhas ficam e as linhas novas do mod são adicionadas. Para um clube que você já mapeou, a escolha ao lado de **Install** decide: *use the mod's* (usar a do mod), ou *keep mine, add the mod's after* (manter a minha e pôr a do mod depois). |
| Módulo Lua | Copiado para `SiderAddons\modules` e ligado no lugar certo da ordem. |
| .cpk empacotado | Descompactado numa pasta de conteúdo na instalação. |
| Pacote de liga | Adicionado à sua receita do League Builder (seção 9). |
| Mundo do League Builder | Um mundo pronto vindo de **Export the world** (seção 9.1), ou uma pasta `SiderAddons` copiada com `modules\fl26world.txt`. A pasta do mundo é copiada com o próprio nome, o arquivo do mundo vai para `SiderAddons\modules`, e o mundo é ligado. |
| DLL | **Não é instalada.** Uma DLL roda com os direitos do jogo; instale uma só de uma fonte em que você confia, na mão. |

Dê um nome ao mod, escolha se as pastas de conteúdo novas vão no topo (elas ganham) ou
embaixo, marque o que quiser e aperte **Install**. A lista abaixo mostra todos os mods instalados com
o programa. **Remove the mod** apaga os arquivos que ele adicionou e devolve os arquivos que ele substituiu.

## 5. Pastas de conteúdo e módulos Lua

**Content folders** lista as linhas `cpk.root` do `sider.ini`; os mundos do League Builder (`_FL26...`)
aparecem quando você marca **Show League Builder worlds**, e **Only switched on** esconde o resto. O Sider
procura um arquivo de cima para baixo, então a pasta mais alta na lista ganha quando duas têm o mesmo
arquivo.

- Marque ou desmarque uma pasta para ligar ou desligar (a linha vira comentário, nunca é apagada).
- **To top**, **Up**, **Down** mudam a ordem; **Add folder...** adiciona uma pasta que você já tem.
- O tamanho e o que tem dentro (rostos, uniformes, estádios...) aparecem para cada pasta.
- **Rescan**, **Remove from the list** e **Delete from disk...** também estão lá.
- Nada é gravado até você apertar **Apply**. **Discard** esquece as mudanças.

**Lua modules** é a mesma coisa para as linhas `lua.module`. O programa conhece a ordem certa dos
módulos comuns (servidores de conteúdo depois dos módulos que eles usam) e avisa quando um módulo está
no lugar errado. Alguns módulos precisam de uma configuração do Sider (por exemplo o Goal Song Server precisa de
`match-stats.enabled = 1`); o programa diz qual. Os módulos `fl26...` do próprio Mod Studio ficam escondidos
até você desmarcar **Hide the League Builder's own modules**; **Add module...** adiciona um módulo que você
tem.

Os módulos do League Builder mantêm a ordem em que foram instalados.

Desde a 0.2.0 as doze pequenas proteções contra crash entram como dois arquivos, `fl26guards.lua` (as oito `fl26nullguard`) e `fl26lateguards.lua` (`fl26superguard`, `fl26resultsguard`, `fl26ctlguard`, `fl26kitguard`), então a lista fica mais curta. O sider.log ainda cita cada proteção numa linha própria. O Build desliga as linhas antigas avulsas e guarda os arquivos antigos em `modules\before-builder-<n>`; não há nada a fazer na mão.

**Desligar os regens** (0.2.0): o `fl26regen` dá aos regens nomes novos, um potencial novo e um
rosto do pacote de rostos de regens. Para jogar sem ele, desmarque **Hide the League Builder's own modules
(fl26...)** para os nossos aparecerem, desmarque `fl26regen` e aperte **Apply**. O Mod Studio anota isso em
`modules\fl26-off.txt` na pasta do Sider, então **Build**, **Install the modules** e a troca de
mundo deixam ele desligado em vez de ligar de novo, como fazem com todos os outros módulos. O jogo
então faz os próprios regens: potencial e nomes do jogo, sem rostos do pacote de regens. Marque
de novo e **Apply** para ligar outra vez. Só o `fl26regen` pode ficar desligado desse jeito.

## 6. Conteúdo do jogo: os servidores de conteúdo

**Stadiums, Kits, Balls, Music, Commentary** e **Other content** (placares, menus, uniformes de
árbitro, patches de manga e clima) pertencem cada um a um servidor de conteúdo. Os módulos próprios do SPFL26 para uniformes, estádios e placares (`common\kits.lua`, `common\stadiums.lua`, `common\scoreboards.lua`) leem os mesmos arquivos de `content\kits`, `content\stadiums` e `content\scoreboards`; quando o servidor em si não está instalado, a página dele edita esses no lugar (uniformes desde a 0.1.7, estádios e placares desde a 0.1.8). Toda página tem:

- uma **linha de status**: o módulo está ligado, a pasta de conteúdo dele existe;
- uma aba por **arquivo de mapeamento**, mostrada como tabela: qual campeonato, clube ou estádio recebe o quê.
  **Add...**, **Change...**, **Copy**, **On / off** (a linha vira comentário) e **Remove**;
  escolha itens da biblioteca em vez de digitar ids. **Save** grava o arquivo; a cópia de antes vai para Restore
  points;
- a **Library**: o que tem na pasta de conteúdo do servidor, com imagens onde houver.
  Itens que nenhuma linha do mapeamento usa e linhas que apontam para itens que não existem são marcados;
- **Settings** do servidor, onde houver (estádio, bola, placar favorito ...).

O programa confere as tabelas antes de salvar: número onde vai número, nenhuma vírgula dentro de um
nome, um item que existe. Uma linha com problema fica colorida: **pare o mouse em cima dela para ver
o motivo**. **Only lines with problems** mostra só essas. Um clube listado duas vezes também é marcado: só a
primeira linha dele conta. O problema mais comum, "... not found in the library", quer dizer que a linha aponta
para uma pasta que não está na pasta de conteúdo do servidor, e o jogo não mostra nada ali (um estádio
preto, o uniforme antigo do clube): aponte para uma pasta que a aba **Library** lista, ou remova a linha.
**Other content** também tem uma aba **Look modules** que liga ou desliga módulos sem arquivos de
mapeamento.

Uma linha de campeonato tem como chave uma **fase** do campeonato, não o campeonato: o jogo
informa aos servidores de conteúdo a fase que está jogando (a Conference League é 186, 1210, 187,
189 e as rodadas seguintes 1213 ... 8381; a Champions League 2, 3, 4 e as dela), então uma linha
com o número do próprio campeonato (174) nunca é usada. O seletor de campeonato lista todo
campeonato mais uma vez como **(all N stages)**: escolha isso e é gravada uma linha para cada fase
(0.1.9). Uma linha com o número de um campeonato como chave é marcada como problema.

**Import kits...** (0.1.8, na página *Kits*): uniformes para muitos clubes de uma vez. Escolha uma pasta de uniformes prontos do kit-server -- uma pasta por clube, com `p1`, `p2`, `g1` ... e `order.ini`, com o nome do clube (`Dinamo Zagreb`) ou o team ID dele (`2215`). **Match to** escolhe *All clubs* ou *The new clubs of the live world*. Correspondências de 60% ou mais vêm marcadas; confira as desmarcadas e a coluna *Match* antes de **OK** (uma pasta sem correspondência diz "no club found"). Os uniformes são copiados para a biblioteca do kit-server (`League\Club`, como a pasta tinha) e cada clube ganha uma linha no `map.txt`; **Save** grava. Um clube que já tem uma linha fica com ela, a não ser que **Replace kits already set** esteja marcado. Os uniformes de um clube novo do League Builder vão pelo team ID que o Build deu a ele, então faça o Build do mundo e deixe ele ligado antes. A pasta de um clube pode ter, em vez disso, simples imagens dos uniformes (0.2.0): `p1.png`, `p2.png` ... para os uniformes e `g1.png` para o goleiro (2048 x 2048 é o ideal; `.jpg` e `.dds` também funcionam). O Mod Studio transforma elas em uniformes do kit-server; os números das costas, os números do calção e a fonte do nome são texturas próprias, então vêm de um uniforme que já está na biblioteca, escolhido em **Numbers and names from** (começa no primeiro uniforme da biblioteca que tem isso; *none*: o jogo mantém os do próprio clube). As cores do `config.txt` são lidas da imagem. A conversão das imagens é do Xxspedd, da ferramenta de uniformes dele. O Mod Studio não desenha uniformes: as imagens vêm de você ou de quem faz uniformes.

## 7. Perfis

Um perfil lembra quais pastas de conteúdo e módulos estão ligados, e em que ordem. Tenha um para
a Master League, um para jogar online, um para testes:

- **Save current setup...** guarda com um nome o que está ligado agora.
- **Switch to it** coloca essa configuração no `sider.ini` (o `sider.ini` antigo vai para Restore points).
- **Update with current setup** sobrescreve o perfil; **Delete** remove.
- **Export...** / **Import...** levam um perfil para outro PC (`.fl26profile.json`).

## 8. League Builder: novas ligas, clubes e jogadores

O League Builder adiciona novas ligas ao jogo e muda as do próprio jogo. O que ele cria é um
**mundo**: uma pasta de conteúdo chamada `_FL26...` que o jogo lê enquanto ela está ligada.

**Remove** (Leagues) apaga a liga selecionada com os clubes dela. Para apagar várias de uma vez, abra
**More → World name and recipe...**, escolha com Ctrl+clique, Shift+clique ou Ctrl+A, depois
**Remove** ou a tecla Delete.

**Leagues → Add league**

| Campo | O que significa |
|---|---|
| **Name** | O nome da liga no jogo. Não pode haver duas iguais. |
| **Country** | Dá a bandeira e onde a liga aparece na lista. Um país para o qual o jogo não tem liga ganha um título próprio. |
| **Clubs** | 10 a 24 (1 a 24 para clubes sem liga). |
| **Clubs in no league** | Para um clube, ou alguns, sem uma liga em volta (0.1.8): digamos só o BATE Borisov, da Belarus. Escolha o grupo em que eles entram: *Other European teams*, *Other Latin American teams*, *Other Asia-Oceania teams*, *Other Africa teams* ou *Classic Teams* -- onde o jogo guarda os próprios clubes que não jogam liga nenhuma (Dynamo Kyiv, Wydad Casablanca ...). No Select Team eles aparecem nesse grupo. Eles ganham nomes, escudos, uniformes, técnico, formação, jogadores e estádio como qualquer clube novo (**Edit club**, **Players**); o nome acima é só como o Mod Studio lista eles. Eles não jogam liga, copa nem competição europeia, e todo o resto desta janela fica cinza. |
| **Format** | *Everyone plays everyone* (todos contra todos), 1 a 4 vezes, *splits in two (Scottish style)* (divide em dois, estilo escocês), ou *Apertura and Clausura*: dois torneios por temporada (setembro ao início de janeiro, janeiro a maio), cada um começando do zero, depois playoffs de 8 ou 4 clubes (ou nenhum). A tabela da temporada inteira decide acesso e rebaixamento. No máximo 18 clubes. Uma liga dividida tem no máximo 46 rodadas, antes e depois da divisão juntas (16 clubes duas vezes são 30, então o maior grupo dela duas vezes pode ter 8 clubes, 14 rodadas). Por enquanto só uma liga por país pode ser dividida ou Apertura/Clausura. |
| **Division** | *(top division)* (primeira divisão), ou a liga acima dela: outra liga nova, ou uma do jogo. Para pôr uma liga nova embaixo de outra liga nova num passo só: selecione ela e aperte **Add lower tier** (pega o país, a quantidade de clubes, o formato e o sobe/desce da liga de cima; só falta o nome). Uma liga que já tem outra liga nova embaixo fica cinza (0.1.9): o jogo segue um único link para baixo a partir de uma liga, então grupos de uma mesma divisão (três grupos da Serie C embaixo da Serie B) ainda não são possíveis. |
| **Up / down** | Quantos clubes trocam de lugar com a liga de cima no fim da temporada. |
| **Season** | Só para a primeira divisão de um país novo: *August to May* (agosto a maio, o padrão) ou *February to December* (fevereiro a dezembro), como Brasil, Japão ou Arábia Saudita: os clubes sobem e descem na virada do ano, e as divisões de baixo acompanham. Ainda não com divisão em dois, Apertura/Clausura, copa nacional ou copa da liga -- nem com divisão em dois ou Apertura/Clausura numa divisão embaixo de uma liga de fevereiro a dezembro, incluindo a Liga BetPlay e a J1 League do jogo. |
| **Europe** | Só primeira divisão: qual posição da liga vai para qual competição europeia. **Top flight: 1st UCL qualifying, 2nd UEL, 3rd UECL** preenche as três de sempre (*... qualifying* são os play-offs de agosto, veja 8.2); **Add place**, o ✕ numa linha e **Clear** para qualquer outra coisa. Cada posição uma vez, e só posições que a liga tem. Abaixo de 1 a posição fica **Cup winner** (0.1.7): o campeão da copa do país (um país novo precisa de **National cup**) -- e quando o campeão já tem vaga europeia pela liga, a vaga desce na tabela para o próximo clube, como a UEFA faz. Desde a 0.2.0 o campeão da copa também pode ir para as copas que o Mod Studio monta (Copa Sudamericana, CAF Confederation Cup, AFC Champions League Two ...); numa carreira nova, antes de alguém ter ganhado a copa, essa vaga também vai para o próximo clube da liga. Uma liga do jogo também pode ter uma (*European places of the game's leagues*). Deixe vazio para uma divisão inferior. O padrão segue o país: a Ásia ganha a AFC Champions League e a AFC Champions League Two, a América do Sul a Libertadores e a Copa Sudamericana, a África a CAF Champions League e a CAF Confederation Cup, a América do Norte e Central a CONCACAF Champions Cup, a Oceania a OFC Champions League. A **AFC Challenge League** (0.2.0) é a terceira copa da AFC, abaixo da AFC Champions League Two como a Conference League na Europa; escolha ela com **Add place** (*AFC CHL* na lista de Leagues). Essas sete copas que o jogo não tem são montadas com o mundo (seção 8.2). Uma vaga *Libertadores qualifying* toma o lugar de um clube do jogo na fase preliminar (o último do país com mais clubes nela), no máximo seis das oito vagas dela; **Check the plan** diz quais ligas ficam de fora além disso. |
| **Logo** | Qualquer imagem (PNG com fundo transparente fica melhor). Vazio: um é desenhado para você. |
| **Country flag** | Sua própria imagem da bandeira do país, esticada no quadro de bandeira do jogo. Ela substitui a bandeira do jogo daquele país em todo lugar (Select Team, nacionalidade dos jogadores, o título do país em Database > Competition Info) enquanto o mundo está ligado. Vazio: a bandeira do próprio jogo. |
| **Cup** | Só primeira divisão. **National cup**: o país ganha uma copa própria, com o nome que você der (vazio: `<league> Cup`). O jogo preenche a copa de um país com a primeira divisão e a divisão de baixo, e o tamanho da copa segue a linha National cup dos Limites (8.3): o maior tamanho que a tela da copa desenha e que cabe, então um grupo de 22 dá uma copa de 20, primeira divisão primeiro. Acima de 44 clubes a copa fica só com a primeira divisão. Uma segunda divisão nova embaixo de um país que o jogo já tem (Alemanha, Rússia ...) também entra na copa desse país, depois dos clubes da primeira divisão, quando as rodadas da copa cabem no grupo. Uma terceira divisão nova ou mais baixa (a League One embaixo do Championship) deixa a copa do país para as duas primeiras divisões do jogo, como no jogo. **Super cup**: também uma supercopa de jogo único antes da temporada, o campeão contra o campeão da copa. |
| **League cup** | Só primeira divisão. Um mata-mata desta liga e da de baixo, do jeito que a Carabao Cup é jogada (0.2.0): um jogo por rodada, semifinal e final também, nas semanas da Carabao Cup: 27 de agosto, 23 de setembro, 28 de outubro, as quartas de final em 23 de dezembro, a semifinal em 14 de janeiro e a final no domingo, 15 de março (uma liga de fevereiro a dezembro: do fim de setembro a dezembro), em dias próprios, nunca num dia de copa nacional ou de competição europeia. O grupo tem tantos clubes das duas divisões quanto a tela da copa desenha, até 44 (20 + 24: a Premier League e o Championship inteiros); quando isso não dá 16 ou 32, os clubes desta liga ganham as folgas e começam na segunda rodada. Todo confronto é sorteado. Dê um nome ou deixe vazio (`<league> League Cup`). Um mundo montado antes da 0.2.0 mantém a copa antiga de 16 em jogos de ida e volta, com a rodada prévia, até você montar ele de novo; uma carreira começada antes desse Build joga a copa antiga. |
| **Cup logos** | Uma imagem para a copa nacional, a supercopa, a copa da liga e os playoffs do Apertura/Clausura, cada uma separada. Vazio: um emblema com as iniciais da copa é desenhado para ela. |
| **Exhibition only -- not in Master League** | Para Kick Off e partidas amistosas: uma liga histórica, lendas e coisas do tipo. Os clubes dela nunca jogam uma temporada da Master League, então a liga fica sozinha: sem divisão acima ou abaixo, sem vagas europeias, sem copas. Ela ainda aparece na lista de times da Master League; escolha seu clube de outra liga. |
| **Formation** | Como os clubes da liga entram em campo. Escolha uma das formações que os clubes do jogo usam (4-2-3-1, 4-1-2-3, 4-3-3, 5-3-2 ...; a lista diz quantos clubes do jogo jogam assim): cada clube novo ganha uma cópia da tática de um clube do jogo com essa formação, e o melhor onze dele é escalado no Build. Vazio: o padrão do jogo, um 4-2-3-1 fixo. Um clube sozinho pode ter a própria (**Edit club**). |

**World name** (Leagues → More → **World name and recipe...**) tem que começar com `_FL26`. Essa página também lista suas ligas: depois do **Build** a coluna **League ID**
mostra o id de campeonato de cada liga no jogo, o mesmo que o arquivo de logo dela leva. A coluna **#** é o
lugar da liga na ordem (**Move up** / **Move down**), e **Select Team** diz onde o último Build
colocou ela: *yes*, *in place of* um dos grupos do jogo, ou *no place (it plays)*. Um `*` ali quer dizer que a
ordem mudou desde então: faça o Build de novo para ver onde ela vai. Arrastar na página **Leagues** move uma liga só entre os lugares que as ligas do continente dela já ocupam aqui (0.2.0; antes, colocava a ordem toda por continente, então as ligas da América do Norte e da Oceania sempre ficavam por último).

**Pre-season cups** (Leagues → More): mata-matas amistosos de 4 ou 8 clubes convidados em julho, antes da temporada, emparelhados na ordem que você der (primeiro contra segundo ...). Um clube é de uma liga nova ou um clube do jogo (pelo id); pelo menos um tem que ser de uma liga nova, e o país dele sedia a copa. Uma carreira começa em agosto, então a primeira é jogada na segunda temporada. Cada copa pode ter um **Logo**; vazio: um é desenhado para ela.

**Cups of the game's countries** (Leagues → More): uma copa da liga -- a Carabao Cup, digamos -- para ligas do jogo. Marque **League cup** ao lado de uma liga: ela e a liga de baixo, até 44 clubes, um jogo por rodada do fim de agosto até a final em meados de março, sorteada, com os clubes da própria liga ganhando folga até a segunda rodada (0.2.0; a mesma copa de uma liga nova), nos dias que o calendário de liga e copa do jogo deixa livres. **Super cup**, o campeão contra o campeão da copa no fim de julho, só onde o jogo não tem uma (Brasil, Chile, Escócia, Grécia, EUA); quando ainda não há campeão da copa (o primeiro verão de uma carreira nova), ou o campeão também ganhou a copa, joga o vice da liga (0.2.0; antes, a copa não começava). Nome vazio: o nome da liga e *League Cup* / *Super Cup*. **Logo** ao lado de cada nome (0.2.0): uma imagem para essa copa; nenhuma, um emblema com as iniciais da copa.

**European places of the game's leagues** (Leagues → More): quais posições da Premier League, LaLiga, Serie A ... vão para qual competição europeia. A lista mostra as vagas do próprio jogo; marque **Own places for this league** para mudar. Uma liga não marcada fica com as vagas do jogo, uma liga marcada sem linhas não manda ninguém.

**UEFA ranking** (Leagues → More, 0.1.7): todas as ligas europeias do mundo -- as do jogo e suas
novas primeiras divisões -- numa lista só, o país mais forte primeiro. Arraste uma liga (ou **Up** / **Down**)
para mudar a ordem, desmarque uma para não dar vaga europeia a ela, **UEFA's order** devolve a lista
ao ranking de associações da UEFA para 2026-27. O lado direito mostra o que cada liga ganha, e
**OK** grava: as vagas da tabela de distribuição da UEFA para 2024-27 -- o 1º do ranking tem cinco vagas na Champions
League, o 6º duas e uma vaga de play-off, o 30º uma vaga na segunda fase preliminar da Champions League
e três na da Conference League, e assim por diante, incluindo a vaga do campeão da copa na Europa League. Um mundo nunca tem todos os 55 países da UEFA, então
as vagas das posições do ranking que ele não tem vão para os próximos clubes das ligas mais fortes, uma de cada vez,
rodada por rodada, e toda competição fica completa: com doze ligas o 6º, o 7º
e o 8º da Inglaterra vão para a fase preliminar da Champions League, digamos. Depois da 31ª liga não sobra vaga, e
a lista diz isso. Cada fase preliminar comporta dezesseis clubes: com todas as 31 posições num mundo, as
vagas das posições mais baixas além desses dezesseis ficam sem nada (as notas dizem quais; as posições 26 e abaixo na verdade
começam na primeira fase preliminar, que o Mod Studio não tem). As vagas de fase preliminar vão para as rodadas na ordem da tabela, o país
mais forte para a rodada mais perto da fase de liga. Depois você ainda pode mudar as vagas de qualquer liga
na mão (*Europe* na liga, *European places of the game's leagues*): o Build usa
as vagas, não o ranking.

**South American places** (Leagues → More, 0.1.7, só leitura): para cada liga sul-americana, as
quatro do jogo e as suas, quais posições vão para a Copa Libertadores, a fase preliminar dela e a
Copa Sudamericana. As vagas de Libertadores do jogo são as dele (Brasil do 1º ao 4º e o campeão da Copa do
Brasil, preliminar 5º-6º, e assim por diante -- as mesmas que o Competition Info do jogo mostra); a
Copa Sudamericana é do Mod Studio, então a lista mostra quantos clubes cada liga do jogo
manda para ela com as suas vagas incluídas: suas ligas primeiro, depois Brasil, Argentina, Chile e Colômbia,
um clube cada, alternando até 32. Um clube que já está na Libertadores ou na preliminar dela cede o lugar ao
próximo da liga dele. **Check the plan** imprime a mesma lista sempre que o mundo tem uma
vaga de Libertadores ou Sudamericana.

**Competition names** (Leagues → More): um nome e um logo novos para as copas, supercopas e competições continentais do jogo -- a FA Cup, a Champions League, a Libertadores ... -- e para as copas continentais que o mundo monta (CAF Champions League, Confederation Cup, AFC Champions League Two, Copa Sudamericana, CONCACAF Champions Cup, OFC Champions League, AFC Challenge League, CAF Super Cup). Todas as fases de uma competição recebem o nome. Vazio: o do próprio jogo. As ligas do jogo são renomeadas em *Leagues* (escolha uma liga do jogo).

**League order** (Leagues → More → World name and recipe..., 0.2.0): a ordem dos países no Select Team da Master League e na lista de times do Kick Off / Edit. *By continent* é a ordem do jogo (Europa, as Américas, Ásia, depois África, cada um de A a Z). *Every country A-Z* coloca todos numa sequência alfabética só, e *My own order* deixa você pôr do jeito que quiser (arrastando, ou Up / Down). As ligas de um país ficam juntas, primeira divisão primeiro, e as competições de clubes, os grupos "Other" e os Classic Teams vêm depois dos países. Alemanha, EUA e Japão ficam nos grupos "Other" do Select Team, então só mudam de lugar no Kick Off. Faça o Build do mundo de novo depois.

**Seasons of the game's leagues** (Leagues → More → World name and recipe..., 0.2.0, experimental): Japão, China, Brasil, Chile e Arábia Saudita jogam de fevereiro a dezembro no jogo. Marque um e as ligas dele passam a jogar de agosto a maio como a Europa: a temporada começa em agosto, acesso e rebaixamento acontecem no meio do ano, as copas dele vão para datas de agosto a maio e as vagas continentais saem da tabela que terminou em maio. Uma divisão sua embaixo de uma dessas ligas acompanha. Colômbia e EUA jogam Apertura e Clausura e não podem mudar. Faça o Build do mundo de novo e comece uma carreira nova.

**First-season European clubs** (Leagues → More → World name and recipe..., 0.1.8): escolha na mão
os clubes da fase de liga da Champions League, Europa League e Conference League na primeira
temporada de uma carreira nova. Seus clubes entram primeiro e o jogo completa o resto; a partir da segunda temporada as
vagas europeias decidem.

**New clubs**: escolha a liga, depois **Edit club** (nome, nome curto, escudo), ou **More ▾ → Paste
names...** / **Load names from file...** (o mesmo menu tem **Insert club**, **Remove club**, **New
club here**, **Move to another league...** e **Import crests...**). Um nome vazio vira `<league> 01`, `<league> 02` ...; um clube
sem escudo ganha um distintivo numerado. Os uniformes são emprestados dos próprios clubes do jogo. Um uniforme desses é
licenciado, e o Edit mode não muda ele ("You cannot edit this strip"): marque **Kits you
can edit in the game** na página Build e os clubes novos não pegam nenhum emprestado, cada um veste um uniforme simples
que o Edit > Teams > Strip muda como o de qualquer outro clube, incluindo o Paste Image.
Com o Kit Server instalado, **Make kits for the new clubs** (página Build, ligado a menos que você desmarque, 0.2.1)
faz para cada clube novo uniformes de casa, fora, terceiro e de goleiro nas cores da camisa dele (as do NewLife, ou as do
escudo quando ele não tem), com o escudo no peito e no calção, para ligas inteiras de uma vez
quando o mundo é ligado. Um escudo que você coloca depois (Import crests) vai para os uniformes na
próxima vez que o mundo for ligado. Um clube com um uniforme próprio do Kit Server, ou só com um distintivo numerado, não ganha nenhum.
Os nomes mantêm as letras (FK Željezničar); o nome curto de três letras não tem, como no jogo,
então Č, Ž, Đ viram C, Z, D ali. Depois do **Build** a coluna **Team ID** mostra o id de cada clube no
jogo.

**Técnico**: no **Edit club** de um clube novo você pode dar nome ao técnico. Vazio: um nome inventado a partir de jogadores do país do clube (um clube croata ganha um nome como `Tomislav Krovinović`; o mesmo em todo Build), ou um numerado (`FL M0001` ...) para um país do qual o jogo tem poucos jogadores. **Manager picture** embaixo dá um retrato ao técnico (o mesmo que **Manager portrait...** na página Players); *Leagues* (uma liga do jogo) > **Edit club** tem isso também para os clubes do jogo.

**Cores dos uniformes**: **Home kit colours** e **Away kit colours** no **Edit club**: o Build empresta o
uniforme do jogo mais parecido com elas, e **Make kits for the new clubs** usa elas.

**Formação**: no **Edit club** de um clube novo você pode dar a ele uma formação própria; *As the league* mantém a da liga. O campo embaixo da lista mostra onde cada um fica.

**Estádio** (0.1.7): no **Edit club**, um estádio da biblioteca do Stadium Server para o clube; o slot e o nome são preenchidos a partir da pasta, mude o nome se quiser. Ele é gravado no `map_teams.txt` do Stadium Server quando o mundo é ligado (e quando o mundo ativo é montado de novo), então nunca é preciso procurar o id de um clube novo. Uma linha sua para o mesmo clube fica desligada enquanto isso, e volta a ligar quando o clube não tiver mais um aqui. *Leagues* (uma liga do jogo) > **Edit club** tem isso também para os clubes do jogo. O Stadium Server tem que estar instalado (a página *Stadiums*), ou o módulo de estádios próprio do SPFL26 (`common\stadiums.lua` com a pasta `content\stadiums`): desde a 0.1.8 o Mod Studio grava ali quando o Stadium Server não está instalado.

**Clubes que o jogo já tem.** Um lugar de uma liga nova pode ter um dos clubes do jogo em vez
de um novo: selecione o lugar, depois **Club of the game...**, e busque pelo nome ou pelo team ID
(**Only clubs in no league** filtra a lista). O clube mantém nome, escudo, uniformes, técnico e
jogadores, e joga só na sua liga. Quando ele joga em algum lugar no jogo (uma liga, uma copa, a
Europa League ...), você escolhe quem toma o lugar dele ali: um clube do jogo que não joga nada,
ou um clube novo que você nomeia. **It keeps its places in continental competitions** (0.1.8, #84) deixa ele continuar jogando a Champions League, a Libertadores ou a AFC Champions League em que está: um clube que no jogo só joga a competição continental então simplesmente se muda, e um que também joga uma liga do jogo entrega só a liga e as copas ao clube que você escolher. Da segunda temporada em diante as vagas da sua liga decidem quem vai. Um torneio de pré-temporada (as *Pre-season friendly Cups* do SPFL26) não conta: o clube continua jogando ele, como os clubes da Premier League fazem (0.1.7). **Edit club** num clube do jogo muda nome, escudo, retrato do técnico e estádio, como em *Leagues* para uma liga do jogo (0.1.7). Assim nenhuma competição do jogo muda a quantidade de clubes; as
ligas do jogo só mantêm as datas com a quantidade para a qual foram feitas. Seleções, os times
clássicos e padrão e clubes com menos de 18 jogadores não podem ser escolhidos. **New club
here** devolve o lugar a um clube novo. O clube deixa de aparecer nos grupos *Other ... clubs*
da Master League.

**NewLife club...** (0.1.8, #83) coloca clubes do NewLife Database, com seus elencos, no lugar selecionado e nos lugares seguintes: marque um ou mais clubes (busque por clube ou por liga) e cada um toma seu lugar na ordem. Uma liga que você fez na mão ganha clubes reais assim. Usa a pasta do NewLife que você abriu por último; na primeira vez, abra ela na página *NewLife Database*.

**Insert club** e **Remove club** adicionam um lugar antes do clube selecionado ou tiram um (10 a
24 clubes); nomes, escudos, técnicos e mudanças de jogadores se movem com os clubes. Confira as
vagas europeias da liga, depois **Build** de novo. Qualquer mudança nos clubes de uma liga exige uma **carreira nova**.

**Move to another league...** (0.1.7) leva o clube novo selecionado para o fim de outra liga nova, com nome, nome curto, escudo, técnico, formação, uniformes, id do NewLife e mudanças de jogadores; a liga que ele deixa fica com um clube a menos. Um clube do jogo se move com **Club of the game**: tire ele de uma liga, ponha na outra.

**As ligas do jogo** (escolha uma em *Leagues*): um nome ou logo novo, depois **Keep league changes** (**Undo league changes** volta atrás); **Edit club** para escudo, nome, retrato do técnico e estádio de um clube.

**Import crests...** (0.1.8, *New clubs* → More): escudos para muitos clubes de uma vez. Escolha uma pasta de imagens; cada uma é ligada a um clube pelo nome do arquivo -- o nome do clube (`Alianza Lima.png`, `alianza_lima_r_l.png`) ou o team ID dele (`2287.png`, o `e_2287_r.png` dos pacotes de escudos). A lista mostra cada correspondência com uma marca; desmarque uma errada antes de **OK**. Um clube que já tem escudo fica com ele, a não ser que **Replace crests already set** esteja marcado. As imagens ficam naquela pasta e o Build lê elas de lá, então guarde a pasta. (A correspondência pelo nome é uma ideia do script de escudos do Xxspedd.)

**Swap leagues with a club...** (0.1.7): dois clubes das ligas do jogo trocam de lugar -- um clube que subiu por um rebaixado, um clube da liga de um país por um de outro. Cada um toma os lugares do outro na liga, nas copas e nas competições europeias, então toda liga do jogo mantém a quantidade de clubes. Um clube numa liga nova da receita não pode trocar também. **Undo club changes** desfaz a troca. Depois **Build** de novo e comece uma carreira nova.

> **Arquivo Edit.** Se a pasta de saves do jogo tem um arquivo Edit (`EDIT00000000`), ele se sobrepõe aos nomes
> dos clubes. Mova ele para outro lugar para ver seus nomes.

### Jogadores

**Players** muda o elenco de qualquer clube: os clubes novos da receita e os do próprio jogo.
Escolha um clube (ou aperte **Players** em New clubs), depois um jogador:

- **Name**, **shirt number**, **position** e as posições em que ele pode jogar (A = natural,
  B = pode jogar ali), pé mais forte, altura, peso, idade, nacionalidade, estilo de jogo;
- todas as **habilidades** e **skills** (os nomes são os do próprio jogo);
- **Rating**: o overall da lista, feito das habilidades em que a posição se apoia. Mudar
  ele move todas as habilidades do jogador na mesma quantidade. Um jogador de um clube novo não tem
  nome até o Build numerar ele (FL P00001 ...); digite um em **Name** para dar o seu;
  desde a 0.2.0 um elenco desses começa no nível da divisão dele (cerca de 72 numa primeira divisão até 57
  a partir da quinta divisão);
- **Face**: **Choose...** uma pasta de rosto (seção 8.1). **Clear** devolve o rosto do jogo. Um
  jogador novo sem rosto ganha um rosto do pacote de rostos de regens que combina com a nacionalidade dele, com o
  retrato (0.1.5.5, com os módulos instalados e o `fl26regen` ligado, seção 5). Um rosto feito para outro jogador traz também
  o corpo desse jogador, então braços e pernas ficam com a cor de pele do rosto (0.1.9);
- **Portrait**: **Choose...** uma imagem (PNG ou JPG) para o retratinho do jogador nas listas do
  elenco, sem um rosto próprio. O Build deixa em 180 x 180; ele ganha do retrato de uma pasta de rosto;
- **Order up / Order down**: a ordem do elenco. Os primeiros onze começam a partida;
- **Add player** (uma cópia do jogador que você escolher, com um id novo; só clubes do jogo),
  **Remove from club** (aperte de novo para voltar atrás). Um clube novo mantém pelo menos 18 dos próprios
  jogadores; na 0.2.1 a página esquece de contar os jogadores contratados para ele, então pode dizer não cedo
  demais: remova um jogador contratado no lugar. Clubes do jogo não têm mínimo;
- **Best eleven** coloca o jogador mais forte em cada posição; **Squad level...** sobe ou
  desce todas as habilidades do elenco inteiro;
- **Pitch** (clubes novos): os onze titulares na formação do clube. Arraste um jogador da lista
  para uma posição, ou arraste uma posição para outra para trocar as duas; um clique numa posição seleciona o
  jogador que está ali;
- **Export CSV... / Import CSV...**: edite um elenco numa planilha. Exporte primeiro, mude as
  células, importe de volta as mesmas colunas.
- **Import a squad from a table...**: qualquer tabela de jogadores vira o elenco do clube -- uma
  digitada na mão, uma lista de elenco copiada de um site, uma exportação do Football Manager ou do EA FC. As
  colunas são reconhecidas pelo nome (nome, posição, idade ou data de nascimento, nacionalidade,
  altura, pé, número da camisa, overall e quaisquer notas) e mostradas para você corrigir uma que esteja
  errada. O que a tabela não tem vem dos próprios jogadores do jogo da mesma posição
  e overall; as notas de 1-20 do Football Manager são esticadas para o 40-99 do jogo. Os jogadores da
  tabela tomam os lugares do clube na ordem do elenco: um clube novo mantém os 30 lugares (menos
  jogadores = o resto sai, até 18), um clube do jogo ganha ou perde jogadores para bater.

Toda mudança é gravada no mundo quando você faz o **Build**; os arquivos do jogo ficam como estão.
**Undo changes to this player** e **Undo all changes of this club** voltam ao que o jogo tem.

A lista de clubes também tem **National teams** e **Other clubs (no league)**: os times que o jogo guarda fora de qualquer liga (seleções, clubes que só jogam uma copa ou uma competição continental). Os jogadores deles são editados do mesmo jeito.

#### Transferências, seleções, ids, o retrato do técnico

- **Sign players...** (um clube): uma lista de todos os jogadores do jogo e dos seus clubes novos, com
  filtro de nacionalidade e busca por nome; escolha vários com Ctrl ou Shift. Eles vão para este
  clube: o clube antigo perde eles (uma transferência). **Transfer to...** faz o mesmo pelo outro
  lado: o jogador selecionado vai para o clube que você escolher. A lista mostra *from ...* no clube
  que recebe ele e *to ...* no clube que ele deixa; **Remove from club** em qualquer das linhas cancela a
  transferência. Um clube tem no máximo 40 jogadores.
- **Call up players...** (uma seleção: escolha *National teams* na lista de ligas): a lista
  abre no país da seleção. Os jogadores entram no elenco da seleção **e continuam nos clubes deles**,
  como no jogo. **Remove from club** tira um jogador do elenco da seleção (não do clube
  dele). Uma seleção tem no máximo 26 jogadores; um jogador está em uma seleção por vez.
  Seu elenco é gravado nos dados do jogo, mas numa carreira da Master League o jogo escolhe os
  próprios elencos das seleções, então ali suas convocações não ficam.
- Um jogador que chega vai para o fim da ordem do elenco com um número de camisa livre; o elenco que ele
  deixou fecha o buraco na ordem.
- Coluna **Player ID**: o id de cada jogador -- o do próprio jogo, o que você digitou, ou o que o
  último **Build** deu a um jogador novo (faça o Build uma vez antes de fazer minifaces ou rostos para jogadores
  novos). **Export CSV...** grava ele como `player_id`; o Import CSV ignora essa coluna.
- **Club ID** (ao lado do clube) e **Player ID** (aba Basics): só para seus clubes e
  jogadores **novos**. Vazio = o próximo id livre no Build. Digite um quando um uniforme, escudo ou pacote de rosto foi
  feito para um certo id. Ids de clube: do primeiro id depois dos clubes do jogo (71578) até 81919;
  ids de jogador: acima do maior do jogo até 399999; nunca um que o jogo ou outro clube ou
  jogador novo já tem. O id é usado em todo lugar em que o mundo se refere ao clube ou jogador (elencos,
  campeonatos, uniformes, escudos, técnico, rostos). Os clubes e jogadores do próprio jogo mantêm os ids:
  os uniformes, rostos e os seus saves estão ligados a eles.
- **Manager portrait...**: um PNG ou JPG para o técnico do clube. O Build deixa em 256 x 256 e coloca
  em `common/render/symbol/coach/coach_<manager id>.png`, o lugar do próprio jogo para retratos de
  técnicos. Aperte de novo para tirar a imagem.

### 8.1 Rostos

Um mod de rosto é uma pasta assim (do jeito que quem faz rostos compartilha):

```
<any name>\
    #Win\face.fpk
    #Win\face.fpkd
    sourceimages\#windx11\*.ftex
    portrait.dds            (or <id>.dds, optional)
```

Escolha essa pasta para um jogador. No **Build** o rosto é copiado para o mundo e apontado para
o jogador, então funciona para um jogador novo cujo id não existia quando o rosto foi feito, e
nunca substitui um rosto do jogo. Sem retrato, a fotinho do jogador nos menus continua
sendo o contorno vazio; o rosto em si aparece mesmo assim. Uma pasta com mais de um rosto dentro é recusada: escolha o
rosto que você quer.

### 8.2 Montar, ligar, jogar

**Mantenha o Team.bin do próprio mundo.** Ele fica na pasta do mundo e guarda os clubes do mundo e os play-offs dele. Trocar ele pelo Team.bin do próprio jogo apaga os dois, e as escalações só parecem consertadas porque os clubes do mundo sumiram (GitHub #75). Faça o Build do mundo de novo no lugar.

**Build and install** (página Build, e na Home) faz o 0, o 2 e o 3 abaixo com um clique, depois mostra o que
falta fazer: uma janela **Build finished** que também pode **Move the Edit save aside** e **Close the
game**. Ou passo a passo, na página **Build**:

0. **Install the modules** — uma vez, e de novo depois de uma versão nova do programa. Os arquivos que ele
   substitui ficam guardados em `SiderAddons\modules\before-builder-1\`.
1. **Check the plan** — o que vai ser feito; nada é gravado.
2. **Build the world**.
3. **Switch it on** — torna ele o mundo ativo no `sider.ini`.
4. Inicie o jogo, volte e aperte **After a start: check**. Ele lê o `sider.log` e diz,
   módulo por módulo, se o mundo foi carregado.

**Include the Conference League** (na página Build, ligado por padrão) também monta a
Conference League: uma fase de liga de 36 clubes e um play-off em fevereiro, como as outras duas. A
Champions League e a Europa League ganham a fase de liga de 36 e o play-off de fevereiro
de qualquer jeito. Desligado: sem Conference League. (O Mod Studio 0.1.3 e anteriores deixavam a Champions League e a Europa
League nos grupos de quatro do jogo quando isso estava desligado, o que o mod não consegue rodar -- elas quebravam;
o Checks marca um mundo assim: monte ele de novo.) **Conference League logo** ao lado: sua própria imagem
para ela; vazio: é desenhado um emblema da UECL (o jogo não tem um para ela). **Conference League name**
embaixo: como o jogo chama ela, *FL Conference League* quando vazio (digite *UEFA Conference
League* se quiser); um nome novo exige montar o mundo de novo. Os dois também são usados por **Build only the
European cups...**.

> **Vagas europeias.** As vagas que você dá às suas ligas vêm depois das que as ligas do próprio jogo
> têm. Cada competição recebe 36 clubes; vagas além da 36ª não dão nada, e
> **Check the plan** avisa. Ligas novas sem vagas não mandam ninguém para a Europa, e a Home
> avisa sobre isso. Os campeões vêm primeiro: os campeões da Champions League e da Europa League
> pegam duas das vagas diretas da Champions League, o campeão da Conference League uma das da Europa
> League. O sorteio da fase de liga segue as regras da UEFA: nenhum clube enfrenta um clube do próprio
> país, e no máximo dois dos adversários vêm de um mesmo outro país.
>
> **As preliminares de agosto.** Uma vaga *qualifying* coloca o clube nas preliminares de agosto
> daquela competição: até três rodadas (0.1.7) -- a segunda fase preliminar (dias 220 e 225),
> a terceira (229 e 236) e o play-off (243 e 250; os da Champions League 244 e 251) --
> cada uma de 16 clubes em ida e volta, os oito elencos mais fortes como cabeças de chave (volta em casa), dois
> clubes de um mesmo país separados. Os vencedores vão para a próxima rodada, do play-off para a
> fase de liga. Os perdedores caem como os da UEFA: os perdedores do play-off da *Champions League qualifying* para a
> Europa League, os da terceira fase dela para o play-off da Europa League, os da segunda fase para a
> terceira fase da Europa League; *Europa League qualifying* do mesmo jeito para a Conference League;
> os perdedores da *Conference League qualifying* estão fora. As primeiras vagas listadas vão para o play-off,
> as seguintes para as rodadas anteriores. Quantas rodadas um mundo tem depende das vagas dele, e
> cada rodada da Conference League precisa de mais 8 clubes: 116 vagas na Europa só para os três
> play-offs, 132 para todas as nove rodadas. Com as vagas do próprio jogo são só os
> play-offs; o resumo do Build diz quais rodadas um mundo tem (*August qualifying*). Cada play-off
> tira 8 vagas dos que entram direto nas competições para onde vão seus vencedores e perdedores: com
> os três, a Champions League recebe 28 clubes direto, a Europa League e a Conference
> League 20 cada. Uma vaga além dessas é jogada nas preliminares daquela competição. As vagas de
> preliminar das suas ligas vêm antes das do jogo (Portugal, Escócia, Grécia, Dinamarca ...).

Depois **comece uma carreira nova da Master League** (ou Become a Legend). As ligas novas ficam embaixo do
país delas no Select Team e no Kick Off. Nas listas do Kick Off e do Edit um país asiático novo vem
antes de *Other Clubs (Asia)*, um sul-americano junto com os do jogo (depois da Colômbia, antes da MLS,
0.1.7), um da CONCACAF depois da MLS, e os africanos e da Oceania (o jogo
não tem seção para eles) depois da Ásia.

> **Copas de outros continentes.** Quando suas ligas mandam clubes para a CAF Champions League, a
> CAF Confederation Cup, a AFC Champions League Two, a AFC Challenge League, a Copa
> Sudamericana, a CONCACAF Champions Cup ou a OFC Champions League (as três últimas novas na
> 0.2.0), o **Build** monta essas copas também. Cada uma recebe 32, 16, 8 ou 4 clubes: as vagas das suas ligas
> primeiro, depois as próprias ligas do jogo daquele continente (Ásia, América do Sul, e a MLS para a
> da CONCACAF) completam; para a AFC Challenge League isso é do 11º ao 14º da J1 League, do 10º ao 13º da
> Chinese Super League e do 11º ao 14º da Saudi Pro League. Com 8
> ou mais ela joga grupos de quatro e depois um mata-mata; abaixo de 8, só mata-mata. A CONCACAF
> Champions Cup é sempre mata-mata, de no máximo 16 clubes, como a de verdade, e dois clubes de
> uma mesma liga não se enfrentam na primeira rodada quando dá para evitar. Elas são preenchidas no
> fim de agosto, a partir das tabelas das ligas. Um clube que já está na Copa Libertadores, na
> fase preliminar dela ou na AFC Champions League não é sorteado nelas. Uma copa da CAF ou da OFC com menos
> de 4 vagas pega primeiro as vagas da outra copa da CAF (com duas e duas, a CAF Champions
> League fica com as quatro), depois as próximas posições das suas ligas. **CAF Super Cup** (página
> Build, ligado por padrão) faz os campeões das duas copas da CAF se enfrentarem uma vez no fim de julho, a partir da
> segunda temporada de uma carreira.

> **Country cup draw** (página Build) decide como as copas nacionais das suas ligas são sorteadas.
> *Seeded* (o padrão): os clubes da primeira divisão ganham as folgas e as rodadas mais adiante, são espalhados
> por igual nas duas metades da chave, e enfrentam os clubes das ligas de baixo em vez de se enfrentarem
> nas primeiras rodadas. *Random*: um sorteio às cegas. *Off*: o jogo preenche a chave na ordem
> da lista, o que coloca todos os clubes grandes de um lado só. No arquivo do mundo é a linha
> `cupdraw seeded|random|off`; `cupdraw <cup regulation> seeded|random|off` define uma copa.

> **Saves pertencem a um mundo.** Uma carreira salva com um mundo ligado precisa desse mesmo mundo para carregar.

**File → Save recipe** guarda tudo num arquivo `.json`; **Open recipe** traz de volta.
O **Build** também guarda uma cópia da receita em `%APPDATA%\FL26ModStudio\recipes\<world>.json`,
e o Mod Studio abre a última receita de novo quando inicia, então fechar sem salvar não perde
nada que foi montado.

**Build only the European cups...** (página Build; *Only the European cups...* na Home) monta um mundo só com a nova
Champions League e a Europa League -- fase de liga de 36 e o play-off de fevereiro -- e a
Conference League quando **Include the Conference League** está marcado. Sem ligas novas; os clubes e ligas
do jogo ficam como estão, e sua receita não muda. Ele pede um nome de mundo
(`_FL26Euro` por padrão), monta e oferece ligar. Só um mundo pode estar ligado, então ele
substitui um mundo com ligas novas: um mundo com ligas novas já tem o formato novo.

> **Ligas de exibição e Master League.** Uma liga marcada como *Exhibition only* nunca joga uma
> temporada da Master League, mas o jogo tem uma lista de times só para Kick Off e Master League, então os
> clubes dela ainda aparecem quando você escolhe seu clube para uma carreira nova. Não comece uma carreira com um
> deles. **Check the plan** e **Build** avisam.

### 8.3 Limites

| | |
|---|---|
| Ligas novas por mundo | 39 |
| Clubes por liga | 10 – 24 |
| Clubes novos no total | 793 |
| Vezes que os clubes se enfrentam | 1 – 4 |
| Ligas divididas | 2 por mundo |
| Divisões num país | até a 7ª |
| Jogadores por clube novo | 30 no início; dá para remover até 18; jogadores contratados levam até 40 |
| Jogadores por seleção | 26 |
| Copa nacional | a primeira divisão e a de baixo, até 44 clubes. Até 32 os tamanhos são 2-16, 18, 20, 24, 28, 30 e 32 -- o maior que cabe (22 clubes dão uma copa de 20); de 33 a 43 vira 32; 44, ou um tamanho que uma copa do jogo tem, fica; mais de 44: só a primeira divisão |

### 8.4 NewLife Database: clubes e jogadores reais

O NewLife Database é um download separado com clubes e jogadores reais para ligas novas: nomes,
datas de nascimento, posições e notas na escala do jogo, e as cores dos clubes. Cada clube e
jogador nele tem um id próprio que continua o mesmo em todas as versões do banco de dados. Ele
não está no GitHub: pegue no canal do NewLife do nosso [Discord](https://discord.gg/StQqtk3G3M).
Ele vem em partes, uma por continente (um continente grande em mais de uma), mais *Free agents*, cada
uma com menos de 10 MB. Baixe só as partes que você quer.

1. Coloque as partes que você baixou numa pasta só. Não descompacte: o Mod Studio lê os zips como
   estão. (São zips LZMA: o 7-Zip abre, o visualizador de zip do próprio Windows não.)
2. **League Builder > NewLife Database > Open NewLife Database...** e escolha essa pasta. A lista
   mostra todas as ligas dessas partes: país, clubes, clubes que o jogo já tem (*In game*),
   jogadores e nível. Clique numa liga para ver os clubes dela. Clique no título de uma coluna (League, Country,
   Clubs, Players, Level) para ordenar por ela, de novo para inverter a ordem (0.2.0); a lista abre
   ordenada por país.
3. Selecione uma ou mais ligas (Ctrl ou Shift para mais) e aperte **Add to the recipe**. Cada
   uma vira uma liga nova com seus clubes e elencos, a primeira divisão do país dela. Mude
   a divisão, o formato, as vagas europeias e o resto em *Leagues*, como qualquer outra liga.
4. **Build**, ligue o mundo e comece uma carreira nova (seção 8.2).

- **Sua própria formação de clubes** (0.1.7): desmarque um clube na lista da direita para deixar ele de fora, e
  **Add a club from another league...** para trazer clubes de qualquer liga da versão -- a primeira divisão
  desta temporada é a da temporada passada com dois clubes que subiram, digamos. A linha da liga ganha um
  `*`. Um clube só pode estar em uma liga da receita.
- Uma liga aceita de 10 a 24 clubes, os novos e os do próprio jogo juntos; as outras ficam cinza. Uma liga do próprio jogo (a Premier League, o Championship ...) também fica cinza (0.1.9): ela já está no jogo, traga ela para a temporada do NewLife com **Bring the game's leagues to this season...** abaixo. A linha embaixo conta os clubes novos
  da receita contra os 793 que um mundo aceita.
- Clubes que o jogo já tem entram na liga nova como clubes do jogo (seção 8, *Clubes que o
  jogo já tem*), nos últimos lugares dela, com os próprios nomes, escudos, uniformes e jogadores. Um
  que também joga uma competição do jogo (Basel e Young Boys jogam a Europa League) precisa
  do clube que toma o lugar dele ali: *New clubs*, escolha ele, **Club of the game**. O Build diz
  quais até lá. Um clube cuja única competição do jogo é continental (o Ludogorets na
  fase preliminar da Champions League) continua jogando ela por conta própria (0.1.9).
- Um jogador que o jogo já tem (o mesmo jogador com o mesmo nome, o Urbański no Górnik no
  jogo e no Legia no NewLife, digamos) vai para o clube do NewLife em vez de ser criado uma
  segunda vez (0.1.7): ele mantém rosto, nome e id e pega a posição e as notas do NewLife.
  Ele fica onde está quando o clube antigo ficaria com menos de 18 jogadores, ou quando uma liga anterior
  já levou ele; aí ele fica de fora do clube do NewLife, não é copiado (0.1.8).
- Um clube do NewLife ganha um id de mundo próprio (0.1.8), no bloco que o jogo lê para clubes,
  contando a partir dos ids que o builder dá aos próprios clubes. A coluna **Team ID** em New clubs
  mostra ele, e o `map.txt` de um Kit Server usa ele como chave. Um mundo montado antes da 0.1.8 tem que ser
  montado de novo e a carreira começada do zero para os uniformes acompanharem. A partir da 0.1.8 um clube mantém o id
  do primeiro Build dele (a receita lembra): remover, adicionar ou atualizar outra liga
  não muda mais ele.
- **Uma versão mais nova do NewLife** (0.1.8): coloque as partes dela numa pasta (sem misturar com as antigas),
  **Open NewLife Database...** nessa pasta e aperte **Update my leagues to this version**. Cada
  liga que você adicionou de uma versão mais antiga é listada com o que muda (*16 clubs now, 18 in
  NewLife 1.3 (5 new, 3 not in it)*) e uma caixa **Keep my clubs**: marcada, a liga mantém os
  clubes; desmarcada, ela pega os clubes que tem na versão nova. De qualquer jeito os elencos vêm da
  versão nova, e a liga mantém nome, divisão, formato, vagas europeias e copas; um
  clube que fica mantém o técnico e um escudo que você escolheu, e clubes seus que você colocou na
  liga ficam. As habilidades, posições e o resto dos elencos vêm da versão nova; um rosto
  que você ligou ou um retrato que você escolheu em *Players* fica com um jogador que ainda está no clube
  (0.2.0, #111). Depois faça o Build e comece uma carreira nova.
- **As próprias ligas do jogo na temporada do NewLife** (0.1.8): com um NewLife Database aberto, aperte
  **Bring the game's leagues to this season...**. Cada liga do jogo que a versão tem é
  listada com o que acontece com ela, cada uma com uma caixa. Um clube que subiu ou desceu entre duas
  ligas do jogo troca de lugar com um que foi no sentido contrário (Burnley para o Championship,
  Coventry para a Premier League), como faz o *Swap leagues with a club...*. Um clube que caiu para fora
  das ligas do jogo (Leicester para a League One) vira o clube que subiu no lugar dele
  (Bolton): nome, nome curto, escudo e elenco; o uniforme, o estádio e o técnico ficam. Todo clube
  das ligas marcadas ganha o elenco do NewLife: jogadores que o jogo tem chegam do clube antigo,
  os que ele não tem são adicionados, o resto sai como agente livre. As notas são colocadas na
  escala do jogo, medida nos jogadores que os dois têm, então um craque fica onde o jogo avalia ele (0.2.0;
  antes, o topo ficava de 2 a 4 acima). As ligas mantêm a quantidade de
  clubes, o formato e as copas. Clubes que você já mudou na mão (uma troca, um nome novo, um
  clube de uma liga nova, mudanças de jogadores) ficam como estão. Fazer de novo com uma versão mais nova
  substitui o que a mais antiga fez; **Undo the game's leagues** desfaz tudo. Faça o Build e comece
  uma carreira nova.
- Um clube do NewLife ganha um escudo em forma de brasão nas cores dele e o uniforme do jogo mais parecido com as
  cores dele, até você dar um seu (**Edit club**).

## 9. Pacotes de ligas: compartilhe uma liga inteira

Um modder faz uma liga uma vez — clubes, nomes, escudos, logos, elencos, rostos — e compartilha **um
arquivo `.fl26pack`**. Qualquer um adiciona à própria receita e monta.

**Criar um pacote** (League packages → **Make a package...**, ou File → Make a league package):

1. Nome, autor, versão e uma descrição curta.
2. Marque as ligas que entram (**Select all** / **Select none** em cima da lista). Uma liga embaixo de
   outra liga nova tem que ir junto com ela.
3. Opcionalmente **also my changes to the game's own leagues, clubs and players** (também minhas mudanças nas ligas, clubes e jogadores do jogo).
4. **What goes in** (0.1.8): vem tudo marcado; desmarque o que você não quer compartilhar -- **Squads**,
   **Player faces and portraits**, **Crests and league logos**, **Managers**, **Kit colours**, **Home
   stadiums** (a linha do Stadium Server, não o estádio em si), e (0.2.1) **Kits** (os uniformes do
   Kit Server dos clubes) e **Scoreboards** (o placar do Scoreboard Server de cada liga). Uniformes e
   placares são pegos do seu jogo como o mundo está agora: o que o kit-server\map.txt e o
   scoreboard-server\map_competitions.txt dão aos clubes e ligas dele. Um pacote sem elencos vai por cima
   de um banco de elencos que é atualizado por conta própria, como o NewLife, sem trazer de volta elencos antigos.
5. Salve. O arquivo guarda as imagens, rostos, uniformes e placares, não caminhos do seu computador.
   Quem adicionar ele recebe os uniformes e placares no lugar com os próprios ids de time e liga quando
   fizer o Build (o Kit Server / Scoreboard Server tem que estar instalado). Uniformes somam uns 10 MB por liga e
   um placar uns 7 MB, então um pacote desses muitas vezes passa do limite de 10 MB do Discord: compartilhe por um
   serviço de nuvem (Google Drive, Dropbox, MEGA ...); o programa avisa quando o arquivo é maior.

**Adicionar um pacote** (League packages → **Add a package...**, File → Add a league package, ou
arraste para Install mods):

1. O programa mostra o que tem dentro e pergunta. Um pacote de várias ligas lista elas, todas marcadas:
   desmarque as que você não quer (0.2.1). Uma liga embaixo de outra liga do pacote traz essa
   outra junto. Em What to take você também pode desmarcar partes dele (placares, uniformes, escudos,
   rostos ...), por exemplo para pegar os placares de outro pacote.
2. Uma liga com um nome que você já tem: o programa pergunta, e adiciona como `Name (Package)` (não: nada é adicionado).
   Um pacote feito sem elencos vai para essa liga no lugar: os escudos e técnicos dele caem nos
   clubes de mesmo nome, seus jogadores ficam, e o programa diz quantos clubes encontrou.
   Um pacote que a receita já tem (mesmo nome) é substituído pela versão nova (0.1.7): as
   ligas, clubes e mudanças de jogadores do antigo saem, os novos entram.
3. **Save the recipe**, depois **Build**.

Os ids são distribuídos quando cada pessoa faz o Build, a partir do que o jogo dela tem, então um pacote funciona ao lado
de outros pacotes e ao lado das suas próprias ligas. **Remove from the recipe** tira um pacote
de novo, incluindo as mudanças que ele fez nos clubes do jogo.

Uma liga colocada embaixo de uma das ligas do jogo funciona para todo mundo com a mesma versão do jogo.

### 9.1 Exportar o mundo: um mundo pronto para outro PC

Um pacote exige que a outra pessoa faça o Build. Para entregar o mundo exatamente como você montou,
aperte **Export the world...** na página Build (depois de **2. Build the world**). Ele salva um
`.zip`:

- `SiderAddons\livecpk\<world>\...`: a pasta inteira do mundo, com o **arquivo do mundo**
  `fl26world.txt`. As linhas `newfaces` / `faceapp` nesse arquivo listam os jogadores novos que ganham um
  rosto gerado. Sem elas todo jogador novo fica com a mesma cara.
- `READ ME - FL26 world.txt` e `fl26worldpack.json`: o que quem recebe precisa.

**Quem recebe precisa dos módulos do Mod Studio com o pacote de rostos** (`modules\fl26regen_faces.bin`):
League Builder → Build → **0. Install the modules**, uma vez. Os rostos vêm desse pacote, então o
zip não leva eles.

Para instalar, arraste o zip para **Install mods** e aperte **Install**. O Mod Studio copia o mundo, coloca
o `fl26world.txt` em `SiderAddons\modules` (onde o `fl26regen` lê ele), oferece instalar os
módulos se o pacote de rostos estiver faltando, e liga o mundo. Depois comece uma carreira nova da Master
League. **Remove the mod** tira o mundo de novo e volta o arquivo do mundo anterior.

**Mudar um mundo instalado.** O `fl26worldpack.json` guarda só o nome do mundo e o que ele
precisa, não uma receita, mas a pasta do mundo leva o `leaguebuilder-plan.json`. Quando o Mod Studio
inicia com esse mundo ligado e as tabelas do jogo descompactadas, ele faz uma receita a partir desse
plano e abre ela, então quem recebeu pode mudar o mundo e montar de novo, nas próprias tabelas.
Fica perto do original, não igual: ligas, clubes, nomes, escudos, Europa, copas,
mudanças de jogadores e a Conference League voltam; copas de pré-temporada, copas dos países do
jogo, nomes de competições, as vagas europeias das ligas do jogo, a ordem das ligas e os
clubes europeus da primeira temporada não. Imagens e rostos apontam para o PC de quem mandou: o Build desenha um
distintivo para uma imagem que falta e diz qual.
O Mod Studio não instala por cima de um mundo de mesmo nome que foi montado naquele PC: renomeie ou
remova essa pasta antes.

## 10. Ferramentas

**Diagnostics — Run the checks** olha a configuração inteira: pastas de conteúdo que estão ligadas mas
faltando, módulos na ordem errada ou ligados duas vezes, linhas de mapeamento que apontam para o nada,
mundos do League Builder (só um deve estar ligado), e o último `sider.log`. **Copy a report**
coloca tudo na área de transferência para colar num post de fórum ou num relatório de bug.

**Restore points**: todo arquivo que o programa mudou, com a cópia de antes. **Put this copy
back** restaura ele. As cópias ficam em `SiderAddons\ModStudio\backups`. **Clean up...** remove as
antigas.

## 11. Quando algo dá errado

| O que você vê | O que fazer |
|---|---|
| *sider.ini not found* | Settings → Game folder: escolha a pasta com o `FL_2026.exe`. |
| *no game tables* | Settings → Unpack the game's tables. |
| Um mod não aparece no jogo | Diagnostics → Run the checks. Uma pasta de conteúdo mais alta na lista pode ter o mesmo arquivo. |
| O jogo não inicia depois de uma mudança | Restore points → volte o `sider.ini`, ou troque para um perfil que funcionava. |
| A liga nova não está no Select Team | Comece uma carreira *nova*; carreiras antigas mantêm as ligas antigas. |
| Os nomes dos clubes são os do jogo | Um arquivo Edit se sobrepõe a eles (seção 8). |
| *your leagues send nobody to Europe* | Leagues → escolha a primeira divisão → **Edit league...** → Europe (o botão **Top flight** preenche as três de sempre), depois Build de novo. |
| *the Conference League is on, but its tables are missing* | Faça o Build do mundo de novo: ele foi montado antes da opção, ou com ela desligada. |
| Um rosto não aparece | A pasta tem que ter `#Win\face.fpk`; faça o Build de novo depois de escolher ela. |
| Qualquer outra coisa | Diagnostics → **Copy a report**, e poste junto com o `SiderAddons\sider.log`. |
