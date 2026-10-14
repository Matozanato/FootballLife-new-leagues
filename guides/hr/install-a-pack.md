# Instaliraj gotov paket: svaki klik, redom

> [English](../en/install-a-pack.md) · **hrvatski** · [español](../es/install-a-pack.md) · [português](../pt/install-a-pack.md)

> Drugi vodič korak po korak: [Napravi svoje lige i pakete](make-your-own-leagues.md)
> · sve stranice objašnjene: [mod-studio-guide.md](mod-studio-guide.md)
> · pitanja: [faq.md](../../docs/faq.md) (na engleskom) · pomoć: [Discord](https://discord.gg/StQqtk3G3M)

Ova stranica je za nekoga tko Mod Studio nikad nije otvorio, a dobio je nešto gotovo za igranje:
svijet, modpack ili paket liga. Ne objašnjava kako stvari rade. Kaže samo što kliknuti, kojim
redom i što trebaš vidjeti nakon svakog koraka. Radi korake redom i ne preskači nijedan. Ako
vidiš nešto drugo nego što korak kaže, stani tu i idi na [Ako nešto ne valja](#ako-nešto-ne-valja).

Vodič piše engleske nazive gumba, kako ih Mod Studio pokazuje. (Prozor možeš prebaciti na
hrvatski: gore **Language** → Hrvatski.)

Koraci 1 do 3 su isti za sve i radiš ih jednom. Onda izaberi način koji odgovara datoteci koju
si dobio:

- **Način A: gotov svijet**, kao jedan `.zip` (modpack, svijet od prijatelja). Najbrže: ništa se
  ne gradi.
- **Način C: paket liga**, datoteka `.fl26pack` koju je netko napravio. Mod Studio ga izgradi
  umjesto tebe.

Nitko ti nije ništa dao, a želiš sam izabrati prave lige (iz NewLife baze) ili napraviti svoje?
To je drugi vodič: [Napravi svoje lige i pakete](make-your-own-leagues.md). Prvo ovdje odradi
korake 1 do 3.

---

## Korak 1. Ugasi igru

Igra mora biti ugašena dok bilo što mijenjaš. Sider čita postavke samo kad se igra pali.
Pogledaj traku dolje: nema prozora Football Lifea, nema launchera.

## Korak 2. Skini Mod Studio

1. Otvori [zadnje izdanje](https://github.com/Matozanato/FootballLife-new-leagues/releases/latest).
2. Pod **Assets** klikni `FL26ModStudio-<version>.zip` (npr. `FL26ModStudio-0.2.1.zip`).
3. Desni klik na skinuti zip → **Extract All...** → izaberi mapu, npr.
   `Documents\FL26 Mod Studio` → **Extract**.

   Ne pokreći program iz zipa. Ne vadi `FL26ModStudio.exe` iz njegove mape: mape `_internal`
   i `pack` moraju ostati uz njega.

4. Otvori tu mapu i dvaput klikni `FL26ModStudio.exe`.

**Trebaš vidjeti:** tamni prozor. Gore: **File, Game, Profiles, Language, Help, Credits** i
zeleni gumb **Play** desno. Lijevo: **Home**, pa **YOUR WORLD** (**Build and edit your world**,
**Import your world**, **NewLife Database**), **GAME CONTENT**, **TOOLS** i, skroz dolje,
**Settings**.

Ako Windows kaže "Windows protected your PC": klikni **More info** → **Run anyway**.

Prozor na drugom jeziku? Gore **Language** → Hrvatski, Español ili Français.

## Korak 3. Reci mu gdje ti je igra

1. Lijevo, skroz dolje: klikni **Settings**.
2. Pored mape igre klikni **Browse...**.
3. Izaberi mapu u kojoj je `FL_2026.exe` (npr. `C:\Football Life 2026`). Ne `SiderAddons`, ne
   neku podmapu: baš mapu u kojoj je `FL_2026.exe`.
4. Klikni **Use this folder**.

**Trebaš vidjeti:** ispod mape red koji kaže da je `SiderAddons\sider.ini` pronađen.

(Isto je i gore: **Game → Choose the game folder...**.)

Više ništa ne treba postavljati. Kad zna gdje ti je igra, Mod Studio sam raspakira tablice igre
(njen popis klubova, liga i igrača), samo prvi put. Moduli Mod Studija uđu s **Install the
world** (način A) ili s **Build and install** (način C). Nove lige rade samo s tim modulima, a u
njima je i paket lica koji novim igračima daje lica. Ako **Home** ikad kaže da fale ili da su
stariji, klikni tamo **Install now**.

Sad izaberi način koji odgovara tvojoj datoteci.

---

## Način A: gotov svijet (jedan .zip)

Za kad ti je netko dao svijet kao zip (modpack, izvezeni svijet).

**A1.** Ne raspakiravaj ga sam.

**A2.** Lijevo, pod **YOUR WORLD**: klikni **Import your world**.

**A3.** Klikni **Choose a file...** i izaberi zip. (Ili ga samo povuci mišem na tu stranicu.)

**A4. Trebaš vidjeti:** jedan red koji kaže što je to, npr. `a ready world to play
(_FL26Modpack)`, ili `a newer version of the world _FL26Modpack you have` kad imaš stariju
verziju, a ispod koliko je liga unutra. Dijelovi (svijet, dresovi, scoreboardi ...) su pod
**More options: which parts, name, order of the content folders, map lines**, svi označeni
kvačicom. Tako i ostavi. (Da ga instaliraš bez dresova, tamo makni kvačicu dresovima.)

**A5.** Klikni **Install the world**. Ako je starija verzija istog svijeta već instalirana (raniji
Modpack), pita da je zamijeni: **Yes**. Stara se prvo makne, pa ništa od nje ne ostaje; tvoja
spremanja se ne diraju. Pričekaj dok ne kaže da je gotovo. Mod Studio instalira svoje module (ove
verzije), kopira svijet, stavi njegovu datoteku svijeta gdje je moduli čitaju i stavi svijet u
igru.

**Trebaš vidjeti:** `✓ Ready to play: press Play and start a new Master League` i prozor
**Ready to play** s popisom kvačica (svijet, moduli, paket lica ...). Ako umjesto toga kaže
**Almost ready**, nabroji što treba popraviti.

Gotov svijet ne treba Build: već je napravljen. Dok je u igri, koraci Builda su ugašeni (0.2.4).
Za svoje lige kasnije prvo stavi svoj svijet u igru (**Home → Switch world...**). Idi na
[Korak 4](#korak-4-pokreni-igru).

---

## Način B: napravi svoje lige

Biranje pravih liga iz NewLife baze, ili pravljenje vlastitih liga, ima svoj vodič, sa svakim
poljem objašnjenim: [Napravi svoje lige i pakete](make-your-own-leagues.md).

---

## Način C: paket liga (.fl26pack)

**C1.** Lijevo, pod **YOUR WORLD**: klikni **Build and edit your world**, pa karticu **League
packages**.

**C2.** Klikni **Add a package...** i izaberi `.fl26pack` datoteku. (Ili gore: **File → Add a
league package...**.)

**C3. Trebaš vidjeti:** prozor **Add a league package** s onim što je unutra: ime, verzija i
autor, pa njegove lige, svaka označena kvačicom. Paket s više liga iznad popisa ima **Select all**
/ **Select none**: makni kvačicu ligi koju ne želiš. Pod **What to take** možeš odznačiti dijelove
(npr. **Scoreboards ...**). Ako nisi siguran, ostavi sve označeno. Klikni **OK**.

Ako paket ima ligu s imenom koje već imaš, pita da je doda pod novim imenom: klikni **Yes**.

**Trebaš vidjeti:** zeleni red ispod naslova stranice: "Added ... Build and install puts its
leagues in the game."

Ništa ne trebaš spremati: tvoj svijet se sam spremi trenutak nakon svake promjene (dolje piše
**Your world is saved**).

**C4.** Kartica **Build** (pored **League packages**) → veliki plavi **Build and install** → **Yes**.

To odjednom stavi module Mod Studija, izgradi tvoj svijet i stavi ga u igru. Traje od par sekundi
do par minuta.

(Ako `.fl26pack` ispustiš na **Import your world**, dogodi se isto: nakon prozora iz C3 paket uđe
u tvoj svijet i **Build and install** krene sam.)

**Trebaš vidjeti:** prozor **Build finished** s kvačicama (World built, Leagues and clubs,
Modules installed and switched on, In the game). Klikni **Done**. U okviru dolje na stranici
Build nema reda koji počinje s `error:`.

---

## Korak 4. Pokreni igru

Klikni zeleni **Play** gore desno (ili **Game → Start the game**). Pričekaj izbornik igre.

## Korak 5. Pokreni NOVU Master Ligu

1. **Master League** → **New game** (ne Continue: stara karijera ne dobije nove lige).
2. Na **Select Team** listaj: nove lige su na popisu, pod svojim državama.
3. Izaberi klub i igraj.

Nove lige su i u **Kick Off** → League, i u **Database → Competition Info**.

## Korak 6. Neka Mod Studio provjeri je li uspjelo

1. Ugasi igru.
2. U Mod Studiju: **Build and edit your world** → kartica **Build** → **Step by step, and Export
   the world** → **4. After a start: check**.

**Trebaš vidjeti:** za svaki modul red koji kaže koliko je liga pročitao iz svijeta, a na kraju
`the world works as built`. Red koji kaže `not loaded` ili `did NOT read the world file`, i zadnji
red `something is wrong -- see the lines above`, kažu ti što ne valja.

---

## Ako nešto ne valja

| Što vidiš | Što napraviti |
|---|---|
| `error: no game tables -- Settings > Unpack the game's tables` | **Settings → Unpack the game's tables**. |
| Nema novih liga na Select Team | Jesi li pokrenuo **novu** Master Ligu? Onda **4. After a start: check** ([Korak 6](#korak-6-neka-mod-studio-provjeri-je-li-uspjelo)). Ako u logu piše `world file -- 0 leagues`, tvoj svijet je bio prazan: opet dodaj paket (Način C) i opet Build. |
| Svijet je napravljen s `0 leagues, 0 clubs` | Isto: tvoj svijet nije imao liga. Prvo dodaj lige, pa Build. |
| `sider.log is older than the world switched on -- start the game to the main menu, then check again` | Provjera je pokrenuta prije nego si pokrenuo igru. Pokreni je do glavnog izbornika, ugasi je i opet stisni **4. After a start: check**. |
| Svi novi igrači imaju isto lice | **Home → Install now** (kad Home kaže da moduli fale ili su stariji), ili **Build and edit your world → Build → Step by step, and Export the world → 0. Install the modules**: donosi paket lica. Pa opet pokreni igru. |
| Igra se ruši pri pokretanju | Pokreni je još jednom preko launchera (pad u prvih 10 sekundi se događa i bez modova). Ako se i dalje ruši: **Game → Start the game without mods (safe mode)...** i pitaj na Discordu. |
| Hoćeš sve vratiti kako je bilo | **Import your world** → označi ga pod **In the game now** → **Remove** vadi instalirani svijet. **TOOLS → Restore points → Put Sider back as before Mod Studio...** (i u izborniku **Game**) vraća svaku datoteku koju je Mod Studio promijenio i vadi ono što je donio. Ništa se ne briše: čuva se u `SiderAddons\ModStudio\reset-<time>`, a **Undo the last reset** to vraća. |

**Kad tražiš pomoć:** na [Discordu](https://discord.gg/StQqtk3G3M) pošalji sliku onoga što vidiš i
svoj `sider.log` (**Game → Open sider.log**, ili `SiderAddons\sider.log` u mapi igre).
