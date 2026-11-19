# Estaduais brasileiros no FL26

O mesmo clube pode disputar seu estadual e uma das divisões nacionais com o mesmo elenco. A receita cria uma inscrição adicional em `CompetitionEntry.bin` para cada clube, duas divisões com vínculo próprio de acesso e descenso e uma competição brasileira de mata-mata. O Paulista foi o piloto no FL26 v1. O gerador desta branch permite declarar vários estados no mesmo mundo.

## Chave única da revisão 7

As receitas desta branch declaram `"revision": 7`. Uma receita antiga, sem essa chave, reproduz o formato de duas etapas da revisão 5. A atualização requer um mundo gerado em uma pasta nova e uma Liga Observadora nova. Para repetir uma instalação anterior, preserve a receita, o commit, os módulos ativos e os saves daquela versão.

No FL26 v1 o mata-mata doméstico de quatro clubes usa **rodada 46** para os dois jogos de abertura e **53** para a decisão. Usar 52 nas semifinais deixou quatro partidas sem data no slot da R6. A R7 classifica os quatro primeiros da A1, cruza 1º × 4º e 2º × 3º, e gera uma única árvore. O regulamento da chave contém a semifinal simples e as duas pernas da decisão. A propriedade `cal=1` conserva a chave até dezembro, e `startyear=1` registra as duas divisões em janeiro.

| Piloto no modo Liga | Semifinais | Ida | Volta | Campeão |
|---|---|---|---|---|
| 2025 | 22/03, São Paulo 3–0 Corinthians e Palmeiras 4–3 Bragantino | São Paulo 1–4 Palmeiras | Palmeiras 3–0 São Paulo | Palmeiras, 7–1 |
| 2026 | 21/03, Palmeiras 1–0 Corinthians e Santos 4–0 Bragantino | Palmeiras 1–1 Santos | Santos 0–1 Palmeiras | Palmeiras, 2–1 |

O log e os slots 8 e 9 mostraram quatro partidas disputadas em três datas por edição. No calendário, a A1 teve 66 partidas e a A2 teve 56 em cada temporada. A validação visual pertence ao piloto paulista instalado. O porte sobre a fonte desta branch foi compilado com um estado e dois estados e precisa de teste no jogo de destino. A coordenação das datas de Copa do Brasil, Brasileiro e torneios continentais depende do mundo-base. [Evidências do laboratório](https://github.com/will-serrano/rea/blob/docs/pes21-mapa/research/pes21-modstudio/grade-paulista/VALIDACAO_R7_LIGA_2025_2026.md)

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
3. Reserve três `cids`, na ordem A1, A2, mata-mata, e quatro `regulations`, na ordem A1, A2, semifinal, final. Para as ligas, escolha regulamentos com slots livres em `fl26world.DEFAULT_SLOT`. O gerador usa o terceiro ID e suas réplicas como intermediários. Na saída R7 o quarto ID contém todo o mata-mata. O mundo e os módulos de capacidades do seu patch precisam suportar os IDs e slots selecionados. A capacidade das tabelas limita o número de estaduais simultâneos.
4. Em `calendar`, cada ano tem 14 dias em ordem crescente. O ordinal 0 representa 1º de janeiro no ano de 365 dias do motor. A A1 usa as primeiras 11 datas, seguida de semifinal única (1º × 4º, 2º × 3º) e final em ida e volta. A A2 usa as 14 datas. Estados distintos compartilham essas datas. Para uma temporada adicional, acrescente sua grade depois de confrontá-la com o calendário do patch. Informe anos consecutivos. Após o último ano, a R7 projeta os dias da semana da grade mais recente. Confira os conflitos com o calendário do destino.
5. Gere o mundo e confira os jogos do clube que disputa mais competições. A ausência de conflito no Paulista de uma carreira não comprova a grade de outro estado com outros participantes na Libertadores ou na Sul-Americana.

O gerador usa Brasil (região 16, país 146, confederação 4), preserva os cabeçalhos existentes e agrupa A1, A2 e mata-mata na categoria da Série A nacional. As duas semifinais e a decisão compartilham o CID do mata-mata. O vínculo na base e no descritor estabelece duas promoções e dois descensos. O módulo aplica a grade ao encontrar o vínculo entre os regulamentos declarados e abre a chave após a última rodada da A1. [Rotinas estaduais](../tools/native/estadual_r7.inc)

## Ativar no ambiente de ensaio e conferir

Use o Sider de uma instalação de teste compatível com os módulos desta versão do ModStudio. Feche o FL26 e preserve o mundo ativo, `sider.ini`, `modules/fl26world.txt`, `fl26regions.lua`, `fl26regnames.lua`, `fl26swiss.dll`, `fl26joindll.lua` e `fl26join.dll`, com SHA-256. Coloque a saída em `SiderAddons/livecpk/<nome da saída>`, selecione esse mundo na entrada `cpk.root` que ativava a base e copie da pasta `modules` da saída esses seis arquivos para `SiderAddons/modules`. Confira seus hashes nos destinos. O mundo-base já deve ter os carregadores Sider do ModStudio ativos. Para reverter, restaure a entrada e os seis arquivos do backup.

Crie uma carreira nova. Na ML e na Liga, registre a abertura, a decisão estadual, o fim do ano e a próxima temporada em slots separados. O time observador sem partidas próprias agiliza a simulação. Confira a tabela final, os participantes das duas divisões seguintes, as partidas da decisão e o calendário nacional do mesmo clube. Uma convocação ou abertura de transferências no calendário é um evento diferente de uma partida; valide conflitos pelas referências reais de jogo.

Em cópias dos slots já decodificadas no layout expandido do FL26, rode:

```powershell
py -3 tools/audit_estadual.py 'D:\ensaio\fim2025\decoded\data.dat' 'D:\ensaio\fim2026\decoded\data.dat' 2025 181 182
```

O auditor informa IDs promovidos e rebaixados, contagens e pontos por clube e hashes dos dois arquivos. Exige as divisões completas para confirmar a troca, sinaliza empate na linha de corte e reconhece amostras incompletas. Use dois slots da mesma carreira. No piloto, os slots da Liga produziram `confirmed` e os da ML produziram `insufficient_evidence`. [Auditor](../tools/audit_estadual.py)

## Auditar a temporada

Com as triggers do laboratório ativas desde o início da Liga, recorte o intervalo de relógio de uma carreira completa. O auditor exige os jogos das duas divisões, quatro semifinalistas, um vencedor de cada par na decisão, partidas disputadas e inversão dos mandos. Para conferir placares e quem venceu os confrontos, compare a tela e as cópias decodificadas dos saves. [Auditor do calendário](../tools/check_estadual_calendar.py)

```powershell
py -3 tools/check_estadual_calendar.py sessao.tsv examples/estaduais/paulista.json SP 2026 2026-11-19T10:02:47 2026-11-19T10:07:00
```

O ensaio com um estado gerou 97 competições, 222 regulamentos e 1.347 inscrições. Com dois, gerou 100, 225 e 1.367. A segunda chave tem regulamento 202 e usa a classificação da A1 de teste, regulamento 254. Refaça o ensaio em uma pasta nova ao mudar a receita. [Receita de dois estados](../examples/estaduais/dois-estados-ensaio.json)

As skills [construir estadual](../.agents/skills/fl26-construir-estadual/SKILL.md) e [validar estadual](../.agents/skills/fl26-validar-estadual/SKILL.md) acompanham esta branch. O laboratório mantém também o [procedimento do mundo observador](https://github.com/will-serrano/rea/blob/docs/pes21-mapa/.agents/skills/fl26-mundo-observador/SKILL.md).
