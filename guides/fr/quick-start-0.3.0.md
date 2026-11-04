# FL Mod Studio 0.3.0 — démarrage rapide (FL26 et FL27)

> [English](../en/quick-start-0.3.0.md) · [hrvatski](../hr/quick-start-0.3.0.md) · [español](../es/quick-start-0.3.0.md) · [português](../pt/quick-start-0.3.0.md) · **français**

Tout ce qu'il faut pour commencer avec 0.3.0, dans l'ordre. Chaque page et option en détail se
trouve dans le [guide d'utilisation](mod-studio-guide.md) ; un monde prêt ou un zip de Modpack est
dans [Installer un pack prêt](install-a-pack.md).

> [!WARNING]
> **0.3.0 est plutôt une version de test.** Si 0.2.5.1 marche bien chez vous et que vous n'avez
> pas besoin de FL27, rien ne presse : restez dessus jusqu'à ce que 0.3.0 ait été jouée un moment.
> Si vous êtes dans une longue carrière, gardez une copie de votre dossier de sauvegardes et de
> votre ancien dossier Mod Studio avant de mettre à jour.

## 1. Obtenir 0.3.0

**Vous avez 0.2.5.1 :** **Aide → Rechercher des mises à jour...** → **Télécharger et installer**.
Ou fermez Mod Studio et décompressez `FL26ModStudio-0.3.0.zip` par-dessus l'ancien dossier (tout
remplacer). Vos réglages, mondes et recettes restent.

