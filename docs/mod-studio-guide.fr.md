# FL26 Mod Studio — guide d'utilisation

> Questions fréquentes (mise à jour, plantage au démarrage, coupes, montées, quoi envoyer quand
> quelque chose ne va pas), en anglais : [faq.md](faq.md) · questions et aide sur [Discord](https://discord.gg/StQqtk3G3M)

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
   `FL_2026.exe`. La ligne en dessous indique si `SiderAddons\sider.ini` a été trouvé. Sider peut avoir un
   autre nom ou être un niveau plus bas (`sider\patch 1` ...) ; s'il y en a plusieurs, **Settings → Sider folder** choisit celui avec lequel le programme travaille.
2. Si vous voulez de nouvelles ligues ou des modifications de joueurs : **Réglages → Extraire les
   tables du jeu**. Le programme lit les clubs, ligues et joueurs du jeu dans un dossier de
   travail (quelques secondes). À refaire seulement après une mise à jour du jeu ;
   Build la remarque (0.1.9) et propose d'abord une nouvelle extraction. Il le faut une fois
   sur chaque PC (un paquet ou un nouveau monde le demande et propose d'ouvrir les Réglages).
   **Utiliser un autre dossier de tables** seulement si vous avez déjà un dossier `pesdb` extrait
   (Team.bin, Competition.bin ...).
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

**Carrières d'avant la 0.2.0.** La 0.2.0 permet 792 matchs par jour du calendrier au lieu de 280, ce qui change les tables avec lesquelles une carrière est sauvegardée : **une carrière sauvegardée avec une version plus ancienne ne se charge pas** (elle reste sur l'écran de chargement). Commencez une nouvelle carrière après la mise à jour. Vos mondes, projets et données Edit ne changent pas.

**Crédits.** Le bouton **Crédits**, à côté d'**Aide**, nomme tous ceux qui ont aidé à faire Mod
Studio : les testeurs, ceux qui ont envoyé des rapports et des logs, et ceux dont les idées y sont.

**Plusieurs dossiers Sider ?** Sider ne s'appelle pas forcément `SiderAddons`. Le programme
cherche le dossier à côté de `FL_2026.exe` qui contient un `sider.ini` ; s'il y en a plusieurs,
**Réglages → Dossier de Sider** choisit celui avec lequel il travaille.

## 3. Les pages

La liste à gauche a quatre groupes.

| Groupe | Pages |
|---|---|
| **Gérer** | Vue d'ensemble, Installer des mods, Dossiers de contenu, Modules Lua, Profils, Points de restauration |
| **Contenu du jeu** | Stades, Maillots, Ballons, Commentaires, Musique, Autre contenu |
| **League Builder** | NewLife Database, Nouvelles ligues, Nouveaux clubs, Ligues et clubs du jeu, Joueurs, Paquets de ligues, Construction |
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

Depuis 0.2.0 les douze petites protections contre les plantages arrivent en deux fichiers, `fl26guards.lua` (les huit `fl26nullguard`) et `fl26lateguards.lua` (`fl26superguard`, `fl26resultsguard`, `fl26ctlguard`, `fl26kitguard`), la liste est donc plus courte. sider.log nomme toujours chaque protection sur sa propre ligne. Le Build désactive les anciennes lignes séparées et garde les anciens fichiers dans `modulesefore-builder-<n>` ; rien à faire à la main.

**Désactiver les regens** (0.2.0) : `fl26regen` donne aux regens de nouveaux noms, un nouveau
potentiel et un visage du pack de visages des regens. Pour jouer sans lui, décochez **Masquer
les modules du League Builder (fl26...)** pour voir les nôtres, décochez `fl26regen` et appuyez
sur **Appliquer**. Mod Studio le note dans `modules\fl26-off.txt` dans le dossier de Sider : la
**Construction**, **Installer les modules** et le changement de monde le laissent désactivé au
lieu de le réactiver, comme ils le font pour tous les autres modules. Le jeu fait alors ses
propres regens : son potentiel et ses noms, sans visages du pack de visages des regens.
Recochez-le et appuyez sur **Appliquer** pour le réactiver. Seul `fl26regen` peut rester
désactivé ainsi.

## 6. Contenu du jeu : les serveurs de contenu

**Stades, Maillots, Ballons, Musique, Commentaires** et **Autre contenu** (tableaux de score,
menus, tenues d'arbitre, badges de manche et météo) appartiennent chacun à un serveur de contenu.
Les modules propres à SPFL26 pour les maillots, les stades et les tableaux de score (`common\kits.lua`, `common\stadiums.lua`, `common\scoreboards.lua`) lisent les mêmes fichiers dans `content\kits`, `content\stadiums` et `content\scoreboards` ; quand le serveur lui-même n'est pas installé, sa page modifie ceux-là (maillots depuis 0.1.7, stades et tableaux de score depuis 0.1.8).
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

Une ligne de compétition va par **phase** de la compétition, pas par compétition : le jeu donne
aux serveurs de contenu la phase jouée (la Conference League, c'est 186, 1210, 187, 189 et ses
tours suivants 1213 ... 8381 ; la Ligue des champions 2, 3, 4 et les siens), donc une ligne avec
le numéro de la compétition (174) ne sert jamais. Le sélecteur de compétitions propose chaque
compétition une fois de plus en **(toutes les phases : N)** : choisissez-la et une ligne est écrite par
phase (0.1.9). Une ligne avec le numéro d'une compétition est signalée comme problème.

**Importer des maillots...** (0.1.8, sur la page *Kits*) : des maillots pour beaucoup de clubs d'un coup. Choisissez un dossier de maillots kit-server prêts -- un dossier par club, avec `p1`, `p2`, `g1` ... et `order.ini`, nommé d'après le club (`Dinamo Zagreb`) ou son ID d'équipe (`2215`). La liste montre chaque association cochée ; décochez une mauvaise avant **OK**. Les maillots sont copiés dans la bibliothèque de kit-server (`Ligue\Club`, comme le dossier les avait) et chaque club reçoit une ligne dans `map.txt` ; **Save** l'écrit. Un club qui a déjà une ligne la garde, sauf si **Remplacer les maillots déjà définis** est coché. Les maillots d'un nouveau club du League Builder suivent l'ID que Build lui a donné : faites d'abord Build du monde et laissez-le activé. Le dossier d'un club peut aussi contenir de simples images de maillots (0.2.0) : `p1.png`, `p2.png` ... pour les maillots et `g1.png` pour le gardien (2048 x 2048 de préférence ; `.jpg` et `.dds` marchent aussi). Mod Studio en fait des maillots kit-server ; les numéros de dos, les numéros de short et la police du nom sont des textures à part, ils viennent donc d'un maillot déjà dans la bibliothèque, choisi dans **Numéros et noms de** (*aucun* : le jeu garde ceux du club). Les couleurs de `config.txt` sont lues sur l'image. La conversion des images est de Xxspedd, tirée de son outil de maillots. Mod Studio ne dessine pas de maillots : les images viennent de vous ou d'un créateur de maillots.

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

**Retirer** supprime la ligue sélectionnée avec ses clubs. Pour en supprimer plusieurs d'un coup (0.1.8),
sélectionnez-les avec Ctrl+clic, Maj+clic ou Ctrl+A, puis **Retirer** ou la touche Suppr.

**Nouvelles ligues → Ajouter une ligue**

| Champ | Ce que cela veut dire |
|---|---|
| **Nom** | Le nom de la ligue dans le jeu. Deux ligues ne peuvent pas avoir le même. |
| **Pays** | Donne le drapeau et l'endroit où la ligue apparaît dans la liste. Un pays pour lequel le jeu n'a pas de ligue reçoit son propre titre. |
| **Clubs** | De 10 à 24 (de 1 à 24 pour des clubs sans championnat). |
| **Clubs sans championnat** | Pour un club, ou quelques-uns, sans championnat autour (0.1.8) : par exemple seulement le BATE Borisov de Biélorussie. Choisissez le groupe où ils vont : *Other European teams*, *Other Latin American teams*, *Other Asia-Oceania teams*, *Other Africa teams* ou *Classic Teams* -- là où le jeu range ses propres clubs qui ne jouent dans aucun championnat (Dynamo Kyiv, Wydad Casablanca ...). Dans Select Team ils apparaissent dans ce groupe. Ils ont nom, écusson, maillots, entraîneur, formation, joueurs et stade comme tout nouveau club (**Edit club**, **Players**) ; le nom du haut sert seulement à Mod Studio pour les lister. Ils ne jouent ni championnat, ni coupe, ni compétition européenne, et tout le reste de cette fenêtre est en gris. |
| **Format** | *Tous contre tous*, 1 à 4 fois, *se divise en deux (à l'écossaise)* ou *Apertura et Clausura* : deux tournois par saison (septembre à début janvier, janvier à mai), chacun à partir de zéro point, puis des play-offs de 8 ou 4 clubs (ou aucun). Le classement de toute la saison décide des montées et descentes. 18 clubs au maximum. Une ligue divisée a 46 journées au maximum, avant et après la division ensemble (16 clubs deux fois font 30, donc son plus grand groupe deux fois peut avoir 8 clubs, 14 journées). Pour l'instant, une seule ligue par pays peut se diviser ou jouer Apertura/Clausura. |
| **Division** | *(première division)*, ou la ligue au-dessus : une autre nouvelle ligue, ou une ligue du jeu. Pour placer une nouvelle ligue sous une autre nouvelle ligue en une étape : sélectionnez-la et appuyez sur **Ajouter une division inférieure** (elle reprend le pays, le nombre de clubs, le format et les montées/descentes de la ligue au-dessus ; il ne reste que le nom). Une ligue qui a déjà une autre nouvelle ligue en dessous est grisée (0.1.9) : le jeu ne suit qu'un seul lien vers le bas depuis une ligue, donc les groupes d'une même division (trois groupes de Serie C sous la Serie B) ne sont pas encore possibles. |
| **Montée / descente** | Combien de clubs échangent leur place avec la ligue au-dessus en fin de saison. |
| **Saison** | Première division d'un nouveau pays uniquement : *août à mai* (par défaut) ou *février à décembre*, comme le Brésil, le Japon ou l'Arabie saoudite : les clubs montent et descendent au Nouvel An, et les divisions en dessous la suivent. Pas encore avec une scission, Apertura/Clausura, une coupe nationale ni une coupe de la ligue, ni avec une scission ou Apertura/Clausura sur une division sous un championnat de février à décembre (la Liga BetPlay ou la J1 League du jeu comprises). |
| **Europe** | Première division uniquement : quelle position en ligue va dans quelle compétition européenne. **Première division : 1er qualifications LDC, 2e LE, 3e LECE** remplit les trois places habituelles (*... (qualifications)* sont les barrages d'août, voir 8.2) ; **Ajouter une place**, **Retirer une place** et **Effacer** pour tout le reste. Chaque position une seule fois, et seulement les positions que la ligue a. Sous 1, la position s'affiche **Vainqueur de la coupe** (0.1.7) : le vainqueur de la coupe du pays (un nouveau pays a besoin de **Coupe nationale**) -- et si le vainqueur a déjà une place européenne par la ligue, la place descend la ligue jusqu'au club suivant, comme à l'UEFA. Depuis 0.2.0, le vainqueur de la coupe peut aussi aller dans les coupes que Mod Studio construit (Copa Sudamericana, Coupe de la Confédération CAF, AFC Champions League Two ...) ; dans une nouvelle carrière, avant que quiconque ait gagné la coupe, cette place va aussi au club suivant de la ligue. Une ligue du jeu peut aussi en avoir une (*Places européennes des ligues du jeu*). Laissez vide pour une division inférieure. Le modèle suit le pays : l'Asie reçoit l'AFC Champions League et l'AFC Champions League Two, l'Amérique du Sud la Libertadores et la Copa Sudamericana, l'Afrique la Ligue des champions CAF et la Coupe de la Confédération CAF, l'Amérique du Nord et centrale la CONCACAF Champions Cup, l'Océanie l'OFC Champions League. L'**AFC Challenge League** (0.2.0) est la troisième coupe de l'AFC, sous l'AFC Champions League Two, comme la Ligue Europa Conférence en Europe ; elle se choisit avec **Ajouter une place** (*AFC CHL* dans la liste des ligues). Ces sept coupes que le jeu n'a pas sont construites avec le monde (section 8.2). Une place en *qualifications de la Libertadores* prend la place d'un club du jeu au tour préliminaire (le dernier du pays qui y a le plus de clubs), au plus six de ses huit places ; **Vérifier le plan** indique quelles ligues restent dehors au-delà. |
| **Logo** | N'importe quelle image (un PNG à fond transparent rend le mieux). Vide : un logo est dessiné pour vous. |
| **Drapeau du pays** | Votre propre image du drapeau du pays, étirée dans le cadre des drapeaux du jeu. Elle remplace le drapeau de ce pays partout dans le jeu (Select Team, nationalité des joueurs, l'en-tête du pays dans Database > Competition Info) tant que le monde est activé. Vide : le drapeau du jeu. |
| **Coupe** | Première division uniquement. **Coupe nationale** : le pays a sa propre coupe, avec le nom que vous donnez (vide : `<ligue> Cup`). Le jeu remplit la coupe d'un pays avec sa première division et la division en dessous, et la taille de la coupe suit la ligne Coupe nationale des Limites (8.3) : la plus grande taille que l'écran de la coupe dessine et qui tient, donc 22 clubs donnent une coupe de 20, la première division d'abord. Au-delà de 44 clubs, la coupe ne garde que la première division. Une nouvelle deuxième division sous un pays que le jeu a déjà (Allemagne, Russie ...) entre aussi dans la coupe de ce pays, après les clubs de première division, quand les tours de la coupe conviennent au nombre de clubs. Une nouvelle troisième division ou plus bas (League One sous la Championship) laisse la coupe du pays aux deux premières divisions du jeu, comme dans le jeu. **Supercoupe** : en plus, une supercoupe en un match avant la saison, le champion contre le vainqueur de la coupe. |
| **Coupe de la ligue** | Première division uniquement. Une coupe à élimination directe de 16, 8 ou 4 clubs de cette ligue et de celle du dessous, selon le classement, le plus fort contre le plus faible : aller-retour à chaque tour, finale sur un match, de septembre à décembre. Les clubs au-delà de 16, 8 ou 4 jouent d'abord un tour préliminaire (0.1.7) : les dernières places, le plus fort contre le plus faible, aller-retour les 4 et 7 septembre ; les vainqueurs prennent les dernières places de la coupe, face à ses clubs les plus forts. Une ligue de 20 : du 1er au 12e directement en huitièmes, du 13e au 20e en quatre confrontations préliminaires. Donnez-lui un nom ou laissez vide (`<ligue> League Cup`). |
| **Logos des coupes** | Une image pour la coupe nationale, la supercoupe, la coupe de la ligue et les play-offs de l'Apertura/Clausura, chacune à part. Vide : un emblème aux initiales de la coupe est dessiné. |
| **Exhibition uniquement -- pas en Ligue des Masters** | Pour le Kick Off et les matchs amicaux : une ligue historique, des légendes, etc. Ses clubs ne jouent jamais de saison de Ligue des Masters, donc la ligue reste seule : pas de division au-dessus ni au-dessous, pas de places européennes, pas de coupes. Elle apparaît quand même dans la liste des équipes de la Ligue des Masters ; choisissez votre club dans une autre ligue. |
| **Formation** | Comment les clubs de la ligue se placent. Choisissez une des formations des clubs du jeu (4-2-3-1, 4-1-2-3, 4-3-3, 5-3-2 ... ; la liste indique combien de clubs du jeu la jouent) : chaque nouveau club reçoit une copie de la tactique d'un club du jeu avec cette formation, et son meilleur onze est aligné en conséquence à la construction. Vide : celle du jeu, un 4-2-3-1 fixe. Un club peut avoir la sienne (**Modifier le club**). |

Le **Nom du monde** (sur la même page) doit commencer par `_FL26`. Après la **Construction**, la
colonne **ID de la ligue** montre l'id de compétition de chaque ligue dans le jeu, celui que porte
son fichier de logo. La colonne **#** est la place de la ligue dans l'ordre (**Monter** / **Descendre**),
et **Select Team** dit où le dernier Build l'a mise : *oui*, *à la place de* l'un des groupes du jeu, ou
*pas de place (elle se joue)*. Un `*` veut dire que l'ordre a changé depuis : refaites un Build pour voir
où elle va. Glisser une ligue sur la page **Ligues** ne la déplace qu'entre les places que les ligues de son continent ont déjà ici (0.2.0 ; avant, tout l'ordre passait par continent, et les ligues d'Amérique du Nord et d'Océanie finissaient toujours dernières).

**Tournois de pré-saison** (bouton sur la même page) : des tournois amicaux à élimination directe de 4 ou 8 clubs invités en juillet, avant la saison, appariés dans l'ordre donné (le premier contre le deuxième ...). Un club est celui d'une nouvelle ligue ou un club du jeu (son id) ; au moins un doit venir d'une nouvelle ligue, dont le pays accueille le tournoi. Une carrière commence en août, donc le premier se joue la deuxième saison. Chaque tournoi peut avoir son **Logo** ; vide : un logo est dessiné.

**Coupes des pays du jeu** (bouton sur la même page) : une coupe de la Ligue -- la Carabao Cup, par exemple -- pour des ligues du jeu. Cochez **Coupe de la ligue** à côté d'une ligue : 16 clubs de cette ligue et de celle du dessous, selon le classement (au-delà de 16, par un tour préliminaire début septembre, 0.1.7), un match par tour de fin septembre à décembre, les jours que le calendrier des ligues et coupes du jeu laisse libres. **Supercoupe**, le champion contre le vainqueur de la coupe fin juillet, seulement là où le jeu n'en a pas (Brésil, Chili, Écosse, Grèce, États-Unis) ; une nouvelle carrière n'a pas encore de vainqueur de coupe, la première se joue donc le deuxième été. Nom vide : le nom de la ligue et *League Cup* / *Super Cup*. **Logo** à côté de chaque nom (0.2.0) : une image pour cette coupe ; sans elle, un emblème avec les initiales de la coupe.

**Places européennes des ligues du jeu** (bouton sur la même page) : quelles places de la Premier League, de la LaLiga, de la Serie A ... vont dans quelle compétition européenne. La liste montre les places du jeu ; cochez **Places propres pour cette ligue** pour les changer. Une ligue non cochée garde celles du jeu, une ligue cochée sans lignes n'envoie personne.

**Classement UEFA** (même page, 0.1.7) : toutes les ligues européennes du monde -- celles du jeu et
vos nouvelles premières divisions -- dans une seule liste, le pays le plus fort d'abord. Glissez une
ligue (ou **Monter** / **Descendre**) pour changer l'ordre, décochez-la pour ne lui donner aucune
place européenne, et **Ordre de l'UEFA** remet la liste au classement des associations de l'UEFA
pour 2026-27. La partie droite montre ce que reçoit chaque ligue, et **OK** l'écrit : les places de
la clé de l'UEFA pour 2024-27 -- le rang 1 a cinq places en Ligue des champions, le rang 6 deux et
une place de barrage, le rang 30 une place au deuxième tour de qualification de la Ligue des
champions, et ainsi de suite, la place du vainqueur de la coupe en Ligue Europa comprise. Un monde
n'a jamais les 55 pays de l'UEFA, donc les places des rangs absents vont tour à tour aux clubs
suivants des ligues les plus fortes, un tour à la fois, et chaque compétition reste pleine : avec
douze ligues, les 6e, 7e et 8e d'Angleterre vont aux qualifications de la Ligue des champions, par
exemple. Après la 30e ligue il ne reste aucune place, et la liste le dit. Les places de
qualification vont aux tours dans l'ordre de la clé, le pays le plus fort au tour le plus proche de
la phase de ligue. Ensuite vous pouvez encore changer à la main les places de n'importe quelle ligue
(*Europe* sur la ligue, *Places européennes des ligues du jeu*) : Build prend les places, pas le
classement.

**Places sud-américaines** (même page, 0.1.7, lecture seule) : pour chaque ligue sud-américaine,
les quatre du jeu et les vôtres, quelles positions vont en Copa Libertadores, dans ses
qualifications et en Copa Sudamericana. Les places en Libertadores des ligues du jeu sont celles du
jeu (Brésil 1er-4e et le vainqueur de la Copa do Brasil, qualifications 5e-6e, et ainsi de suite --
ce que montre aussi le Competition Info du jeu) ; la Copa Sudamericana est celle de Mod Studio,
donc la liste montre combien de clubs chaque ligue du jeu y envoie avec vos places dedans : d'abord
vos ligues, puis le Brésil, l'Argentine, le Chili et la Colombie, un club chacun à tour de rôle
jusqu'à 32. Un club déjà en Libertadores ou dans ses qualifications laisse sa place au suivant de
sa ligue. **Vérifier le plan** affiche la même liste dès que le monde a une place en Libertadores
ou en Sudamericana.

**Noms des compétitions** (bouton sur la même page) : un nouveau nom et un logo pour les coupes, supercoupes et compétitions continentales du jeu -- la FA Cup, la Ligue des champions, la Libertadores ... -- et pour les coupes continentales que le monde construit (CAF Champions League, Coupe de la Confédération, AFC Champions League Two, Copa Sudamericana, CONCACAF Champions Cup, OFC Champions League, AFC Challenge League, Supercoupe de la CAF). Toutes les phases de la compétition prennent le nom. Vide : celui du jeu. Les ligues du jeu se renomment dans *Game's leagues and clubs*.

**Ordre des championnats** (bouton sur la même page, 0.2.0) : l'ordre des pays dans le Select Team de la Ligue des Masters et dans la liste des équipes Kick Off / Edit. *Par continent* est l'ordre du jeu (Europe, Amériques, Asie, puis Afrique, chacun de A à Z). *Tous les pays de A à Z* les met tous dans une seule suite alphabétique, et *Mon propre ordre* vous laisse les placer comme vous voulez (glisser, ou Up / Down). Les championnats d'un pays restent ensemble, première division d'abord, et les compétitions de clubs, les groupes "Other" et Classic Teams viennent après les pays. L'Allemagne, les USA et le Japon sont dans les groupes "Other" du Select Team, ils ne bougent donc que dans Kick Off. Relancez ensuite le Build du monde.

**Saisons des championnats du jeu** (même page, 0.2.0, expérimental) : le Japon, la Chine, le Brésil, le Chili et l'Arabie saoudite jouent de février à décembre dans le jeu. Cochez-en un et ses championnats jouent d'août à mai comme l'Europe : la saison commence en août, les montées et descentes ont lieu en été, ses coupes passent aux dates d'août à mai et ses places continentales viennent du classement terminé en mai. Une division à vous sous l'un de ces championnats le suit. La Colombie et les USA jouent Apertura et Clausura et ne peuvent pas changer. Relancez le Build du monde et commencez une nouvelle carrière.

**Nouveaux clubs** : choisissez la ligue, puis **Modifier le club** (nom, nom court, écusson),
**Coller des noms...** ou **Charger des noms depuis un fichier...**. Un nom vide devient
`<ligue> 01`, `<ligue> 02` ... ; un club sans écusson reçoit un écusson numéroté. Les maillots sont
empruntés aux clubs du jeu. Un tel maillot est sous licence, et le mode Edit refuse de le modifier
("You cannot edit this strip") : cochez **Maillots modifiables dans le jeu** sur la page Construire
et les nouveaux clubs n'en empruntent aucun ; chacun porte un maillot simple que Edit > Teams >
Strip modifie comme celui de n'importe quel club, Paste Image compris.
Avec Kit Server installé, **Créer les maillots des nouveaux clubs** (page Construire, activé sauf si
vous le décochez, 0.2.1) crée pour chaque nouveau club domicile, extérieur, troisième et gardien dans
les couleurs de son maillot (celles de NewLife, ou de l'écusson à défaut), avec l'écusson sur la
poitrine et le short, pour des ligues entières d'un coup à l'activation du monde. Un écusson ajouté
plus tard (Importer des écussons) passe sur les maillots à l'activation suivante. Un club qui a son
propre maillot Kit Server, ou seulement l'écusson numéroté, n'en reçoit pas.
Les noms gardent leurs accents (FK Željezničar) ; le nom court de trois lettres n'en a pas, comme
dans le jeu, donc Č, Ž, Đ y deviennent C, Z, D. Après la **Construction**, la colonne **ID du
club** montre l'id de chaque club dans le jeu.

**Entraîneur** : dans **Modifier le club** d'un nouveau club, vous pouvez nommer son entraîneur. Vide : un nom inventé à partir des joueurs du pays du club (un club croate reçoit un nom comme `Tomislav Krovinović` ; le même à chaque Build), ou un nom numéroté (`FL M0001` ...) pour un pays dont le jeu a peu de joueurs. **Photo de l'entraîneur** en dessous lui donne un portrait (comme **Portrait de l'entraîneur...** sur la page Joueurs) ; *Ligues et clubs du jeu* > **Modifier le club** l'a aussi pour les clubs du jeu.

**Formation** : dans **Modifier le club** d'un nouveau club, vous pouvez lui donner sa propre formation ; *Comme la ligue* garde celle de la ligue. Le terrain sous la liste montre la place de chacun.

**Stade à domicile** (0.1.7) : dans **Modifier le club**, un stade de la bibliothèque de Stadium Server pour le club ; l'emplacement et le nom sont remplis depuis le dossier, changez le nom si vous voulez. Il est écrit dans le `map_teams.txt` de Stadium Server quand le monde est activé (et quand le monde actif est reconstruit), donc l'id d'un nouveau club n'a jamais à être cherché. Une ligne à vous pour le même club est désactivée en attendant, et réactivée quand le club n'a plus de stade ici. *Ligues et clubs du jeu* > **Modifier le club** l'a aussi pour les clubs du jeu. Stadium Server doit être installé (page *Stades*), ou le module de stades propre à SPFL26 (`common\stadiums.lua` avec son dossier `content\stadiums`) : depuis 0.1.8, Mod Studio y écrit quand Stadium Server n'est pas installé.

**Clubs que le jeu a déjà.** Une place d'une nouvelle ligue peut accueillir un des clubs du jeu au
lieu d'un nouveau : sélectionnez la place, puis **Club du jeu...**, et cherchez par nom ou ID de
l'équipe (**Seulement les clubs sans ligue** réduit la liste). Le club garde son nom, son écusson,
ses maillots, son entraîneur et ses joueurs, et ne joue que dans votre ligue. S'il joue quelque
chose dans le jeu (une ligue, une coupe, la Ligue Europa ...), vous choisissez qui y prend sa
place : un club du jeu qui ne joue rien, ou un nouveau club que vous nommez. **Il garde ses places dans les compétitions continentales** (0.1.8, #84) le laisse disputer la Ligue des champions, la Libertadores ou l'AFC Champions League où il est : un club qui dans le jeu ne joue que le continent déménage simplement, et un club qui joue aussi une ligue du jeu ne cède que la ligue et les coupes au club que vous choisissez. À partir de la deuxième saison, les places de votre ligue décident qui y va. Un tournoi de pré-saison (les *Pre-season friendly Cups* de SPFL26) ne compte pas : le club continue d'y jouer, comme les clubs de Premier League (0.1.7). **Modifier le club** sur un club du jeu change son nom, son blason, le portrait de l'entraîneur et le stade, comme sur *Ligues et clubs du jeu* (0.1.7). Ainsi aucune
compétition du jeu ne change son nombre de clubs ; les ligues du jeu ne gardent leurs dates
qu'avec le nombre pour lequel elles ont été faites. Les sélections nationales, les équipes
classiques et par défaut et les clubs de moins de 18 joueurs ne peuvent pas être choisis.
**Nouveau club ici** rend la place à un nouveau club. Le club n'apparaît plus dans les groupes
*Other ... clubs* de la Master League.

**Club NewLife...** (0.1.8, #83) place des clubs de la NewLife Database, avec leurs effectifs, à la place sélectionnée et aux suivantes : cochez un ou plusieurs clubs (recherche par club ou par ligue), chacun prend sa place dans l'ordre. Une ligue faite à la main reçoit ainsi de vrais clubs. Ouvrez d'abord la NewLife Database sur la page *NewLife*.

**Insérer un club** et **Retirer le club** ajoutent une place avant le club sélectionné ou la
retirent (10 à 24 clubs) ; noms, écussons, entraîneurs et changements de joueurs suivent leurs
clubs. Vérifiez les places européennes de la ligue, puis relancez la **Construction**. Tout
changement des clubs d'une ligue demande une **nouvelle carrière**.

**Déplacer vers une autre ligue...** (0.1.7) emmène le nouveau club sélectionné à la fin d'une autre nouvelle ligue, avec son nom, son nom court, son écusson, son entraîneur, sa formation, ses maillots, son id NewLife et ses changements de joueurs ; la ligue qu'il quitte garde un club de moins. Un club du jeu se déplace avec **Club du jeu** : retirez-le d'une ligue, mettez-le dans l'autre.

**Ligues et clubs du jeu** : nouveaux noms, logos et écussons pour ce que le jeu a déjà.

**Importer des écussons...** (0.1.8, sur cette page et sur *Nouveaux clubs*) : des écussons pour beaucoup de clubs d'un coup. Choisissez un dossier d'images ; chacune est associée à un club par le nom du fichier -- le nom du club (`Alianza Lima.png`, `alianza_lima_r_l.png`) ou son ID d'équipe (`2287.png`, le `e_2287_r.png` des packs d'écussons). La liste montre chaque association cochée ; décochez une mauvaise avant **OK**. Un club qui a déjà un écusson le garde, sauf si **Remplacer les écussons déjà définis** est coché. Les images restent dans ce dossier et Build les lit là, gardez-le donc. (L'association par nom est une idée du script d'écussons de Xxspedd.)

**Échanger de ligue avec un club...** (0.1.7) : deux clubs des ligues du jeu échangent leurs places -- un promu contre un relégué, un club de la ligue d'un pays contre un club d'un autre. Chacun prend les places de l'autre dans la ligue, les coupes et les compétitions européennes, donc chaque ligue du jeu garde son nombre de clubs. Un club qui joue dans une nouvelle ligue de la recette ne peut pas aussi être échangé. **Annuler les changements du club** retire l'échange. Puis **Construire** à nouveau et commencez une nouvelle carrière.

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
  pour lui donner le vôtre ; depuis 0.2.0 cet effectif part du niveau de sa division (environ
  72 en première division, jusqu'à 57 à partir de la cinquième) ;
- **Visage** : **Choisir...** un dossier de visage (section 8.1). **Effacer** redonne le visage du
  jeu. Un nouveau joueur sans visage reçoit un visage du pack de visages des regens qui va avec sa
  nationalité, avec son portrait (0.1.5.5, modules installés et `fl26regen` actif, section 5).
  Un visage fait pour un autre joueur
  apporte aussi l'apparence de son corps : les bras et les jambes ont la couleur de peau de ce
  visage (0.1.9) ;
- **Portrait** : **Choisir...** une image (PNG ou JPG) pour le petit portrait du joueur dans les listes
  de l'effectif, sans visage à lui. Le Build la met en 180 x 180 ; elle passe avant le portrait d'un
  dossier de visage ;
- **Monter dans l'ordre / Descendre dans l'ordre** : l'ordre de l'effectif. Les onze premiers
  commencent le match ;
- **Ajouter un joueur** (une copie du joueur choisi, avec un nouvel id ; clubs du jeu seulement),
  **Retirer du club** (un nouveau club garde au moins 18 joueurs) ;
- **Meilleur onze** place le joueur le plus fort à chaque poste ; **Niveau de l'effectif...**
  monte ou baisse chaque capacité de tout l'effectif ;
- **Terrain** (nouveaux clubs) : le onze de départ dans la formation du club. Choisissez un joueur
  dans la liste, puis cliquez sur un poste pour l'y placer ; celui qui s'y trouvait prend sa place dans l'ordre de l'effectif ;
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

#### Transferts, sélections, ID, le portrait de l'entraîneur

- **Recruter des joueurs...** (un club) : une liste de tous les joueurs du jeu et de tes nouveaux
  clubs, avec un filtre de nationalité et une recherche par nom ; choisis-en plusieurs avec Ctrl
  ou Maj. Ils passent dans ce club et leur ancien club les perd (un transfert). **Transférer
  vers...** fait la même chose dans l'autre sens : le joueur sélectionné part dans le club que tu
  choisis. La liste affiche *de : ...* sur le club qui le reçoit et *vers : ...* sur le club qu'il
  quitte ; **Retirer du club** sur l'une ou l'autre ligne annule le transfert. Un club a au plus
  40 joueurs.
- **Convoquer des joueurs...** (une sélection : choisis *Équipes nationales* dans la liste des
  ligues) : la liste s'ouvre sur le pays de la sélection. Les joueurs rejoignent la sélection **et
  restent dans leurs clubs**, comme dans le jeu. **Retirer du club** retire le joueur de la
  sélection (pas de son club). Une sélection a au plus 26 joueurs ; un joueur est dans une seule
  sélection à la fois. Ta liste est écrite dans les données du jeu, mais dans une carrière Master
  League le jeu choisit lui-même ses sélections, donc tes convocations n'y restent pas.
- Un joueur qui arrive va à la fin de l'ordre de l'effectif avec un numéro libre ; l'effectif
  qu'il quitte resserre son ordre.
- Colonne **ID du joueur** : l'id de chaque joueur -- celui du jeu, celui que tu as tapé, ou celui
  que le dernier **Build** a donné à un nouveau joueur (fais un Build avant de créer des minifaces
  ou des visages pour les nouveaux joueurs). **Exporter en CSV...** l'écrit comme `player_id` ;
  Importer un CSV ignore cette colonne.
- **ID du club** (à côté du club) et **ID du joueur** (onglet Bases) : seulement pour tes **nouveaux**
  clubs et joueurs. Vide = le prochain ID libre au Build. Tape-en un quand un pack de maillots,
  d'écusson ou de visages a été fait pour un ID précis. ID de club : du premier après les clubs du
  jeu (71578) jusqu'à 81919 ; ID de joueur : au-dessus du plus haut du jeu jusqu'à 399999 ; jamais
  un que le jeu ou un autre nouveau club ou joueur a déjà. L'ID sert partout où le monde parle du
  club ou du joueur (effectifs, compétitions, maillots, écussons, entraîneur, visages). Les clubs
  et joueurs du jeu gardent leurs ID : leurs maillots, visages et tes sauvegardes en dépendent.
- **Portrait de l'entraîneur...** : un PNG ou JPG pour l'entraîneur du club. Le Build le met en
  256 x 256 dans `common/render/symbol/coach/coach_<ID de l'entraîneur>.png`, là où le jeu range
  les portraits d'entraîneurs. Appuie de nouveau pour enlever l'image.

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

**Gardez le Team.bin du monde.** Il est dans le dossier du monde et contient les clubs et les barrages du monde. Le remplacer par le Team.bin du jeu les fait disparaître, et les compositions ont l'air réparées seulement parce que les clubs n'y sont plus (GitHub #75). Construisez plutôt le monde à nouveau.

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
un tel monde : reconstruisez-le.) **Logo de la Ligue Europa Conférence** à côté : votre propre
image pour elle ; vide : un emblème UECL est dessiné (le jeu n'en a pas). **Nom de la Ligue
Conférence** en dessous : le nom que le jeu lui donne, *FL Conference League* si vide (tapez
*UEFA Conference League* si vous voulez) ; un nouveau nom demande de reconstruire le monde.
**Seulement les nouvelles coupes européennes...** utilise les deux aussi.

> **Places européennes.** Les places que vous donnez à vos ligues viennent après celles des ligues
> du jeu. Chaque compétition prend 36 clubs ; les places au-delà de la 36e ne donnent rien, et
> **Vérifier le plan** le signale. Les nouvelles ligues sans places n'envoient personne en
> Europe, et Vue d'ensemble vous en avertit. Les tenants du titre passent en premier : les
> vainqueurs de la Ligue des champions et de la Ligue Europa prennent deux des places directes de la
> Ligue des champions, celui de la Ligue Conférence une place en Ligue Europa. Le tirage de la
> phase de ligue suit les règles de l'UEFA : aucun club n'affronte un club de son propre pays,
> et au plus deux de ses adversaires viennent d'un même autre pays.
>
> **Les qualifications d'août.** Une place *(qualifications)* envoie le club dans les
> qualifications d'août de cette compétition : jusqu'à trois tours (0.1.7) -- le deuxième tour de
> qualification (jours 220 et 225), le troisième (229 et 236) et le barrage (243 et 250 ; celui de
> la Ligue des champions 244 et 251) --, chacun de 16 clubs en deux matchs ; les huit effectifs
> les plus forts sont têtes de série (retour à domicile), et deux clubs d'un même pays ne se
> rencontrent jamais. Les vainqueurs passent au tour suivant, et du barrage à la phase de ligue.
> Les perdants descendent comme à l'UEFA : en *Ligue des champions (qualifications)*, ceux du
> barrage en Ligue Europa, ceux du troisième tour au barrage de la Ligue Europa, ceux du deuxième
> au troisième tour de la Ligue Europa ; la *Ligue Europa (qualifications)* de même vers la Ligue
> Europa Conférence ; les perdants de la *Ligue Europa Conférence (qualifications)* sont
> éliminés. Les premières places de la liste vont au barrage, les suivantes aux tours précédents.
> Le nombre de tours d'un monde dépend de ses places, et chaque tour de la Ligue Europa Conférence
> demande 8 clubs de plus : 116 places en Europe pour les trois barrages seuls, 132 pour les neuf
> tours. Avec les places du jeu seul, il n'y a que les barrages ; le résumé de Build indique les
> tours du monde (*qualifications d'août*). Chaque barrage retire 8 places directes aux
> compétitions où vont ses vainqueurs et ses perdants : avec les trois, la Ligue des champions
> prend 28 clubs directement, la Ligue Europa et la Ligue Europa Conférence 20 chacune. Une place
> au-delà se joue dans les qualifications de cette compétition. Les places de qualification de
> vos ligues passent avant celles du jeu (Portugal, Écosse, Grèce, Danemark ...).

Ensuite, **commencez une nouvelle carrière Master League** (ou Become a Legend). Les nouvelles
ligues se trouvent sous leur pays dans Select Team et Kick Off. Dans les listes de Kick Off et
Edit, un nouveau pays d'Asie vient avant *Other Clubs (Asia)*, un pays d'Amérique du Sud avec ceux du jeu (après la Colombie, avant la MLS, 0.1.7), un pays de la
CONCACAF après la MLS,
et les pays d'Afrique et d'Océanie (le jeu n'a pas de section pour eux) après l'Asie.

> **Coupes des autres continents.** Quand vos ligues envoient des clubs en Ligue des champions
> CAF, en Coupe de la Confédération CAF, en AFC Champions League Two, en AFC Challenge League,
> en Copa Sudamericana, en CONCACAF Champions Cup ou en OFC Champions League (ces trois
> dernières nouvelles en 0.2.0), la **Construction** crée aussi ces coupes. Chacune a 32, 16, 8
> ou 4 clubs : d'abord les places de vos ligues, puis les ligues du jeu de ce continent (Asie,
> Amérique du Sud, et la MLS pour celle de la CONCACAF) la complètent ; pour l'AFC Challenge
> League, ce sont les 11e-14e de la J1 League, les 10e-13e de la Super League chinoise et les
> 11e-14e de la Saudi Pro League. À 8 ou plus, des groupes de quatre puis une phase à
> élimination directe ; en dessous de 8, l'élimination directe seule. La CONCACAF Champions Cup
> se joue toujours à élimination directe, à 16 clubs au plus, comme la vraie, et deux clubs
> d'une même ligue ne se rencontrent pas à son premier tour quand c'est évitable. Elles sont
> remplies fin août, avec les classements des ligues. Un club qui joue déjà la Copa
> Libertadores, ses qualifications ou l'AFC Champions League n'entre pas dans leur tirage. Une
> coupe CAF ou OFC avec moins de 4 places prend d'abord les places
> de la coupe CAF suivante (avec deux et deux, la Ligue des champions CAF a les quatre), puis
> les positions suivantes de vos ligues. **Supercoupe de la CAF** (page Construire, cochée par
> défaut) fait se rencontrer les vainqueurs des deux coupes CAF en un match fin juillet, à partir
> de la deuxième saison de la carrière.

> **Les sauvegardes appartiennent à un monde.** Une carrière sauvegardée avec un monde activé a
> besoin de ce même monde pour se charger.

**Fichier → Enregistrer la recette** enregistre tout dans un fichier `.json` ; **Ouvrir une
recette** le recharge. **Construction** garde aussi une copie de la recette dans
`%APPDATA%\FL26ModStudio\recipes\<monde>.json`, et Mod Studio rouvre la dernière recette au
démarrage : le fermer sans enregistrer ne perd rien de ce qui a été construit.

**Seulement les nouvelles coupes européennes...** (page Construire) construit un monde avec
seulement la nouvelle Ligue des champions et la Ligue Europa -- phase de ligue à 36 et barrages de
février -- et la Ligue Europa Conférence quand **Inclure la Ligue Europa Conférence** est coché. Pas de
nouvelles ligues ; les clubs et ligues du jeu restent tels quels et ta recette ne change pas. Il
demande un nom de monde (`_FL26Euro` par défaut), le construit et propose de l'activer. Un seul
monde peut être activé, il remplace donc un monde avec de nouvelles ligues : un monde avec de
nouvelles ligues a déjà le nouveau format.

> **Ligues d'exhibition et Master League.** Une ligue cochée *Exhibition uniquement* ne joue jamais
> de saison de Master League, mais le jeu a une seule liste d'équipes pour Kick Off et la Ligue
> Master, donc ses clubs apparaissent toujours quand tu choisis ton club pour une nouvelle
> carrière. Ne commence pas de carrière avec l'un d'eux. **Vérifier le plan** et **Construire** le
> signalent.

### 8.3 Limites

| | |
|---|---|
| Nouvelles ligues par monde | 39 |
| Clubs par ligue | 10 – 24 |
| Nouveaux clubs au total | 793 |
| Nombre de rencontres entre clubs | 1 – 4 |
| Ligues qui se divisent | 2 par monde |
| Divisions dans un pays | jusqu'à la 7e |
| Joueurs par nouveau club | 30 au départ ; retirez-en jusqu'à 18 ; avec des recrues, jusqu'à 40 |
| Joueurs par sélection | 26 |
| Coupe nationale | la première division et celle du dessous, jusqu'à 44 clubs. Jusqu'à 32 les tailles sont 2-16, 18, 20, 24, 28, 30 et 32 -- la plus grande qui tient (22 clubs donnent une coupe de 20) ; de 33 à 43 elles deviennent 32 ; 44 ou la taille d'une coupe du jeu reste ; plus de 44 : la première division seule |

### 8.4 NewLife Database : vrais clubs et vrais joueurs

La NewLife Database est un téléchargement à part, avec de vrais clubs et joueurs pour les
nouvelles ligues : noms, dates de naissance, postes et notes à l'échelle du jeu, et les couleurs
des clubs. Chaque club et chaque joueur y a son propre ID, le même dans toutes les versions de la
base. Elle n'est pas sur GitHub : téléchargez-la depuis le canal NewLife de notre
[Discord](https://discord.gg/StQqtk3G3M). Elle vient en parties, une par continent (un grand en
plusieurs), plus *Free agents*, chacune de moins de 10 Mo. Ne téléchargez que celles qu'il vous faut.

1. Mettez les parties téléchargées dans un même dossier. Ne les décompressez pas : Mod Studio
   lit les zip tels quels. (Ce sont des zip LZMA : 7-Zip les ouvre, le lecteur de zip de Windows non.)
2. **League Builder > NewLife Database > Ouvrir la NewLife Database...** et choisissez ce dossier.
   La liste montre toutes les ligues de ces parties : pays, clubs, clubs que le jeu a déjà
   (*Dans le jeu*), joueurs et niveau. Cliquez sur une ligue pour voir ses clubs. Un clic sur
   l'en-tête d'une colonne (Ligue, Pays, Clubs, Joueurs, Niveau) trie selon elle, un second
   clic inverse l'ordre (0.2.0) ; la liste s'ouvre triée par pays.
3. Sélectionnez une ou plusieurs ligues (Ctrl ou Maj pour plusieurs) et appuyez sur **Ajouter à
   la recette**. Chacune devient une nouvelle ligue avec ses clubs et leurs effectifs, première
   division de son pays. Changez sa division, son format, ses places européennes et le reste dans
   *Nouvelles ligues*, comme pour toute autre ligue.
4. **Build**, activez le monde et commencez une nouvelle carrière (section 8.2).

- **Votre propre composition** (0.1.7) : décochez un club dans la liste de droite pour le
  laisser de côté, et **Ajouter un club d'une autre ligue...** amène des clubs de n'importe
  quelle ligue de la base -- la première division de cette saison est celle de l'an dernier avec
  deux promus, par exemple. La ligne de la ligue porte un `*`. Un club ne peut être que dans une
  ligue de la recette.
- Une ligue prend de 10 à 24 clubs, ses nouveaux clubs et ceux du jeu ensemble ; les autres sont en gris. Une ligue que le jeu a déjà (la Premier League, le Championship ...) est grisée aussi (0.1.9) : elle est déjà dans le jeu, amenez-la à la saison NewLife avec **Amener les ligues du jeu à cette saison...** plus bas. La ligne du bas compte les nouveaux
  clubs de la recette par rapport aux 793 qu'un monde accepte.
- Les clubs que le jeu a déjà entrent dans la nouvelle ligue comme clubs du jeu (section 8),
  à ses dernières places, avec leur nom, écusson, maillots et joueurs. Celui qui joue aussi une
  compétition du jeu (Bâle et Young Boys jouent la Ligue Europa) a besoin du club qui prend sa
  place là-bas : *Nouveaux clubs*, choisissez-le, **Club du jeu**. Jusque-là, Build dit lesquels.
  Un club dont la seule compétition du jeu est continentale (Ludogorets en qualifications de la
  Ligue des champions) continue de la jouer seul (0.1.9).
- Un joueur que le jeu a déjà (le même joueur sous le même nom, par exemple Urbański au Górnik
  dans le jeu et au Legia dans NewLife) passe au club NewLife au lieu d'être créé une deuxième fois
  (0.1.7) : il garde son visage, son nom et son ID et prend le poste et les notes de NewLife. Il
  reste où il est si son ancien club passait sous 18 joueurs ou si une ligue précédente l'a déjà ;
  il est alors laissé hors du club NewLife, sans copie (0.1.8).
- Un club NewLife reçoit un ID de monde à lui (0.1.8), dans le bloc que le jeu lit pour les
  clubs, après les ID que le constructeur donne aux siens. La colonne **ID du club** de la page
  Clubs nouveaux le montre, et le `map.txt` du Kit Server est bâti dessus. Un monde fait avant
  0.1.8 doit être reconstruit et la carrière recommencée pour que les maillots suivent. Depuis
  0.1.8, un club garde l'ID de son premier Build (la recette s'en souvient) : retirer, ajouter ou
  mettre à jour une autre ligue ne le déplace plus.
- **Une version plus récente de NewLife** (0.1.8) : mettez ses parties dans un dossier (sans
  les mélanger avec les anciennes), **Ouvrir la NewLife Database...** sur ce dossier et appuyez sur
  **Mettre mes ligues à jour vers cette version**. Chaque ligue ajoutée depuis une version plus
  ancienne est listée avec ce qui change (*16 clubs maintenant, 18 dans NewLife 1.3 (5 nouveaux,
  3 absents)*) et une case **Garder mes clubs** : cochée, la ligue garde ses clubs ; décochée,
  elle reçoit les clubs qu'elle a dans la nouvelle version. Dans les deux cas, les effectifs
  viennent de la nouvelle version, et la ligue garde son nom, sa division, son format, ses places
  européennes et ses coupes ; un club qui reste garde son entraîneur et le blason que vous avez
  choisi, et vos propres clubs mis dans la ligue restent. Les changements de joueurs faits dans
  *Joueurs* pour ces clubs sont remplacés. Ensuite Build et nouvelle carrière.
- **Les ligues du jeu dans la saison NewLife** (0.1.8) : avec une NewLife Database ouverte,
  appuyez sur **Amener les ligues du jeu à cette saison...**. Chaque ligue du jeu que la version
  contient est listée avec ce qui lui arrive, chacune avec une case. Un club promu ou relégué entre
  deux ligues du jeu échange sa place avec un club qui va dans l'autre sens (Burnley en
  Championship, Coventry en Premier League), comme *Échanger de ligue avec un club...*. Un club
  relégué hors des ligues du jeu (Leicester en League One) devient le club promu à sa place
  (Bolton) : nom, nom court, blason et effectif ; son maillot, son stade et son entraîneur restent.
  Chaque club des ligues cochées reçoit son effectif NewLife : les joueurs que le jeu a arrivent de
  leur ancien club, ceux qu'il n'a pas sont ajoutés, les autres partent libres. Les ligues gardent
  leur nombre de clubs, leur format et leurs coupes. Les clubs que vous avez déjà changés à la main
  (un échange, un nom, un club d'une nouvelle ligue, des changements de joueurs) restent tels quels.
  Le refaire avec une version plus récente remplace ce qu'a fait l'ancienne ; **Annuler les ligues
  du jeu** retire tout. Build et nouvelle carrière.
- Un club NewLife reçoit un écusson en forme de blason à ses couleurs et le maillot du jeu aux
  couleurs les plus proches, jusqu'à ce que vous lui donniez les vôtres (**Modifier le club**).

## 9. Paquets de ligues : partager une ligue entière

Un moddeur crée une ligue une fois — clubs, noms, écussons, logos, effectifs, visages — et
partage **un seul fichier `.fl26pack`**. N'importe qui l'ajoute à sa propre recette et construit.

**Créer un paquet** (Paquets de ligues → **Créer un paquet...**, ou Fichier → Créer un paquet de
ligues) :

1. Nom, auteur, version et une courte description.
2. Cochez les ligues à inclure (**Tout cocher** / **Tout décocher** au-dessus de la liste). Une
   ligue placée sous une autre nouvelle ligue doit l'accompagner.
   Un paquet que la recette a déjà (le même nom) est remplacé par la nouvelle version (0.1.7) :
   les ligues, clubs et changements de joueurs de l'ancien sortent, ceux du nouveau entrent.
3. Si vous le voulez, **aussi mes modifications des ligues, clubs et joueurs du jeu**.
4. **Ce qui va dedans** (0.1.8) : tout est coché ; décochez ce que vous ne voulez pas partager --
   **Effectifs**, **Visages et portraits des joueurs**, **Blasons et logos des ligues**, **Entraîneurs**,
   **Couleurs des maillots**, **Stades à domicile** (la ligne de Stadium Server, pas le stade lui-même)
   et (0.2.1) **Maillots** (ceux de Kit Server des clubs) et **Tableaux de score** (celui de Scoreboard
   Server de chaque ligue), pris dans votre jeu tel qu'est le monde maintenant (kit-server\map.txt et
   scoreboard-server\map_competitions.txt).
   Un paquet sans effectifs va sur une base mise à jour à part, comme NewLife, sans remettre les anciens.
5. Enregistrez. Le fichier contient les images, les visages, les maillots et les tableaux de score, pas
   des chemins de votre ordinateur. Qui l'ajoute les reçoit en place, avec ses propres ids d'équipes et
   de ligues, au Build (Kit Server / Scoreboard Server requis). Les maillots ajoutent environ 10 Mo par
   ligue et un tableau de score environ 7 Mo : un tel paquet dépasse souvent la limite de 10 Mo de
   Discord, partagez-le par un service cloud (Google Drive, Dropbox, MEGA ...) ; le programme le signale.

**Ajouter un paquet** (Paquets de ligues → **Ajouter un paquet...**, Fichier → Ajouter un paquet
de ligues, ou déposez-le sur Installer des mods) :

1. Le programme montre ce qu'il contient et vous demande. Un paquet de plusieurs ligues les liste,
   toutes cochées : décochez celles que vous ne voulez pas (0.2.1). Une ligue placée sous une autre
   ligue du paquet amène celle-ci avec elle.
2. Une ligue dont vous avez déjà le nom est ajoutée sous la forme `Nom (Paquet)`.
   Un paquet fait sans effectifs va sur cette ligue : ses blasons et entraîneurs vont aux clubs du
   même nom, vos joueurs restent et le programme dit combien de clubs il a trouvés.
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
