---
name: fl26-validar-estadual
description: Use when validating state competition fixtures, promotion, a single bracket and reversed home legs from FL26 observer logs and saves.
---

# Validar o estadual em duas temporadas

## Objetivo e critério de aceite

Comprovar que o estadual roda, decide o campeão e se renova depois da virada. O resultado deve identificar a edição, datas, clubes, placares, mandos, modo de jogo e qual versão foi testada.

## Supervisor (Codex)

Confirme que o usuário abriu o mundo gerado pela receita. Guarde capturas, log da sessão e cópias com hash de cada slot. Decodifique as cópias. O visor do jogo confirma a árvore; a lista completa de partidas no save permite descobrir jogos sem data, invisíveis no log.

## Executor (MiniMax Code)

1. Crie ou acompanhe uma Liga Observadora nova. Salve ao fim do ano e novamente após a temporada seguinte em slots distintos. No menu Brasil, confira que a fase final mostra quatro clubes e abre uma única árvore, com dois resultados de semifinal e o campeão.
2. Rode `tools/check_estadual_calendar.py LOG RECEITA CODIGO ANO INICIO FIM` para cada ano. Os dois últimos argumentos são horários locais ISO do log da mesma carreira. Procure 66/66 na A1, 56/56 na A2 e 4/4 na chave. As vagas provisórias da final devem receber os vencedores; cada clube deve mandar uma perna.
3. Compare os dois saves com `tools/audit_estadual.py ANTERIOR/data.dat SEGUINTE/data.dat ANO REG_A1 REG_A2`. Se houver empate na linha de corte, confira a classificação do jogo. Para o mata-mata, a rodada 46 tem duas partidas únicas e a 53 tem ida e volta. Leia os gols em cada save e confira o agregado com a captura.
4. Se a árvore estiver vazia, preserve a temporada antes de mudar a instalação. O caso R6 continha quatro semifinais sem data no save e duas vagas de final no log. Registre as diferenças, o que foi observado em cada modo e o backup da versão antes de propor outra revisão.

[Guia, exemplos e comandos completos](../../../guides/estaduais-brasileiros.md)