**Première fois :** téléchargez `FL26ModStudio-0.3.0.zip` depuis la
[dernière version](https://github.com/Matozanato/FootballLife-new-leagues/releases/latest),
décompressez-le dans un dossier à part (gardez `_internal` et `pack` à côté de l'exe) et lancez
`FL26ModStudio.exe`. Si Windows dit « Windows a protégé votre ordinateur » (Windows protected your
PC) : **Informations complémentaires** (More info) → **Exécuter quand même** (Run anyway).

La fenêtre affiche maintenant **FL Mod Studio** : c'est le même programme, renommé parce qu'il
marche aussi avec FL27. L'exe, le dossier du zip et `%APPDATA%\FL26ModStudio` gardent leurs noms.

## 2. Choisir le jeu : FL26 ou FL27

1. **5. Réglages → Dossier du jeu → Parcourir...** → le dossier avec `FL_2026.exe` (FL26) ou
   `FL_2027.exe` (FL27) → **Utiliser ce dossier**.
2. La première fois que vous choisissez un jeu, Mod Studio décompresse les tables de ce jeu (une
   minute ou deux ; la barre du bas l'indique). FL26 et FL27 ont leurs propres tables et leurs
   propres sauvegardes, donc vous pouvez passer de l'un à l'autre : choisissez le dossier de
   l'autre jeu de la même façon.
3. **1. Accueil** : quand la vérification générale dit que les modules manquent ou sont plus
   anciens, appuyez sur **Installer maintenant**.

## 3. Votre monde de 0.2.5.1 (FL26)

Vos mondes continuent de marcher. Après la mise à jour :

1. **1. Accueil → Installer maintenant** (les modules de 0.3.0).
2. **2. Mon monde → Construire et installer** une fois.
3. Chargez votre carrière et continuez à jouer. Certaines corrections ne se voient que dans une
   nouvelle Master League : l'argent des transferts des petits clubs, les effectifs NewLife et
   les ligues aux places 76, 77 et 80 de Select Team.

## 4. De vrais clubs : NewLife Database 1.6b4

Téléchargez NewLife 1.6b4 depuis le canal **#newlife** de notre [Discord](https://discord.gg/StQqtk3G3M).
**Dans FL27, utilisez 1.6b4** (ou 1.6b3) : les versions plus anciennes ont été faites pour les
clubs de FL26.

1. Mettez les parties (`NewLife-1.6b4-Europe.zip` ...) dans un nouveau dossier, sans les mélanger
   avec des plus anciennes. Ne décompressez pas les parties.
2. **2. Mon monde → NewLife Database → Ouvrir la NewLife Database...** → ce dossier.
3. **Nouvelles ligues :** sélectionnez-en une ou plusieurs → **Ajouter à votre monde**. Une ligue
   d'un pays où le jeu a déjà une ligue (Greek Super League 2, Scottish Championship ...) entre
   comme la division sous la ligue du jeu, avec montées et descentes ; la page indique laquelle.
4. **Ligues ajoutées depuis un ancien NewLife :** **Plus → Mettre mes ligues à jour vers cette
   version**.
5. **Les ligues du jeu lui-même** restent comme le jeu les a. **Plus → Amener les ligues du jeu à
   cette saison...** passe leurs clubs et effectifs à la saison NewLife, si vous le voulez. Cochez
   **Seulement les joueurs du jeu** pour n'avoir que les transferts et les notes, sans nouveaux
   joueurs.
6. **Construire et installer**, puis lancez une **nouvelle** Master League : une ancienne
   sauvegarde ne prend pas les nouveaux effectifs.

## 5. Créer votre propre monde

Le chemin complet, clic par clic : [Créer vos propres ligues et packs](make-your-own-leagues.md).
En bref :

1. **2. Mon monde → Ligues** : ajoutez une ligue (ou des ligues NewLife, étape 4), réglez son
   pays, ses clubs, sa **Division**, ses places européennes et ses coupes avec **Modifier la
   ligue...**.
2. **Division** peut maintenant être aussi l'une des ligues divisées du jeu (Scottish
   Premiership, 3F Superliga, Jupiler Pro League) : votre ligue va en dessous, avec montées et
   descentes.
3. **Construire et installer**, puis une nouvelle Master League.

## 6. Jouer

- **Lancer le jeu** (en haut à droite) lance le jeu avec tout en place.
- **FL27 : lancez-le toujours par son launcher** (**FL 2027 start.exe**, son raccourci, ou
  **Lancer le jeu** dans Mod Studio). FL_2027.exe lancé tout seul peut se fermer pendant la
  création d'une nouvelle Master League ou pendant ses premiers jours.
- Dans FL27, la Ligue des champions et la Ligue Europa sont celles de FL27 ; Mod Studio décide qui
  y entre depuis vos ligues et joue les qualifications d'été ; la Ligue Europa Conférence est
  celle de Mod Studio.

## 7. Nouveau dans 0.3.0, et où le trouver

| Quoi | Où |
|---|---|
| Prise en charge de FL27 | **5. Réglages → Dossier du jeu** |
| Les clubs d'une ligue (avec blasons) dans Select Team | dans le jeu : Team Info, League mode ... avec le curseur sur une ligue |
| Places en couleur dans les classements (Ligue des champions, Ligue Europa, Ligue Europa Conférence, montée, barrage, descente) | dans le jeu, après **Construire et installer** |
| Une ligue à la place d'un des groupes « Other ... » du jeu dans Select Team | **2. Mon monde → Ligues → Places dans Select Team** (chaque ligue : *Automatique*, ou *à la place de* suivi d'un groupe), puis Build |
| Une ligue sous les ligues divisées du jeu | **Ligues → Modifier la ligue... → Division** |
| Ligue NewLife sous la ligue du jeu de son pays | automatique avec **Ajouter à votre monde** ; à changer dans **Division** |
| Ligues de janvier à décembre d'un nouveau pays : montées et descentes au Nouvel An, et leur coupe | automatique après le Build |

## 8. Quelque chose ne va pas ?

1. **4. Outils → Diagnostic → Lancer les vérifications → Copier un rapport.**
2. Postez-le dans **#support** sur le [Discord](https://discord.gg/StQqtk3G3M) (un fil par
   problème) avec une capture d'écran et `SiderAddons\sider.log` (le menu **Jeu** l'ouvre).

Connu dans 0.3.0 : [changelog](../../docs/changelog/changelog-0.3.0.md#known) ·
questions fréquentes : [FAQ](../../docs/faq.md)
