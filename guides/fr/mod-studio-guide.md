# FL26 Mod Studio — guide d'utilisation

> [English](../en/mod-studio-guide.md) · [hrvatski](../hr/mod-studio-guide.md) · [español](../es/mod-studio-guide.md) · [português](../pt/mod-studio-guide.md) · **français**

> **Première fois avec Mod Studio ?** Deux guides pas à pas, chaque clic dans l'ordre : [Installer un pack prêt](install-a-pack.md)
> (on vous a donné un monde, un modpack ou un `.fl26pack`) · [Créer vos propres ligues et packs](make-your-own-leagues.md)
> (vous choisissez les ligues et les construisez). Ce guide explique chaque page et option en détail.

> Questions fréquentes (mise à jour, plantage au démarrage, coupes, montées, quoi envoyer quand
> quelque chose ne va pas), en anglais : [faq.md](../../docs/faq.md) · questions et aide sur [Discord](https://discord.gg/StQqtk3G3M)

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

La fenêtre est en anglais. **Language** dans la barre du haut (ou **Settings → Language**) la
passe en croate (Hrvatski), en espagnol (Español), en portugais du Brésil (Português) ou en
français (Français). La nouvelle langue s'affiche au prochain démarrage de Mod Studio.

## 2. Premier lancement

**La visite rapide.** La première fois que vous lancez la 0.2.4, une petite carte vous montre où
tout se trouve maintenant, un endroit à la fois, avec un cadre orange autour de ce dont elle
parle : la langue, les cases de ce qui est dans le jeu, **Lancer le jeu**, puis de **1. Accueil**
à **5. Réglages** et **Aide**. Dix étapes. Rien ne change pendant la visite. **Suivant** et
**Retour** avancent et reculent, **Passer la visite** la ferme, et **Aide → Visite rapide** la
remontre à tout moment. Sa dernière carte a **Montrez-moi comment installer un Modpack** : une
deuxième carte qui vous guide pour installer un Modpack (un zip de monde), clic par clic (aussi dans
**Aide → Installer un Modpack, étape par étape**).

1. **5. Réglages → Dossier du jeu** : appuyez sur **Parcourir...**, choisissez le dossier qui
   contient `FL_2026.exe`, puis **Utiliser ce dossier**. La ligne en dessous dit ce qui a été
   trouvé, p. ex. `Trouvé : FL_2026.exe, Sider dans SiderAddons, sider.ini.`
2. Les tables du jeu : Mod Studio les extrait tout seul la première fois (il lit les clubs, ligues
   et joueurs du jeu dans un dossier de travail ; cela prend une minute ou deux, et la barre du
   bas le dit). Après une mise à jour du jeu, Build le remarque et propose d'abord une nouvelle
   extraction ; **Réglages → Les tables du jeu → Extraire les tables du jeu** le fait à la main.
   **Utiliser un autre dossier de tables...** sert pour votre propre base, comme un dossier
   `pesdb` dans livecpk : extrayez d'abord les tables du jeu, puis choisissez ce dossier. Ses
   fichiers passent par-dessus ceux du jeu, qui fournissent tout ce qu'il n'a pas. Un mod de base
   qui déplace les ligues du jeu à la place d'autres ligues (UML 2026 et autres) convient : chaque
   ligue du jeu prend le pays de la plupart de ses clubs, et NewLife Database ne compte un club
   comme celui du jeu que si ces tables l'ont (0.2.4).
3. Ouvrez **1. Accueil**. Il montre le monde qui est dans le jeu (**DANS LE JEU MAINTENANT**, avec
   **Ouvrir ses ligues** et **Changer de monde...**, qui ouvre **2. Mon monde**), une carte qui dit
   si votre monde a des changements que le jeu n'a pas encore (**Aller à Construction** et
   **Seulement les coupes d'Europe...**), et la **Vérification générale** : un tableau avec une
   ligne par vérification (jeu, Sider, modules, dossiers de contenu ...). Quand quelque chose ne
   va pas, une barre rouge nomme le problème et a le bouton qui le corrige. Quand les modules de
   Mod Studio manquent, sont plus anciens ou désactivés, la ligne dit lesquels et **Installer
   maintenant** les met en place. À droite : **Actions rapides** (**Installer les modules**,
   **Reconstruire le monde**, **Importer un zip de monde**, **Ajouter un paquet de ligues**) et
   **Derniers changements** (les points de restauration les plus récents, **Tous les points de
   restauration**).

**Mises à jour.** Quelques secondes après le démarrage, le programme demande à GitHub si une
nouvelle version de FL26 Mod Studio est sortie, et ne le signale que s'il y en a une.
**Télécharger et installer** récupère le nouveau zip, le vérifie avec la somme de contrôle de la
version, ferme le programme, place les nouveaux fichiers par-dessus les anciens et le relance. Vos
réglages, mondes, points de restauration et le jeu ne sont pas touchés. **Aide → Rechercher des
mises à jour...** vérifie à tout moment ; décochez **Aide → Rechercher des mises à jour au
démarrage** et le programme ne vérifie plus que sur demande. Si le programme se trouve dans un
dossier où Windows ne le laisse pas écrire (comme Program Files), il ouvre la page de la version à
la place : décompressez le zip vous-même, ou déplacez le programme dans un dossier à vous.

**Carrières d'avant la 0.2.0.** La 0.2.0 permet 792 matchs par jour du calendrier au lieu de 280, ce qui change les tables avec lesquelles une carrière est sauvegardée : **une carrière sauvegardée avec une version plus ancienne ne se charge pas** (elle reste sur l'écran de chargement). Commencez une nouvelle carrière après la mise à jour. Vos mondes et données Edit ne changent pas.

**La 0.2.4 et votre carrière.** Une carrière sauvegardée avec la 0.2.2 ou la 0.2.3 continue de
marcher, et une coupe sauvegardée avant la 0.2.4 se charge aussi. Une correction demande un
nouveau Build : jusqu'à la 0.2.4, le gardien était le capitaine de chaque club d'un monde fait
avec Mod Studio. **Construction** donne maintenant à chaque club et chaque sélection qui n'en a
pas un capitaine et des joueurs qui tirent les penalties, les coups francs et les corners. Pour
les avoir, reconstruisez votre monde et commencez une nouvelle carrière.

**Jouer.** Le bouton **Lancer le jeu** en haut à droite (ou **Jeu → Lancer le jeu**) lance le jeu
et prévient d'abord quand des modules sont dans un mauvais ordre. À côté, une étiquette dit si
tout est prêt : **PRÊT À JOUER**, **PAS PRÊT** ou **PAS ENCORE DE MONDE**. **Jeu → Lancer le jeu
sans mods (mode sans échec)...** remet la configuration que Mod Studio a trouvée la première fois.

**Crédits.** Le bouton **Crédits**, à côté d'**Aide**, nomme tous ceux qui ont aidé à faire Mod
Studio : les testeurs, ceux qui ont envoyé des rapports et des logs, et ceux dont les idées y sont.

**Plusieurs dossiers Sider ?** Sider ne s'appelle pas forcément `SiderAddons`. Le programme
cherche le dossier à côté de `FL_2026.exe` qui contient un `sider.ini`, et aussi un niveau plus
bas (`sider\patch 1`, `sider\patch 2` ... quand un dossier contient plusieurs copies de Sider).
S'il y en a plusieurs, **Réglages → Dossier de Sider** choisit celui avec lequel il travaille ;
les autres ne sont pas touchés.

**Jeu dans Program Files.** Windows n'y laisse modifier des fichiers qu'à un programme lancé en
administrateur. Quand Mod Studio ne peut pas écrire dans le dossier du jeu, il le dit (sur
**Accueil** aussi) et propose **Redémarrer en administrateur**. Ou déplacez le jeu dans un dossier
à vous.

## 3. Les pages

En haut de la fenêtre, de gauche à droite :

- les menus **Fichier**, **Jeu**, **Profils**, **Langue (Language)** et **Aide**, et **Crédits** ;
- le bouton **Lancer le jeu**, avec l'étiquette « prêt » à côté ;
- en dessous, des cases avec ce qui est dans le jeu maintenant : **DOSSIER DU JEU**, **SIDER**,
  **MONDE ACTIF**, **MODULES**, **LIGUES** et **PACK**. Une case rouge nomme le problème ; cliquez
  sur une case pour aller à la page où il se corrige ;
- puis les sections numérotées, et en bas de la fenêtre une barre d'état (prêt ou le problème, ce
  que fait le programme, **Votre monde est enregistré**, le nombre de points de restauration).

| Section | Ce qu'elle contient |
|---|---|
| **1. Accueil** | Le monde dans le jeu, la vérification générale, les actions rapides |
| **2. Mon monde** | Vos mondes sous forme de cartes, et les onglets **Construction**, **Ligues**, **Clubs**, **Joueurs**, **Maillots**, **Stades** et **Coupes** (section 3.1) |
| **3. Contenu du jeu** ▾ | **Ballons**, **Commentaires**, **Musique**, **Autre contenu** |
| **4. Outils** ▾ | **Modules Lua**, **Dossiers de contenu**, **Profils**, **Points de restauration**, **Diagnostic** |
| **5. Réglages** | Dossier du jeu, dossier de Sider, langue, carrières Master League, tables du jeu |

**Fichier** contient **Nouveau monde**, **Ouvrir un monde...**, **Enregistrer votre monde
sous...**, **Modifications de ce monde...** (tout ce que votre monde change dans le jeu, dans une
seule liste ; choisissez des lignes et appuyez sur **Annuler les modifications choisies** pour
les retirer), **Ajouter un paquet de ligues...** et **Créer un paquet de ligues...**. **Jeu**
ouvre le dossier du jeu, le dossier de Sider, `sider.ini` et `sider.log`, et lance le jeu.
**Aide** contient **Guide d'utilisation**, **Visite rapide**, **Installer un Modpack, étape par
étape**, **Modifier un Modpack, étape par étape**, **Rechercher des mises à jour...** et **À propos de FL26 Mod Studio**.

### 3.1 Mon monde

**2. Mon monde** est l'endroit de vos mondes. Un **monde** est un dossier de contenu nommé
`_FL26...` qui contient de nouvelles ligues, de nouveaux clubs et joueurs ; le jeu en lit un à la
fois (section 8).

**En haut** : **COMPÉTITIONS** (combien de compétitions, ligues et coupes ensemble, a le monde qui
est dans le jeu ; le jeu a de la place pour 255), **NOUVEAUX PAYS** (combien de pays il ajoute ;
de la place pour 99), un rappel que **les changements demandent une nouvelle Master League**, et
l'état du monde ouvert. **▾ Mondes** replie la rangée de cartes pour faire de la place, et la
réaffiche.

**Les cartes** : une carte pour chaque monde sur le disque. Le monde qui est dans le jeu vient en
premier, puis les plus récents ; la molette de la souris fait défiler la rangée à gauche et à
droite.

- Le monde qui est dans le jeu est vert, avec **● DANS LE JEU MAINTENANT** et **● Actif**. Un
  monde installé depuis un zip a l'étiquette **Depuis un zip**.
- Chaque autre monde construit (**PAS DANS LE JEU**) a **▶ Activer** : il met ce monde dans le
  jeu (activé dans `sider.ini`) et en retire celui qui y était. Rien n'est supprimé : l'autre
  monde reste sur le disque avec ses propres carrières. Commencez ensuite une nouvelle Master
  League.
- Chaque carte a **Exporter...** (un seul `.zip` du monde pour un autre PC, section 9.1),
  **Renommer** et **Supprimer**. **Supprimer** retire le monde du jeu et du disque, mais le garde
  en entier dans **Points de restauration** (section 5). Le monde qui est dans le jeu ne peut pas
  être supprimé : activez d'abord un autre monde.
- **+ Nouveau monde** à la fin commence un monde vide à vous (comme **Fichier → Nouveau monde**) ;
  ajoutez ensuite ses ligues dans **Ligues**.

Si deux mondes sont activés en même temps, la carte verte affiche **▶ Garder seulement
celui-ci** : il garde ce monde dans le jeu et désactive les autres.

**Les onglets** sous les cartes modifient le monde ouvert : **Construction** (section 8.2),
**Ligues**, **Clubs** et **Joueurs** (section 8), **Maillots** et **Stades** (section 6).
**Coupes ▾** ouvre les fenêtres des coupes : **Tournois de pré-saison**, **Coupes de nos pays**,
**Coupes des pays du jeu** et **Noms des compétitions**. À droite :

- **NewLife Database** ouvre la page NewLife (section 8.4) ;
- **+ Ajouter...** est une seule fenêtre pour trois choses : un zip de monde (un Modpack), un
  paquet de ligues (`.fl26pack`) et la NewLife Database (un dossier ou ses zips). Déposez le
  fichier dessus ou utilisez **Choisir un fichier...** / **Choisir un dossier...**. Une ligne
  verte dit ce qu'elle a trouvé ; pour un paquet de ligues, elle liste les ligues à cocher et
  combien de compétitions le monde aura. **Ajouter** le passe à la bonne page : un zip de monde à
  **Importer votre monde** (section 4), un paquet dans votre monde, la NewLife Database à sa page.
  Rien n'arrive dans le jeu avant **Construire et installer** ;
- **Plus ▾** contient **Paquets de ligues** (section 9), **Importer un zip de monde** (section 4),
  **NewLife Database** et **Dossiers de contenu** (section 5).

