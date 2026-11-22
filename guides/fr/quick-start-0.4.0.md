# FL Mod Studio 0.4.0 — démarrage rapide (FL26 et FL27)

> [English](../en/quick-start-0.4.0.md) · [hrvatski](../hr/quick-start-0.4.0.md) · [español](../es/quick-start-0.4.0.md) · [português](../pt/quick-start-0.4.0.md) · **français**

Tout ce qu'il faut pour commencer avec 0.4.0, dans l'ordre. Chaque page et option en détail se
trouve dans le [guide d'utilisation](mod-studio-guide.md) ; un zip de monde prêt est dans
[Installer un pack prêt](install-a-pack.md). Vous venez de 0.2.5.1 ou d'avant ? Lisez aussi le
[démarrage rapide de 0.3.0](quick-start-0.3.0.md).

## 1. Avant de mettre à jour

- **Gardez une copie de votre dossier de sauvegardes et de votre ancien dossier Mod Studio**,
  comme toujours.
- **Après la mise à jour, installez de nouveau les modules : 1. Accueil → Installer
  maintenant.** Beaucoup de corrections sont dans nos modules dans le jeu.
- **Une carrière en cours garde ce que contient sa sauvegarde.** Les nouvelles ligues, coupes et
  clubs d'un monde mis à jour n'arrivent que dans une nouvelle Master League. Votre carrière
  continue avec les ligues qu'elle a.
- **Nouvelle licence.** Depuis 0.4.0, Mod Studio est sous la FL Mod Studio License (`LICENSE.txt`
  dans le zip). Il reste libre à utiliser, modifier et partager. Le vendre et retirer la marque
  « Powered by FL ModStudio » ne sont pas permis. 0.3.0 et les versions plus anciennes restent sous
  la licence MIT.

## 2. Obtenir 0.4.0

**Vous avez 0.3.0 :** **Aide → Rechercher des mises à jour...** → **Télécharger et installer**.
Mod Studio se ferme, met les nouveaux fichiers dans son dossier et redémarre.

**Première fois, ou à la main :** téléchargez `FL26ModStudio-0.4.0.zip` depuis la
[dernière version](https://github.com/Matozanato/FootballLife-new-leagues/releases/latest) et
décompressez-le dans un dossier à part (par exemple `Documents\FL26 Mod Studio`). Ne le lancez
pas depuis l'intérieur du zip, et gardez `_internal` et `pack` à côté de `FL26ModStudio.exe`.
Double-cliquez sur `FL26ModStudio.exe`. Si Windows dit « Windows a protégé votre ordinateur »
(Windows protected your PC) : **Informations complémentaires** (More info) → **Exécuter quand même**
(Run anyway). Vos réglages, mondes et recettes sont dans `%APPDATA%\FL26ModStudio` : ils restent.

**Choisir le jeu :** **5. Réglages → Parcourir...** → le dossier avec `FL_2026.exe` (FL26) ou
`FL_2027.exe` (FL27), pas `SiderAddons` → **Utiliser ce dossier**. La première fois, Mod Studio
décompresse les tables du jeu : une minute ou deux, attendez.

## 3. Votre monde de 0.3.0

1. **1. Accueil → Installer maintenant** (les modules de 0.4.0).
2. Un monde que vous construisez vous-même : **2. Mon monde → Construire et installer** une fois.
   Beaucoup de corrections de 0.4.0 demandent un nouveau Build.
3. Chargez votre carrière et continuez à jouer. Les nouvelles ligues, coupes et clubs n'arrivent
   que dans une nouvelle Master League.

Un monde prêt venu d'un zip (GigaPack, un Modpack) n'a pas besoin de Build. Quand son auteur vous
donne une nouvelle version, installez le nouveau zip comme la première fois (section 4).

## 4. GigaPack (Football Life 2027)

GigaPack by MatoZanato 1.0 est un monde prêt pour **Football Life 2027** : 317 ligues et 5 239
clubs, en un seul zip, installé par Mod Studio, sans Build. Téléchargements, md5, ce qu'il ne fait
pas encore et les problèmes connus : [GigaPack](../../docs/gigapack.md) (en anglais).

En bref (il faut FL27 avec la **mise à jour 1.1** ; fermez d'abord le jeu et son launcher) :

1. Mod Studio 0.4.0, et le dossier du jeu avec `FL_2027.exe` (section 2).
2. Ne décompressez pas GigaPack. **1. Accueil → Importer un zip de monde** → choisissez
   `GigaPack-1.0.zip` → **Installer le monde**. Attendez **Prêt à jouer**. S'il dit **Presque
   prêt**, il liste ce qu'il faut corriger.
3. Le bouton vert **Lancer le jeu** dans Mod Studio (ou le launcher de FL27, pas `FL_2027.exe`
   directement) → **Master League** → **New game**. Seule une nouvelle Master League reçoit les
   nouvelles ligues.

## 5. Nouveautés de 0.4.0, et où les trouver

| Quoi | Où |
|---|---|
| GigaPack 1.0, un monde prêt de 317 ligues pour FL27 | [GigaPack](../../docs/gigapack.md) (section 4) |
| Un zip de monde s'installe d'un coup | **2. Mon monde → + Ajouter... → Choisir un fichier...** → le zip → **Installer le monde** |
| Importer votre monde dit si un zip est une version plus récente, plus ancienne ou la même de votre monde | **1. Accueil → Importer un zip de monde** |
| Une mise à jour d'un monde que vous partagez garde les carrières de ses joueurs : l'export demande une version | **Exporter...** sur la carte du monde dans **2. Mon monde** ; FAQ (en anglais) : [Updating a shared world without breaking careers](../../docs/faq.md#updating-a-shared-world-without-breaking-careers) |
| Un onglet pour les coupes : coupes nationales et compétitions continentales | **2. Mon monde → Coupes** : **Game Countries**, **Our Countries**, **Continental**. **Appliquer**, puis **Construire et installer** |
| Les trophées, aussi dans FL27 (dans FL27 pas encore vérifié en jeu) | **3. Contenu du jeu → Trophées** |
| Une troisième coupe pour les divisions inférieures (FL27) | **Ligues → Modifier la ligue... → Troisième coupe (comme l'EFL Trophy)**, vos propres dates dans **Dates des coupes** |
| Ligues jusqu'à 32 clubs (de 29 à 32 ils se rencontrent une fois) ; FL27 prend aussi 8 et 9. Pas encore jouées sur une saison entière dans le jeu | **Ligues → Modifier la ligue... → Clubs** |
| Votre propre ordre des clubs d'une ligue dans Select Team (FL27) | **2. Mon monde → Clubs → Plus → Ordre dans Select Team...** |
| Un bouton **Enregistrer** pour un joueur | **2. Mon monde → Joueurs**, à côté de **Annuler les modifications de ce joueur** |
| FL27 : ids de compétition jusqu'à 1023 (FL26 reste à 255) | **COMPÉTITIONS** en haut de **2. Mon monde**, après **1. Accueil → Installer maintenant** |
| Les animations, et comment les couper | **5. Réglages → Programme → Animations (les pages, les boutons et les dialogues apparaissent en douceur)** |

Tout le reste, avec les corrections : [changelog 0.4.0](../../docs/changelog/changelog-0.4.0.md) (en anglais).

## 6. Quelque chose ne va pas ?

1. **4. Outils → Diagnostic → Lancer les vérifications → Copier un rapport.**
2. Sur notre [Discord](https://discord.gg/StQqtk3G3M) : **#support** → **Open a support ticket**
   dans le message épinglé, avec le rapport, une capture d'écran, `sider.log` et `sider.ini` (le
   menu **Jeu** ouvre les deux).

Connu dans 0.4.0 : [problèmes connus](../../docs/known-issues.md#open-in-mod-studio-040-2026-11-21) ·
ce qui a changé : [changelog 0.4.0](../../docs/changelog/changelog-0.4.0.md) ·
questions fréquentes : [FAQ](../../docs/faq.md)
