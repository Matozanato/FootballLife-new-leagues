# FL26 Mod Studio — guide d'utilisation

> Questions fréquentes (mise à jour, plantage au démarrage, coupes, montées, quoi envoyer quand
> quelque chose ne va pas), en anglais : [faq.md](faq.md)

FL26 Mod Studio est un seul programme pour tout ce que vous ajoutez à Football Life 2026 :

- les **mods** que vous téléchargez : stades, maillots, ballons, tableaux de score, commentaires,
  musique, visages, modules Lua ;
- les **serveurs de contenu** qui les fournissent au jeu (Stadium Server, Ball Server, Kit Server
  et les autres), avec leurs fichiers de correspondance modifiés sous forme de tableau plutôt qu'à
  la main ;
- la **configuration de Sider** elle-même : quels dossiers de contenu et modules sont activés, et
  dans quel ordre ;
- les **nouvelles ligues et nouveaux clubs** (le League Builder), vos modifications des ligues,
  clubs et **joueurs** du jeu, et les **paquets de ligues** qu'un moddeur crée une fois et que
  n'importe qui peut ajouter à son jeu.

Rien du jeu n'est écrasé. Avant de modifier un fichier, le programme en garde une copie, et chaque
mod qu'il installe peut être retiré ensuite.

---

## 1. Avant de commencer

- **Football Life 2026** installé, avec son dossier `SiderAddons` (FL26 est livré avec Sider).
- Décompressez le programme où vous voulez, p. ex. `Documents\FL26 Mod Studio`. Gardez le dossier
  entier : les dossiers `_internal` et `pack` et les fichiers `README` restent à côté de `FL26ModStudio.exe`.
- **Fermez le jeu** pendant vos changements. Sider lit sa configuration au lancement du jeu.

La fenêtre est en anglais. **Settings → Language → Français** la passe en français.

## 2. Premier lancement

1. **Réglages → Dossier du jeu** : appuyez sur `...` et choisissez le dossier qui contient
   `FL_2026.exe`. La ligne en dessous indique si `SiderAddons\sider.ini` a été trouvé.
2. Si vous voulez de nouvelles ligues ou des modifications de joueurs : **Réglages → Extraire les
   tables du jeu**. Le programme lit les clubs, ligues et joueurs du jeu dans un dossier de
   travail (quelques secondes). À refaire seulement après une mise à jour du jeu.
3. Ouvrez **Vue d'ensemble**. Elle montre votre configuration en un coup d'œil et liste les
   problèmes. Double-cliquez sur un problème pour ouvrir la page qui le corrige.

**Mises à jour.** Quelques secondes après le démarrage, le programme demande à GitHub si une
nouvelle version de FL26 Mod Studio est sortie, et ne le signale que s'il y en a une.
**Télécharger et installer** récupère le nouveau zip, le vérifie avec la somme de contrôle de la
version, ferme le programme, place les nouveaux fichiers par-dessus les anciens et le relance. Vos
réglages, projets, points de restauration et le jeu ne sont pas touchés. **Aide → Rechercher des
mises à jour** vérifie à tout moment ; décochez **Aide → Rechercher des mises à jour au
démarrage** et le programme ne vérifie plus que sur demande. Si le programme se trouve dans un
dossier où Windows ne le laisse pas écrire (comme Program Files), il ouvre la page de la version à
la place : décompressez le zip vous-même, ou déplacez le programme dans un dossier à vous.

**Plusieurs dossiers Sider ?** Sider ne s'appelle pas forcément `SiderAddons`. Le programme
cherche le dossier à côté de `FL_2026.exe` qui contient un `sider.ini` ; s'il y en a plusieurs,
**Réglages → Dossier de Sider** choisit celui avec lequel il travaille.

## 3. Les pages

La liste à gauche a quatre groupes.

| Groupe | Pages |
|---|---|
| **Gérer** | Vue d'ensemble, Installer des mods, Dossiers de contenu, Modules Lua, Profils, Points de restauration |
| **Contenu du jeu** | Stades, Maillots, Ballons, Commentaires, Musique, Autre contenu |
| **League Builder** | Nouvelles ligues, Nouveaux clubs, Ligues et clubs du jeu, Joueurs, Paquets de ligues, Construction |
| **Outils** | Diagnostic, Réglages |

## 4. Installer des mods

