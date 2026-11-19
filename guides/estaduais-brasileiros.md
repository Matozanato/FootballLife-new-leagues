# Estaduais brasileiros no FL26

O mesmo clube pode disputar seu estadual e uma das divisões nacionais com o mesmo elenco. A receita cria uma inscrição adicional em `CompetitionEntry.bin` para cada clube, duas divisões com vínculo próprio de acesso e descenso e uma competição brasileira de mata-mata. O Paulista foi o piloto no FL26 v1. O gerador desta branch permite declarar vários estados no mesmo mundo.

## O que funcionou no jogo

| Medida | Evidência do piloto |
|---|---|
| Paulista A1 | 12 clubes em turno único, 11 rodadas, 66 jogos. |
| Paulista A2 | 8 clubes em ida e volta, 14 rodadas, 56 jogos. |
| Acesso e descenso | Na Liga observadora, os 122 jogos de 2025 foram disputados. REA 08 (25 pontos) e REA 07 (22) subiram. REA 02 (3) e REA 01 (1) caíram. A composição das divisões em 2026 confirmou exatamente essas quatro mudanças. |
| Independência do Brasileiro | Em 2026 o REA 07 disputou Paulista A1 e Série B nacional. O REA 08 disputou Paulista A1 e Série C nacional. |
| Mata-mata na Master Liga | Na revisão 2 houve dois jogos sem participantes além da decisão válida e uma lista provisória de 20 clubes. Na revisão 3, o slot de janeiro tinha zero partidas da final. Em junho havia duas: São Paulo × Palmeiras em 29/03 e Palmeiras × São Paulo em 06/04. |
| Calendário | O piloto usou seis grades de 2025 a 2030. Amistosos, eliminatórias, Copa América, Copa do Mundo e Libertadores entram na análise pelas datas disponíveis no FL. A Sul-Americana ativa ficou fora da amostra. |

**Pendências observadas.** No modo Liga, a telemetria confirmou duas semifinais e dois jogos da decisão em 2025 e 2026. Em julho as referências saíram da agenda ou foram reutilizadas pelo motor; os slots de dezembro já não exibiam esses jogos. Na ML os slots terminam em 13/06/2025, antes da virada. Nos registros estaduais da Liga de 31/12/2026, 30 partidas da A1 estão datadas de 2026 e 36 de 2027, e na A2 a divisão é 32 e 24. A segunda troca de temporada continua aberta. Na Copa do Brasil do piloto a decisão foi disputada duas vezes no mesmo sábado em 2025 e 2026 (94 partidas, contra 93 previstas). O gerador cuida das competições estaduais; a coordenação das datas nacionais e continentais continua a cargo do mundo-base.

## Gerar um mundo de teste

Use um mundo FL26 já funcional com `fl26world.txt`, `common/etc/pesdb` e os clubes inscritos no Brasileiro. O exemplo reproduz os IDs do **mundo observador REA com Série C**. Para outra base, confira os IDs no seu próprio banco. A receita cita 12 equipes de teste da Série C. Seus IDs e elencos pertencem àquela base.

São necessários o Python 3 com as dependências usuais das ferramentas do ModStudio, o executável local do FL26 para os geradores de categoria e um Zig com o alvo Windows x86-64. A pasta pai da saída deve existir. Exemplo em PowerShell a partir da raiz desta branch:

```powershell
$env:FL26_EXE = 'D:\Program Files (x86)\SP Football Life 2026\FL_2026.exe'
$base = 'D:\Program Files (x86)\SP Football Life 2026\SiderAddons\livecpk\_FL26REAObservador'
py -3 tools/mkestaduais.py --base $base --out 'D:\ensaios\_EstaduaisBrasil' --recipe examples/estaduais/paulista.json --zig 'D:\tools\zig\zig.exe'
```

O processo trabalha numa cópia temporária, relê as três tabelas, verifica que seus registros originais permanecem como prefixo, roda o `buildcheck` e compila a DLL específica da receita. A pasta de saída aparece após a conclusão. Para refazer, use outro destino. [Gerador](../tools/mkestaduais.py) · [Receita paulista](../examples/estaduais/paulista.json)