**Un monde depuis un zip** (un Modpack) est déjà construit, donc **Construction** est désactivé
pour lui (section 8.2). Pour le changer quand même, **Le rendre modifiable...** en haut de Mon
monde en fait un monde à vous, sur place et sous son propre nom. Tout est d'abord copié dans
**Points de restauration**. Après le Build, commencez une nouvelle Master League.
**Aide → Modifier un Modpack, étape par étape** le montre clic par clic.

**Chaque monde garde ses propres carrières Master League** (0.2.4). Une carrière est faite pour
un monde : dans un autre monde, ses ligues et ses clubs n'existent pas. Donc chaque fois que le
monde du jeu change (**Activer**, **Construire et installer** d'un autre monde, Importer votre
monde, Dossiers de contenu, un profil), Mod Studio change le dossier de sauvegarde du jeu avec
lui. Les carrières du monde qui sort sont gardées dans `save_<monde>`, à côté de `save`, dans
`Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026`. Les carrières du monde qui entre
reviennent dans `save` ; un monde qui n'en a pas encore commence avec un dossier vide. Tout le
dossier suit le monde (carrières, Become a Legend, les données Edit), sauf vos réglages du jeu,
qui vous suivent dans chaque monde.

Rien n'est supprimé : avant le premier changement, Mod Studio copie tout votre dossier de
sauvegarde dans `SiderAddons\ModStudio\backups\saves\<date>` (**Points de restauration** le
liste), et la première fois il vous dit où sont allées vos carrières. Il ne change rien pendant
que le jeu tourne, ni quand un dossier `save_<monde>` de ce nom existe déjà : il dit pourquoi et
ne touche à rien. **Renommer** renomme aussi le `save_<monde>` du monde ; **Supprimer** le laisse
(vos carrières sont à vous). Vous n'en voulez pas ? Décochez **Réglages → Chaque monde garde ses
propres carrières (le dossier de sauvegarde change avec le monde)**.