Déposez un mod téléchargé sur **Installer des mods** (`.zip`, `.7z`, un dossier, `.lua`, `.cpk`
ou `.fl26pack`), ou utilisez **Choisir un fichier...**.

Le programme regarde à l'intérieur et liste chaque partie : ce que c'est et où elle ira.

| Partie | Ce qui se passe |
|---|---|
| Dossier de contenu (livecpk) | Copié dans `SiderAddons\livecpk\<nom>` et ajouté à `sider.ini`. |
| Fichiers de serveur de contenu | Copiés dans le dossier `content` du serveur. Son **fichier de correspondance est fusionné avec le vôtre** : vos lignes restent et les nouvelles lignes du mod sont ajoutées. Pour un club que vous avez déjà, le choix à côté d'**Installer** décide : *utiliser celles du mod*, ou *garder les miennes, ajouter celles du mod après*. |
| Module Lua | Copié dans `SiderAddons\modules` et activé à la bonne place dans l'ordre. |
| .cpk compressé | Extrait dans un dossier de contenu à l'installation. |
| Paquet de ligues | Ajouté à votre recette du League Builder (section 9). |
| DLL | **Non installée.** Une DLL s'exécute avec les droits du jeu ; n'en installez une qu'à la main, et seulement depuis une source de confiance. |

Donnez un nom au mod, choisissez si les nouveaux dossiers de contenu vont en haut (ils
l'emportent) ou en bas, cochez ce que vous voulez et appuyez sur **Installer**. La liste en
dessous montre chaque mod installé avec le programme. **Retirer le mod** supprime les fichiers
qu'il a ajoutés et remet en place ceux qu'il a remplacés.

## 5. Dossiers de contenu et modules Lua

**Dossiers de contenu** liste chaque ligne `cpk.root` de `sider.ini`. Sider cherche un fichier de
haut en bas, donc quand deux dossiers ont le même fichier, celui qui est plus haut dans la liste
l'emporte.

- Cochez ou décochez un dossier pour l'activer ou le désactiver (la ligne est mise en
  commentaire, jamais supprimée).
- **En haut**, **Monter**, **Descendre** changent l'ordre ; **Ajouter un dossier...** ajoute un
  dossier que vous avez déjà.
- La taille et le contenu (visages, maillots, stades...) sont affichés pour chaque dossier.
- Rien n'est écrit tant que vous n'appuyez pas sur **Appliquer**. **Abandonner** oublie les
  modifications.

**Modules Lua** fonctionne de la même façon pour les lignes `lua.module`. Le programme connaît le
bon ordre des modules courants (les serveurs de contenu après les modules qu'ils utilisent) et le
signale quand un module est mal placé. Certains modules ont besoin d'un réglage de Sider (par
exemple Goal Song Server a besoin de `match-stats.enabled = 1`) ; le programme dit lequel.

Les modules du League Builder gardent l'ordre dans lequel ils ont été installés.

## 6. Contenu du jeu : les serveurs de contenu