## Acrescentar outro estado

1. Na lista `states`, duplique o objeto do Paulista. Escolha `name` para o menu e um `code` exclusivo, como `RJ` ou `MG`. Construa todos os estaduais desejados juntos a partir do mundo anterior aos estaduais. A DLL e o descritor devem representar a mesma lista de estados.
2. Preencha `a1` e `a2` com 12 e 8 IDs de clubes distintos. Em `national_cids`, indique os CIDs das divisões nacionais do seu patch. O gerador exige que o clube exista em Team.bin e tenha exatamente uma inscrição nessas competições. Um clube pode competir em ambas as pirâmides, mas só em um estadual.
3. Reserve três `cids`, na ordem A1, A2, mata-mata, e quatro `regulations`, na ordem A1, A2, semifinal, final. Para as ligas, escolha regulamentos com slots livres em `fl26world.DEFAULT_SLOT`. A semifinal usa também os IDs `semi+1024` e `semi+2048`. O mundo e os módulos de capacidades do seu patch precisam suportar os IDs e slots selecionados. A capacidade das tabelas limita o número de estaduais simultâneos.
4. Em `calendar`, cada ano tem 14 dias em ordem crescente. O ordinal 0 representa 1º de janeiro no ano de 365 dias do motor. A A1 usa as primeiras 11 datas, seguida de semifinal única (1º × 4º, 2º × 3º) e final em ida e volta. A A2 usa as 14 datas. Estados distintos compartilham essas datas. Para uma temporada adicional, acrescente sua grade depois de confrontá-la com o calendário do patch. Fora dos anos informados, o módulo deixa o agendamento de partidas ao ModStudio.
5. Gere o mundo e confira os jogos do clube que disputa mais competições. A ausência de conflito no Paulista de uma carreira não comprova a grade de outro estado com outros participantes na Libertadores ou na Sul-Americana.

O gerador usa Brasil (região 16, país 146, confederação 4), preserva os cabeçalhos existentes e agrupa A1, A2 e mata-mata na categoria da Série A nacional. As duas semifinais e a decisão compartilham o CID do mata-mata. O vínculo na base e no descritor estabelece duas promoções e dois descensos. O módulo aplica a grade ao encontrar o vínculo entre os regulamentos declarados e libera a decisão quando há dois vencedores. [Rotinas estaduais](../tools/native/estadual.inc)

## Ativar no ambiente de ensaio e conferir

Use o Sider de uma instalação de teste compatível com os módulos desta versão do ModStudio. Feche o FL26 e preserve o mundo ativo, `sider.ini`, `modules/fl26world.txt`, `fl26regions.lua`, `fl26regnames.lua`, `fl26swiss.dll`, `fl26joindll.lua` e `fl26join.dll`, com SHA-256. Coloque a saída em `SiderAddons/livecpk/<nome da saída>`, selecione esse mundo na entrada `cpk.root` que ativava a base e copie da pasta `modules` da saída esses seis arquivos para `SiderAddons/modules`. Confira seus hashes nos destinos. O mundo-base já deve ter os carregadores Sider do ModStudio ativos. Para reverter, restaure a entrada e os seis arquivos do backup.

Crie uma carreira nova. Na ML e na Liga, registre a abertura, a decisão estadual, o fim do ano e a próxima temporada em slots separados. O time observador sem partidas próprias agiliza a simulação. Confira a tabela final, os participantes das duas divisões seguintes, as partidas da decisão e o calendário nacional do mesmo clube. Uma convocação ou abertura de transferências no calendário é um evento diferente de uma partida; valide conflitos pelas referências reais de jogo.

Em cópias dos slots já decodificadas no layout expandido do FL26, rode:

```powershell
py -3 tools/audit_estadual.py 'D:\ensaio\fim2025\decoded\data.dat' 'D:\ensaio\fim2026\decoded\data.dat' 2025 181 182
```

