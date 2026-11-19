---
name: fl26-construir-estadual
description: Use when building or porting Brazilian state divisions and a mixed-leg four-team knockout in an FL26 ModStudio world.
---

# Construir um estadual no FL26

## Objetivo e critério de aceite

Produzir um mundo novo com A1 de 12 clubes, A2 de oito, duas vagas de acesso e descenso e uma chave única para os quatro primeiros da A1. Comece pelo [guia da branch](../../../guides/estaduais-brasileiros.md).

## Supervisor (Codex)

Identifique o mundo ativo e a versão do FL e do Sider. Escolha como entrada o mundo anterior à inclusão dos estaduais. Registre o commit do gerador e copie a receita para um nome novo. Antes de trocar arquivos na instalação, preserve o mundo, os módulos e o INI com hashes e um caminho de reversão. Guarde saves de ensaio em slots separados. Registre documentação, backup e publicação conforme o pedido do dono do repositório.

## Executor (MiniMax Code)

1. Parta de `examples/estaduais/paulista.json` ou `dois-estados-ensaio.json`. Confira em Team.bin e CompetitionEntry.bin os IDs reais, a inscrição nacional e a exclusividade dos 20 clubes por estado. Reserve IDs e slots de menu livres para todas as receitas no mesmo mundo.
2. Declare revisão 7 e preencha 14 datas por ano. Os quatro primeiros da A1 são definidos após a 11ª rodada. A 12ª data serve as duas semifinais e as duas seguintes servem a decisão. Confronte datas continentais, nacionais e de seleções com a base do usuário.
3. Na raiz da branch, execute o comando de `tools/mkestaduais.py` do guia. Use uma saída inédita. Confira buildcheck, os descritores idênticos na raiz e em modules, e uma única linha ccup por chave com posições 1,4,2,3 oriundas da A1 correspondente. O cadastro final do estadual deve ter um único regulamento de mata-mata.
4. Para instalar, siga a lista de arquivos do guia com o FL26 fechado. Releia os hashes dos destinos e registre a revisão. A prova esportiva começa numa Liga Observadora nova. Passe a receita, o commit, o recibo e as datas à validação.