**Stades, Maillots, Ballons, Musique, Commentaires** et **Autre contenu** (tableaux de score,
menus, tenues d'arbitre, badges de manche et météo) appartiennent chacun à un serveur de contenu.
Chaque page a :

- une **ligne d'état** : le module est-il activé, son dossier de contenu est-il là ;
- un onglet par **fichier de correspondance**, affiché sous forme de tableau : quelle compétition,
  quel club ou quel stade reçoit quoi. Ajoutez, modifiez, désactivez (la ligne devient un
  commentaire) ou supprimez des lignes ; choisissez les éléments dans la bibliothèque au lieu de
  taper des id. **Enregistrer** écrit le fichier ; la copie d'avant va dans Points de
  restauration ;
- la **Bibliothèque** : ce qu'il y a dans le dossier de contenu du serveur, avec des images quand
  il y en a. Les éléments qu'aucune ligne n'utilise et les lignes qui pointent vers des éléments
  manquants sont signalés ;
- les **Réglages** du serveur quand il en a (stade, ballon, tableau de score préférés ...).

Le programme vérifie les tableaux avant d'enregistrer : un nombre là où il faut un nombre, pas de
virgule dans un nom, un élément qui existe.

## 7. Profils

Un profil retient quels dossiers de contenu et modules sont activés, et dans quel ordre. Gardez-en
un pour la Master League, un pour le jeu en ligne, un pour les tests :

- **Enregistrer la configuration actuelle...** enregistre ce qui est activé maintenant sous un nom.
- **Passer à ce profil** met cette configuration dans `sider.ini` (l'ancien `sider.ini` va dans
  Points de restauration).
- **Mettre à jour avec la configuration actuelle** écrase le profil.

## 8. League Builder : nouvelles ligues, nouveaux clubs et joueurs

Le League Builder ajoute de nouvelles ligues au jeu et modifie celles du jeu. Ce qu'il crée est un
**monde** : un dossier de contenu nommé `_FL26...` que le jeu lit tant qu'il est activé.

**Nouvelles ligues → Ajouter une ligue**

| Champ | Ce que cela veut dire |
|---|---|
| **Nom** | Le nom de la ligue dans le jeu. Deux ligues ne peuvent pas avoir le même. |
| **Pays** | Donne le drapeau et l'endroit où la ligue apparaît dans la liste. Un pays pour lequel le jeu n'a pas de ligue reçoit son propre titre. |
| **Clubs** | De 10 à 24. |
| **Format** | *Tous contre tous*, 1 à 4 fois, *se divise en deux (à l'écossaise)* ou *Apertura et Clausura* : deux tournois par saison (septembre à début janvier, janvier à mai), chacun à partir de zéro point, puis des play-offs de 8 ou 4 clubs (ou aucun). Le classement de toute la saison décide des montées et descentes. 18 clubs au maximum. |
| **Division** | *(première division)*, ou la ligue au-dessus : une autre nouvelle ligue, ou une ligue du jeu. Pour placer une nouvelle ligue sous une autre nouvelle ligue en une étape : sélectionnez-la et appuyez sur **Ajouter une division inférieure** (elle reprend le pays, le nombre de clubs, le format et les montées/descentes de la ligue au-dessus ; il ne reste que le nom). |
| **Montée / descente** | Combien de clubs échangent leur place avec la ligue au-dessus en fin de saison. |
| **Europe** | Première division uniquement : quelle position en ligue va dans quelle compétition européenne. **1re division : 1er LdC, 2e LE, 3e LEC** remplit les trois places habituelles ; **Ajouter une place**, **Retirer une place** et **Effacer** pour tout le reste. Chaque position une seule fois, et seulement les positions que la ligue a. Laissez vide pour une division inférieure. Le modèle suit le pays : l'Asie reçoit l'AFC Champions League et l'AFC Champions League Two, l'Amérique du Sud la Libertadores et la Copa Sudamericana, l'Afrique la Ligue des champions CAF et la Coupe de la Confédération CAF. Ces quatre coupes que le jeu n'a pas sont construites avec le monde (section 8.2). Les places en qualifications de la Libertadores ne sont pas encore remplies : ce tour n'a pas de place libre pour un nouveau club, qui reste donc chez lui (Mod Studio signale l'option). |
| **Logo** | N'importe quelle image (un PNG à fond transparent rend le mieux). Vide : un logo est dessiné pour vous. |
| **Drapeau du pays** | Votre propre image du drapeau du pays, étirée dans le cadre des drapeaux du jeu. Elle remplace le drapeau de ce pays partout dans le jeu (Select Team, nationalité des joueurs, l'en-tête du pays dans Database > Competition Info) tant que le monde est activé. Vide : le drapeau du jeu. |
| **Coupe** | Première division uniquement. **Coupe nationale** : le pays a sa propre coupe, avec le nom que vous donnez (vide : `<ligue> Cup`). Le jeu remplit la coupe d'un pays avec sa première division et la division en dessous ; avec les deux, elle joue les tours de la coupe française, italienne ou anglaise, avec la première seule ceux de l'écossaise, la belge, la néerlandaise ou l'anglaise, selon le nombre de clubs. **Supercoupe** : en plus, une supercoupe en un match avant la saison, le champion contre le vainqueur de la coupe. |
| **Coupe de la ligue** | Première division uniquement. Une coupe à élimination directe de 16, 8 ou 4 clubs de cette ligue et de celle du dessous, selon le classement, le plus fort contre le plus faible : aller-retour à chaque tour, finale sur un match, de septembre à décembre. Donnez-lui un nom ou laissez vide (`<ligue> League Cup`). |
| **Exhibition uniquement -- pas en Ligue des Masters** | Pour le Kick Off et les matchs amicaux : une ligue historique, des légendes, etc. Ses clubs ne jouent jamais de saison de Ligue des Masters, donc la ligue reste seule : pas de division au-dessus ni au-dessous, pas de places européennes, pas de coupes. Elle apparaît quand même dans la liste des équipes de la Ligue des Masters ; choisissez votre club dans une autre ligue. |

Le **Nom du monde** (sur la même page) doit commencer par `_FL26`. Après la **Construction**, la
colonne **ID de la ligue** montre l'id de compétition de chaque ligue dans le jeu, celui que porte
son fichier de logo.

**Tournois de pré-saison** (bouton sur la même page) : des tournois amicaux à élimination directe de 4 ou 8 clubs invités en juillet, avant la saison, appariés dans l'ordre donné (le premier contre le deuxième ...). Un club est celui d'une nouvelle ligue ou un club du jeu (son id) ; au moins un doit venir d'une nouvelle ligue, dont le pays accueille le tournoi. Une carrière commence en août, donc le premier se joue la deuxième saison.

**Nouveaux clubs** : choisissez la ligue, puis **Modifier le club** (nom, nom court, écusson),
**Coller des noms...** ou **Charger des noms depuis un fichier...**. Un nom vide devient
`<ligue> 01`, `<ligue> 02` ... ; un club sans écusson reçoit un écusson numéroté. Les maillots sont
empruntés aux clubs du jeu.
Les noms gardent leurs accents (FK Željezničar) ; le nom court de trois lettres n'en a pas, comme
dans le jeu, donc Č, Ž, Đ y deviennent C, Z, D. Après la **Construction**, la colonne **ID du
club** montre l'id de chaque club dans le jeu.

**Entraîneur** : dans **Modifier le club** d'un nouveau club, vous pouvez nommer son entraîneur. Vide : un nom numéroté (`FL M0001` ...).

**Ligues et clubs du jeu** : nouveaux noms, logos et écussons pour ce que le jeu a déjà.

> **Fichier Edit.** Si le dossier de sauvegarde du jeu contient un fichier Edit (`EDIT00000000`),
> il remplace les noms des clubs. Déplacez-le ailleurs pour voir vos noms.

### Joueurs

**Joueurs** modifie l'effectif de n'importe quel club : les nouveaux clubs de la recette et ceux du
jeu. Choisissez un club (ou appuyez sur **Joueurs** dans Nouveaux clubs), puis un joueur :

- **nom**, **numéro de maillot**, **poste** et les postes où il peut jouer (A = naturel,
  B = peut y jouer), pied fort, taille, poids, âge, nationalité, style de jeu ;
- toutes les **capacités** et **compétences** (les noms sont ceux du jeu) ;
- **Note** : la note de la liste, faite des capacités sur lesquelles le poste s'appuie. La
  changer déplace chaque capacité du joueur d'autant. Un joueur d'un nouveau club n'a pas de
  nom tant que la construction ne le numérote pas (FL P00001 ...) ; tapez-en un dans **Nom**
  pour lui donner le vôtre ;
- **Visage** : **Choisir...** un dossier de visage (section 8.1). **Effacer** redonne le visage du
  jeu ;
- **Monter dans l'ordre / Descendre dans l'ordre** : l'ordre de l'effectif. Les onze premiers
  commencent le match ;
- **Ajouter un joueur** (une copie du joueur choisi, avec un nouvel id ; clubs du jeu seulement),
  **Retirer du club** (un nouveau club garde au moins 18 joueurs) ;
- **Meilleur onze** place le joueur le plus fort à chaque poste ; **Niveau de l'effectif...**
  monte ou baisse chaque capacité de tout l'effectif ;
- **Exporter en CSV... / Importer un CSV...** : modifiez un effectif dans un tableur. Exportez
  d'abord, changez les cellules, puis réimportez les mêmes colonnes.
- **Importer un effectif depuis un tableau...** : n'importe quel tableau de joueurs devient
  l'effectif du club -- tapé à la main, une liste copiée d'un site, un export de Football
  Manager ou d'EA FC. Les colonnes sont reconnues par leur nom (nom, poste, âge ou date de
  naissance, nationalité, taille, pied, numéro, note générale et toutes les notes) et
  affichées pour corriger celle qui est fausse. Ce que le tableau n'a pas vient des joueurs du
  jeu de même poste et même note ; les notes 1-20 de Football Manager sont étirées au 40-99 du
  jeu. Les joueurs du tableau prennent les places du club dans l'ordre de l'effectif : un
  nouveau club garde ses 30 places (moins de joueurs = les autres partent, jusqu'à 18), un club
  du jeu gagne ou perd des joueurs pour correspondre.

Chaque modification est écrite dans le monde lors de la **Construction** ; les fichiers du jeu
restent tels quels. **Annuler les modifications de ce joueur** et **Annuler toutes les
modifications de ce club** reviennent à ce qu'il y a dans le jeu.

La liste des clubs a aussi **Équipes nationales** et **Autres clubs (sans ligue)** : les équipes que le jeu garde hors de toute ligue (sélections, clubs qui ne jouent qu'une coupe ou une compétition continentale). Leurs joueurs se modifient de la même façon.

### 8.1 Visages

Un mod de visage est un dossier comme celui-ci (c'est ainsi que les créateurs de visages les
partagent) :

```
<n'importe quel nom>\
    #Win\face.fpk
    #Win\face.fpkd
    sourceimages\#windx11\*.ftex
    portrait.dds            (ou <id>.dds, facultatif)
```

Choisissez ce dossier pour un joueur. À la **Construction**, le visage est copié dans le monde et
attribué au joueur : il fonctionne donc pour un nouveau joueur dont l'id n'existait pas quand le
visage a été créé, et il ne remplace jamais un visage du jeu. Sans portrait, la petite image du
joueur dans les menus reste une silhouette vide ; le visage lui-même s'affiche quand même. Un
dossier contenant plus d'un visage est refusé : choisissez le visage que vous voulez.

### 8.2 Construire, activer, jouer

**Construction** :

0. **Installer les modules** — une fois, puis à nouveau après une nouvelle version du programme.
   Les fichiers remplacés sont conservés dans `SiderAddons\modules\before-builder-1\`.
1. **Vérifier le plan** — ce qui sera créé ; rien n'est écrit.
2. **Construire le monde**.
3. **L'activer** — en fait le monde actif dans `sider.ini`.
4. Lancez le jeu, revenez et appuyez sur **Après un lancement : vérifier**. Le programme lit
   `sider.log` et dit, module par module, si le monde a été pris en compte.

**Inclure la Ligue Europa Conférence** (sur la page Construction, activé par défaut) construit
aussi la Ligue Europa Conférence : une phase de ligue à 36 clubs et un barrage en février, comme
les deux autres. La Ligue des champions et la Ligue Europa reçoivent leur phase de ligue à 36 et
leur barrage de février dans tous les cas. Désactivé : pas de Ligue Europa Conférence. (Mod Studio
0.1.3 et les versions précédentes laissaient la Ligue des champions et la Ligue Europa dans les groupes de quatre du jeu quand
c'était désactivé, ce que le mod ne sait pas gérer -- elles cassaient ; les Vérifications signalent
un tel monde : reconstruisez-le.)

> **Places européennes.** Les places que vous donnez à vos ligues viennent après celles des ligues
> du jeu. Chaque compétition prend 36 clubs ; les places au-delà de la 36e ne donnent rien, et
> **Vérifier le plan** le signale. Les nouvelles ligues sans places n'envoient personne en
> Europe, et Vue d'ensemble vous en avertit. Les tenants du titre passent en premier : les
> vainqueurs de la Ligue des champions et de la Ligue Europa prennent deux des 36 places de la
> Ligue des champions, celui de la Ligue Conférence une place en Ligue Europa.

Ensuite, **commencez une nouvelle carrière Master League** (ou Become a Legend). Les nouvelles
ligues se trouvent sous leur pays dans Select Team et Kick Off.

> **Coupes des autres continents.** Quand vos ligues envoient des clubs en Ligue des champions
> CAF, en Coupe de la Confédération CAF, en AFC Champions League Two ou en Copa Sudamericana,
> la **Construction** crée aussi ces coupes. Chacune a 32, 16, 8 ou 4 clubs : d'abord les places
> de vos ligues, puis les ligues du jeu de ce continent (Asie et Amérique du Sud) la complètent.
> À 8 ou plus, des groupes de quatre puis une phase à élimination directe ; en dessous de 8,
> l'élimination directe seule. Elles sont remplies fin août, avec les classements des ligues.

> **Les sauvegardes appartiennent à un monde.** Une carrière sauvegardée avec un monde activé a
> besoin de ce même monde pour se charger.

**Fichier → Enregistrer la recette** enregistre tout dans un fichier `.json` ; **Ouvrir une
recette** le recharge.

### 8.3 Limites

| | |
|---|---|
| Nouvelles ligues par monde | 39 |
| Clubs par ligue | 10 – 24 |
| Nouveaux clubs au total | 793 |
| Nombre de rencontres entre clubs | 1 – 4 |
| Ligues qui se divisent | 2 par monde |
| Divisions dans un pays | jusqu'à la 7e |
| Joueurs par nouveau club | 30 au départ ; retirez-en jusqu'à 18, pas de joueurs en plus |

## 9. Paquets de ligues : partager une ligue entière

Un moddeur crée une ligue une fois — clubs, noms, écussons, logos, effectifs, visages — et
partage **un seul fichier `.fl26pack`**. N'importe qui l'ajoute à sa propre recette et construit.

**Créer un paquet** (Paquets de ligues → **Créer un paquet...**, ou Fichier → Créer un paquet de
ligues) :

1. Nom, auteur, version et une courte description.
2. Cochez les ligues à inclure. Une ligue placée sous une autre nouvelle ligue doit
   l'accompagner.
3. Si vous le voulez, **aussi mes modifications des ligues, clubs et joueurs du jeu**.
4. Enregistrez. Le fichier contient les images et les visages, pas des chemins de votre
   ordinateur.

**Ajouter un paquet** (Paquets de ligues → **Ajouter un paquet...**, Fichier → Ajouter un paquet
de ligues, ou déposez-le sur Installer des mods) :

1. Le programme montre ce qu'il contient et vous demande.
2. Une ligue dont vous avez déjà le nom est ajoutée sous la forme `Nom (Paquet)`.
3. **Enregistrer la recette**, puis **Construction**.

Les id sont attribués quand chaque personne construit, d'après ce que son propre jeu contient :
un paquet fonctionne donc à côté d'autres paquets et de vos propres ligues. **Retirer de la
recette** retire à nouveau un paquet, y compris les modifications qu'il a faites aux clubs du jeu.

Une ligue placée sous une ligue du jeu fonctionne pour tous ceux qui ont la même version du jeu.

## 10. Outils

**Diagnostic — Lancer les vérifications** examine toute la configuration : dossiers de contenu
activés mais manquants, modules mal placés ou activés deux fois, lignes de correspondance qui ne
pointent vers rien, mondes du League Builder (un seul devrait être activé), et le dernier
`sider.log`. **Copier un rapport** met tout dans le presse-papiers, à coller dans un message de
forum ou un rapport de bug.

**Points de restauration** : chaque fichier que le programme a modifié, avec la copie d'avant.
**Restaurer cette copie** le remet en place. Les copies sont dans
`SiderAddons\ModStudio\backups`. **Nettoyer...** supprime les anciennes.

## 11. Quand quelque chose ne va pas

| Ce que vous voyez | Que faire |
|---|---|
| *sider.ini not found* | Réglages → Dossier du jeu : choisissez le dossier avec `FL_2026.exe`. |
| *no game tables* | Réglages → Extraire les tables du jeu. |
| Un mod n'apparaît pas dans le jeu | Diagnostic → Lancer les vérifications. Un dossier de contenu plus haut dans la liste a peut-être le même fichier. |
| Le jeu ne se lance plus après un changement | Points de restauration → remettez `sider.ini` en place, ou passez à un profil qui fonctionnait. |
| La nouvelle ligue n'est pas dans Select Team | Commencez une *nouvelle* carrière ; les anciennes carrières gardent leurs anciennes ligues. |
| Les noms des clubs sont ceux du jeu | Un fichier Edit les remplace (section 8). |
| *vos ligues n'envoient personne en Europe* | Nouvelles ligues → Modifier la première division → Europe (le bouton **1re division** remplit les trois places habituelles), puis construisez à nouveau. |
| *la Ligue Europa Conférence est activée, mais ses tables sont manquantes* | Construisez à nouveau le monde : il a été construit avant cette option, ou avec l'option désactivée. |
| Un visage ne s'affiche pas | Le dossier doit contenir `#Win\face.fpk` ; construisez à nouveau après l'avoir choisi. |
| Autre chose | Diagnostic → **Copier un rapport**, et publiez-le avec `SiderAddons\sider.log`. |
