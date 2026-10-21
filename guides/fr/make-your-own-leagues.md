# Créer vos propres ligues et packs : chaque clic, dans l'ordre

> [English](../en/make-your-own-leagues.md) · [hrvatski](../hr/make-your-own-leagues.md) · [español](../es/make-your-own-leagues.md) · [português](../pt/make-your-own-leagues.md) · **français**

> L'autre guide pas à pas : [Installer un pack prêt](install-a-pack.md)
> · chaque page et option expliquée : [mod-studio-guide.md](mod-studio-guide.md)
> · questions : [faq.md](../../docs/faq.md) · aide : [Discord](https://discord.gg/StQqtk3G3M)

Cette page vous mène de rien jusqu'à vos propres ligues dans le jeu : de vraies ligues avec de
vrais clubs et joueurs de la **NewLife Database**, réglées comme vous le voulez, construites,
jouées et partagées avec d'autres. Elle dit quoi cliquer, le nom exact de chaque bouton et de
chaque champ tel que Mod Studio l'affiche, et ce que vous devez voir après chaque étape. Faites
les étapes dans l'ordre. Si vous voyez autre chose que ce que dit une étape, arrêtez-vous là et
regardez dans [Si quelque chose ne va pas](#si-quelque-chose-ne-va-pas).

Trois mots que vous rencontrerez tout le temps :

- **Votre monde** : votre liste de ligues et tout ce que vous réglez pour elles. Vous le modifiez
  dans les onglets de **2. Mon monde**, et il s'enregistre tout seul un instant après chaque
  changement. Ce n'est qu'un plan : rien n'arrive dans le jeu avant le **Build**.
- **Dossier du monde** : ce que Build fait à partir de votre monde, un dossier dont le nom
  commence par `_FL26` (`_FL26MyWorld` si vous ne le changez pas). Le jeu le lit tant qu'il est
  dans le jeu (la case **MONDE ACTIF** en haut de la fenêtre affiche son nom).
- **Build** : le bouton qui transforme votre monde en ce dossier et le met dans le jeu.

**Sommaire**

- [Avant de commencer : la configuration unique](#avant-de-commencer--la-configuration-unique)
- [Étape 1. Obtenir la NewLife Database](#étape-1-obtenir-la-newlife-database)
- [Étape 2. L'ouvrir sur la page NewLife Database](#étape-2-louvrir-sur-la-page-newlife-database)
- [Étape 3. Choisir vos ligues](#étape-3-choisir-vos-ligues)
- [Étape 4. Choisir les clubs d'une ligue](#étape-4-choisir-les-clubs-dune-ligue)
- [Étape 5. Ajouter à votre monde](#étape-5-ajouter-à-votre-monde)
- [Étape 6. La page Ligues : chaque réglage d'une ligue](#étape-6-la-page-ligues--chaque-réglage-dune-ligue)
- [Étape 7. Exemple : un pays avec deux divisions](#étape-7-exemple--un-pays-avec-deux-divisions)
- [Étape 8. L'onglet Clubs : noms, écussons, maillots, clubs du jeu](#étape-8-longlet-clubs--noms-écussons-maillots-clubs-du-jeu)
- [Étape 9. La page Joueurs](#étape-9-la-page-joueurs)
- [Étape 10. Les limites qui arrêtent un Build](#étape-10-les-limites-qui-arrêtent-un-build)
- [Étape 11. Votre monde s'enregistre tout seul](#étape-11-votre-monde-senregistre-tout-seul)
- [Étape 12. Build](#étape-12-build)
- [Étape 13. Jouer : une NOUVELLE Master League, puis la vérification](#étape-13-jouer--une-nouvelle-master-league-puis-la-vérification)
- [Étape 14. Changer quelque chose plus tard](#étape-14-changer-quelque-chose-plus-tard)
- [Étape 15. Partager ce que vous avez créé](#étape-15-partager-ce-que-vous-avez-créé)
- [Si quelque chose ne va pas](#si-quelque-chose-ne-va-pas)

---

## Avant de commencer : la configuration unique

Faites d'abord, une fois, les étapes 1 à 3 de l'autre guide :
[fermer le jeu](install-a-pack.md#étape-1-fermer-le-jeu),
[télécharger Mod Studio](install-a-pack.md#étape-2-télécharger-mod-studio) et
[indiquer où se trouve votre jeu](install-a-pack.md#étape-3-indiquer-où-se-trouve-votre-jeu).
Puis revenez ici. Mod Studio extrait tout seul les tables du jeu, et **Construire et installer**
(étape 12) installe ses modules.

Gardez le jeu fermé tout le temps que vous travaillez dans Mod Studio.

Si un monde prêt depuis un zip (un Modpack) est dans le jeu maintenant, ce n'est pas grave : vous
pouvez construire votre propre monde à côté. Build demande d'abord, et retire le monde prêt du jeu
tant que le vôtre y est. Sa carte dans **2. Mon monde** reste, et **Activer** le remet.

---

## Étape 1. Obtenir la NewLife Database

La NewLife Database est un téléchargement à part, avec de vrais clubs et joueurs : noms, dates de
naissance, postes, notes à l'échelle du jeu, et les couleurs des clubs. Elle n'est pas sur GitHub.

1. Ouvrez notre [Discord](https://discord.gg/StQqtk3G3M) et allez dans le canal **#newlife**.
2. Téléchargez les parties que vous voulez. Il y a une partie par continent (un grand continent
   vient en plusieurs parties), plus *Free agents*. Chaque partie est un fichier `.zip` nommé
   `NewLife-...zip`.
3. Créez un dossier pour elles, par exemple `Documents\NewLife`, et mettez **toutes** les parties
   dans ce seul dossier.
4. **Ne les décompressez pas.** Mod Studio lit les zip tels quels. (Le lecteur de zip de Windows ne
   peut de toute façon pas les ouvrir ; c'est normal.)

Quand une version plus récente de NewLife sort, mettez ses parties dans un **nouveau** dossier. Ne
mélangez jamais deux versions dans un même dossier.

## Étape 2. L'ouvrir sur la page NewLife Database

1. Cliquez sur **2. Mon monde**, puis sur **NewLife Database** (le bouton à droite, à côté des
   onglets).
2. Cliquez sur **Ouvrir la NewLife Database...** en haut.
3. Choisissez le dossier de l'étape 1 (le dossier, pas un zip à l'intérieur) et confirmez.
4. Attendez quelques secondes pendant la lecture.

(Ou : **2. Mon monde → + Ajouter...**, **Choisir un dossier...**, choisissez le dossier, puis
**Ajouter**.)

**Vous devez voir :** au-dessus de la liste, la version de NewLife et le dossier, et en dessous
`Parties :` avec les parties trouvées. Plus bas, une longue liste de ligues.

Mod Studio retient le dossier : la prochaine fois, la page l'ouvre toute seule.

**Recherche.** Le champ au-dessus de la liste, *Chercher des ligues ou des pays*, ne garde que les
ligues dont le nom ou le pays contient ce que vous tapez. Tapez `brazil` ou `liga`, par exemple.
Videz le champ pour tout revoir.

**Les colonnes.** Cliquez sur l'en-tête d'une colonne pour trier selon elle, cliquez de nouveau
pour inverser l'ordre.

| Colonne | Ce qu'elle vous dit |
|---|---|
| **Ligue** | Le nom de la ligue. Un `*` après veut dire que vous avez changé ses clubs (étape 4). |
| **Pays** | Où elle va dans le jeu. |
| **Clubs** | Combien de clubs elle aura, tel que vous l'avez réglée maintenant. |
| **Dans le jeu** | Combien de ses clubs le jeu a déjà (ils gardent leurs propres noms, écussons, maillots et joueurs). |
| **Joueurs** | Combien de joueurs ses clubs ont dans NewLife. |
| **Niveau** | La force de la ligue. Plus haut = plus fort. |
| (dernière colonne) | Pourquoi une ligue grise ne peut pas être ajoutée. Vide pour une ligue que vous pouvez ajouter. |

**Pourquoi certaines ligues sont grises.** Une ligue grise ne peut pas être ajoutée, et la
dernière colonne dit pourquoi :

- `une ligue a de 10 à 24 clubs` : une ligue du jeu a de 10 à 24 clubs, les nouveaux et ceux du
  jeu ensemble. Celle-ci en a moins ou plus. Vous pouvez encore la corriger à l'étape 4 (ajouter
  ou laisser de côté des clubs) jusqu'à ce qu'elle convienne.
- `ligue propre au jeu : Amener les ligues du jeu à cette saison` : le jeu a déjà cette ligue (la
  Premier League, le Championship ...). Elle n'est pas ajoutée une deuxième fois.
  **Plus ▾ → Amener les ligues du jeu à cette saison...** en haut donne plutôt aux ligues du jeu
  les clubs et effectifs de cette saison NewLife ; voir
  [8.4 dans le guide complet](mod-studio-guide.md#84-newlife-database--vrais-clubs-et-vrais-joueurs).

Si la page dit que Mod Studio n'a pas de tables du jeu et propose d'ouvrir les Réglages : cliquez
sur **Oui**, puis sur **Extraire les tables du jeu** là-bas.

## Étape 3. Choisir vos ligues

1. Cliquez sur une ligue de la liste pour la sélectionner. Sa ligne est surlignée.
2. Pour en prendre plusieurs : maintenez **Ctrl** et cliquez sur chacune. (Ou cliquez sur la
   première, maintenez **Maj** et cliquez sur la dernière pour prendre tout ce qu'il y a entre
   les deux.)

**Vous devez voir :** en bas de la page, une ligne comme
`Nouveaux clubs dans votre monde : 0 sur les 1544 que le jeu accepte.  Sélectionnés : 18 de plus.`

- Le **premier** nombre, c'est combien de nouveaux clubs votre monde a déjà.
- Le **deuxième**, c'est combien de nouveaux clubs tiennent dans le jeu en tout (environ 1 500).
  Mod Studio le calcule à partir des tables de votre jeu, il peut donc être un peu différent sur
  une autre version du jeu.
- **Sélectionnés**, c'est combien de nouveaux clubs les ligues choisies ajouteraient.

Si votre monde et la sélection ensemble dépassent ce que le jeu accepte, **Ajouter à votre monde**
reste grisé : choisissez moins de ligues.

## Étape 4. Choisir les clubs d'une ligue

Cette étape est facultative. Sautez-la pour prendre une ligue exactement comme NewLife l'a.

Sélectionnez **une** ligue (une seule). La liste de droite montre ses clubs : **Club** et
**Joueurs** (combien de joueurs NewLife lui donne). Un club que le jeu a déjà est gris, avec
`dans le jeu` au lieu d'un nombre.

- **Laisser un club de côté :** cliquez sur sa case pour la décocher.
- **Amener un club d'une autre ligue** (la première division de cette saison est celle de l'an
  dernier avec deux promus, par exemple) : cliquez sur **Ajouter un club d'une autre ligue...**
  sous la liste.
  1. Une fenêtre s'ouvre avec chaque club des parties NewLife que vous avez ouvertes, chacun avec
     sa ligue entre parenthèses.
  2. Tapez dans le champ de recherche pour trouver un club ou une ligue.
  3. Cochez un ou plusieurs clubs. La ligne sous la liste dit combien vous en avez choisi.
  4. Cliquez sur **OK**.

  **Vous devez voir :** le club à la fin de la liste, avec `de : <sa ligue>` à côté.

**Vous devez voir :** la ligne de la ligue dans la liste a maintenant un `*`, et son nombre de
**Clubs** a changé. Une ligue grise qui a maintenant de 10 à 24 clubs redevient normale.

Un club ne peut jouer que dans une ligue. Si vous l'ajoutez à deux, Mod Studio vous arrête à
l'étape 5.

## Étape 5. Ajouter à votre monde

Avec votre ligue ou vos ligues sélectionnées, cliquez sur **Ajouter à votre monde** en haut.

**Vous devez voir :** une ligne verte sous le titre de la page. Ce que veut dire chaque ligne :

| Ligne verte | Ce qu'elle veut dire |
|---|---|
| `Ajouté : <ligues>. Modifiez-les dans Ligues, Clubs et Joueurs, puis faites un Build.` | Les ligues sont dans votre monde, chacune comme première division de son pays, tous contre tous deux fois. Rien n'est encore dans le jeu. |
| `<clubs> jouent aussi une compétition du jeu : dans Clubs, choisissez chacun et utilisez Club du jeu pour choisir le club qui prend sa place là-bas.` | Ces clubs de votre nouvelle ligue sont des clubs que le jeu a déjà, et ils jouent aussi quelque part dans le jeu (une ligue, une coupe, la Ligue Europa ...). Un club ne joue que dans une ligue, donc son ancienne place a besoin d'un autre club. Vous choisissez ce club à l'[étape 8](#clubs-que-le-jeu-a-déjà). Tant que ce n'est pas fait, Build s'arrête avec une erreur qui nomme le club. |
| `<n> joueurs restent dans leur club du jeu (leur club aurait trop peu de joueurs).` | Les joueurs que le jeu a déjà passent normalement au club NewLife. Ceux-là restent, pour que leur ancien club garde au moins 18 joueurs. Rien à faire. |
| `<n> joueurs ne sont pas ajoutés : une autre ligue les a déjà.` | Une ligue ajoutée plus tôt a déjà pris ces joueurs. Rien à faire. |

Si une fenêtre d'erreur dit `<club> jouerait dans deux ligues (<ligue> et <ligue>).`, décochez ce
club dans l'une des deux ligues (étape 4) et réessayez.

Vous voulez des ligues d'autres continents ? Sélectionnez-les aussi et cliquez de nouveau sur
**Ajouter à votre monde**. Chaque clic ajoute ; il ne retire jamais ce qui est déjà là.

---

## Étape 6. La page Ligues : chaque réglage d'une ligue

1. **2. Mon monde**, onglet **Ligues**.
2. Au-dessus de la liste, cliquez sur **Nôtres** : la liste ne montre que les ligues de votre
   monde. (**Toutes** montre toutes les ligues, celles du jeu aussi ; **Modifié**, les ligues du
   jeu que vous avez changées.) Les ligues sont groupées par continent.
3. Cliquez sur votre ligue.

**Vous devez voir :** à droite, `À NOUS`, le nom et le logo de la ligue, et les lignes **Pays**,
**Clubs**, **Format**, **Division**, **Montée / descente**, **Europe** et **ID de la ligue**
(`pas encore construite` jusqu'au premier Build), puis les écussons de ses clubs. En dessous, les
boutons **Modifier la ligue...**, **Ajouter une division inférieure**, **Clubs et noms**,
**Joueurs** et **Retirer**.

La liste va par pays, les divisions de chaque pays de haut en bas (Bundesliga, 2. Bundesliga,
3. Liga). Vous pouvez glisser une ligue vers le haut ou le bas de la liste pour mettre en ordre
les ligues d'un continent.

4. Cliquez sur **Modifier la ligue...**.

**Vous devez voir :** une fenêtre appelée **Ligue** avec les champs ci-dessous, de haut en bas. Un
champ gris ne peut pas servir avec ce que vous avez réglé au-dessus (par exemple une coupe sur une
deuxième division). Le **?** à côté de **OK** explique la fenêtre en bref. Rien n'est obligatoire :
les valeurs par défaut marchent, et **Annuler** ne change rien.

| Champ | Ce que c'est, et quoi faire |
|---|---|
| **Nom** | Le nom de la ligue dans le jeu. Deux ligues ne peuvent pas avoir le même nom. Restez sous environ 38 caractères : un nom plus long s'affiche comme une ligne vide dans la liste des ligues de Kick Off. |
| **Pays** | Tapez quelques lettres et choisissez dans la liste (`korea` trouve les deux Corées). Il donne le drapeau et l'endroit où la ligue apparaît dans le jeu. |
| **Clubs** | De 10 à 24. Pour une ligue NewLife, laissez tel quel : un nombre plus petit retire les derniers clubs, un plus grand ajoute des clubs inventés à la fin. |
| **Clubs sans championnat** | Laissez sur `(non -- un championnat)`. Les autres choix (*Other European teams* ...) sont pour un club, ou quelques-uns, sans championnat autour ; ils vont dans les groupes « Other ... » du jeu, et la plupart des champs en dessous deviennent gris. [Plus de détails](mod-studio-guide.md#8-league-builder--nouvelles-ligues-nouveaux-clubs-et-joueurs). |
| **Format** | Choisissez-en un : **tous contre tous, nombre de fois :** et le nombre (1 à 4 ; 2, c'est aller et retour) ; **se divise en deux (à l'écossaise)**, avec `d'abord` *n* `x, puis groupes` *6/6* *n* `x` (la somme des groupes doit faire le nombre de clubs) ; ou **Apertura et Clausura, puis play-offs de :** *8 clubs*, *4 clubs* ou *pas de play-offs* (deux courts tournois par saison, 18 clubs au maximum). La division en deux et Apertura et Clausura sont **expérimentales** : elles marchent, mais ont encore plus de bugs que tous contre tous, le format entièrement testé. La fenêtre le dit sous les formats. Pour un premier monde, prenez tous contre tous. |
| **Division** | `(première division)` = la meilleure ligue de son pays. Pour une deuxième division, choisissez la ligue un niveau au-dessus : vos nouvelles ligues sont en haut de la liste, puis les ligues du jeu avec un nombre entre parenthèses. `= division 2` à côté montre le niveau. Une ligue qui a déjà une ligue en dessous est grise (`-- en dessous : ...`) : une ligue peut avoir une seule ligue en dessous. Voir l'[étape 7](#étape-7-exemple--un-pays-avec-deux-divisions). |
| **Exhibition uniquement -- pas en Ligue des Masters** | Laissez-le désactivé. Activé : la ligue ne sert qu'à Kick Off et aux matchs amicaux (légendes, une saison historique) ; elle ne joue jamais de saison de Master League, et la division, les coupes et l'Europe deviennent grises. Ne commencez pas de carrière avec un de ses clubs. |
| **Saison** | Première division uniquement : **août à mai** (comme l'Europe) ou **février à décembre** (comme le Brésil ou le Japon). Une division en dessous suit la ligue au-dessus. Février à décembre ne peut pas encore avoir de division en deux, d'Apertura/Clausura ni de coupe de la ligue ; une coupe nationale, oui. |
| **Montée / descente** | De 1 à 6 : combien de clubs échangent leur place avec la ligue au-dessus en fin de saison. N'a de sens que pour une division sous une autre. |
| **Logo** | **Choisir une image...** : un PNG ou JPG pour la ligue (un PNG à fond transparent rend le mieux). **Effacer** l'enlève. Vide : `(créé pour vous)`, un logo est dessiné au Build. |
| **Drapeau du pays** | Votre propre image du drapeau du pays. Vide : `(celui du jeu)`. Laissez vide sauf si le jeu n'a pas de bon drapeau. |
| **Coupe** | Première division uniquement. Cochez **Coupe nationale** pour donner au pays une coupe à élimination directe (cette ligue et la division en dessous). Le champ à côté est le nom de la coupe ; vide = le nom de la ligue + Cup. |
| **Supercoupe (champion contre vainqueur de la coupe)** | Un match avant la saison. Demande que **Coupe nationale** soit cochée. |
| **Coupe de la ligue** | Première division uniquement. Une deuxième coupe à élimination directe, comme la Carabao Cup en Angleterre : cette ligue et celle du dessous, jusqu'à 44 clubs. Le champ est son nom ; vide = le nom de la ligue + League Cup. |
| **Logos des coupes** | Une image chacune pour la **Coupe**, la **Supercoupe**, la **Coupe de la ligue** et les **Play-offs**. Vide : un emblème aux initiales de la coupe. |
| **Formation** | Comment les clubs de la ligue se placent. Choisissez-en une dans la liste, ou laissez vide et Build choisit celle qui convient le mieux à l'effectif de chaque club. Un club peut avoir la sienne (étape 8). |
| **Europe** | Première division uniquement : quelle position au classement va dans quelle compétition continentale. Le bouton qui commence par **1re division :** / **Première division :** remplit les places habituelles du continent du pays (pour l'Europe : `Première division : 1er qualifications LDC, 2e LE, 3e LECE`). **Ajouter une place** ajoute une ligne : choisissez la **Position en ligue** (sous 1, elle s'affiche **Vainqueur de la coupe**) et la **Compétition**. Le **✕** d'une ligne la retire, **Effacer** retire tout. Laissez vide pour une deuxième division. |

5. Cliquez sur **OK**.

**Vous devez voir :** la fenêtre se ferme et les lignes à droite montrent ce que vous avez réglé.

Une ligue NewLife arrive sans places européennes. Si vous voulez ses clubs en Ligue des champions
et dans les autres, réglez **Europe** maintenant ; sinon **1. Vérifier le plan** vous le rappelle
avec `no European places: the new leagues send nobody to Europe`.

Le sens de chaque format, coupe et place européenne en détail (dates, tours de qualification,
tailles des coupes) :
[section 8 du guide complet](mod-studio-guide.md#8-league-builder--nouvelles-ligues-nouveaux-clubs-et-joueurs)
et [8.2](mod-studio-guide.md#82-construire-activer-jouer).

**Plus ▾** (en haut de l'onglet Ligues) contient les outils pour tout le monde : **Tournois de
pré-saison**, **Coupes de nos pays** (les coupes de toutes vos ligues dans un seul tableau),
**Coupes des pays du jeu**, **Places européennes des ligues du jeu**, **Clubs européens de la
première saison**, **Classement UEFA**, **Places sud-américaines** (avec la case **Compétitions modernes de la CONMEBOL**, 0.2.5), **Pays de la CONMEBOL sans championnat**, **Noms des compétitions**
(nouveaux noms et logos pour les coupes et les compétitions continentales), **IDs des
compétitions**, **Ordre des championnats**, **Saisons des championnats du jeu** et **Nom du monde
et fichier...** (le nom du dossier du monde ; il doit commencer par `_FL26`). Vous n'avez besoin
d'aucun d'eux pour un premier monde. Les fenêtres des coupes sont aussi sous **Coupes ▾**, à côté
des onglets.

**Une ligue sans clubs NewLife.** **Ajouter une ligue** en haut de l'onglet Ligues ouvre la même
fenêtre **Ligue** pour une ligue partie de zéro : donnez-lui un **Nom**, un **Pays** et un nombre
de **Clubs**, et Build crée les clubs avec des effectifs complets et un entraîneur. Vous les
nommez dans l'onglet **Clubs** (étape 8), où **Club NewLife...** peut aussi y mettre de vrais
clubs.

## Étape 7. Exemple : un pays avec deux divisions

Disons que vos parties NewLife ont la première et la deuxième division d'un pays, appelées ici
*First League* et *Second League*. Vous voulez des montées et descentes entre elles.

1. **NewLife Database** : sélectionnez *First League* et cliquez sur **Ajouter à votre monde**.
   (Celle du haut d'abord.)
2. Sélectionnez *Second League* et cliquez sur **Ajouter à votre monde**.

   **Vous devez voir :** la ligne verte `Ajouté :` à chaque fois. Les deux sont maintenant des
   premières divisions du même pays, ce qui n'est pas encore ce que vous voulez.

3. **Ligues** → **Nôtres** → cliquez sur *Second League* → **Modifier la ligue...**.
4. **Division** : ouvrez la liste et choisissez *First League* (vos ligues sont en haut).

   **Vous devez voir :** `= division 2` à côté. **Coupe**, **Coupe de la ligue**, **Saison** et le
   bouton **Première division** deviennent gris : ils appartiennent à la première division.

5. **Montée / descente** : combien de clubs montent et descendent entre les deux, par exemple `3`.
6. **Europe** : s'il y a des lignes, cliquez sur **Effacer**. Une deuxième division n'envoie
   personne en Europe.
7. Cliquez sur **OK**.

   **Vous devez voir :** à droite, **Division** `2  (sous First League)` et **Montée / descente**
   `3 avec First League au-dessus`. Cliquez sur *First League* : sa **Montée / descente** dit
   `3 avec Second League en dessous`.

8. Cliquez sur *First League* → **Modifier la ligue...** et réglez ce qui appartient à la première
   division : **Europe** (le bouton **Première division**), et si vous voulez **Coupe nationale**,
   **Supercoupe** et **Coupe de la ligue**. Cliquez sur **OK**.

Une troisième division marche de la même façon : sa **Division** est *Second League*. Le jeu
descend jusqu'à la 7e division.

**Une ligue sous une ligue.** Deux ligues ne peuvent pas être sous la même ligue (trois groupes
régionaux sous une même deuxième division, par exemple). La deuxième s'affiche en gris dans la
liste **Division**.

**Sous une ligue du jeu.** Votre nouvelle ligue peut aussi aller sous une ligue que le jeu a :
choisissez la ligue du jeu dans **Division** (celles avec un nombre entre parenthèses). Elle joue
alors les montées et descentes avec elle.

**Sans NewLife.** Dans **Ligues**, cliquez sur votre ligue du haut, puis sur **Ajouter une
division inférieure** : une fenêtre **Ligue** s'ouvre avec le pays, les clubs, le format et la
division déjà remplis. Donnez-lui un **Nom** et cliquez sur **OK**.

---

## Étape 8. L'onglet Clubs : noms, écussons, maillots, clubs du jeu

1. **2. Mon monde**, onglet **Clubs** (ou **Clubs et noms** dans l'onglet Ligues).
2. En haut, **Ligue** : choisissez une de vos ligues.

**Vous devez voir :** ses clubs avec les colonnes **#**, **Nom**, **Nom court** et **Joueurs
modifiés** ; laissez la souris sur un nom pour voir son **ID de l'équipe** (`au Build` jusqu'au
premier Build) et le fichier de son écusson. Les clubs NewLife ont déjà leurs noms, noms courts et
écussons. Un club sans nom affiche `<ligue> 01`, `<ligue> 02` ... en gris. Au-dessus de la liste :
**Modifier le club** et **Plus ▾**.

### Nom, écusson, maillots, entraîneur

1. Double-cliquez sur un club (ou sélectionnez-le et cliquez sur **Modifier le club**).

**Vous devez voir :** une fenêtre appelée **Club** avec :

| Champ | Quoi faire |
|---|---|
| **Nom** | Le nom du club. Les lettres accentuées (Željezničar) sont acceptées. |
| **Nom court** | Trois lettres ou chiffres. Vide = fait à partir du nom. Č, Ž, Đ ... deviennent C, Z, D, comme dans le jeu. |
| **Écusson** | **Choisir une image...** : un PNG ou JPG. **Effacer** l'enlève. Un club sans écusson reçoit un écusson numéroté. |
| **Stade à domicile** | Seulement quand Stadium Server est installé : **Choisir le stade...** dans votre pack de stades, ou **Du jeu**. |
| **Entraîneur** | Le nom de l'entraîneur. Vide : un nom inventé à partir des joueurs du pays du club. |
| **Photo de l'entraîneur** | Un PNG ou JPG ; le jeu l'affiche dans le mode Edit et dans la Master League. |
| **Formation** | `Comme la ligue (...)` garde la formation de la ligue ; ou choisissez-en une pour ce club. |
| **Couleurs du maillot domicile**, **Couleurs du maillot extérieur** | Cliquez sur les deux carrés de couleur (maillot, deuxième couleur) pour choisir les couleurs ; **Aucune** = Build choisit un maillot tout seul. Build donne au club le maillot du jeu le plus proche de ces couleurs. |

2. Cliquez sur **OK**.

**Vous devez voir :** le nouveau nom et le nouvel écusson dans la liste.

**Maillots.** Un nouveau club emprunte le maillot d'un club du jeu à ses couleurs. Deux options de
l'onglet **Construction**, sous **Options du monde**, changent cela : **Maillots aux couleurs des
clubs** (activée par défaut, demande Kit Server installé : chaque nouveau club reçoit des maillots
domicile, extérieur, troisième et gardien faits à ses couleurs, avec son écusson) et **Maillots
simples pour le mode Édition** (chaque nouveau club porte un maillot simple que vous pouvez
modifier dans le mode Edit du jeu).
[Plus de détails dans le guide complet](mod-studio-guide.md#8-league-builder--nouvelles-ligues-nouveaux-clubs-et-joueurs).

**Capitaine et coups de pied arrêtés.** Vous n'avez pas à les choisir : Build donne à chaque club
un capitaine et des joueurs qui tirent les penalties, les coups francs et les corners.

**Beaucoup de clubs d'un coup.** **Plus ▾** contient **Coller des noms...** et **Charger des noms
depuis un fichier...** (un nom par ligne, dans l'ordre) et **Importer des écussons...** (un
dossier d'images, associées aux clubs par le nom du fichier). Il contient aussi **Joueurs**,
**Club du jeu...**, **Club NewLife...**, **Nouveau club ici**, **Insérer un club**, **Retirer le
club** et **Déplacer vers une autre ligue...**.

### Clubs que le jeu a déjà

Une ligue NewLife peut contenir des clubs que le jeu a déjà. Ils apparaissent dans la liste avec
le nom du jeu (la souris dessus montre leur **ID de l'équipe**). Si la ligne verte de l'étape 5
disait qu'ils *jouent aussi une compétition du jeu*, faites ceci pour **chacun** d'eux :

1. Cliquez sur le club dans la liste.
2. Cliquez sur **Plus ▾ → Club du jeu...**.

**Vous devez voir :** une fenêtre appelée **Club du jeu**, avec le club sélectionné et sous la
liste une ligne comme `<club> joue en <compétitions>. Chacune de ces compétitions garde son nombre
de clubs : choisissez qui y prend sa place.`

3. Choisissez qui prend son ancienne place :
   - **Sa place revient à un club du jeu qui ne joue rien :** et choisissez un club dans la liste
     en dessous ; ou
   - **Sa place revient à un nouveau club, nommé :** et tapez un nom. Build crée ce club.
4. Si le club joue une compétition continentale (Ligue des champions, Libertadores ...), il y a
   aussi **Il garde ses places dans les compétitions continentales**. Cochée, il continue de jouer
   cette compétition et personne n'a à y prendre sa place.
5. Cliquez sur **OK**.

Le même élément de menu met n'importe quel club du jeu à une place de votre ligue : sélectionnez
la place, **Plus ▾ → Club du jeu...**, cherchez par nom, nom court ou ID d'équipe (**Seulement les
clubs sans ligue** réduit la liste). **Nouveau club ici** (dans **Plus ▾**) rend la place à un
nouveau club ; il est gris sauf si un club du jeu occupe la place.

**Club NewLife...** (dans **Plus ▾**) met des clubs NewLife, avec leurs effectifs, à la place
sélectionnée et aux suivantes : cochez-en un ou plusieurs dans la fenêtre qui s'ouvre, puis
**OK**. C'est ainsi qu'une ligue faite à la main reçoit de vrais clubs.

## Étape 9. La page Joueurs

Les clubs NewLife arrivent avec des effectifs complets, vous n'avez donc pas à toucher cette
page. Elle est là si vous voulez changer un effectif.

1. **2. Mon monde**, onglet **Joueurs** (ou sélectionnez un club dans l'onglet **Clubs** et
   cliquez sur **Plus ▾ → Joueurs**).
2. En haut, choisissez la **Ligue** et le **Club**. (Ou tapez dans *Trouver un club...*.)

**Vous devez voir :** l'effectif avec les colonnes **Ordre**, **N°**, **Nom**, **Poste**, **Âge**,
**Note**, **Pied**, **Modifié** et **ID du joueur**, et le onze de départ sur un terrain en
dessous. Cliquez sur un joueur : la partie droite le montre, dans les onglets **Bases**,
**Postes**, **Capacités** et **Compétences**.

- Changez un nom, un numéro, un poste, une note ou une capacité à droite. Le changement est gardé
  tout de suite.
- **Monter dans l'ordre** / **Descendre dans l'ordre** : l'ordre de l'effectif. Les onze premiers
  commencent le match. Ou glissez un joueur sur un poste du terrain. **Meilleur onze** place le
  joueur le plus fort à chaque poste.
- **Recruter des joueurs...** amène des joueurs d'autres clubs ; **Transférer vers...** envoie le
  joueur sélectionné dans un autre club.
- **Annuler les modifications de ce joueur** et **Annuler toutes les modifications de ce club**
  reviennent en arrière.

Tout ce qui concerne cette page est dans [Joueurs dans le guide complet](mod-studio-guide.md#joueurs).

---

## Étape 10. Les limites qui arrêtent un Build

| Limite | Où vous la voyez |
|---|---|
| Nouveaux clubs en tout (environ 1 500) : le nombre sur la ligne `Nouveaux clubs dans votre monde : X sur les Y que le jeu accepte.` | Page NewLife Database : **Ajouter à votre monde** reste grisé. Build : `erreur : <n> new clubs, but the game has room for <m> more (a full squad each)`. |
| De 10 à 24 clubs dans une ligue | NewLife Database : ligue grise, `une ligue a de 10 à 24 clubs`. Onglet Clubs : `Une ligue a de 10 à 24 clubs.` |
| Nouvelles ligues par monde : pas de nombre fixe. Chaque ligue et chaque coupe prend une des 255 compétitions du jeu ; **2. Mon monde** montre combien sont utilisées (**COMPÉTITIONS**). Notre monde de test joue 86 nouvelles ligues. | Build : `erreur : <n> leagues, but the game has room for <m> ...` |
| Une ligue sous une ligue | Liste **Division** : grise. Build : `... are all under ...; the game follows one link down from a league ...` |
| Divisions jusqu'à la 7e | Build : `erreur : <league>: division 8 -- the rank field stops at 7`. |
| 2 ligues divisées par monde ; une seule division en deux ou Apertura/Clausura par pays | Build : `erreur : at most 2 split leagues for now ...`, `... only one league of a country can be split or Apertura/Clausura`. |
| Un club dans une seule ligue | Build : `erreur : <club> is in <league> and in <league>: a club plays in one league`. |
| Un club du jeu qui joue quelque part a besoin d'un remplaçant | Build : `erreur : <league>, club <n>: <club> plays in <...> -- pick the club that takes its place there`. Faites [Clubs que le jeu a déjà](#clubs-que-le-jeu-a-déjà). |

Tous les nombres : [8.3 Limites](mod-studio-guide.md#83-limites).

## Étape 11. Votre monde s'enregistre tout seul

Il n'y a rien à enregistrer à la main : Mod Studio enregistre votre monde un instant après chaque
changement.

**Vous devez voir :** en bas de la fenêtre, **Votre monde est enregistré**.

**Fichier → Enregistrer votre monde sous...** en enregistre une copie sous un autre nom, dans un
dossier que vous choisissez (par exemple `Documents\FL26 Mod Studio`) : ce fichier, vous pouvez le
retrouver et le copier. **Fichier → Ouvrir un monde...** en rouvre un enregistré. **Fichier →
Nouveau monde** en commence un vide.

Mod Studio rouvre votre monde au démarrage, donc ce que vous avez fait n'est jamais perdu.

## Étape 12. Build

1. **2. Mon monde**, onglet **Construction** (le premier onglet).

**Vous devez voir :** une note qui dit que Build est pour les moddeurs, puis le grand bouton
**Construire et installer** et deux plis en dessous : **Options du monde : coupes d'Europe, coupes
nationales, maillots et visages des nouveaux clubs** (deux cartes, **Coupes d'Europe** et
**Nouveaux clubs**, avec des options) et **Étape par étape, et Exporter le monde** (la rangée
**0. Installer les modules**, **1. Vérifier le plan**, **2. Construire le monde**, **3. L'activer**,
**4. Après un lancement : vérifier** et **Exporter le monde...**). Puis une ligne comme
`Monde _FL26MyWorld : pas encore construite · modules de Mod Studio : installés`, et une case pour
le journal en bas. Pendant que le monde se construit, la ligne en haut de **2. Mon monde** et la
barre du bas montrent le temps écoulé et l'étape en cours (`Building... 3:12 · squads: filling
them`).

2. Ouvrez **Étape par étape, et Exporter le monde** et cliquez d'abord sur **1. Vérifier le
   plan**. Il ne change rien ; il lit seulement votre monde.

**Vous devez voir :** dans la case, une ligne `world _FL26MyWorld: 2 new leagues, ...` et une ligne
pour chaque ligue avec ses clubs, sa division et son format (`18 clubs x2`, c'est 18 clubs, tous
contre tous deux fois ; `division 2  below ... (3 up/down)`, c'est une deuxième division), et ses
`European places:`. Une ligne qui commence par `erreur :` dit quoi corriger d'abord ; voir le
tableau à la fin.

3. Cliquez sur **Construire et installer**. Il demande `Construire _FL26MyWorld et le mettre dans
   le jeu ? ...` : cliquez sur **Oui**.

   Si les tables du jeu sont plus anciennes que le jeu, il demande d'abord s'il faut les extraire
   à nouveau : cliquez sur **Oui** (une minute ou deux).

   Il installe les modules de Mod Studio, construit votre monde et le met dans le jeu, tout en
   un. Cela prend de quelques secondes à quelques minutes. Quand seules des images ont changé
   depuis le dernier Build (un logo, un écusson, un drapeau), cela prend quelques secondes.

**Vous devez voir :** une fenêtre **Build terminé** avec une coche sur chaque ligne : **Monde
construit**, **Ligues et clubs** (`2 ligues · 36 nouveaux clubs`), **Modules installés et
activés**, **Dans le jeu** et **Lancez le jeu pour y jouer**. Sous **Avant de jouer** :
`Commencez une nouvelle carrière Ligue des Masters : une carrière sauvegardée avant garde l'ancien monde.`
Cliquez sur **Terminé**.

S'il dit **Une sauvegarde Edit antérieure à ce Build est dans le dossier des sauvegardes du jeu** :
cliquez sur **Mettre la sauvegarde Edit de côté**. Une ancienne sauvegarde Edit cache les nouveaux
noms et effectifs.

Dans **2. Mon monde**, la carte de votre monde est maintenant verte : **● DANS LE JEU MAINTENANT**.

**Étape par étape au lieu du grand bouton** (le même résultat, sous **Étape par étape, et
Exporter le monde**) :

1. **1. Vérifier le plan** : comme ci-dessus.
2. **2. Construire le monde** : le construit. Si le monde existe, il demande `... existe déjà. Le
   reconstruire ?` : **Oui**. Le journal se termine par `Ensuite : 3. L'activer, puis lancez le jeu.`
3. **3. L'activer** : demande `Mettre _FL26MyWorld dans le jeu (l'activer dans sider.ini) ?` :
   **Oui**. Le journal se termine par `Lance le jeu, puis 4. vérifie.`

**Ce que veulent dire les lignes du journal :**

| Ligne | Sens |
|---|---|
| `installation des modules ...`, `modules: ... copied, ... already there` | Les modules de Mod Studio sont mis en place. |
| `world ...: N new leagues, changes to ... of the game's leagues and ... of its clubs` | Le résumé de votre monde. |
| `<league>  reg ...  comp ...  division 1  18 clubs x2` | Une ligue : ses id dans le jeu, sa division et son format. |
| `European places: 1st Champions League qualifying, ...` | Où vont ses meilleurs clubs. |
| `no European places: the new leagues send nobody to Europe` | Un avertissement, pas une erreur : réglez **Europe** sur une première division si vous le voulez. |
| `construction ...` | Le monde est en train d'être écrit. |
| `livecpk: _FL26MyWorld (... files), sider.ini loads it` | Le monde est dans le jeu. |
| `erreur : ...` | Build s'est arrêté et rien n'a changé dans le jeu. Corrigez ce qu'il dit (tableau à la fin) et reconstruisez. |

Les options sous **Options du monde** (**Inclure la Ligue Europa Conférence**, **Tirage de la
coupe nationale**, **Maillots aux couleurs des clubs** ...) sont expliquées en
[8.2](mod-studio-guide.md#82-construire-activer-jouer). Les valeurs par défaut conviennent.

## Étape 13. Jouer : une NOUVELLE Master League, puis la vérification

1. Cliquez sur le bouton vert **Lancer le jeu** en haut à droite (ou **Jeu → Lancer le jeu**).
2. Dans le jeu : **Master League** → **New game**. Pas Continue : une carrière sauvegardée avant
   garde l'ancien monde.
3. Dans **Select Team**, faites défiler : vos ligues sont dans la liste, sous leur pays.
4. Choisissez un club et jouez.

Chaque monde garde ses propres carrières : quand un autre monde entre dans le jeu, Mod Studio met
de côté les carrières de ce monde-ci, et les ramène quand ce monde est de nouveau dans le jeu.
Rien n'est supprimé. ([Plus de détails](mod-studio-guide.md#31-mon-monde).)

Ensuite, laissez Mod Studio vérifier que le jeu a pris le monde :

1. Fermez le jeu (ou lancez-le au moins une fois jusqu'au menu principal).
2. Dans Mod Studio : **2. Mon monde** → onglet **Construction** → **Étape par étape, et Exporter
   le monde** → **4. Après un lancement : vérifier**.

**Vous devez voir :** une ligne par module qui dit combien de ligues il a lues dans le fichier du
monde, et à la fin `the world works as built`. Une ligne `not loaded` ou `did NOT read the world
file`, et à la fin `something is wrong -- see the lines above`, veulent dire que quelque chose n'a
pas marché : voir le tableau à la fin.

## Étape 14. Changer quelque chose plus tard

1. Fermez le jeu.
2. Ouvrez Mod Studio. Il ouvre votre monde tout seul (ou **Fichier → Ouvrir un monde...**).
3. Changez ce que vous voulez sur la page **NewLife Database**, ou dans les onglets de **2. Mon
   monde** : **Ligues**, **Clubs** ou **Joueurs**. Il s'enregistre tout seul.
4. **Construire et installer** (onglet **Construction**) → **Oui**.

**Faut-il une nouvelle carrière ?** Oui : commencez une nouvelle Master League après chaque
changement que vous construisez. Une carrière prend sa propre copie des ligues, clubs et effectifs
au moment où elle commence, donc une carrière en cours garde les anciens. Et une carrière
sauvegardée avec un monde a besoin de ce même monde pour se charger, donc gardez le monde dans le
jeu pendant que vous la jouez.

**Après une mise à jour de Mod Studio.** Reconstruisez votre monde une fois avec la nouvelle
version et commencez une nouvelle carrière. Avec la 0.2.4 c'est important : un monde construit
avant a le gardien comme capitaine de chaque club. Build donne maintenant à chaque club un
capitaine et des tireurs de coups de pied arrêtés.

**Une version plus récente de NewLife.** Mettez ses parties dans un nouveau dossier, **Ouvrir la
NewLife Database...** sur ce dossier, puis **Plus ▾ → Mettre mes ligues à jour vers cette
version**. Chaque ligue garde son nom, sa division, son format, ses places européennes et ses
coupes ; les clubs et les effectifs viennent de la nouvelle version (la case **Garder mes clubs**
garde votre propre composition). Reconstruisez et commencez une nouvelle carrière.
[Plus de détails](mod-studio-guide.md#84-newlife-database--vrais-clubs-et-vrais-joueurs).

**Retirer une ligue.** **Ligues** → **Nôtres** → cliquez dessus → **Retirer** → **Oui**. Ses clubs
et leurs changements de joueurs partent avec elle.

## Étape 15. Partager ce que vous avez créé

Il y a deux façons. Choisissez-en une :

| | Paquet de ligues (`.fl26pack`) | Monde exporté (`.zip`) |
|---|---|---|
| Ce qu'il contient | Vos ligues, prêtes à être ajoutées à un autre monde : clubs, noms, écussons, logos, effectifs, visages, et si vous voulez maillots et tableaux de score. | Le monde exactement tel que vous l'avez construit. |
| L'autre personne | L'ajoute à son propre monde et construit, donc il marche à côté de ses propres ligues et d'autres paquets. | L'installe et joue. Rien à construire, mais il remplace tout autre monde qu'elle a dans le jeu. |
| Comment l'installer | [Voie C d'Installer un pack prêt](install-a-pack.md#voie-c--un-paquet-de-ligues-fl26pack) | [Voie A d'Installer un pack prêt](install-a-pack.md#voie-a--un-monde-prêt-un-seul-zip) |

### Un paquet de ligues

1. **2. Mon monde → Plus ▾ → Paquets de ligues → Créer un paquet...** (ou dans la barre du haut :
   **Fichier → Créer un paquet de ligues...**).

**Vous devez voir :** une fenêtre **Créer un paquet de ligues**.

2. Remplissez **Nom** (obligatoire), **Auteur**, **Version** (`1.0` pour commencer) et
   **Description**.
3. Sous **Ligues**, cochez les ligues qui y vont (**Tout cocher** / **Tout décocher**). Une ligue
   sous une autre ligue doit l'accompagner.
4. **Aussi mes modifications des ligues, clubs et joueurs du jeu** (seulement si vous en avez
   changé) : cochez-la pour les mettre aussi.
5. Sous **Ce qui va dedans**, tout est coché : **Effectifs**, **Visages et portraits des
   joueurs**, **Blasons et logos des ligues**, **Entraîneurs**, **Couleurs des maillots**,
   **Maillots**, **Tableaux de score** et **Stades à domicile**. Décochez ce que vous ne voulez pas
   partager. Les maillots ajoutent environ 10 Mo par ligue et un tableau de score environ 7 Mo.
6. Cliquez sur **Enregistrer le paquet...**. Une fenêtre d'enregistrement **Enregistrer le
   paquet** s'ouvre avec un nom comme `<nom>-1.0.fl26pack`. Choisissez un dossier que vous
   retrouverez (Bureau, Documents ...) et cliquez sur **Enregistrer**.

**Vous devez voir :** `Enregistré : <fichier>` avec combien de ligues, de clubs et de visages il
contient. Ce seul fichier est ce que vous partagez. S'il dépasse 10 Mo, Mod Studio le dit :
Discord ne le prendra pas, alors partagez-le par Google Drive, Dropbox, MEGA ou un service
semblable, ou décochez **Maillots** et **Tableaux de score**, ou faites un paquet par ligue.

Plus de détails : [9. Paquets de ligues](mod-studio-guide.md#9-paquets-de-ligues--partager-une-ligue-entière).

### Un monde entier (zip)

1. Faites d'abord le Build (étape 12). Le monde doit être construit.
2. **2. Mon monde** → **Exporter...** sur la carte du monde. (Ou onglet **Construction** →
   **Étape par étape, et Exporter le monde** → **Exporter le monde...**.)
3. Une fenêtre d'enregistrement s'ouvre avec le nom du monde comme nom de fichier
   (`_FL26MyWorld.zip`), dans votre dossier utilisateur la première fois (ensuite, dans le
   dernier dossier utilisé). Choisissez un dossier et cliquez sur **Enregistrer**.

**Vous devez voir :** après un instant, `Enregistré <fichier>` et combien de nouveaux joueurs
reçoivent un visage généré. Le zip contient le dossier du monde, son fichier de monde et un
lisez-moi.

La personne qui l'installe a besoin des modules de Mod Studio avec le pack de visages ; installer
le zip sur **Importer votre monde** les met en place. Sans eux, tous les nouveaux joueurs ont le
même visage. Le lisez-moi du zip le dit.

Plus de détails : [9.1 Exporter le monde](mod-studio-guide.md#91-exporter-le-monde--un-monde-construit-pour-un-autre-pc).

---

## Si quelque chose ne va pas

Les messages apparaissent dans une fenêtre d'erreur, dans la ligne verte ou rouge sous le titre
d'une page, ou dans le journal du Build après `erreur :`. `<...>` remplace un nom ou un nombre.

| Ce que vous voyez | Que faire |
|---|---|
| `no NewLife Database here: put the NewLife-....zip parts you downloaded in one folder (no need to unpack them) and open that folder` | Vous avez choisi le mauvais dossier, ou décompressé les parties. Ouvrez le dossier qui contient les fichiers `NewLife-...zip` eux-mêmes. |
| `the parts in this folder are of different versions (...): keep one version's parts only` | Deux versions de NewLife sont mélangées. Ne gardez dans le dossier que les parties d'une version. |
| `<file> is not a NewLife part (...) -- download it again` | Le téléchargement s'est mal passé. Téléchargez de nouveau cette partie. |
| Une ligue grise, `une ligue a de 10 à 24 clubs` | Ajoutez ou laissez de côté des clubs (étape 4) jusqu'à en avoir de 10 à 24. |
| Une ligue grise, `ligue propre au jeu : Amener les ligues du jeu à cette saison` | Le jeu l'a déjà. Utilisez **Amener les ligues du jeu à cette saison...**. |
| **Ajouter à votre monde** reste grisé | Rien d'ajoutable n'est sélectionné, ou la sélection dépasserait la limite de nouveaux clubs (la ligne en bas). |
| `<club> jouerait dans deux ligues (<ligue> et <ligue>).` | Décochez le club dans l'une des deux. |
| `<ligue> n'a pas de pays que le jeu connaisse.` | Cette ligue ne peut pas être ajoutée. |
| `Une ligue a besoin d'un nom et d'un pays.` / `Choisissez le pays dans la liste.` | Dans **Modifier la ligue...**, remplissez **Nom**, et choisissez le **Pays** dans la liste au lieu de le taper en entier. |
| `Il existe déjà une ligue nommée <nom>.` | Donnez un autre nom à la ligue. |
| `European places: position <n> -- the league has <m> clubs` | Une ligne de **Europe** pointe au-delà du dernier club. Changez-la ou retirez-la. |
| `European places: position <n> is listed twice` | Deux lignes ont la même position. Retirez-en une. |
| `European places: a cup winner's place, but the country has no cup` | Cochez **Coupe nationale**, ou retirez la ligne **Vainqueur de la coupe**. |
| `Les clubs, le nombre de tours et les groupes doivent être des nombres.` | Sous **se divise en deux**, tapez les groupes en nombres, par exemple `6/6`. |
| `Une ligue de février à décembre n'a pas encore de phase finale, d'Apertura/Clausura ni de coupe de la ligue.` | Mettez **Saison** sur **août à mai**, ou retirez la division en deux, l'Apertura/Clausura ou la coupe de la ligue. |
| `Cette division joue de février à décembre avec la ligue au-dessus, et une ligue qui joue de février à décembre n'a pas encore de scission ni d'Apertura/Clausura.` | Donnez à cette division **tous contre tous**. |
| `Les clubs sans championnat sont tous de nouveaux clubs : retirez d'abord les clubs du jeu (Modifier le club).` | La ligue contient des clubs du jeu. Dans l'onglet **Clubs**, sélectionnez chacun et utilisez **Plus ▾ → Nouveau club ici**, puis réglez de nouveau **Clubs sans championnat**. |
| `<ligue> est sous ce championnat ; les clubs sans championnat n'ont rien en dessous.` (ou `<ligue> est sous cette ligue ; une ligue d'exhibition n'en a aucune.`) | Une autre ligue a celle-ci comme **Division**. Changez d'abord cette ligue-là. |
| `Une ligue a de 10 à 24 clubs.` (onglet Clubs) | Insérer un club / Retirer le club mettrait la ligue hors de 10 à 24. |
| `Ouvrez d'abord la NewLife Database sur la page NewLife.` | **Club NewLife...** a besoin du dossier NewLife : ouvrez-le une fois sur **NewLife Database**. |
| `Choisissez le club qui prend sa place.` / `Donnez un nom au nouveau club.` / `Un club ne peut pas prendre sa propre place.` | Dans **Club du jeu**, choisissez un club de remplacement, ou tapez un nom pour le nouveau. |
| `erreur : pas de tables du jeu -- Réglages > Extraire les tables du jeu` | **5. Réglages → Extraire les tables du jeu**. |
| `erreur : pas de dossier du jeu -- Jeu > Choisir le dossier du jeu` | **Jeu → Choisir le dossier du jeu...**. |
| `erreur : le nom du monde doit commencer par _FL26` | **Ligues → Plus ▾ → Nom du monde et fichier...** : un nom qui commence par `_FL26`. |
| `erreur : rien à construire : ajoutez une ligue ou modifiez-en une du jeu ...` | Votre monde est vide. Ajoutez des ligues (étapes 3 à 5). |
| `erreur : <league>, club <n>: <club> plays in <...> -- pick the club that takes its place there` | Faites [Clubs que le jeu a déjà](#clubs-que-le-jeu-a-déjà) pour ce club. |
| `erreur : <league>, club <n>: the new club taking <club>'s place needs a name` | Même fenêtre : tapez un nom à côté de **Sa place revient à un nouveau club, nommé :**. |
| `erreur : <club> is in <league> and in <league>: a club plays in one league` | Retirez le club d'une des ligues (**Nouveau club ici** dans l'onglet Clubs, ou décochez-le avant de l'ajouter). |
| `erreur : <n> new clubs, but the game has room for <m> more (a full squad each)` | Trop de nouveaux clubs. Retirez une ligue, ou des clubs. |
| `erreur : <n> leagues, but the game has room for <m> ...` | Trop de nouvelles ligues. Retirez-en. |
| `erreur : <league> has <n> leagues below it; the game follows one link` / `... are all under ...` | Une seule ligue peut être sous une ligue. Changez la **Division** des autres. |
| `erreur : <league>: division 8 -- the rank field stops at 7` | Un pays descend jusqu'à la 7e division. |
| `erreur : at most 2 split leagues for now ...` / `... only one league of a country can be split or Apertura/Clausura` | Donnez aux autres ligues **tous contre tous**. |
| `Les tables du jeu utilisées par Mod Studio sont plus anciennes que le jeu : ... Les extraire à nouveau d'abord ?` | Cliquez sur **Oui**. |
| Les étapes du Build et **Construire et installer** sont grisés | Le monde ouvert est un monde prêt depuis un zip : il est déjà construit. Ouvrez ou créez un monde à vous (**+ Nouveau monde** dans **2. Mon monde**, ou **Activer** sur la carte de votre monde), ou faites du monde prêt le vôtre avec **Le rendre modifiable...**. |
| `<monde> n'est pas encore construit : d'abord 2. Construire le monde.` (Exporter le monde) | Faites d'abord le Build, puis exportez. |
| `Donnez un nom au paquet.` / `Cochez au moins une ligue.` / `Votre monde n'a pas encore de ligues.` | Dans **Créer un paquet de ligues**, remplissez **Nom** et cochez une ligue ; votre monde a d'abord besoin de ligues. |
| Pas de nouvelles ligues dans Select Team | Commencez une **nouvelle** Master League. Ensuite **4. Après un lancement : vérifier** (étape 13). |
| `sider.log is older than the world switched on -- start the game to the main menu, then check again` | Lancez le jeu jusqu'à son menu principal, fermez-le, vérifiez de nouveau. |
| `<module> not loaded` / `did NOT read the world file` | **2. Mon monde → Construction → Étape par étape, et Exporter le monde → 0. Installer les modules**, puis **3. L'activer**, relancez le jeu et vérifiez de nouveau. Toujours faux : demandez sur Discord. |
| Les noms des clubs sont ceux du jeu, pas les vôtres | Une ancienne sauvegarde Edit les cache : **Mettre la sauvegarde Edit de côté** dans la fenêtre **Build terminé**, ou sortez `EDIT00000000` du dossier de sauvegarde du jeu. |
| Le gardien est le capitaine de chaque nouveau club | Le monde a été construit avant la 0.2.4. Reconstruisez-le et commencez une nouvelle carrière. |
| L'écusson sur le short d'un maillot dessiné est de travers | Le maillot a été dessiné avant la 0.2.4. Supprimez les fichiers `kitmaker.txt` dans `SiderAddons\content\kit-server\<votre monde>` et appuyez de nouveau sur **Construire et installer** : les maillots sont redessinés avec l'écusson dans le bon sens. |
| Tous les nouveaux joueurs ont le même visage | **1. Accueil → Installer maintenant** (quand Accueil dit que les modules manquent ou sont plus anciens), ou **2. Mon monde → Construction → Étape par étape, et Exporter le monde → 0. Installer les modules** : il apporte le pack de visages. Puis relancez le jeu. |

**Demander de l'aide :** sur le [Discord](https://discord.gg/StQqtk3G3M), envoyez une capture
d'écran de ce que vous voyez, le texte du journal du Build, et votre `sider.log` (**Jeu → Ouvrir
sider.log**).
