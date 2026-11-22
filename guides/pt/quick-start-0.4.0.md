# FL Mod Studio 0.4.0 — início rápido (FL26 e FL27)

> [English](../en/quick-start-0.4.0.md) · [hrvatski](../hr/quick-start-0.4.0.md) · [español](../es/quick-start-0.4.0.md) · **português** · [français](../fr/quick-start-0.4.0.md)

Tudo o que você precisa para começar com a 0.4.0, em ordem. Cada página e opção em detalhe está no
[guia de uso](mod-studio-guide.md); um zip de mundo pronto está em [Instalar um pacote pronto](install-a-pack.md).
Vem da 0.2.5.1 ou anterior? Leia também o [início rápido da 0.3.0](quick-start-0.3.0.md).

## 1. Antes de atualizar

- **Guarde uma cópia da sua pasta de saves e da sua pasta antiga do Mod Studio**, como sempre.
- **Depois de atualizar, instale os módulos de novo: 1. Início → Instalar agora.** Muitas
  correções estão nos nossos módulos dentro do jogo.
- **Uma carreira em andamento fica com o que o save dela tem.** Os campeonatos, copas e clubes
  novos de um mundo atualizado chegam só numa Master League nova. A sua carreira continua com os
  campeonatos que tem.
- **Licença nova.** Desde a 0.4.0 o Mod Studio está sob a FL Mod Studio License (`LICENSE.txt` no
  zip). Continua livre para usar, mudar e compartilhar. Vender e tirar a marca "Powered by FL
  ModStudio" não é permitido. A 0.3.0 e as anteriores continuam sob a licença MIT.

## 2. Pegue a 0.4.0

**Você tem a 0.3.0:** **Ajuda → Procurar atualizações...** → **Baixar e instalar**. O Mod Studio
fecha, coloca os arquivos novos na pasta dele e abre de novo.

**Primeira vez, ou na mão:** baixe `FL26ModStudio-0.4.0.zip` da
[última versão](https://github.com/Matozanato/FootballLife-new-leagues/releases/latest) e
descompacte numa pasta só dele (por exemplo `Documents\FL26 Mod Studio`). Não rode de dentro do
zip, e deixe `_internal` e `pack` junto do `FL26ModStudio.exe`. Clique duas vezes em
`FL26ModStudio.exe`. Se o Windows disser "O Windows protegeu o computador": **Mais informações** →
**Executar assim mesmo**. Suas configurações, mundos e receitas estão em `%APPDATA%\FL26ModStudio`,
então continuam.

**Escolha o jogo:** **5. Configurações → Procurar...** → a pasta com `FL_2026.exe` (FL26) ou
`FL_2027.exe` (FL27), não `SiderAddons` → **Usar esta pasta**. Na primeira vez o Mod Studio
descompacta as tabelas do jogo: um ou dois minutos, espere.

## 3. Seu mundo da 0.3.0

1. **1. Início → Instalar agora** (os módulos da 0.4.0).
2. Um mundo que você mesmo constrói: **2. Meu mundo → Construir e instalar** uma vez. Muitas
   correções da 0.4.0 precisam de um Build novo.
3. Carregue a sua carreira e continue jogando. Campeonatos, copas e clubes novos chegam só numa
   Master League nova.

Um mundo pronto de um zip (GigaPack, um Modpack) não precisa de Build. Quando o autor dele te der
uma versão nova, instale o zip novo do mesmo jeito que da primeira vez (seção 4).

## 4. GigaPack (Football Life 2027)

GigaPack by MatoZanato 1.0 é um mundo pronto para o **Football Life 2027**: 317 ligas e 5.239
clubes, num zip só, instalado pelo Mod Studio, sem Build. Downloads, md5, o que ele ainda não faz e
os problemas conhecidos: [GigaPack](../../docs/gigapack.md) (em inglês).

Em resumo (você precisa do FL27 com a **atualização 1.1**; feche antes o jogo e o launcher dele):

1. Mod Studio 0.4.0, e a pasta do jogo com `FL_2027.exe` (seção 2).
2. Não descompacte o GigaPack. **1. Início → Importar um zip de mundo** → escolha
   `GigaPack-1.0.zip` → **Instalar o mundo**. Espere **Pronto para jogar**. Se disser **Quase
   pronto**, ele lista o que corrigir.
3. O botão verde **Iniciar o jogo** no Mod Studio (ou o launcher do FL27, não o `FL_2027.exe`
   direto) → **Master League** → **New game**. Só uma Master League nova recebe as ligas novas.

## 5. Novidades da 0.4.0, e onde encontrar

| O quê | Onde |
|---|---|
| GigaPack 1.0, um mundo pronto de 317 ligas para o FL27 | [GigaPack](../../docs/gigapack.md) (seção 4) |
| Um zip de mundo entra de uma vez | **2. Meu mundo → + Adicionar... → Escolher um arquivo...** → o zip → **Instalar o mundo** |
| Importe seu mundo diz se um zip é uma versão mais nova, mais antiga ou a mesma do seu mundo | **1. Início → Importar um zip de mundo** |
| Uma atualização de um mundo que você compartilha mantém as carreiras dos jogadores dele: a exportação pede uma versão | **Exportar...** no cartão do mundo em **2. Meu mundo**; FAQ (em inglês): [Updating a shared world without breaking careers](../../docs/faq.md#updating-a-shared-world-without-breaking-careers) |
| Uma aba para as copas: copas nacionais e competições continentais | **2. Meu mundo → Copas**: **Game Countries**, **Our Countries**, **Continental**. **Aplicar**, depois **Construir e instalar** |
| Troféus, também no FL27 (no FL27 ainda não verificado no jogo) | **3. Conteúdo do jogo → Troféus** |
| Uma terceira copa para as divisões de baixo (FL27) | **Campeonatos → Editar campeonato... → Terceira copa (como o EFL Trophy)**, suas próprias datas em **Datas das copas** |
| Campeonatos de até 32 clubes (de 29 a 32 se enfrentam uma vez); o FL27 aceita também 8 e 9. Ainda não jogados por uma temporada inteira no jogo | **Campeonatos → Editar campeonato... → Clubes** |
| A sua própria ordem dos clubes de um campeonato no Select Team (FL27) | **2. Meu mundo → Clubes → Mais → Ordem no Select Team...** |
| Um botão **Salvar** para um jogador | **2. Meu mundo → Jogadores**, ao lado de **Desfazer as alterações deste jogador** |
| FL27: ids de competição até 1023 (o FL26 fica em 255) | **Competições** no topo de **2. Meu mundo**, depois de **1. Início → Instalar agora** |
| Animações, e como desligar | **5. Configurações → Programa → Animações (as páginas, os botões e os diálogos aparecem suavemente)** |

Todo o resto, com as correções: [changelog 0.4.0](../../docs/changelog/changelog-0.4.0.md) (em inglês).

## 6. Algo deu errado?

1. **4. Ferramentas → Diagnóstico → Rodar as verificações → Copiar um relatório.**
2. No nosso [Discord](https://discord.gg/StQqtk3G3M): **#support** → **Open a support ticket** na
   mensagem fixada, com o relatório, um print da tela, `sider.log` e `sider.ini` (o menu **Jogo**
   abre os dois).

Conhecido na 0.4.0: [problemas conhecidos](../../docs/known-issues.md#open-in-mod-studio-040-2026-11-21) ·
o que mudou: [changelog 0.4.0](../../docs/changelog/changelog-0.4.0.md) ·
perguntas comuns: [FAQ](../../docs/faq.md)
