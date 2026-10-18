# Installer un pack prêt : chaque clic, dans l'ordre

> [English](../en/install-a-pack.md) · [hrvatski](../hr/install-a-pack.md) · [español](../es/install-a-pack.md) · [português](../pt/install-a-pack.md) · **français**

> L'autre guide pas à pas : [Créer vos propres ligues et packs](make-your-own-leagues.md)
> · chaque page expliquée : [mod-studio-guide.md](mod-studio-guide.md)
> · questions : [faq.md](../../docs/faq.md) · aide : [Discord](https://discord.gg/StQqtk3G3M)

Cette page est pour quelqu'un qui n'a jamais ouvert Mod Studio et à qui on a donné quelque chose
de prêt à jouer : un monde, un modpack ou un paquet de ligues. Elle n'explique pas comment les
choses marchent. Elle dit seulement quoi cliquer, dans quel ordre, et ce que vous devez voir
après chaque étape. Faites les étapes dans l'ordre et n'en sautez aucune. Si vous voyez autre
chose que ce que dit une étape, arrêtez-vous là et allez à
[Si quelque chose ne va pas](#si-quelque-chose-ne-va-pas).

Les étapes 1 à 3 sont les mêmes pour tout le monde et se font une seule fois. Ensuite, choisissez
la voie qui correspond au fichier qu'on vous a donné :

- **Voie A : un monde prêt**, en un seul `.zip` (un modpack, le monde d'un ami). La voie la plus
  rapide : rien à construire.
- **Voie C : un paquet de ligues**, un fichier `.fl26pack` que quelqu'un a créé. Mod Studio le
  construit pour vous.

Personne ne vous a rien donné, et vous voulez choisir vous-même de vraies ligues (dans la NewLife
Database) ou créer les vôtres ? C'est l'autre guide :
[Créer vos propres ligues et packs](make-your-own-leagues.md). Faites d'abord ici les étapes 1 à 3.

---

## Étape 1. Fermer le jeu

Le jeu doit être fermé pendant vos changements. Sider ne lit sa configuration qu'au lancement du
jeu. Regardez la barre des tâches : pas de fenêtre Football Life, pas de launcher.

## Étape 2. Télécharger Mod Studio

1. Ouvrez la [dernière version](https://github.com/Matozanato/FootballLife-new-leagues/releases/latest).
2. Sous **Assets**, cliquez sur `FL26ModStudio-<version>.zip` (par exemple `FL26ModStudio-0.2.4.zip`).
3. Clic droit sur le zip téléchargé → **Extraire tout...** (Extract All...) → choisissez un
   dossier, par exemple `Documents\FL26 Mod Studio` → **Extraire** (Extract).

   Ne lancez pas le programme depuis l'intérieur du zip. Ne sortez pas `FL26ModStudio.exe` de son
   dossier : les dossiers `_internal` et `pack` à côté doivent rester avec lui.

4. Ouvrez ce dossier et double-cliquez sur `FL26ModStudio.exe`.

**Vous devez voir :** une fenêtre sombre. En haut : les menus **Fichier, Jeu, Profils, Langue,
Aide**, le bouton **Crédits**, et un bouton vert **Lancer le jeu** à droite. En dessous, des cases
avec ce qui est dans le jeu maintenant (**DOSSIER DU JEU**, **SIDER**, **MONDE ACTIF** ...), puis
les sections **1. Accueil**, **2. Mon monde**, **3. Contenu du jeu**, **4. Outils** et
**5. Réglages**.

La première fois, une petite carte vous fait visiter la fenêtre en dix étapes (la visite rapide).
Lisez-la avec **Suivant**, ou fermez-la avec **Passer la visite**. Elle ne change rien.
**Aide → Visite rapide** la remontre.

Si Windows dit « Windows a protégé votre ordinateur » (Windows protected your PC) : cliquez sur
**Informations complémentaires** (More info) → **Exécuter quand même** (Run anyway).

Vous voulez la fenêtre dans une autre langue ? Barre du haut → **Langue (Language)** → Hrvatski,
Español, Português ou Français, puis relancez Mod Studio.

## Étape 3. Indiquer où se trouve votre jeu

1. Cliquez sur **5. Réglages**.
2. À côté du dossier du jeu, cliquez sur **Parcourir...**.
3. Choisissez le dossier qui contient `FL_2026.exe` (par exemple `D:\Games\Football Life 2026`).
   Pas `SiderAddons`, pas un sous-dossier : le dossier où se trouve `FL_2026.exe`.
4. Cliquez sur **Utiliser ce dossier**.

**Vous devez voir :** sous le dossier, une ligne qui commence par `Trouvé : FL_2026.exe` et qui
nomme le dossier de Sider et `sider.ini`.

(La même chose est dans la barre du haut : **Jeu → Choisir le dossier du jeu...**.)

Il n'y a rien d'autre à régler. Dès qu'il sait où est votre jeu, Mod Studio extrait tout seul les
tables du jeu (sa liste de clubs, de ligues et de joueurs), la première fois seulement. Cela prend
une minute ou deux. Les modules de Mod Studio s'installent avec **Installer le monde** (voie A) ou
**Construire et installer** (voie C). Les nouvelles ligues ne marchent qu'avec ces modules, et ils
apportent le pack de visages qui donne leurs visages aux nouveaux joueurs. Si **1. Accueil** dit
un jour qu'ils manquent ou sont plus anciens, cliquez sur **Installer maintenant** là-bas.

Choisissez maintenant la voie qui correspond à votre fichier.

---

## Voie A : un monde prêt (un seul .zip)

Utilisez-la quand quelqu'un vous a donné un monde sous forme de zip (un modpack, un monde exporté).

**A1.** Ne le décompressez pas vous-même.

**A2.** Cliquez sur **2. Mon monde**, puis sur **+ Ajouter...** (à droite, à côté des onglets).

**A3.** Cliquez sur **Choisir un fichier...** et choisissez le zip. (Ou glissez le zip sur cette
fenêtre.) Une ligne verte commence par `Trouvé : un zip de monde`. Cliquez sur **Ajouter** : la
page **Importer votre monde** s'ouvre avec le zip.

(Deux autres chemins vers la même page : **1. Accueil → Importer un zip de monde**, ou **2. Mon
monde → Plus ▾ → Importer un zip de monde**, puis choisissez le zip.)

**A4. Vous devez voir :** une ligne qui dit ce que c'est, par exemple `un monde prêt à jouer
(_FL26Modpack)`, ou `une version plus récente du monde _FL26Modpack que vous avez` quand vous en
avez une plus ancienne, et en dessous combien de ligues il contient. Les parties (le monde, les
maillots, les tableaux de score ...) sont sous **Plus d'options : quelles parties, nom, ordre des
dossiers de contenu, lignes des map**, toutes cochées. Laissez-les ainsi. (Pour l'installer sans
les maillots, décochez les maillots là.)

**A5.** Cliquez sur **Installer le monde**. Si une version plus ancienne du même monde est
installée (un Modpack plus ancien), il demande s'il faut la remplacer : répondez **Oui**.
L'ancienne est retirée d'abord, pour que rien n'en reste ; vos sauvegardes ne sont pas touchées.
Attendez qu'il dise que c'est fini. Mod Studio installe ses modules (ceux de cette version), copie
le monde, met son fichier de monde là où les modules le lisent, et met le monde dans le jeu.

**Vous devez voir :** `✓ Prêt à jouer : appuyez sur Play et lancez une nouvelle Master League`
(Play veut dire le bouton **Lancer le jeu**), et une fenêtre **Prêt à jouer** avec une liste de
coches (le monde, les modules, le pack de visages ...). Si elle dit **Presque prêt** à la place,
elle liste ce qu'il faut corriger.

Dans **2. Mon monde**, le monde a maintenant une carte verte qui dit **● DANS LE JEU MAINTENANT**,
avec l'étiquette **Depuis un zip**.

Un monde prêt n'a pas besoin de Build : il est déjà construit. Tant qu'il est dans le jeu, les
étapes du Build sont désactivées. Pour construire plus tard vos propres ligues, mettez d'abord
votre propre monde dans le jeu (**Activer** sur sa carte dans **2. Mon monde**). Allez à
l'[Étape 4](#étape-4-lancer-le-jeu).

---

## Voie B : construire vos propres ligues

Choisir de vraies ligues dans la NewLife Database, ou créer vos propres ligues, a son propre
guide, avec chaque champ expliqué :
[Créer vos propres ligues et packs](make-your-own-leagues.md).

---

## Voie C : un paquet de ligues (.fl26pack)

**C1.** Cliquez sur **2. Mon monde**, puis sur **+ Ajouter...** (à droite, à côté des onglets).

**C2.** Cliquez sur **Choisir un fichier...** et choisissez le fichier `.fl26pack`. (Ou glissez-le
sur cette fenêtre.)

**C3. Vous devez voir :** une ligne verte `Trouvé : paquet de ligues "..."` avec son nombre de
ligues et de clubs, et ses ligues dans une liste, chacune cochée. Décochez une ligue dont vous ne
voulez pas. Sous la liste : combien de compétitions votre monde aura (le jeu a de la place pour
255), et que rien n'arrive dans le jeu avant **Construire et installer**. Cliquez sur **Ajouter**.

(Les autres chemins : **2. Mon monde → Plus ▾ → Paquets de ligues → Ajouter un paquet...**, ou
**Fichier → Ajouter un paquet de ligues...**. Ceux-là affichent une fenêtre **Ajouter un paquet de
ligues** : vous pouvez aussi y décocher des parties sous **Que prendre**, par exemple les tableaux
de score. Si vous n'êtes pas sûr, laissez tout coché et cliquez sur **OK**.)

Si le paquet a une ligue dont vous avez déjà le nom, il demande s'il faut l'ajouter sous un
nouveau nom : cliquez sur **Oui**.

**Vous devez voir :** l'onglet **Ligues**, avec les ligues du paquet dans la liste, et en bas de
la fenêtre : « ... ajouté. Construire et installer met ses ligues dans le jeu. »

Il n'y a rien à enregistrer : votre monde s'enregistre tout seul un instant après chaque
changement (la barre du bas dit **Votre monde est enregistré**).

**C4.** Onglet **Construction** (le premier onglet de **2. Mon monde**) → le grand bouton
**Construire et installer** → **Oui**.

Il installe les modules de Mod Studio, construit votre monde et le met dans le jeu, tout en un.
Cela prend de quelques secondes à quelques minutes ; la barre du bas montre où il en est.

(Déposer le `.fl26pack` sur **Importer votre monde** fait la même chose : après la fenêtre
**Ajouter un paquet de ligues**, le paquet entre dans votre monde et **Construire et installer**
démarre tout seul.)

**Vous devez voir :** une fenêtre **Build terminé** avec des coches (Monde construit, Ligues et
clubs, Modules installés et activés, Dans le jeu). Cliquez sur **Terminé**. Dans la case en bas de
l'onglet Construction, aucune ligne ne commence par `erreur :`.

---

## Étape 4. Lancer le jeu

Cliquez sur le bouton vert **Lancer le jeu** en haut à droite (ou **Jeu → Lancer le jeu**).
Attendez le menu du jeu.

## Étape 5. Commencer une NOUVELLE Master League

1. **Master League** → **New game** (pas Continue : une ancienne carrière ne reçoit pas les
   nouvelles ligues).
2. Dans **Select Team**, faites défiler : les nouvelles ligues sont dans la liste, sous leur pays.
3. Choisissez un club et jouez.

Les nouvelles ligues sont aussi dans **Kick Off** → League, et dans **Database → Competition Info**.

Chaque monde garde ses propres carrières. Quand vous mettez un autre monde dans le jeu, Mod Studio
met vos carrières de côté avec le monde auquel elles appartiennent, et les ramène quand ce monde
est de nouveau dans le jeu. Rien n'est supprimé.

## Étape 6. Laisser Mod Studio vérifier que tout marche

1. Fermez le jeu.
2. Dans Mod Studio : **2. Mon monde** → onglet **Construction** → **Étape par étape, et Exporter le
   monde** → **4. Après un lancement : vérifier**.

**Vous devez voir :** une ligne par module qui dit combien de ligues il a lues dans le monde, et à
la fin `the world works as built`. Une ligne qui dit `not loaded` ou `did NOT read the world
file`, et la dernière ligne `something is wrong -- see the lines above`, vous disent ce qui ne va
pas.

---

## Si quelque chose ne va pas

| Ce que vous voyez | Que faire |
|---|---|
| `erreur : pas de tables du jeu -- Réglages > Extraire les tables du jeu` | **5. Réglages → Extraire les tables du jeu**. |
| Pas de nouvelles ligues dans Select Team | Avez-vous commencé une **nouvelle** Master League ? Ensuite **4. Après un lancement : vérifier** ([Étape 6](#étape-6-laisser-mod-studio-vérifier-que-tout-marche)). Si son journal dit `world file -- 0 leagues`, votre monde était vide : ajoutez de nouveau le paquet (voie C) et reconstruisez. |
| Le monde dit qu'il a été construit avec `0 championnats, 0 clubs` | Pareil : votre monde n'avait pas de ligues. Ajoutez-en d'abord, puis Build. |
| `sider.log is older than the world switched on -- start the game to the main menu, then check again` | La vérification a tourné avant que vous lanciez le jeu. Lancez-le jusqu'au menu principal, fermez-le, appuyez de nouveau sur **4. Après un lancement : vérifier**. |
| **Construire et installer** est grisé | Un monde prêt depuis un zip est ouvert (voie A). Il n'a pas besoin de Build. Pour construire vos propres ligues, cliquez d'abord sur **Activer** sur la carte de votre propre monde dans **2. Mon monde**. |
| Mon ancienne carrière a disparu | Elle est gardée avec le monde où elle a été faite. Cliquez sur **Activer** sur la carte de ce monde dans **2. Mon monde** et elle revient. |
| Tous les nouveaux joueurs ont le même visage | **1. Accueil → Installer maintenant** (quand Accueil dit que les modules manquent ou sont plus anciens), ou **2. Mon monde → Construction → Étape par étape, et Exporter le monde → 0. Installer les modules** : il apporte le pack de visages. Puis relancez le jeu. |
| Le jeu plante au démarrage | Lancez-le encore une fois par le launcher (un plantage dans les 10 premières secondes arrive aussi sans mods). S'il continue de planter : **Jeu → Lancer le jeu sans mods (mode sans échec)...** et demandez sur Discord. |
| Vous voulez tout remettre comme avant | **Importer votre monde** (**2. Mon monde → Plus ▾ → Importer un zip de monde**) → choisissez-le sous **Dans le jeu maintenant** → **Retirer** retire un monde installé. **4. Outils → Points de restauration → Remettre Sider comme avant Mod Studio...** (aussi dans le menu **Jeu**) remet chaque fichier que Mod Studio a modifié et retire ce qu'il a apporté. Rien n'est supprimé : tout est gardé dans `SiderAddons\ModStudio\reset-<heure>`, et **Annuler la dernière remise** le remet en place. |

**Demander de l'aide :** sur le [Discord](https://discord.gg/StQqtk3G3M), envoyez une capture
d'écran de ce que vous voyez et votre `sider.log` (**Jeu → Ouvrir sider.log**, ou
`SiderAddons\sider.log` dans le dossier du jeu).
