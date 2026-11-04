# FL Mod Studio 0.3.0 — início rápido (FL26 e FL27)

> [English](../en/quick-start-0.3.0.md) · [hrvatski](../hr/quick-start-0.3.0.md) · [español](../es/quick-start-0.3.0.md) · **português** · [français](../fr/quick-start-0.3.0.md)

Tudo o que você precisa para começar com a 0.3.0, em ordem. Cada página e opção em detalhe está no
[guia de uso](mod-studio-guide.md); um mundo pronto ou um zip de Modpack está em [Instalar um pacote pronto](install-a-pack.md).

> [!WARNING]
> **A 0.3.0 é mais uma versão de teste.** Se a 0.2.5.1 funciona para você e você não precisa do
> FL27, não tem pressa: fique nela até a 0.3.0 ser jogada por um tempo. Se você está numa carreira
> longa, guarde uma cópia da sua pasta de saves e da sua pasta antiga do Mod Studio antes de
> atualizar.

## 1. Pegue a 0.3.0

**Você tem a 0.2.5.1:** **Ajuda → Procurar atualizações...** → **Baixar e instalar**. Ou feche o
Mod Studio e descompacte `FL26ModStudio-0.3.0.zip` por cima da pasta antiga (substituir tudo).
Suas configurações, mundos e receitas continuam.

**Primeira vez:** baixe `FL26ModStudio-0.3.0.zip` da
[última versão](https://github.com/Matozanato/FootballLife-new-leagues/releases/latest),
descompacte numa pasta só dele (deixe `_internal` e `pack` junto do exe) e rode
`FL26ModStudio.exe`. Se o Windows disser "O Windows protegeu o computador": **Mais informações** →
**Executar assim mesmo**.

A janela agora diz **FL Mod Studio**: é o mesmo programa, com outro nome porque funciona com o
FL27 também. O exe, a pasta do zip e `%APPDATA%\FL26ModStudio` continuam com os mesmos nomes.

## 2. Escolha o jogo: FL26 ou FL27

1. **5. Configurações → Pasta do jogo → Procurar...** → a pasta com `FL_2026.exe` (FL26) ou
   `FL_2027.exe` (FL27) → **Usar esta pasta**.
2. Na primeira vez que você escolhe um jogo, o Mod Studio descompacta as tabelas desse jogo (um
   ou dois minutos; a barra de baixo avisa). O FL26 e o FL27 têm as próprias tabelas e os próprios
   saves, então você pode trocar de um para o outro: escolha a pasta do outro jogo do mesmo jeito.
3. **1. Início**: quando a verificação geral disser que os módulos estão faltando ou são mais
   antigos, aperte **Instalar agora**.

## 3. Seu mundo da 0.2.5.1 (FL26)

Seus mundos continuam funcionando. Depois de atualizar:

1. **1. Início → Instalar agora** (os módulos da 0.3.0).
2. **2. Meu mundo → Construir e instalar** uma vez.
3. Carregue sua carreira e continue jogando. Algumas correções só aparecem numa Master League
   nova: o dinheiro para transferências dos clubes pequenos, os elencos do NewLife e as ligas nos
   lugares 76, 77 e 80 do Select Team.

## 4. Clubes reais: NewLife Database 1.6b4

Baixe o NewLife 1.6b4 no canal **#newlife** do nosso [Discord](https://discord.gg/StQqtk3G3M).
**No FL27 use a 1.6b4** (ou a 1.6b3): as versões mais antigas foram feitas para os clubes do FL26.

1. Coloque as partes (`NewLife-1.6b4-Europe.zip` ...) numa pasta nova, sem misturar com as mais
   antigas. Não descompacte as partes.
2. **2. Meu mundo → NewLife Database → Abrir NewLife Database...** → essa pasta.
3. **Ligas novas:** selecione uma ou mais → **Adicionar ao seu mundo**. Uma liga de um país em que
   o jogo já tem uma liga (Greek Super League 2, Scottish Championship ...) entra como a divisão
   embaixo da liga do jogo, com acesso e rebaixamento; a página diz qual.
4. **Ligas que você adicionou de um NewLife mais antigo:** **Mais → Atualizar meus campeonatos para
   esta versão**.
5. **As ligas do próprio jogo** ficam como o jogo tem. **Mais → Levar os campeonatos do jogo para
   esta temporada...** leva os clubes e elencos delas para a temporada do NewLife, se você quiser.
   Marque **Só os jogadores do jogo** para ter só as transferências e os overalls, sem jogadores
   novos.
6. **Construir e instalar**, depois comece uma Master League **nova**: um save antigo não pega os
   elencos novos.

## 5. Monte seu próprio mundo

O caminho completo, clique a clique: [Criar suas próprias ligas e pacotes](make-your-own-leagues.md).
Resumindo:

1. **2. Meu mundo → Campeonatos**: adicione uma liga (ou ligas do NewLife, passo 4), defina o país,
   os clubes, a **Divisão**, as vagas europeias e as copas com **Editar campeonato...**.
2. **Divisão** agora também pode ser uma das ligas divididas do jogo (Scottish Premiership, 3F
   Superliga, Jupiler Pro League): sua liga fica embaixo dela, com acesso e rebaixamento.
3. **Construir e instalar**, depois uma Master League nova.

## 6. Jogue

- **Iniciar o jogo** (no alto à direita) inicia o jogo com tudo no lugar.
- **FL27: sempre inicie pelo launcher dele** (**FL 2027 start.exe**, o atalho dele, ou **Iniciar o
  jogo** no Mod Studio). O FL_2027.exe iniciado sozinho pode fechar enquanto uma Master League nova
  é criada ou nos primeiros dias dela.
- No FL27 a Champions League e a Europa League são as do próprio FL27; o Mod Studio decide quem
  entra a partir das suas ligas e joga as eliminatórias de verão; a Conference League é do Mod
  Studio.

## 7. Novidades da 0.3.0, e onde achar

| O quê | Onde |
|---|---|
| Suporte ao FL27 | **5. Configurações → Pasta do jogo** |
| Os clubes de uma liga (com escudos) no Select Team | no jogo: Team Info, League mode ... com o cursor numa liga |
| Vagas coloridas nas tabelas das ligas (Champions League, Europa League, Conference League, acesso, play-off, rebaixamento) | no jogo, depois de **Construir e instalar** |
| Uma liga no lugar de um dos grupos "Other ..." do jogo no Select Team | **2. Meu mundo → Campeonatos → Lugares em Select Team** (cada liga: *Automático* ou *no lugar de* um grupo), depois Build |
| Uma liga embaixo das ligas divididas do jogo | **Campeonatos → Editar campeonato... → Divisão** |
| Liga do NewLife embaixo da liga do jogo do país dela | automático em **Adicionar ao seu mundo**; mude em **Divisão** |
| Ligas de janeiro a dezembro de um país novo: acesso e rebaixamento no Ano Novo, e a copa delas | automático depois do Build |

## 8. Algo deu errado?

1. **4. Ferramentas → Diagnóstico → Rodar as verificações → Copiar um relatório.**
2. Poste no **#support** do [Discord](https://discord.gg/StQqtk3G3M) (um tópico por problema) com
   um print da tela e `SiderAddons\sider.log` (o menu **Jogo** abre ele).

Conhecido na 0.3.0: [changelog](../../docs/changelog/changelog-0.3.0.md#known) ·
perguntas comuns: [FAQ](../../docs/faq.md)