**Ligues** (un onglet de Mon monde) liste toutes les ligues, celles du jeu et les vôtres, sous
leur continent ; les divisions de chaque pays restent ensemble, de haut en bas (Bundesliga,
2. Bundesliga, 3. Liga), jusqu'à ce que vous glissiez une ligue pour la mettre ailleurs. Filtres
**Toutes**, **Nôtres** et **Modifié**, et un champ de recherche. Choisissez-en une : une ligue à
vous a **Modifier la ligue...**, **Ajouter une division inférieure**, **Clubs et noms**,
**Joueurs** et **Retirer** ; une ligue du jeu a son nom, son logo et ses clubs (section 8, « Les
ligues du jeu »). **Ajouter une ligue** en crée une nouvelle. **Places dans Select Team** montre
où le dernier Build a mis chacune de vos ligues. **Plus ▾** contient **Tournois de pré-saison**,
**Coupes de nos pays**, **Coupes des pays du jeu**, **Places européennes des ligues du jeu**,
**Clubs européens de la première saison**, **Classement UEFA**, **Places sud-américaines** (avec sa case **Compétitions modernes de la CONMEBOL**, 0.2.5), **Pays de la CONMEBOL sans championnat** (avec les compétitions modernes),
**Noms des compétitions**, **IDs des compétitions**, **Ordre des championnats**, **Saisons des
championnats du jeu** et **Nom du monde et fichier...**. Ce dernier ouvre la page avec le nom du
monde et la liste de vos ligues (les anciens guides l'appellent *Nouvelles ligues*).

## 4. Importer votre monde

**Importer votre monde** est la page qui installe un pack téléchargé. Vous y arrivez par
**2. Mon monde → Plus ▾ → Importer un zip de monde**, par **Importer un zip de monde** dans
**Actions rapides** sur **Accueil** (il ouvre tout de suite le choix du fichier), ou par
**+ Ajouter...** dans Mon monde.

Déposez le pack dessus (`.zip`, `.7z`, un dossier, `.lua`, `.cpk` ou `.fl26pack`), ou utilisez
**Choisir un fichier...** / **Choisir un dossier...**. Quand Mod Studio tourne en administrateur,
Windows bloque le glisser-déposer ; la page le dit : utilisez les deux boutons.

Le programme regarde à l'intérieur et dit en une ligne ce que c'est : une version plus récente d'un
monde que vous avez, un monde prêt à jouer, un paquet de ligues ou un mod, avec les ligues qu'il
contient. Puis un seul bouton, **Installer** (**Installer le monde** pour un monde). Une version
plus récente d'un monde que vous avez remplace l'ancienne : il demande une fois, l'ancienne est
retirée d'abord pour que rien n'en reste, vos sauvegardes ne sont pas touchées, et vous commencez
une nouvelle Master League avec la nouvelle. Si un monde du même nom a été construit sur ce PC, il
le dit avant que vous appuyiez sur Installer, et vous demande de renommer d'abord ce monde sur sa
carte dans Mon monde.

Les parties, et où va chacune, sont sous le pli **Plus d'options : quelles parties, nom, ordre des
dossiers de contenu, lignes des map** :

| Partie | Ce qui se passe |
|---|---|
| Dossier de contenu (livecpk) | Copié dans `SiderAddons\livecpk\<nom>` et ajouté à `sider.ini`. |
| Fichiers de serveur de contenu | Copiés dans le dossier `content` du serveur. Son **fichier de correspondance est fusionné avec le vôtre** : vos lignes restent et les nouvelles lignes du mod sont ajoutées. Pour un club que vous avez déjà, le choix sous **Plus d'options** décide : *utiliser celles du mod*, ou *garder les miennes, ajouter celles du mod après*. Un pack de tableaux de score ou de menus fait pour un autre monde va sur la compétition que son nom indique dans votre monde, et la page dit quelle ligue votre monde n'a pas. |
| Module Lua | Copié dans `SiderAddons\modules` et activé à la bonne place dans l'ordre. |
| .cpk compressé | Extrait dans un dossier de contenu à l'installation. |
| Paquet de ligues | Ajouté à votre monde (section 9). Un `.fl26pack` déposé ici y entre, et **Construire et installer** démarre tout seul. |
| Monde prêt | Un monde construit venant d'**Exporter le monde** (section 9.1), ou un dossier `SiderAddons` copié avec `modules\fl26world.txt`. Le dossier du monde est copié sous son propre nom, son fichier de monde va dans `SiderAddons\modules`, et le monde est mis dans le jeu avec les modules de Mod Studio. Cela se termine par **✓ Prêt à jouer : appuyez sur Lancer le jeu et lancez une nouvelle Master League** et une liste de vérification finale : le monde, activé, les modules, le pack de visages, les serveurs de contenu que le monde utilise, les stades à domicile. S'il manque quelque chose, il dit **Presque prêt** et ce qu'il faut corriger ; la ligne rouge sous l'installation (*voir quoi corriger*) remontre la liste. |
| DLL | **Non installée.** Une DLL s'exécute avec les droits du jeu ; n'en installez une qu'à la main, et seulement depuis une source de confiance. |

Dans le même pli, vous pouvez décocher une partie dont vous ne voulez pas (les maillots, par
exemple, pour installer un monde sans maillots), donner un nom au mod, et choisir si les nouveaux
dossiers de contenu vont en haut (ils l'emportent) ou en bas. **Dans le jeu maintenant** liste
chaque pack installé avec le programme. **Retirer** supprime les fichiers qu'il a ajoutés et remet
en place ceux qu'il a remplacés.

L'installation copie d'abord tous les fichiers et écrit les lignes des map en dernier, donc une
installation qui s'arrête à mi-chemin ne laisse aucune ligne qui pointe vers un fichier manquant.
Si c'est arrivé avec une version plus ancienne, **Diagnostic** nomme le zip ou le monde :
installez-le à nouveau (un monde construit sur votre PC : reconstruisez-le).

## 5. Dossiers de contenu et modules Lua

**Dossiers de contenu** (**4. Outils**) liste les lignes `cpk.root` de `sider.ini` ; les mondes
(`_FL26...`) s'affichent quand vous cochez **Afficher les mondes (_FL26...)**, et **Seulement les
activés** masque le reste. Le monde que le jeu utilise maintenant est sur une ligne verte, son nom
en gras, avec **DANS LE JEU MAINTENANT** dans la colonne Remarque. Sider cherche un fichier de
haut en bas, donc quand deux dossiers ont le même fichier, celui qui est plus haut dans la liste
l'emporte.

- Cochez ou décochez un dossier pour l'activer ou le désactiver (la ligne est mise en
  commentaire, jamais supprimée).
- **En haut**, **Monter**, **Descendre** changent l'ordre ; **Ajouter un dossier...** ajoute un
  dossier que vous avez déjà.
- La taille et le contenu (visages, maillots, stades...) sont affichés pour chaque dossier.
- Il y a aussi **Actualiser**, **Retirer de la liste** et **Supprimer du disque...**.
- Rien n'est écrit tant que vous n'appuyez pas sur **Appliquer**. **Abandonner** oublie les
  modifications.

**Renommer le monde...** et **Supprimer le monde...** (sous les détails du dossier quand un monde
est choisi, ou clic droit sur le monde) font la même chose que **Renommer** et **Supprimer** sur
la carte d'un monde dans Mon monde :

- **Supprimer le monde...** demande d'abord et ne supprime rien pour de bon. Le dossier du monde,
  ses maillots et tableaux de score, ses lignes dans `sider.ini` et dans les map des maillots et
  des tableaux de score, et sa trace d'installation vont dans
  `SiderAddons\ModStudio\backups\worlds\<monde>\<date> deleted`, et **Points de restauration →
  Restaurer cette copie** remet tout exactement comme avant. Les 3 dernières copies de chaque
  monde sont gardées. Le monde qui est dans le jeu (le vert) ne peut pas être supprimé. Votre
  monde dans Mod Studio (ses ligues) n'est pas supprimé, vous pouvez donc le reconstruire.
  **Supprimer du disque...** sur la ligne d'un monde fait la même suppression sûre.
- **Renommer le monde...** change le nom partout où il est écrit : la ligne de `sider.ini` (même
  place, activée ou non comme avant), les dossiers des maillots et des tableaux de score et leurs
  lignes des map, le fichier du monde, vos profils et votre monde dans Mod Studio. Le nouveau nom
  doit commencer par `_FL26` (lettres, chiffres, `-` et `_`). Un gros monde est renommé en
  arrière-plan (« Renaming ... » dans la barre du bas et sur sa carte). Une carrière continue de
  marcher après un renommage : le jeu ne voit jamais le nom du monde, seulement ses fichiers.

**Modules Lua** (**4. Outils**) fonctionne de la même façon pour les lignes `lua.module`. La ligne
du haut dit si les modules de Mod Studio sont installés, à jour et activés ; sinon, elle nomme ceux
qui manquent, sont plus anciens ou désactivés, et **Installer maintenant** corrige cela. Le
programme connaît le bon ordre des modules courants (les serveurs de contenu après les modules
qu'ils utilisent) et le signale quand un module est mal placé. Certains modules ont besoin d'un
réglage de Sider (par exemple Goal Song Server a besoin de `match-stats.enabled = 1`) ; le
programme dit lequel. Les modules `fl26...` de Mod Studio sont masqués tant que vous ne décochez
pas **Masquer les modules de Mod Studio (fl26...)** ; **Ajouter un module...** ajoute un module
que vous avez.

Les modules de Mod Studio gardent l'ordre dans lequel ils ont été installés, ensemble dans un
seul bloc de `sider.ini` avec son propre titre. Les vieilles lignes laissées par une installation
à la main (un ancien jeu de caps, un module listé deux fois) sont désactivées par **Installer
maintenant** et par **Construction**.

Depuis 0.2.0 les douze petites protections contre les plantages arrivent en deux fichiers, `fl26guards.lua` (les huit `fl26nullguard`) et `fl26lateguards.lua` (`fl26superguard`, `fl26resultsguard`, `fl26ctlguard`, `fl26kitguard`), la liste est donc plus courte. sider.log nomme toujours chaque protection sur sa propre ligne. Le Build désactive les anciennes lignes séparées ; rien à faire à la main.

**Plus de copies à côté de vos fichiers** (0.2.4). Quand Build, L'activer ou Installer les
modules changent un fichier, la copie d'avant va dans `SiderAddons\ModStudio\backups` et apparaît
dans **Points de restauration**, pas à côté du fichier (plus de `map.txt.before-builder` ni de
`modules\before-builder-<n>`).

**Désactiver les regens** (0.2.0) : `fl26regen` donne aux regens de nouveaux noms, un nouveau
potentiel et un visage du pack de visages des regens. Pour jouer sans lui, décochez **Masquer
les modules de Mod Studio (fl26...)** pour voir les nôtres, décochez `fl26regen` et appuyez
sur **Appliquer**. Mod Studio le note dans `modules\fl26-off.txt` dans le dossier de Sider : la
**Construction**, **Installer les modules** et le changement de monde le laissent désactivé au
lieu de le réactiver, comme ils le font pour tous les autres modules. Le jeu fait alors ses
propres regens : son potentiel et ses noms, sans visages du pack de visages des regens.
Recochez-le et appuyez sur **Appliquer** pour le réactiver. Seul `fl26regen` peut rester
désactivé ainsi.

## 6. Contenu du jeu : les serveurs de contenu

Chacune de ces pages appartient à un serveur de contenu. **Maillots** et **Stades** sont des
onglets de **2. Mon monde** ; **Ballons**, **Commentaires**, **Musique** et **Autre contenu** sont
sous **3. Contenu du jeu**. **Autre contenu** a un onglet pour **Tableaux de score**, **Menus**,
**Tenues d'arbitre**, **Badges de manche** et **Météo**, et **Modules d'apparence**. Les modules propres à SPFL26 pour les maillots, les stades et les tableaux de score (`common\kits.lua`, `common\stadiums.lua`, `common\scoreboards.lua`) lisent les mêmes fichiers dans `content\kits`, `content\stadiums` et `content\scoreboards` ; quand le serveur lui-même n'est pas installé, sa page modifie ceux-là (maillots depuis 0.1.7, stades et tableaux de score depuis 0.1.8). Chaque page a :

- une **ligne d'état** : le module est-il activé, son dossier de contenu est-il là ;
- un onglet par **fichier de correspondance**, affiché sous forme de tableau : quelle compétition,
  quel club ou quel stade reçoit quoi. **Ajouter...**, **Modifier...**, **Copier**, **Activé /
  désactivé** (la ligne devient un commentaire) et **Retirer** ; choisissez les éléments dans la
  bibliothèque au lieu de taper des id. **Enregistrer** écrit le fichier ; la copie d'avant va
  dans Points de restauration ;
- la **Bibliothèque** : ce qu'il y a dans le dossier de contenu du serveur, avec des images quand
  il y en a. Les éléments qu'aucune ligne n'utilise et les lignes qui pointent vers des éléments
  manquants sont signalés ;
- les **Réglages** du serveur quand il en a (stade, ballon, tableau de score préférés ...).

Le programme vérifie les tableaux avant d'enregistrer : un nombre là où il faut un nombre, pas de
virgule dans un nom, un élément qui existe. Une ligne avec un problème est colorée : **laissez la
souris dessus pour voir pourquoi**. **Seulement les lignes avec des problèmes** n'affiche que
celles-là. Un club listé deux fois est signalé aussi : seule sa première ligne compte. Le problème
le plus courant, « ... introuvable dans la bibliothèque », veut dire que la ligne pointe vers un
dossier qui n'est pas dans le dossier de contenu du serveur, et le jeu n'affiche rien à cet endroit
(un stade noir, l'ancien maillot du club) : faites-la pointer vers un dossier que liste l'onglet
**Bibliothèque**, ou retirez la ligne. **Modules d'apparence** (dans **Autre contenu**) active ou
désactive les modules sans fichier de correspondance.

Une ligne de compétition va par **phase** de la compétition, pas par compétition : le jeu donne
aux serveurs de contenu la phase jouée (la Conference League, c'est 186, 1210, 187, 189 et ses
tours suivants 1213 ... 8381 ; la Ligue des champions 2, 3, 4 et les siens), donc une ligne avec
le numéro de la compétition (174) ne sert jamais. Le sélecteur de compétitions propose chaque
compétition une fois de plus en **(toutes les phases : N)** : choisissez-la et une ligne est
écrite par phase (0.1.9). Une ligne avec le numéro d'une compétition est signalée comme problème.

**Tableaux de score d'un monde depuis un zip.** Un monde prêt (le Modpack) apporte les tableaux
de score de ses ligues. Tant qu'un autre monde est dans le jeu, leurs lignes restent dans **Autre
contenu → Tableaux de score**, désactivées, et elles se réactivent avec leur monde. Il en va de
même pour les thèmes de menus qu'un monde a apportés.

**Importer des maillots...** (0.1.8, dans l'onglet *Maillots*) : des maillots pour beaucoup de clubs d'un coup. Choisissez un dossier de maillots kit-server prêts -- un dossier par club, avec `p1`, `p2`, `g1` ... et `order.ini`, nommé d'après le club (`Dinamo Zagreb`) ou son ID d'équipe (`2215`). **Associer à** choisit *Tous les clubs* ou *Les nouveaux clubs du monde du jeu*. Les associations à 60 % ou plus sont cochées ; vérifiez celles qui ne le sont pas et la colonne *Correspondance* avant **OK** (un dossier sans association affiche « aucun club trouvé »). Les maillots sont copiés dans la bibliothèque de kit-server (`Ligue\Club`, comme le dossier les avait) et chaque club reçoit une ligne dans `map.txt` ; **Enregistrer** l'écrit. Un club qui a déjà une ligne la garde, sauf si **Remplacer les maillots déjà définis** est coché. Les maillots d'un nouveau club suivent l'ID que Build lui a donné : faites d'abord Build du monde et laissez-le dans le jeu. Le dossier d'un club peut aussi contenir de simples images de maillots (0.2.0) : `p1.png`, `p2.png` ... pour les maillots et `g1.png` pour le gardien (2048 x 2048 de préférence ; `.jpg` et `.dds` marchent aussi). Mod Studio en fait des maillots kit-server ; les numéros de dos, les numéros de short et la police du nom sont des textures à part, ils viennent donc d'un maillot déjà dans la bibliothèque, choisi dans **Numéros et noms de** (il commence sur le premier maillot de la bibliothèque qui en a ; *aucun* : le jeu garde ceux du club). Les couleurs de `config.txt` sont lues sur l'image. La conversion des images est de Xxspedd, tirée de son outil de maillots. Mod Studio ne dessine pas de maillots : les images viennent de vous ou d'un créateur de maillots.

Si votre monde est construit avec **Maillots simples pour le mode Édition** (section 8), Kit
Server n'habille pas les nouveaux clubs, donc les maillots importés ne s'affichent pas sur eux ;
**Importer des maillots** le dit. Décochez cette option dans l'onglet **Construction** et
reconstruisez.

## 7. Profils

Un profil retient quels dossiers de contenu et modules sont activés, et dans quel ordre. Gardez-en
un pour la Master League, un pour le jeu en ligne, un pour les tests (**4. Outils → Profils**, ou
le menu **Profils**) :

- **Enregistrer la configuration actuelle...** enregistre ce qui est activé maintenant sous un nom.
- **Passer à ce profil** met cette configuration dans `sider.ini` (l'ancien `sider.ini` va dans
  Points de restauration).
- **Mettre à jour avec la configuration actuelle** écrase le profil ; **Supprimer** le retire.
- **Exporter...** / **Importer...** déplacent un profil vers un autre PC (`.fl26profile.json`).

## 8. League Builder : nouvelles ligues, nouveaux clubs et joueurs

Le League Builder ajoute de nouvelles ligues au jeu et modifie celles du jeu. Ce qu'il crée est un
**monde** : un dossier de contenu nommé `_FL26...` que le jeu lit tant qu'il est dans le jeu. Vous
travaillez dans les onglets de **2. Mon monde**.

**Retirer** (Ligues) supprime la ligue sélectionnée avec ses clubs. Pour en supprimer plusieurs
d'un coup, ouvrez **Plus → Nom du monde et fichier...**, sélectionnez-les avec Ctrl+clic,
Maj+clic ou Ctrl+A, puis **Retirer** ou la touche Suppr.

**Ligues → Ajouter une ligue**

| Champ | Ce que cela veut dire |
|---|---|
| **Nom** | Le nom de la ligue dans le jeu. Deux ligues ne peuvent pas avoir le même. |
| **Pays** | Donne le drapeau et l'endroit où la ligue apparaît dans la liste. Un pays pour lequel le jeu n'a pas de ligue reçoit son propre titre. |
| **Clubs** | De 10 à 24 (de 1 à 24 pour des clubs sans championnat). |
| **Clubs sans championnat** | Pour un club, ou quelques-uns, sans championnat autour (0.1.8) : par exemple seulement le BATE Borisov de Biélorussie. Choisissez le groupe où ils vont : *Other European teams*, *Other Latin American teams*, *Other Asia-Oceania teams*, *Other Africa teams* ou *Classic Teams* -- là où le jeu range ses propres clubs qui ne jouent dans aucun championnat (Dynamo Kyiv, Wydad Casablanca ...). Dans Select Team ils apparaissent dans ce groupe. Ils ont nom, écusson, maillots, entraîneur, formation, joueurs et stade comme tout nouveau club (**Modifier le club**, **Joueurs**) ; le nom du haut sert seulement à Mod Studio pour les lister. Ils ne jouent ni championnat, ni coupe, ni compétition européenne, et tout le reste de cette fenêtre est en gris. Dans *Ligues*, un tel groupe affiche *no league (...)* au lieu d'un ID de ligue. |
| **Format** | *Tous contre tous*, 1 à 4 fois, *se divise en deux (à l'écossaise)* ou *Apertura et Clausura* : deux tournois par saison (septembre à début janvier, janvier à mai), chacun à partir de zéro point, puis des play-offs de 8 ou 4 clubs (ou aucun). Le classement de toute la saison décide des montées et descentes. 18 clubs au maximum. Une ligue divisée a 46 journées au maximum, avant et après la division ensemble (16 clubs deux fois font 30, donc son plus grand groupe deux fois peut avoir 8 clubs, 14 journées). Pour l'instant, une seule ligue par pays peut se diviser ou jouer Apertura/Clausura. **La division en deux et Apertura et Clausura sont expérimentales** (0.2.4) : elles fonctionnent, mais ont encore plus de bugs ouverts que tous contre tous, le format entièrement testé. La fenêtre le dit sous les formats. Continuez à signaler ce que vous trouvez. |
| **Division** | *(première division)*, ou la ligue au-dessus : une autre nouvelle ligue, ou une ligue du jeu. Pour placer une nouvelle ligue sous une autre nouvelle ligue en une étape : sélectionnez-la et appuyez sur **Ajouter une division inférieure** (elle reprend le pays, le nombre de clubs, le format et les montées/descentes de la ligue au-dessus ; il ne reste que le nom). Une ligue qui a déjà une autre nouvelle ligue en dessous est grisée (0.1.9) : le jeu ne suit qu'un seul lien vers le bas depuis une ligue, donc les groupes d'une même division (trois groupes de Serie C sous la Serie B) ne sont pas encore possibles. |
| **Montée / descente** | Combien de clubs échangent leur place avec la ligue au-dessus en fin de saison. |
| **Saison** | Première division d'un nouveau pays uniquement : *août à mai* (par défaut) ou *février à décembre*, comme le Brésil, le Japon ou l'Arabie saoudite : les clubs montent et descendent au Nouvel An, et les divisions en dessous la suivent. Pas encore avec une division en deux, Apertura/Clausura ou une coupe de la ligue -- ni avec une division en deux ou Apertura/Clausura sur une division sous un championnat de février à décembre (la Liga BetPlay ou la J1 League du jeu comprises). |
| **Europe** | Première division uniquement : quelle position en ligue va dans quelle compétition européenne. **Première division : 1er qualifications LDC, 2e LE, 3e LECE** remplit les trois places habituelles (*... (qualifications)* sont les barrages d'août, voir 8.2) ; **Ajouter une place**, le ✕ d'une ligne et **Effacer** pour tout le reste. Chaque position une seule fois, et seulement les positions que la ligue a. Sous 1, la position s'affiche **Vainqueur de la coupe** (0.1.7) : le vainqueur de la coupe du pays (un nouveau pays a besoin de **Coupe nationale**) -- et si le vainqueur a déjà une place européenne par la ligue, la place descend la ligue jusqu'au club suivant, comme à l'UEFA. Depuis 0.2.0, le vainqueur de la coupe peut aussi aller dans les coupes que Mod Studio construit (Copa Sudamericana, Coupe de la Confédération CAF, AFC Champions League Two ...) ; dans une nouvelle carrière, avant que quiconque ait gagné la coupe, cette place va aussi au club suivant de la ligue. Une ligue du jeu peut aussi en avoir une (*Places européennes des ligues du jeu*). Laissez vide pour une division inférieure. Le modèle suit le pays : l'Asie reçoit l'AFC Champions League et l'AFC Champions League Two, l'Amérique du Sud la Libertadores et la Copa Sudamericana, l'Afrique la Ligue des champions CAF et la Coupe de la Confédération CAF, l'Amérique du Nord et centrale la CONCACAF Champions Cup, l'Océanie l'OFC Champions League. L'**AFC Challenge League** (0.2.0) est la troisième coupe de l'AFC, sous l'AFC Champions League Two, comme la Ligue Europa Conférence en Europe ; elle se choisit avec **Ajouter une place** (*AFC CHL* dans la liste des ligues). Ces sept coupes que le jeu n'a pas sont construites avec le monde (section 8.2). Une place en *qualifications de la Libertadores* prend la place d'un club du jeu au tour préliminaire (le dernier du pays qui y a le plus de clubs), au plus six de ses huit places ; **Vérifier le plan** indique quelles ligues restent dehors au-delà. |
| **Logo** | N'importe quelle image (un PNG à fond transparent rend le mieux). Vide : un logo est dessiné pour vous. |
| **Drapeau du pays** | Votre propre image du drapeau du pays, étirée dans le cadre des drapeaux du jeu. Elle remplace le drapeau de ce pays partout dans le jeu (Select Team, nationalité des joueurs, l'en-tête du pays dans Database > Competition Info) tant que le monde est activé. Vide : le drapeau du jeu. |
| **Coupe** | Première division uniquement. **Coupe nationale** : le pays a sa propre coupe, avec le nom que vous donnez (vide : `<ligue> Cup`). Le jeu remplit la coupe d'un pays avec sa première division et la division en dessous, et la taille de la coupe suit la ligne Coupe nationale des Limites (8.3) : la plus grande taille que l'écran de la coupe dessine et qui tient, donc 22 clubs donnent une coupe de 20, la première division d'abord. Au-delà de 44 clubs, la coupe ne garde que la première division. Une nouvelle deuxième division sous un pays que le jeu a déjà (Allemagne, Russie ...) entre aussi dans la coupe de ce pays, après les clubs de première division, quand les tours de la coupe conviennent au nombre de clubs. Une nouvelle troisième division ou plus bas (League One sous la Championship) laisse la coupe du pays aux deux premières divisions du jeu, comme dans le jeu. **Supercoupe (champion contre vainqueur de la coupe)** : en plus, une supercoupe en un match avant la saison. Elle a besoin de la coupe nationale. |
| **Coupe de la ligue** | Première division uniquement. Une coupe à élimination directe de cette ligue et de celle du dessous, jouée comme la Carabao Cup (0.2.0) : un match par tour, la demi-finale et la finale aussi, aux semaines de la Carabao Cup : 27 août, 23 septembre, 28 octobre, le quart de finale le 23 décembre, la demi-finale le 14 janvier et la finale le dimanche 15 mars, à des jours à elle, jamais un jour de coupe nationale ou d'Europe. Le tableau compte autant de clubs des deux divisions que l'écran de la coupe en dessine, jusqu'à 44 (20 + 24 : toute la Premier League et la Championship) ; quand ce n'est pas 16 ou 32, les clubs de cette ligue sont exemptés et commencent au deuxième tour. Chaque rencontre est tirée au sort. Donnez-lui un nom ou laissez vide (`<ligue> League Cup`). Un monde construit avant 0.2.0 garde l'ancienne coupe aller-retour à 16 avec son tour préliminaire jusqu'à ce que vous le reconstruisiez ; une carrière commencée avant ce Build joue l'ancienne coupe. |
| **Logos des coupes** | Une image pour la coupe nationale, la supercoupe, la coupe de la ligue et les play-offs de l'Apertura/Clausura, chacune à part. Vide : un emblème aux initiales de la coupe est dessiné. |
| **Exhibition uniquement -- pas en Ligue des Masters** | Pour le Kick Off et les matchs amicaux : une ligue historique, des légendes, etc. Ses clubs ne jouent jamais de saison de Master League, donc la ligue reste seule : pas de division au-dessus ni au-dessous, pas de places européennes, pas de coupes. Elle apparaît quand même dans la liste des équipes de la Master League ; choisissez votre club dans une autre ligue. |
| **Formation** | Comment les clubs de la ligue se placent. Choisissez une des formations des clubs du jeu (4-2-3-1, 4-1-2-3, 4-3-3, 5-3-2 ... ; la liste indique combien de clubs du jeu la jouent) : chaque nouveau club reçoit une copie de la tactique d'un club du jeu avec cette formation, et son meilleur onze est aligné en conséquence au Build. Vide : Build choisit pour chaque club la formation qui convient le mieux à son effectif (0.2.4 ; avant, un 4-2-3-1 fixe) : deux bons attaquants jouent à deux en pointe, de bons ailiers donnent trois attaquants, trois défenseurs centraux une défense à trois ou à cinq. Le journal du Build dit quelles formations ont été choisies. Un club peut avoir la sienne (**Modifier le club**). |

Le **Nom du monde** (Ligues → Plus → **Nom du monde et fichier...**) doit commencer par `_FL26`. Cette page liste aussi vos ligues : après le **Build**, sa
colonne **ID de la ligue** montre l'id de compétition de chaque ligue dans le jeu, celui que porte
son fichier de logo. La colonne **#** est la place de la ligue dans l'ordre (**Monter** / **Descendre**),
et **Select Team** dit où le dernier Build l'a mise : *oui*, *à la place de* l'un des groupes du jeu, ou
*pas de place (elle se joue)*. Un `*` veut dire que l'ordre a changé depuis : refaites un Build pour voir
où elle va. Glisser une ligue dans l'onglet **Ligues** ne la déplace qu'entre les places que les ligues de son continent ont déjà ici (0.2.0 ; avant, tout l'ordre passait par continent, et les ligues d'Amérique du Nord et d'Océanie finissaient toujours dernières).

**Tournois de pré-saison** (Ligues → Plus, ou Mon monde → Coupes) : des tournois amicaux à élimination directe de 4 ou 8 clubs invités en juillet, avant la saison, appariés dans l'ordre donné (le premier contre le deuxième ...). Un club est celui d'une nouvelle ligue ou un club du jeu (son id) ; au moins un doit venir d'une nouvelle ligue, dont le pays accueille le tournoi. Une carrière commence en août, donc le premier se joue la deuxième saison. Chaque tournoi peut avoir son **Logo** ; vide : un logo est dessiné.

**Coupes de nos pays** (Ligues → Plus, ou Mon monde → Coupes, 0.2.4) : les coupes de vos propres ligues dans un seul tableau. Pour chaque première division : sa coupe nationale, sa supercoupe et sa coupe de la ligue, chacune avec son nom et son logo. Ce sont les mêmes champs que dans **Modifier la ligue...**, sans ouvrir chaque ligue.

**Coupes des pays du jeu** (Ligues → Plus, ou Mon monde → Coupes) : une coupe de la ligue -- la Carabao Cup, par exemple -- pour des ligues du jeu. Cochez **Coupe de la ligue** à côté d'une ligue : elle et la ligue du dessous, jusqu'à 44 clubs, un match par tour de fin août à la finale mi-mars, tirée au sort, les clubs de la ligue exemptés jusqu'au deuxième tour (0.2.0 ; la même coupe que celle d'une nouvelle ligue), les jours que le calendrier des ligues et coupes du jeu laisse libres. **Supercoupe**, le champion contre le vainqueur de la coupe, seulement là où le jeu n'en a pas (Brésil, Chili, Écosse, Grèce, États-Unis). C'est une supercoupe en un match entre deux clubs (0.2.4 ; avant, elle sortait comme une coupe à élimination de 16). Elle se joue fin juillet ; dans un pays de février à décembre (la Supercopa de Chile, la Supercopa Rei), elle se joue fin janvier, entre le champion et le vainqueur de la coupe de la saison qui vient de finir. Quand il n'y a pas encore de vainqueur de coupe (le premier été d'une nouvelle carrière), ou que le champion a aussi gagné la coupe, c'est le deuxième de la ligue qui joue. Nom vide : le nom de la ligue et *League Cup* / *Super Cup*. **Logo** à côté de chaque nom (0.2.0) : une image pour cette coupe ; sans elle, un emblème avec les initiales de la coupe. Ces changements demandent **Installer les modules** (ou Construire et installer), un nouveau Build et une nouvelle carrière.

**Places européennes des ligues du jeu** (Ligues → Plus) : quelles places de la Premier League, de la LaLiga, de la Serie A ... vont dans quelle compétition européenne. La liste montre les places du jeu ; cochez **Places propres pour cette ligue** pour les changer. Une ligue non cochée garde celles du jeu, une ligue cochée sans lignes n'envoie personne.

**Classement UEFA** (Ligues → Plus, 0.1.7) : toutes les ligues européennes du monde -- celles du jeu et
vos nouvelles premières divisions -- dans une seule liste, le pays le plus fort d'abord. Glissez une
ligue (ou **Monter** / **Descendre**) pour changer l'ordre, décochez-la pour ne lui donner aucune
place européenne, et **Ordre de l'UEFA** remet la liste au classement des associations de l'UEFA
pour 2026-27. La partie droite montre ce que reçoit chaque ligue, et **OK** l'écrit : les places de
la clé de l'UEFA pour 2024-27 -- le rang 1 a cinq places en Ligue des champions, le rang 6 deux et
une place de barrage, le rang 30 une place au deuxième tour de qualification de la Ligue des
champions et trois dans celui de la Ligue Conférence, et ainsi de suite, la place du vainqueur de
la coupe en Ligue Europa comprise. Un monde n'a jamais les 55 pays de l'UEFA, donc les places des
rangs absents vont tour à tour aux clubs suivants des ligues les plus fortes, un tour à la fois,
et chaque compétition reste pleine : avec douze ligues, les 6e, 7e et 8e d'Angleterre vont aux
qualifications de la Ligue des champions, par exemple. Après la 31e ligue il ne reste aucune
place, et la liste le dit. Chaque tour de qualification compte seize clubs : avec les 31 rangs
dans un monde, les places des rangs les plus bas au-delà de ces seize n'obtiennent rien (les notes
disent lesquelles ; les rangs 26 et moins commencent en réalité au premier tour de qualification,
que Mod Studio n'a pas). Les places de qualification vont aux tours dans l'ordre de la clé, le
pays le plus fort au tour le plus proche de la phase de ligue. Ensuite vous pouvez encore changer
à la main les places de n'importe quelle ligue (*Europe* sur la ligue, *Places européennes des
ligues du jeu*) : Build prend les places, pas le classement.

**Places sud-américaines** (Ligues → Plus, 0.1.7) : pour chaque ligue sud-américaine,
les quatre du jeu et les vôtres, quelles positions vont en Copa Libertadores, dans ses
qualifications et en Copa Sudamericana. Les places en Libertadores des ligues du jeu sont celles du
jeu (Brésil 1er-4e et le vainqueur de la Copa do Brasil, qualifications 5e-6e, et ainsi de suite --
ce que montre aussi le Competition Info du jeu) ; la Copa Sudamericana est celle de Mod Studio,
donc la liste montre combien de clubs chaque ligue du jeu y envoie avec vos places dedans : d'abord
vos ligues, puis le Brésil, l'Argentine, le Chili et la Colombie, un club chacun à tour de rôle
jusqu'à 32. Un club déjà en Libertadores ou dans ses qualifications laisse sa place au suivant de
sa ligue. **Vérifier le plan** affiche la même liste dès que le monde a une place en Libertadores
ou en Sudamericana.

**Compétitions modernes de la CONMEBOL** (une case dans **Places sud-américaines**, 0.2.5 ;
vmardonesdev et nissindiaz, #146) : les qualifications de la Libertadores en trois phases (phase 1 :
6 clubs, phase 2 : 13 clubs et les trois vainqueurs de la phase 1, phase 3 : les huit vainqueurs de
la phase 2), une Copa Sudamericana avec un premier tour de 32 clubs et un barrage après les groupes,
et la Recopa Sudamericana en février. Activée, la fenêtre Ligue propose **Libertadores, phase 1**,
**phase 2** et **Copa Sudamericana, premier tour** (et plus le tour préliminaire), les ligues
sud-américaines du jeu n'ont que les places que vous leur donnez dans **Places européennes des
ligues du jeu**, et **Pays de la CONMEBOL sans championnat** donne des places aux clubs d'un pays
sans championnat dans votre monde. La fenêtre compte les places par rapport au plateau dont Build a
besoin (26 places en groupes de la Libertadores, 13 en phase 2, 6 en phase 1, 12 en groupes de la
Sudamericana, 32 à son premier tour). Désactivée, par défaut, un monde construit les compétitions
classiques exactement comme avant ; la désactiver ne retire que les places propres aux modernes,
après confirmation.

**Noms des compétitions** (Ligues → Plus, ou Mon monde → Coupes) : un nouveau nom et un logo pour les coupes, supercoupes et compétitions continentales du jeu -- la FA Cup, la Ligue des champions, la Libertadores ... -- et pour les coupes continentales que le monde construit (CAF Champions League, Coupe de la Confédération, AFC Champions League Two, Copa Sudamericana, CONCACAF Champions Cup, OFC Champions League, AFC Challenge League, Supercoupe de la CAF). Toutes les phases de la compétition prennent le nom. Vide : celui du jeu. Les ligues du jeu se renomment dans *Ligues* (choisissez une ligue du jeu).

**IDs des compétitions** (Ligues → Plus) : chaque compétition du monde qui est dans le jeu, ligues et coupes, avec son id. Le jeu a de la place pour 255 ; Mon monde montre combien sont utilisées.

**Ordre des championnats** (Ligues → Plus, 0.2.0) : l'ordre des pays dans le Select Team de la Master League et dans la liste des équipes Kick Off / Edit. *Par continent* est l'ordre du jeu (Europe, Amériques, Asie, puis Afrique, chacun de A à Z). *Tous les pays de A à Z* les met tous dans une seule suite alphabétique, et *Mon propre ordre* vous laisse les placer comme vous voulez (glisser, ou Monter / Descendre). Les championnats d'un pays restent ensemble, première division d'abord, et les compétitions de clubs, les groupes "Other" et Classic Teams viennent après les pays. L'Allemagne, les USA et le Japon sont dans les groupes "Other" du Select Team, ils ne bougent donc que dans Kick Off. Reconstruisez ensuite le monde.

**Saisons des championnats du jeu** (Ligues → Plus, 0.2.0, expérimental) : le Japon, la Chine, le Brésil, le Chili et l'Arabie saoudite jouent de février à décembre dans le jeu. Cochez-en un et ses championnats jouent d'août à mai comme l'Europe : la saison commence en août, les montées et descentes ont lieu en été, ses coupes passent aux dates d'août à mai et ses places continentales viennent du classement terminé en mai. Une division à vous sous l'un de ces championnats le suit. La Colombie et les USA jouent Apertura et Clausura et ne peuvent pas changer. Reconstruisez le monde et commencez une nouvelle carrière.

**Clubs européens de la première saison** (Ligues → Plus, 0.1.8) :
choisissez à la main les clubs de la phase de ligue de la Ligue des champions, de la Ligue Europa et
de la Ligue Europa Conférence pour la première saison d'une nouvelle carrière. Vos clubs entrent
d'abord et le jeu complète le reste ; à partir de la deuxième saison, les places européennes
décident.

**Clubs** (un onglet de Mon monde) : choisissez la ligue, puis **Modifier le club** (nom, nom court, écusson ; ou double-cliquez sur le club). Tout le reste est sous **Plus ▾** : **Joueurs**, **Club du jeu...**, **Club NewLife...**, **Nouveau club ici**, **Insérer un club**, **Retirer le club**, **Déplacer vers une autre ligue...**, **Coller des noms...**, **Charger des noms depuis un fichier...** et **Importer des écussons...**. Un nom vide devient
`<ligue> 01`, `<ligue> 02` ... ; un club sans écusson reçoit un écusson numéroté. Les maillots sont
empruntés aux clubs du jeu. Un tel maillot est sous licence, et le mode Edit refuse de le modifier
("You cannot edit this strip") : cochez **Maillots simples pour le mode Édition** dans l'onglet
Construction (Options du monde) et les nouveaux clubs n'en empruntent aucun ; chacun porte un
maillot simple que Edit > Teams > Strip modifie comme celui de n'importe quel club, Paste Image
compris.
Avec Kit Server installé, **Maillots aux couleurs des clubs** (onglet Construction, Options du
monde, activé sauf si vous le décochez, 0.2.1) crée pour chaque nouveau club des maillots
domicile, extérieur, troisième et gardien dans les couleurs de son maillot (celles de NewLife, ou
de l'écusson à défaut), avec l'écusson sur la poitrine et le short, pour des ligues entières d'un
coup quand le monde entre dans le jeu. Un écusson ajouté plus tard (Importer des écussons) passe
sur les maillots à l'activation suivante. Un club qui a son propre maillot Kit Server, ou
seulement l'écusson numéroté, n'en reçoit pas.
Une ligne de maillot à vous dans `map.txt` (celle que vous avez définie dans l'onglet *Maillots*,
vers un maillot qui est dans la bibliothèque) l'emporte toujours : Build ne fait pas de maillot
pour ce club, n'y met pas de maillot de paquet et laisse votre ligne activée (0.2.4 ; la 0.2.3 la
désactivait à chaque Build pour le maillot d'un paquet de ligues).
Les noms gardent leurs accents (FK Željezničar) ; le nom court de trois lettres n'en a pas, comme
dans le jeu, donc Č, Ž, Đ y deviennent C, Z, D. L'ordre alphabétique d'une ligue dans les
fichiers du jeu range Đakovo sous D et Šibenik sous S (0.2.4). Après le **Build**, la souris sur
le nom d'un club montre son id dans le jeu (**ID de l'équipe**).

**Visages du pack de visages pour les nouveaux joueurs** (onglet Construction, Options du monde,
activé par défaut) : chaque nouveau joueur sans visage à lui reçoit un visage du pack de visages
des regens qui va avec sa nationalité. Désactivé : les nouveaux joueurs gardent l'apparence que
le jeu leur donne, ou celle que vous avez définie dans le mode Edit du jeu. Cela prend effet au
Build suivant.

**Entraîneur** : dans **Modifier le club** d'un nouveau club, vous pouvez nommer son entraîneur. Vide : un nom inventé à partir des joueurs du pays du club (un club croate reçoit un nom comme `Tomislav Krovinović` ; le même à chaque Build), ou un nom numéroté (`FL M0001` ...) pour un pays dont le jeu a peu de joueurs. **Photo de l'entraîneur** en dessous lui donne un portrait (comme **Portrait de l'entraîneur...** dans l'onglet Joueurs) ; *Ligues* (une ligue du jeu) > **Modifier le club** l'a aussi pour les clubs du jeu.

**Couleurs des maillots** : **Couleurs du maillot domicile** et **Couleurs du maillot extérieur**
dans **Modifier le club** : le Build prête le maillot du jeu le plus proche, et **Maillots aux
couleurs des clubs** les utilise.

**Formation** : dans **Modifier le club** d'un nouveau club, vous pouvez lui donner sa propre formation ; *Comme la ligue* garde celle de la ligue. Le terrain sous la liste montre la place de chacun.

**Capitaine et tireurs de coups de pied arrêtés** (0.2.4) : Build donne à chaque club et chaque
sélection qui n'en a pas un capitaine (un joueur avec la compétence Captaincy, sinon le plus fort
et le plus expérimenté) et ses tireurs de penalties, de coups francs et de corners, parmi les
joueurs de champ du onze de départ. Un club du jeu qui a les siens les garde. Un monde construit
avant la 0.2.4 a le gardien comme capitaine partout : reconstruisez-le et commencez une nouvelle
carrière.

**Stade à domicile** (0.1.7) : dans **Modifier le club**, un stade de la bibliothèque de Stadium Server pour le club ; l'emplacement et le nom sont remplis depuis le dossier, changez le nom si vous voulez. Il est écrit dans le `map_teams.txt` de Stadium Server quand le monde entre dans le jeu (et quand le monde du jeu est reconstruit), donc l'id d'un nouveau club n'a jamais à être cherché. Une ligne à vous pour le même club est désactivée en attendant, et réactivée quand le club n'a plus de stade ici. *Ligues* (une ligue du jeu) > **Modifier le club** l'a aussi pour les clubs du jeu. Stadium Server doit être installé (l'onglet *Stades*), ou le module de stades propre à SPFL26 (`common\stadiums.lua` avec son dossier `content\stadiums`) : depuis 0.1.8, Mod Studio y écrit quand Stadium Server n'est pas installé. Un stade du jeu choisi comme stade à domicile est bien éclairé pendant le match (0.2.4 ; avant, il pouvait être complètement sombre) : reconstruisez un monde fait avant.

**Clubs que le jeu a déjà.** Une place d'une nouvelle ligue peut accueillir un des clubs du jeu au
lieu d'un nouveau : sélectionnez la place, puis **Plus → Club du jeu...**, et cherchez par nom,
nom court ou ID de l'équipe (**Seulement les clubs sans ligue** réduit la liste). La fenêtre
**Club du jeu** dit sous la liste où joue le club. Le club garde son nom, son écusson, ses
maillots, son entraîneur et ses joueurs, et ne joue que dans votre ligue. S'il joue quelque chose
dans le jeu (une ligue, une coupe, la Ligue Europa ...), vous choisissez qui y prend sa place :
**Sa place revient à un club du jeu qui ne joue rien :** (choisissez-en un dans la liste), ou
**Sa place revient à un nouveau club, nommé :** (tapez un nom). **Il garde ses places dans les compétitions continentales** (0.1.8, #84) le laisse disputer la Ligue des champions, la Libertadores ou l'AFC Champions League où il est : un club qui dans le jeu ne joue que le continent déménage simplement, et un club qui joue aussi une ligue du jeu ne cède que la ligue et les coupes au club que vous choisissez. À partir de la deuxième saison, les places de votre ligue décident qui y va. Un tournoi de pré-saison (les *Pre-season friendly Cups* de SPFL26) ne compte pas : le club continue d'y jouer, comme les clubs de Premier League (0.1.7). **Modifier le club** sur un club du jeu change son nom, son écusson, le portrait de l'entraîneur et le stade, comme dans *Ligues* pour une ligue du jeu (0.1.7). Ainsi aucune
compétition du jeu ne change son nombre de clubs ; les ligues du jeu ne gardent leurs dates
qu'avec le nombre pour lequel elles ont été faites. Les sélections nationales, les équipes
classiques et par défaut et les clubs de moins de 18 joueurs ne peuvent pas être choisis.
**Nouveau club ici** (dans **Plus**) rend la place à un nouveau club ; il est grisé sauf si le
club choisi est un club du jeu à cette place (0.2.4). Le club n'apparaît plus dans les groupes
*Other ... clubs* de la Master League.

**Club NewLife...** (0.1.8, #83, dans **Plus**) place des clubs de la NewLife Database, avec leurs effectifs, à la place sélectionnée et aux suivantes : cochez un ou plusieurs clubs (recherche par club ou par ligue), chacun prend sa place dans l'ordre. Une ligue faite à la main reçoit ainsi de vrais clubs. Il utilise le dossier NewLife ouvert en dernier ; la première fois, ouvrez-le sur la page *NewLife Database*.

**Insérer un club** et **Retirer le club** ajoutent une place avant le club sélectionné ou la
retirent (10 à 24 clubs) ; noms, écussons, entraîneurs et changements de joueurs suivent leurs
clubs. Vérifiez les places européennes de la ligue, puis refaites le **Build**. Tout changement
des clubs d'une ligue demande une **nouvelle carrière**.

**Déplacer vers une autre ligue...** (0.1.7) emmène le nouveau club sélectionné à la fin d'une autre nouvelle ligue, avec son nom, son nom court, son écusson, son entraîneur, sa formation, ses maillots, son id NewLife et ses changements de joueurs ; la ligue qu'il quitte garde un club de moins. Un club du jeu se déplace avec **Club du jeu** : retirez-le d'une ligue, mettez-le dans l'autre.

**Les ligues du jeu** (choisissez-en une dans *Ligues*) : un nouveau nom ou logo, puis **Garder les modifications de la ligue** (**Annuler les modifications de la ligue** revient en arrière) ; **Modifier le club** pour l'écusson, le nom, le portrait de l'entraîneur et le stade d'un club. La liste des clubs montre combien de joueurs chaque club aura : son effectif, moins les joueurs retirés ou recrutés par un autre club, plus ceux ajoutés et recrutés. Un tel changement est gardé tout de suite dans le fichier de votre monde, comme tout autre changement.

**Importer des écussons...** (0.1.8, *Clubs* → Plus ; pour les ligues du jeu, *Ligues* → Plus) : des écussons pour beaucoup de clubs d'un coup. Choisissez un dossier d'images ; chacune est associée à un club par le nom du fichier -- le nom du club (`Alianza Lima.png`, `alianza_lima_r_l.png`) ou son ID d'équipe (`2287.png`, le `e_2287_r.png` des packs d'écussons). Un nom ne correspond que sur des mots entiers, et une sélection nationale ne prend une image que par son ID d'équipe (0.2.4 ; avant, « termalica » pouvait aller au Mali). La liste montre chaque association cochée ; décochez une mauvaise avant **OK**. **Associer à** peut aussi être une ligue de votre monde : seuls ses clubs sont associés, et un dossier qui porte le nom d'une ligue de votre monde (`Torneo DIMAYOR II`) la choisit tout seul, donc un club du même nom dans une autre ligue n'a rien. Un club qui a déjà un écusson le garde, sauf si **Remplacer les écussons déjà définis** est coché. Les images restent dans ce dossier et Build les lit là, gardez-le donc. (L'association par nom est une idée du script d'écussons de Xxspedd.)

**Échanger de ligue avec un club...** (0.1.7, *Ligues*, une ligue du jeu → Plus) : deux clubs des ligues du jeu échangent leurs places -- un promu contre un relégué, un club de la ligue d'un pays contre un club d'un autre. Chacun prend les places de l'autre dans la ligue, les coupes et les compétitions européennes, donc chaque ligue du jeu garde son nombre de clubs. Un club qui joue dans une nouvelle ligue de votre monde ne peut pas aussi être échangé. **Annuler les changements du club** retire l'échange. Puis refaites le **Build** et commencez une nouvelle carrière.

> **Fichier Edit.** Si le dossier de sauvegarde du jeu contient un fichier Edit (`EDIT00000000`),
> il remplace les noms des clubs. Déplacez-le ailleurs pour voir vos noms.

### Joueurs

**Joueurs** (un onglet de Mon monde) modifie l'effectif de n'importe quel club : les nouveaux
clubs de votre monde et ceux du jeu. Choisissez un club (ou **Plus → Joueurs** dans Clubs), puis
un joueur :

- **Nom**, **numéro de maillot**, **poste** et les postes où il peut jouer (A = naturel,
  B = peut y jouer), pied fort, taille, poids, âge, nationalité, style de jeu ;
- toutes les **capacités** et **compétences** (les noms sont ceux du jeu) ;
- **Note** : la note que montre le jeu, calculée comme dans le jeu à partir des capacités, avec
  des poids propres à chaque poste (un ou deux points d'écart au plus). La changer déplace chaque
  capacité du joueur d'autant, et les quelques-unes qui comptent le plus pour son poste d'un de
  plus, pour tomber sur le nombre tapé. Un joueur d'un nouveau club n'a pas de
  nom tant que le Build ne le numérote pas (FL P00001 ...) ; tapez-en un dans **Nom** pour lui
  donner le vôtre ; depuis 0.2.0 cet effectif part du niveau de sa division (environ 72 en
  première division, jusqu'à 57 à partir de la cinquième) ;
- **Visage** : **Choisir...** un dossier de visage (section 8.1). **Effacer** redonne le visage du
  jeu. Un nouveau joueur sans visage reçoit un visage du pack de visages des regens qui va avec sa
  nationalité, avec son portrait (0.1.5.5, modules installés et `fl26regen` actif, section 5).
  Un visage fait pour un autre joueur apporte aussi l'apparence de son corps : les bras et les
  jambes ont la couleur de peau de ce visage (0.1.9) ;
- **Portrait** : **Choisir...** une image (PNG ou JPG) pour le petit portrait du joueur dans les
  listes de l'effectif, sans visage à lui. Le Build la met en 180 x 180 ; elle passe avant le
  portrait d'un dossier de visage ;
- **Monter dans l'ordre / Descendre dans l'ordre** : l'ordre de l'effectif. Les onze premiers
  commencent le match ;
- **Ajouter un joueur** (une copie du joueur choisi, avec un nouvel id ; clubs du jeu seulement),
  **Retirer du club** (appuyez de nouveau pour annuler). Un nouveau club garde au moins 18
  joueurs, ceux recrutés pour lui compris ; les clubs du jeu n'ont pas de minimum ;
- **Meilleur onze** place le joueur le plus fort à chaque poste (un joueur qui peut y jouer
  mais est enregistré à un autre poste compte 6 de moins, et reste pour son poste quand
  celui-ci resterait vide) ; **Niveau de l'effectif...** (dans **Plus**)
  monte ou baisse chaque capacité de tout l'effectif ;
- **Terrain** (nouveaux clubs) : le onze de départ dans la formation du club. Glissez un joueur de
  la liste sur un poste, ou glissez un poste sur un autre pour échanger les deux ; un clic sur un
  poste sélectionne le joueur qui s'y trouve. La formation que Build a choisie pour le club
  s'affiche ici ; quand vous changez son ordre, le club garde cette formation ;
- **Exporter en CSV... / Importer un CSV...** (dans **Plus**) : modifiez un effectif dans un
  tableur. Exportez d'abord, changez les cellules, puis réimportez les mêmes colonnes.
- **Importer un effectif depuis un tableau...** (dans **Plus**) : n'importe quel tableau de
  joueurs devient l'effectif du club -- tapé à la main, une liste copiée d'un site, ou l'export
  d'un autre jeu de football. Les colonnes sont reconnues par leur nom (nom, poste, âge ou date de
  naissance, nationalité, taille, pied, numéro, note générale et toutes les notes) et affichées
  pour corriger celle qui est fausse. Ce que le tableau n'a pas vient des joueurs du jeu de même
  poste et même note ; les notes sur une échelle de 1 à 20 sont étirées au 40-99 du jeu. Les
  joueurs du tableau prennent les places du club dans l'ordre de l'effectif : un nouveau club
  garde ses 30 places (moins de joueurs = les autres partent, jusqu'à 18), un club du jeu gagne
  ou perd des joueurs pour correspondre.

Chaque modification est écrite dans le monde lors du **Build** ; les fichiers du jeu restent tels
quels. **Annuler les modifications de ce joueur** et **Annuler toutes les modifications de ce
club** reviennent à ce qu'il y a dans le jeu.

La liste des clubs a aussi **Équipes nationales** et **Autres clubs (sans ligue)** : les équipes que le jeu garde hors de toute ligue (sélections, clubs qui ne jouent qu'une coupe ou une compétition continentale). Leurs joueurs se modifient de la même façon.

#### Transferts, sélections, ID, le portrait de l'entraîneur

- **Recruter des joueurs...** (un club) : une liste de tous les joueurs du jeu et de vos nouveaux
  clubs, avec un filtre de nationalité et une recherche par nom ; choisissez-en plusieurs avec
  Ctrl ou Maj. Ils passent dans ce club et leur ancien club les perd (un transfert). **Transférer
  vers...** fait la même chose dans l'autre sens : le joueur sélectionné part dans le club que
  vous choisissez. La liste affiche *de : ...* sur le club qui le reçoit et *vers : ...* sur le
  club qu'il quitte ; **Retirer du club** sur l'une ou l'autre ligne annule le transfert. Un club
  a au plus 40 joueurs. Si un club dépasse 40 joueurs (une sélection plus de 26), Build garde ses
  40 premiers et continue, et le journal du Build nomme le club et les joueurs laissés de côté ;
  quand le club est deux fois dans votre monde, il nomme les deux ligues.
- **Convoquer des joueurs...** (une sélection : choisissez *Équipes nationales* dans la liste des
  ligues) : la liste s'ouvre sur le pays de la sélection. Les joueurs rejoignent la sélection
  **et restent dans leurs clubs**, comme dans le jeu. **Retirer du club** retire le joueur de la
  sélection (pas de son club). Une sélection a au plus 26 joueurs ; un joueur est dans une seule
  sélection à la fois. Votre liste est écrite dans les données du jeu, mais dans une carrière
  Master League le jeu choisit lui-même ses sélections, donc vos convocations n'y restent pas.
- Un joueur qui arrive va à la fin de l'ordre de l'effectif avec un numéro libre ; l'effectif
  qu'il quitte resserre son ordre.
- Colonne **ID du joueur** : l'id de chaque joueur -- celui du jeu, celui que vous avez tapé, ou
  celui que le dernier **Build** a donné à un nouveau joueur (faites un Build avant de créer des
  minifaces ou des visages pour les nouveaux joueurs). **Exporter en CSV...** l'écrit comme
  `player_id` ; Importer un CSV ignore cette colonne.
- **ID du club** (à côté du club) et **ID du joueur** (onglet Bases) : seulement pour vos
  **nouveaux** clubs et joueurs. Vide = le prochain ID libre au Build. Tapez-en un quand un pack de
  maillots, d'écussons ou de visages a été fait pour un ID précis. ID de club : du premier après
  les clubs du jeu (71578) jusqu'à 81919 ; ID de joueur : au-dessus du plus haut du jeu jusqu'à
  399999 ; jamais un que le jeu ou un autre nouveau club ou joueur a déjà. L'ID sert partout où le
  monde parle du club ou du joueur (effectifs, compétitions, maillots, écussons, entraîneur,
  visages). Les clubs et joueurs du jeu gardent leurs ID : leurs maillots, visages et vos
  sauvegardes en dépendent.
- **Les joueurs gardent leur ID quand vous reconstruisez** (0.2.4). Build retrouve chaque joueur
  propre au monde par qui il est (son id NewLife, sinon son nom et sa date de naissance) avant sa
  place dans l'effectif, donc un joueur qui est monté dans l'effectif ou a changé de club garde
  son ID, et une ancienne carrière ne le montre pas comme quelqu'un d'autre.
- **Portrait de l'entraîneur...** : un PNG ou JPG pour l'entraîneur du club. Le Build le met en
  256 x 256 dans `common/render/symbol/coach/coach_<ID de l'entraîneur>.png`, là où le jeu range
  les portraits d'entraîneurs. Appuyez de nouveau pour enlever l'image.

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

Choisissez ce dossier pour un joueur. Au **Build**, le visage est copié dans le monde et
attribué au joueur : il fonctionne donc pour un nouveau joueur dont l'id n'existait pas quand le
visage a été créé, et il ne remplace jamais un visage du jeu. Sans portrait, la petite image du
joueur dans les menus reste une silhouette vide ; le visage lui-même s'affiche quand même. Un
dossier contenant plus d'un visage est refusé : choisissez le visage que vous voulez.

### 8.2 Construire, activer, jouer

**Gardez le Team.bin du monde.** Il est dans le dossier du monde et contient les clubs et les barrages du monde. Le remplacer par le Team.bin du jeu les fait disparaître, et les compositions ont l'air réparées seulement parce que les clubs n'y sont plus (GitHub #75). Reconstruisez plutôt le monde.

**Construction** est le premier onglet de **2. Mon monde**. Une note en haut dit qu'il est pour
les moddeurs : pour jouer un modpack prêt, vous n'en avez pas besoin. En dessous : le fichier où
votre monde est gardé, les boutons **Nouveau monde**, **Ouvrir un monde...** et **Ajouter des
championnats** (pour un monde à vous), et le grand bouton **Construire et installer**.

**Construire et installer** fait 0, 2 et 3 ci-dessous en un clic, puis montre ce qu'il reste à
faire : une fenêtre **Build terminé** avec une coche pour **Monde construit**, **Ligues et clubs**,
**Modules installés et activés** et **Dans le jeu**, et sous **Avant de jouer** un rappel de
commencer une nouvelle Master League. Elle peut aussi **Mettre la sauvegarde Edit de côté** (une
sauvegarde Edit d'avant le Build cache les nouveaux noms et effectifs) et **Fermer le jeu**. La
carte d'Accueil a un bouton **Aller à Construction** qui vous amène ici. Pendant que le monde se
construit, la ligne d'état de Mon monde et la barre du bas montrent le temps écoulé et l'étape en
cours (`Building... 3:12 · squads: filling them`), et la fenêtre reste utilisable. Ou étape par
étape, sous **Étape par étape, et Exporter le monde** dans l'onglet **Construction** :

0. **Installer les modules** — une fois, puis à nouveau après une nouvelle version du programme.
   Les fichiers qu'il remplace sont gardés dans **Points de restauration**.
1. **Vérifier le plan** — ce qui sera créé ; rien n'est écrit.
2. **Construire le monde**.
3. **L'activer** — le met dans le jeu (le monde actif dans `sider.ini`).
4. Lancez le jeu, revenez et appuyez sur **Après un lancement : vérifier**. Le programme lit
   `sider.log` et dit, module par module, si le monde a été pris en compte.

**Activer** sur la carte d'un autre monde dans Mon monde fait l'étape 3 pour ce monde (et change
le dossier de sauvegarde, section 3.1). Le monde qui est dans le jeu affiche **● Actif** à la
place. Commencez une nouvelle Master League après avoir activé un autre monde.

**Un nouveau logo ou écusson se construit en quelques secondes** (0.2.4). Quand seules des images
ont changé depuis le dernier Build (le logo d'une ligue ou d'une coupe, l'écusson d'un club, le
drapeau d'un pays), Build ne redessine que celles-là et laisse le reste du monde tel quel. Tout
autre changement (un nom, un club, un joueur) est un Build complet. Un monde depuis un zip est
construit en entier une fois sur votre PC ; ensuite, ses changements d'images sont rapides aussi.

**Un monde prêt ne se construit pas ici** (0.2.4). Un monde installé depuis un zip est déjà
construit, et Build le remplacerait par le monde ouvert dans Mod Studio. Donc tant qu'un monde
prêt est dans le jeu, les étapes du Build sont grisées avec une note, Accueil dit **Prêt à
jouer**, et Construction explique quoi faire à la place : appuyez sur **Lancer le jeu**, ou
mettez d'abord votre propre monde dans le jeu (**Activer** sur sa carte). Un autre monde
(NewLife, un nouveau monde) peut quand même être construit pendant que le monde prêt est activé :
Build demande d'abord et dit qu'il désactive le monde prêt ; **Activer** sur sa carte le remet,
avec ses carrières. Pour changer le monde prêt lui-même : **Le rendre modifiable...**
(section 3.1).

**Inclure la Ligue Europa Conférence** (onglet Construction, sous Options du monde, activé par
défaut) construit aussi la Ligue Europa Conférence : une phase de ligue à 36 clubs et un barrage
en février, comme les deux autres. La Ligue des champions et la Ligue Europa reçoivent leur phase
de ligue à 36 et leur barrage de février dans tous les cas. Désactivé : pas de Ligue Europa
Conférence. (Mod Studio 0.1.3 et les versions précédentes laissaient la Ligue des champions et la
Ligue Europa dans les groupes de quatre du jeu quand c'était désactivé, ce que le mod ne sait pas
gérer -- elles cassaient ; les vérifications signalent un tel monde : reconstruisez-le.) **Logo de
la Ligue Europa Conférence** à côté : votre propre image pour elle ; vide : un emblème UECL est
dessiné (le jeu n'en a pas). **Nom de la Ligue Conférence** en dessous : le nom que le jeu lui
donne, *FL Conference League* si vide (tapez *UEFA Conference League* si vous voulez) ; un nouveau
nom demande de reconstruire le monde. **Construire seulement les coupes d'Europe...** utilise les
deux aussi.

> **Places européennes.** Les places que vous donnez à vos ligues viennent après celles des ligues
> du jeu. Chaque compétition prend 36 clubs ; les places au-delà de la 36e ne donnent rien, et
> **Vérifier le plan** le signale. Les nouvelles ligues sans places n'envoient personne en
> Europe, et Accueil vous en avertit. Les tenants du titre passent en premier : les
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
> rencontrent pas. Les vainqueurs passent au tour suivant, et du barrage à la phase de ligue.
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
Edit, un nouveau pays d'Asie vient avant *Other Clubs (Asia)*, un pays d'Amérique du Sud avec
ceux du jeu (après la Colombie, avant la MLS, 0.1.7), un pays de la CONCACAF après la MLS, et les
pays d'Afrique et d'Océanie (le jeu n'a pas de section pour eux) après l'Asie.

> **Coupes des autres continents.** Quand vos ligues envoient des clubs en Ligue des champions
> CAF, en Coupe de la Confédération CAF, en AFC Champions League Two, en AFC Challenge League,
> en Copa Sudamericana, en CONCACAF Champions Cup ou en OFC Champions League (ces trois
> dernières nouvelles en 0.2.0), le **Build** crée aussi ces coupes. Chacune a 32, 16, 8
> ou 4 clubs : d'abord les places de vos ligues, puis les ligues du jeu de ce continent (Asie,
> Amérique du Sud, et la MLS pour celle de la CONCACAF) la complètent ; pour l'AFC Challenge
> League, ce sont les 11e-14e de la J1 League, les 10e-13e de la Super League chinoise et les
> 11e-14e de la Saudi Pro League. À 8 ou plus, des groupes de quatre puis une phase à
> élimination directe ; en dessous de 8, l'élimination directe seule. La CONCACAF Champions Cup
> se joue toujours à élimination directe, à 16 clubs au plus, comme la vraie, et deux clubs
> d'une même ligue ne se rencontrent pas à son premier tour quand c'est évitable. Elles sont
> remplies fin août, avec les classements des ligues. Un club qui joue déjà la Copa
> Libertadores, ses qualifications ou l'AFC Champions League n'entre pas dans leur tirage. Une
> coupe CAF ou OFC avec moins de 4 places prend d'abord les places de la coupe CAF suivante (avec
> deux et deux, la Ligue des champions CAF a les quatre), puis les positions suivantes de vos
> ligues. **Supercoupe de la CAF** (onglet Construction, Options du monde, cochée par défaut)
> fait se rencontrer les vainqueurs des deux coupes CAF en un match fin juillet, à partir de la
> deuxième saison de la carrière.
>
> Une ligue qui peut envoyer un club en Copa Libertadores, en AFC Champions League ou en Coupe du
> monde des clubs évite leurs jours de match (0.2.4) : pas de journée de ligue la veille ni le
> lendemain.

> **Tirage de la coupe nationale** (onglet Construction, Options du monde) décide comment les
> coupes nationales de vos ligues sont tirées. *Têtes de série* (par défaut) : les clubs de
> première division sont exemptés des premiers tours et entrent plus tard, sont répartis de façon
> égale dans les deux moitiés du tableau, et affrontent les clubs des ligues inférieures plutôt
> qu'entre eux dans les premiers tours. *Aléatoire* : un tirage à l'aveugle. *Désactivé* : le jeu
> remplit le tableau dans l'ordre de la liste, ce qui met tous les grands clubs du même côté. Dans
> le fichier du monde, c'est la ligne `cupdraw seeded|random|off` ; `cupdraw <règlement de la
> coupe> seeded|random|off` règle une seule coupe.

> **Les sauvegardes appartiennent à un monde.** Une carrière sauvegardée avec un monde dans le jeu
> a besoin de ce même monde pour se charger. Avec **Chaque monde garde ses propres carrières**
> activé (par défaut, section 3.1), Mod Studio garde les carrières de chaque monde à part pour
> vous.

**Votre monde s'enregistre tout seul** un instant après chaque changement (la barre du bas dit
**Votre monde est enregistré**) : dans son propre fichier `.json` s'il en a un, sinon dans
`%APPDATA%\FL26ModStudio\recipes\<monde>.json`, et Mod Studio le rouvre au démarrage.
**Fichier → Enregistrer votre monde sous...** en enregistre une copie sous un autre nom,
**Fichier → Ouvrir un monde...** en rouvre un et **Fichier → Nouveau monde** en commence un vide.

**Construire seulement les coupes d'Europe...** (onglet Construction, Options du monde ;
**Seulement les coupes d'Europe...** sur Accueil) construit un monde avec seulement la nouvelle
Ligue des champions et la Ligue Europa -- phase de ligue à 36 et barrages de février -- et la
Ligue Europa Conférence quand **Inclure la Ligue Europa Conférence** est coché. Pas de nouvelles
ligues ; les clubs et ligues du jeu restent tels quels et votre monde ne change pas. Il demande un
nom de monde (`_FL26Euro` par défaut), le construit et propose de l'activer. Un seul monde peut
être dans le jeu, il remplace donc un monde avec de nouvelles ligues : un monde avec de nouvelles
ligues a déjà le nouveau format.

> **Ligues d'exhibition et Master League.** Une ligue cochée *Exhibition uniquement* ne joue jamais
> de saison de Master League, mais le jeu a une seule liste d'équipes pour Kick Off et la Master
> League, donc ses clubs apparaissent toujours quand vous choisissez votre club pour une nouvelle
> carrière. Ne commencez pas de carrière avec l'un d'eux. **Vérifier le plan** et le **Build** le
> signalent.

### 8.3 Limites

| | |
|---|---|
| Nouvelles ligues par monde | Pas de nombre fixe. Chaque ligue, coupe et supercoupe du monde prend une des 255 compétitions du jeu (le jeu en utilise lui-même environ 90) ; **2. Mon monde** montre combien sont utilisées. Notre monde de test joue 86 nouvelles ligues. |
| Nouveaux pays | 99 |
| Clubs par ligue | 10 – 24 |
| Nouveaux clubs au total | environ 1 500 (la ligne en bas de la page NewLife Database dit combien en tiennent dans votre jeu) |
| Nombre de rencontres entre clubs | 1 – 4 |
| Ligues qui se divisent | 2 par monde |
| Divisions dans un pays | jusqu'à la 7e |
| Joueurs par nouveau club | 30 au départ (un très grand monde reçoit des effectifs plus petits, jamais sous 22) ; retirez-en jusqu'à 18 ; avec des recrues, jusqu'à 40 |
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
2. **2. Mon monde → NewLife Database** (le bouton à droite des onglets), puis **Ouvrir la NewLife
   Database...** et choisissez ce dossier. (Ou déposez le dossier sur **+ Ajouter...**.) La liste
   montre toutes les ligues de ces parties : pays, clubs, clubs que le jeu a déjà (*Dans le jeu*),
   joueurs et niveau. Cliquez sur une ligue pour voir ses clubs. Un clic sur l'en-tête d'une
   colonne (Ligue, Pays, Clubs, Joueurs, Niveau) trie selon elle, un second clic inverse l'ordre
   (0.2.0) ; la liste s'ouvre triée par pays.
3. Sélectionnez une ou plusieurs ligues (Ctrl ou Maj pour plusieurs) et appuyez sur **Ajouter à
   votre monde**. Chacune devient une nouvelle ligue avec ses clubs et leurs effectifs, première
   division de son pays. Changez sa division, son format, ses places européennes et le reste dans
   *Ligues*, comme pour toute autre ligue.
4. **Construire et installer**, puis commencez une nouvelle carrière (section 8.2).

- **Votre propre composition** (0.1.7) : décochez un club dans la liste de droite pour le
  laisser de côté, et **Ajouter un club d'une autre ligue...** amène des clubs de n'importe
  quelle ligue de la base -- la première division de cette saison est celle de l'an dernier avec
  deux promus, par exemple. La ligne de la ligue porte un `*`. Un club ne peut être que dans une
  ligue de votre monde. S'il est déjà dans une de vos ligues sous un autre nom, le message nomme
  cette ligue et le nom que le club y a.
- Une ligue prend de 10 à 24 clubs, ses nouveaux clubs et ceux du jeu ensemble ; les autres sont en gris. Une ligue que le jeu a déjà (la Premier League, le Championship ...) est grisée aussi (0.1.9) : elle est déjà dans le jeu, amenez-la à la saison NewLife avec **Plus → Amener les ligues du jeu à cette saison...** plus bas. La ligne du bas compte les nouveaux
  clubs de votre monde par rapport au nombre que le jeu accepte.
- Les clubs que le jeu a déjà entrent dans la nouvelle ligue comme clubs du jeu (section 8,
  *Clubs que le jeu a déjà*), à ses dernières places, avec leur nom, écusson, maillots et joueurs.
  Celui qui joue aussi une compétition du jeu (Bâle et Young Boys jouent la Ligue Europa) a besoin
  du club qui prend sa place là-bas : *Clubs*, choisissez-le, **Plus → Club du jeu...**.
  Jusque-là, Build dit lesquels. Un club dont la seule compétition du jeu est continentale
  (Ludogorets en qualifications de la Ligue des champions) continue de la jouer seul (0.1.9).
- Un joueur que le jeu a déjà (le même joueur sous le même nom, par exemple Urbański au Górnik
  dans le jeu et au Legia dans NewLife) passe au club NewLife au lieu d'être créé une deuxième fois
  (0.1.7) : il garde son visage, son nom et son ID et prend le poste et les notes de NewLife. Il
  reste où il est si son ancien club passait sous 18 joueurs ou si une ligue précédente l'a déjà ;
  il est alors laissé hors du club NewLife, sans copie (0.1.8).
- Un club NewLife reçoit un ID de monde à lui (0.1.8), dans le bloc que le jeu lit pour les
  clubs, après les ID que le constructeur donne aux siens. La souris sur son nom dans *Clubs* le
  montre (**ID de l'équipe**), et le `map.txt` du Kit Server est bâti dessus. Un monde fait avant
  0.1.8 doit être reconstruit et la carrière recommencée pour que les maillots suivent. Depuis
  0.1.8, un club garde l'ID de son premier Build (votre monde s'en souvient) : retirer, ajouter ou
  mettre à jour une autre ligue ne le déplace plus.
- **Une version plus récente de NewLife** (0.1.8) : mettez ses parties dans un dossier (sans
  les mélanger avec les anciennes), **Ouvrir la NewLife Database...** sur ce dossier et appuyez sur
  **Plus → Mettre mes ligues à jour vers cette version**. Chaque ligue ajoutée depuis une version plus
  ancienne est listée avec ce qui change (*16 clubs maintenant, 18 dans NewLife 1.3 (5 nouveaux,
  3 absents)*) et une case **Garder mes clubs** : cochée, la ligue garde ses clubs ; décochée,
  elle reçoit les clubs qu'elle a dans la nouvelle version. Dans les deux cas, les effectifs
  viennent de la nouvelle version, et la ligue garde son nom, sa division, son format, ses places
  européennes et ses coupes ; un club qui reste garde son entraîneur et l'écusson que vous avez
  choisi, et vos propres clubs mis dans la ligue restent. Les capacités, postes et le reste des
  effectifs viennent de la nouvelle version ; un visage que vous avez lié ou un portrait que vous
  avez choisi dans *Joueurs* reste avec un joueur qui est toujours au club (0.2.0, #111). Un club
  du jeu dont la place est allée à un autre club reste un nouveau club dans votre ligue (0.2.4).
  Ensuite Build et nouvelle carrière.
- **Les ligues du jeu dans la saison NewLife** (0.1.8) : avec une NewLife Database ouverte,
  appuyez sur **Plus → Amener les ligues du jeu à cette saison...**. Chaque ligue du jeu que la
  version contient est listée avec ce qui lui arrive, chacune avec une case. Un club promu ou
  relégué entre deux ligues du jeu échange sa place avec un club qui va dans l'autre sens
  (Burnley en Championship, Coventry en Premier League), comme *Échanger de ligue avec un
  club...*. Un club relégué hors des ligues du jeu (Leicester en League One) devient le club
  promu à sa place (Bolton) : nom, nom court, écusson et effectif ; son maillot, son stade et son
  entraîneur restent. Quand la base n'a pas d'écusson pour ce club, la place reçoit le blason du
  maillot du nouveau club (0.2.4). Chaque club des ligues cochées reçoit son effectif NewLife :
  les joueurs que le jeu a arrivent de leur ancien club, ceux qu'il n'a pas sont ajoutés, et les
  joueurs que NewLife a dans un autre club partent. Un joueur que NewLife a toujours dans ce club
  reste, tant que le club a de la place (40 au plus ; 0.2.4) ; le journal du Build nomme ceux
  pour qui il n'y avait pas de place. Les notes sont mises à l'échelle du jeu, mesurée sur les
  joueurs que les deux ont, donc une star arrive là où le jeu la note (0.2.0 ; avant, le haut de
  l'échelle était 2 à 4 points plus haut). Les ligues gardent leur nombre de clubs, leur format et
  leurs coupes. Les clubs que vous avez déjà changés à la main (un échange, un nom, un club d'une
  nouvelle ligue, des changements de joueurs) restent tels quels. Le refaire avec une version
  plus récente remplace ce qu'a fait l'ancienne ; **Plus → Annuler les ligues du jeu** retire
  tout. Build et nouvelle carrière.
- Un club NewLife reçoit un écusson en forme de blason à ses couleurs et le maillot du jeu aux
  couleurs les plus proches, jusqu'à ce que vous lui donniez les vôtres (**Modifier le club**).

## 9. Paquets de ligues : partager une ligue entière

Un moddeur crée une ligue une fois — clubs, noms, écussons, logos, effectifs, visages — et
partage **un seul fichier `.fl26pack`**. N'importe qui l'ajoute à son propre monde et construit.

La page **Paquets de ligues** est sous **2. Mon monde → Plus ▾ → Paquets de ligues**. Elle liste
les paquets de votre monde, avec **Ajouter un paquet...**, **Créer un paquet...** et **Retirer de
votre monde**.

**Créer un paquet** (**Créer un paquet...** sur cette page, ou **Fichier → Créer un paquet de
ligues...**) :

1. Nom, auteur, version et une courte description.
2. Cochez les ligues à inclure (**Tout cocher** / **Tout décocher** au-dessus de la liste). Une
   ligue placée sous une autre nouvelle ligue doit l'accompagner.
3. Si vous le voulez, **aussi mes modifications des ligues, clubs et joueurs du jeu**.
4. **Ce qui va dedans** (0.1.8) : tout est coché ; décochez ce que vous ne voulez pas partager --
   **Effectifs**, **Visages et portraits des joueurs**, **Blasons et logos des ligues**,
   **Entraîneurs**, **Couleurs des maillots**, **Stades à domicile** (la ligne de Stadium Server,
   pas le stade lui-même), et (0.2.1) **Maillots** (ceux de Kit Server des clubs) et **Tableaux de
   score** (celui de Scoreboard Server de chaque ligue). Les maillots et tableaux de score sont
   pris dans votre jeu tel qu'est le monde maintenant : ce que kit-server\map.txt et
   scoreboard-server\map_competitions.txt donnent à ses clubs et ligues. Un paquet sans effectifs
   va sur une base d'effectifs mise à jour à part, comme NewLife, sans remettre les anciens
   effectifs.
5. **Enregistrer le paquet...**. Le fichier (`.fl26pack`) contient les images, les visages, les
   maillots et les tableaux de score, pas des chemins de votre ordinateur.
   Qui l'ajoute reçoit les maillots et tableaux de score en place, avec ses propres ids d'équipes
   et de ligues, au Build (Kit Server / Scoreboard Server doivent être installés) ; un club auquel
   il a donné sa propre ligne de maillot dans l'onglet *Maillots* garde ce maillot (0.2.4), et un
   maillot de paquet reste avec son club quand un club est retiré, inséré ou déplacé, ou que la
   ligue est mise à jour vers un NewLife plus récent. Les maillots ajoutent environ 10 Mo par
   ligue et un tableau de score environ 7 Mo, donc un tel paquet dépasse souvent la limite de
   10 Mo de Discord : partagez-le par un service cloud (Google Drive, Dropbox, MEGA ...) ; le
   programme le signale quand le fichier est plus gros.

**Ajouter un paquet** (**Ajouter un paquet...** sur cette page, **Ajouter un paquet de ligues**
dans **Actions rapides** sur Accueil, **Fichier → Ajouter un paquet de ligues...**,
**+ Ajouter...** dans Mon monde, ou déposez-le sur **Importer votre monde**, où **Construire et
installer** démarre alors tout seul) :

1. Le programme montre ce qu'il contient et vous demande. Un paquet de plusieurs ligues les liste,
   toutes cochées : décochez celles que vous ne voulez pas (0.2.1). Une ligue placée sous une autre
   ligue du paquet amène celle-ci avec elle. Sous **Que prendre**, vous pouvez aussi décocher des
   parties du paquet (tableaux de score, maillots, écussons, visages ...), par exemple pour prendre
   les tableaux de score d'un autre paquet.
2. Une ligue dont vous avez déjà le nom : le programme demande, et l'ajoute sous la forme `Nom (Paquet)` (si vous refusez, rien n'est ajouté).
   Un paquet fait sans effectifs va sur cette ligue : ses écussons et entraîneurs vont aux clubs du
   même nom, vos joueurs restent et le programme dit combien de clubs il a trouvés.
   Un paquet que votre monde a déjà (le même nom) est remplacé par la nouvelle version (0.1.7) :
   les ligues, clubs et changements de joueurs de l'ancien sortent, ceux du nouveau entrent.
3. **Construire et installer**.

Les id sont attribués quand chaque personne construit, d'après ce que son propre jeu contient :
un paquet fonctionne donc à côté d'autres paquets et de vos propres ligues. **Retirer de votre
monde** retire à nouveau un paquet, y compris les modifications qu'il a faites aux clubs du jeu.
Si un paquet change un club que votre monde change déjà (un club NewLife, par exemple), un joueur
que les deux ajoutent n'est ajouté qu'une fois, et les recrues et départs du paquet suivent
(0.2.4).

Une ligue placée sous une ligue du jeu fonctionne pour tous ceux qui ont la même version du jeu.

### 9.1 Exporter le monde : un monde construit pour un autre PC

Un paquet demande à l'autre personne de construire. Pour donner le monde exactement tel que vous
l'avez construit, appuyez sur **Exporter...** sur la carte du monde dans **2. Mon monde**, ou sur
**Exporter le monde...** sous **Étape par étape, et Exporter le monde** dans l'onglet
Construction (une fois le monde construit). Il enregistre un seul `.zip` :

- `SiderAddons\livecpk\<monde>\...` : tout le dossier du monde, avec son **fichier de monde**
  `fl26world.txt`. Les lignes `newfaces` / `faceapp` de ce fichier listent les nouveaux joueurs
  qui reçoivent un visage généré. Sans elles, tous les nouveaux joueurs se ressemblent.
- `SiderAddons\content\kit-server\<monde>\...` et `...\scoreboard-server\<monde>\...` : les
  **maillots** du monde (les maillots Kit Server de ses clubs, y compris ceux faits à partir des
  couleurs et des écussons) et ses **tableaux de score**, chacun avec un `map.txt` /
  `map_competitions.txt` contenant seulement les lignes de ce monde. Importer votre monde ajoute
  ces lignes aux map de celui qui reçoit (une ligne à lui pour le même club est désactivée et
  revient quand le mod est retiré). Les maillots vont dans le Kit Server que charge le jeu de
  celui qui reçoit (`content\kits` pour celui propre à SPFL26). Un club du monde qui porte un
  maillot d'un autre pack sur votre PC (Other Europe de SPFL26, un modpack) emporte une copie de
  ce maillot, dans `<monde>\_kits\`, donc celui qui reçoit n'a pas besoin de ce pack.
- `SiderAddons\content\scoreboard-server\<monde>\_packs\...` : les **tableaux de score d'autres
  packs** que les lignes des map activées sur votre PC donnent aux compétitions du monde (les
  tableaux d'un modpack pour ses ligues, coupes et supercoupes). Ils viennent avec leurs lignes
  des map, dirigées vers `<monde>\_packs\`, donc celui qui reçoit n'a pas besoin de ce pack non
  plus. Les thèmes de menus ne font pas partie d'un zip de monde : les menus du jeu restent, même
  quand le thème d'un pack est activé sur votre PC.
- `READ ME - FL26 world.txt` et `fl26worldpack.json` : ce dont celui qui reçoit a besoin.

**Celui qui reçoit a besoin des modules de Mod Studio avec le pack de visages**
(`modules\fl26regen_faces.bin`) : installer le zip dans **Importer votre monde** les met en place
(ou **Accueil → Installer maintenant**). Les visages viennent de ce pack, donc le zip ne les
contient pas.

Pour l'installer, déposez le zip sur **Importer votre monde** et appuyez sur **Installer le
monde**. Mod Studio installe ses modules, copie le monde, met `fl26world.txt` dans
`SiderAddons\modules` (où `fl26regen` le lit) et met le monde dans le jeu ; une version plus
récente d'un monde que vous avez remplace l'ancienne. Cela se termine par **Prêt à jouer** et une
liste de vérification finale. Commencez ensuite une nouvelle carrière Master League. **Retirer**
(sous **Dans le jeu maintenant**) retire à nouveau le monde et remet le fichier de monde
précédent.

Un modpack nomme les stades à domicile de ses clubs par les dossiers du pack de stades de son
créateur. Quand votre pack de stades garde un stade dans un autre dossier, Mod Studio le trouve
par son nom ; un stade que vous n'avez pas est laissé de côté (le club joue là où le jeu le met),
et la vérification finale dit combien de clubs ont le leur.

**Changer un monde installé.** `fl26worldpack.json` ne contient que le nom du monde et ce dont il
a besoin, mais le dossier du monde porte `leaguebuilder-plan.json`. Quand Mod Studio démarre avec
ce monde dans le jeu et les tables du jeu extraites, il fait votre monde à partir de ce plan et
l'ouvre, pour que celui qui reçoit puisse voir les ligues du monde. Pour le changer et le
reconstruire sur ses propres tables, il appuie d'abord sur **Le rendre modifiable...** dans Mon
monde (section 3.1).
Il est proche de l'original, pas identique : les ligues, clubs, noms, écussons, l'Europe, les
coupes, les changements de joueurs et la Ligue Conférence reviennent ; les tournois de
pré-saison, les coupes des pays du jeu, les noms des compétitions, les places européennes des
ligues du jeu, l'ordre des championnats et les clubs européens de la première saison ne reviennent
pas. Les images et les visages pointent vers le PC de l'expéditeur : Build dessine un écusson pour
une image manquante et dit lesquelles.
Mod Studio n'installe pas par-dessus un monde du même nom qui a été construit sur ce PC : renommez
d'abord ce monde sur sa carte.

## 10. Outils

**Diagnostic** (**4. Outils**) **— Lancer les vérifications** examine toute la configuration :
dossiers de contenu activés mais manquants, modules mal placés ou activés deux fois, lignes de
correspondance qui ne pointent vers rien, le monde dans le jeu (onglet **Votre monde dans le
jeu** ; un seul monde devrait y être), et le dernier `sider.log`. **Copier un rapport** met tout
dans le presse-papiers, à coller dans un message de forum ou un rapport de bug.

**Points de restauration** (**4. Outils**) : chaque fichier que le programme a modifié, avec la
copie d'avant. **Restaurer cette copie** le remet en place. Les copies sont dans
`SiderAddons\ModStudio\backups`. **Nettoyer...** supprime les anciennes, et garde toujours la plus
ancienne copie d'un fichier (celle d'avant Mod Studio). Les mondes supprimés et renommés et la
copie de votre dossier de sauvegarde sont listés ici aussi.

**Remettre Sider comme avant Mod Studio...** (Points de restauration, et le menu **Jeu**) remet tout
comme avant : il remet chaque fichier que Mod Studio a modifié tel qu'il était au départ
(`sider.ini`, CommonLib, les fichiers de correspondance) et retire ce qu'il a apporté (ses modules,
le pack de visages, les mondes et mods installés avec lui). Rien n'est supprimé : tout est gardé dans
`SiderAddons\ModStudio\reset-<heure>`, et **Annuler la dernière remise** le remet en place.

**Réglages** (**5. Réglages**) : **Dossier du jeu**, **Dossier de Sider** (quand il y en a
plusieurs), **Langue (Language)**, **Carrières Master League** (**Chaque monde garde ses propres
carrières (le dossier de sauvegarde change avec le monde)**, section 3.1), **Les tables du jeu**
(**Extraire les tables du jeu**, **Utiliser un autre dossier de tables...**, section 2) et
**Ouvrir le dossier des réglages du programme**.

## 11. Quand quelque chose ne va pas

| Ce que vous voyez | Que faire |
|---|---|
| *sider.ini not found* | Réglages → Dossier du jeu : choisissez le dossier avec `FL_2026.exe`. |
| *no game tables* | Réglages → Extraire les tables du jeu. |
| *Access is denied*, ou Mod Studio dit qu'il ne peut pas écrire dans le dossier du jeu | Le jeu est dans Program Files : appuyez sur **Redémarrer en administrateur**, ou déplacez le jeu dans un dossier à vous. |
| Mod Studio dit qu'une DLL de ses modules manque (`fl26swiss.dll` ...) | Un antivirus l'a prise. Ajoutez le dossier `SiderAddons` comme exclusion dans l'antivirus, puis **Installer maintenant** à nouveau. |
| Un mod n'apparaît pas dans le jeu | Diagnostic → Lancer les vérifications. Un dossier de contenu plus haut dans la liste a peut-être le même fichier. |
| Le jeu ne se lance plus après un changement | Points de restauration → remettez `sider.ini` en place, ou passez à un profil qui fonctionnait. |
| La nouvelle ligue n'est pas dans Select Team | Commencez une *nouvelle* carrière ; les anciennes carrières gardent leurs anciennes ligues. |
| Mes carrières ont disparu après un changement de monde | Elles sont dans `save_<monde>` à côté du dossier de sauvegarde : activez de nouveau ce monde (section 3.1). |
| Le gardien est le capitaine de chaque nouveau club | Le monde a été construit avant la 0.2.4 : reconstruisez-le et commencez une nouvelle carrière. |
| L'écusson sur le short d'un maillot dessiné est de travers | Le maillot a été dessiné avant la 0.2.4. Supprimez les fichiers `kitmaker.txt` dans `SiderAddons\content\kit-server\<votre monde>` et appuyez de nouveau sur **Construire et installer** : les maillots sont redessinés avec l'écusson dans le bon sens. |
| Les noms des clubs sont ceux du jeu | Un fichier Edit les remplace (section 8). |
| *vos ligues n'envoient personne en Europe* | Ligues → choisissez la première division → **Modifier la ligue...** → Europe (le bouton **Première division** remplit les trois places habituelles), puis reconstruisez. |
| *la Ligue Europa Conférence est activée, mais ses tables sont manquantes* | Reconstruisez le monde : il a été construit avant cette option, ou avec l'option désactivée. |
| Les étapes du Build sont grisées | Un monde prêt depuis un zip est dans le jeu. **Activez** d'abord votre propre monde, ou **Le rendre modifiable...** (section 8.2). |
| Un visage ne s'affiche pas | Le dossier doit contenir `#Win\face.fpk` ; reconstruisez après l'avoir choisi. |
| Autre chose | Diagnostic → **Copier un rapport**, et publiez-le avec `SiderAddons\sider.log`. |