O auditor informa IDs promovidos e rebaixados, contagens e pontos por clube e hashes dos dois arquivos. Exige as divisões completas para confirmar a troca, sinaliza empate na linha de corte e reconhece amostras incompletas. Use dois slots da mesma carreira. No piloto, os slots da Liga produziram `confirmed` e os da ML produziram `insufficient_evidence`. [Auditor](../tools/audit_estadual.py)

## Alcance da branch

O segundo ensaio acrescentou um estado fictício com os CIDs 135, 136 e 142 e os regulamentos 254, 253, 201 e 202. Ele serve para testar o isolamento entre competições. A escolha dos 20 clubes desse segundo estado foi técnica. O primeiro build produziu 97 competições, 225 regulamentos e 1.347 inscrições; o segundo, 100, 231 e 1.367, respectivamente. Em ambos foram conferidos a ordem dos participantes nas inscrições, os vínculos entre divisões, a categoria Brasil e as exportações da DLL. As tabelas dos clubes, jogadores e vínculos de elenco permaneceram idênticas às da origem. [Receita do ensaio duplo](../examples/estaduais/dois-estados-ensaio.json)

A construção foi exercitada no mundo observador com um estadual e com dois estaduais simultâneos (40 clubes distintos no segundo ensaio). A prova esportiva em jogo vem do Paulista instalado pelo laboratório. Outros estados, a nova compilação contra a base desta branch e uma instalação FL27 requerem validação própria no jogo. Os clubes, saves, executáveis de jogo e DLLs compiladas são insumos ou produtos locais da receita.

## Registro das rodadas na virada

A telemetria do piloto de 2026 mostrou a primeira geração das rodadas em 29/01. O módulo havia recusado as divisões estaduais no construtor brasileiro de 01/01. Seis rodadas de cada divisão apareceram datadas do janeiro seguinte. Em 2025, todas as partidas tinham sido disputadas nas datas corretas.

A receita agora declara `startyear=1` nas duas divisões de cada estado. Quando o FL26 monta sua lista anual com os regulamentos 29 e 163, a biblioteca inclui os estaduais marcados. O ingresso de uma divisão com participantes definidos usa a mesma chamada do construtor brasileiro. Inscrições já ativas com rodadas válidas são preservadas. O gerador compila e distribui também o carregador e a biblioteca de registro. A execução no jogo deve ser conferida a partir de um slot anterior à virada.

Para auditar, recorte no log REA apenas o intervalo de relógio da simulação de uma carreira completa. O script verifica os jogos disputados de cada fase nas datas previstas e conta partidas empurradas para outro ano. [Auditor da grade](../tools/check_estadual_calendar.py)

```powershell
py -3 tools/check_estadual_calendar.py sessao.tsv examples/estaduais/paulista.json SP 2026 2026-11-18T22:40:50 2026-11-18T22:41:49
```

### Resultado no jogo e conservação da chave

A Liga observadora com o registro anual disputou, em **2025 e 2026**, os 66 pares distintos da A1 em turno único e os 56 confrontos da A2 em ida e volta. As duas semifinais e os dois jogos da final também foram disputados a cada ano. Nenhuma rodada ficou marcada para janeiro do ano seguinte. Em 2026 a decisão foi Corinthians × São Paulo, em 28/03 e 04/04. A verificação cruzou o marcador de partida disputada, os pares de clubes, as datas e os mandos na sessão 50360.

Na tela **Selecionar competição → Paulista A1 - Fase final**, o painel **Times participantes** ainda estava vazio em dezembro de 2026. Na revisão anterior o regulamento da final usava o encerramento padrão em julho. O descritor da chave agora inclui `cal=1`: a biblioteca conserva a copa no encerramento de julho e inclui final, semifinal e réplicas no encerramento do ano brasileiro. A grade e os classificados continuam definidos pela receita estadual. A aceitação visual exige abrir essa tela depois de julho em uma temporada simulada com o novo descritor. Um save gravado depois da limpeza antiga já perdeu esses registros.
