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

Koraci 1 do 5 su isti za sve i radiš ih jednom. Onda izaberi način koji odgovara datoteci koju
si dobio:

- **Način A: gotov svijet**, kao jedan `.zip` (modpack, svijet od prijatelja). Najbrže: ništa se
  ne gradi.
- **Način C: paket liga**, datoteka `.fl26pack` koju je netko napravio. Mod Studio ga izgradi
  umjesto tebe.

Nitko ti nije ništa dao, a želiš sam izabrati prave lige (iz NewLife baze) ili napraviti svoje?
To je drugi vodič: [Napravi svoje lige i pakete](make-your-own-leagues.md). Prvo ovdje odradi
korake 1 do 5.

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
zeleni gumb **Play** desno. Lijevo: **Home**, pa skupine **LEAGUE BUILDER**, **GAME CONTENT**
i **MANAGE**.

Ako Windows kaže "Windows protected your PC": klikni **More info** → **Run anyway**.

Prozor na drugom jeziku? Gore **Language** → Hrvatski, Español ili Français.

## Korak 3. Reci mu gdje ti je igra

1. Lijevo, skroz dolje pod **MANAGE**: klikni **Settings**.
2. Pored mape igre klikni **Browse...**.
3. Izaberi mapu u kojoj je `FL_2026.exe` (npr. `C:\Football Life 2026`). Ne `SiderAddons`, ne
   neku podmapu: baš mapu u kojoj je `FL_2026.exe`.
4. Klikni **Use this folder**.

**Trebaš vidjeti:** ispod mape red koji kaže da je `SiderAddons\sider.ini` pronađen.

(Isto je i gore: **Game → Choose the game folder...**.)

## Korak 4. Raspakiraj tablice igre

I dalje na **Settings**: klikni **Unpack the game's tables**. Pričekaj par sekundi.

**Trebaš vidjeti:** red koji kaže da su tablice raspakirane.

To se radi jednom. Ponovno samo nakon updatea igre; Mod Studio to sam primijeti i pita.

Ako preskočiš ovaj korak, Build kasnije javi `error: no game tables -- Settings > Unpack the game's tables`.

## Korak 5. Instaliraj module Mod Studija

1. Lijevo, pod **LEAGUE BUILDER**: klikni **Build**.
2. Klikni **0. Install the modules**. Pita da ih kopira: klikni **Yes**.

**Trebaš vidjeti:** u okviru dolje popis instaliranih modula.

Nove lige rade samo s tim modulima. U njima je i paket lica koji novim igračima daje lica.
To se radi jednom, i ponovno nakon svake nove verzije Mod Studija.

Sad izaberi način koji odgovara tvojoj datoteci.

---

## Način A: gotov svijet (jedan .zip)

Za kad ti je netko dao svijet kao zip (modpack, izvezeni svijet).

**A1.** Ne raspakiravaj ga sam.

**A2.** Lijevo, pod **MANAGE**: klikni **Install mods**.

**A3.** Klikni **Choose a file...** i izaberi zip. (Ili ga samo povuci mišem na tu stranicu.)

**A4. Trebaš vidjeti:** popis što je unutra, npr. svijet (`_FL26Modpack` ili slično, označen kao
League Builder world), dresovi i scoreboardi. Sve je označeno kvačicom. Tako i ostavi.

**A5.** Klikni **Install**. Pričekaj dok ne kaže da je gotovo. Mod Studio kopira svijet, stavi
njegovu datoteku svijeta gdje je moduli čitaju i upali svijet.

**A6.** Ako pita da instalira module: **Yes**.

Za gotov svijet **ne** stišći Build. Već je napravljen. Idi na [Korak 6](#korak-6-pokreni-igru).

---

## Način B: napravi svoje lige

Biranje pravih liga iz NewLife baze, ili pravljenje vlastitih liga, ima svoj vodič, sa svakim
poljem objašnjenim: [Napravi svoje lige i pakete](make-your-own-leagues.md).

---

## Način C: paket liga (.fl26pack)

**C1.** Lijevo, pod **LEAGUE BUILDER**: klikni **League packages**.

**C2.** Klikni **Add a package...** i izaberi `.fl26pack` datoteku. (Ili gore: **File → Add a
league package...**.)

**C3. Trebaš vidjeti:** prozor **Add a league package** s onim što je unutra: ime, verzija i
autor, pa njegove lige, svaka označena kvačicom. Paket s više liga iznad popisa ima **Select all**
/ **Select none**: makni kvačicu ligi koju ne želiš. Pod **What to take** možeš odznačiti dijelove
(npr. **Scoreboards ...**). Ako nisi siguran, ostavi sve označeno. Klikni **OK**.

Ako paket ima ligu s imenom koje već imaš, pita da je doda pod novim imenom: klikni **Yes**.

**Trebaš vidjeti:** zeleni red ispod naslova stranice: "Added ... Save the recipe, then Build to
put the leagues in the game."

**C4.** Gore: **File → Save recipe**. Prvi put se otvori prozor za spremanje: daj datoteci ime i
klikni **Save**. (Recept je tvoj popis liga. Spremi ga da ga kasnije možeš mijenjati.)

**C5.** Lijevo: **Build** → veliki plavi **Build and install** → **Yes**.

To odjednom instalira module, napravi svijet i upali ga. Traje od par sekundi do par minuta.

**Trebaš vidjeti:** prozor **Build finished** s kvačicama (World built, Leagues and clubs,
Modules installed and switched on, Switched on in sider.ini). Klikni **Done**. U okviru dolje na
stranici Build nema reda koji počinje s `error:`.

---

## Korak 6. Pokreni igru

Klikni zeleni **Play** gore desno (ili **Game → Start the game**). Pričekaj izbornik igre.

## Korak 7. Pokreni NOVU Master Ligu

1. **Master League** → **New game** (ne Continue: stara karijera ne dobije nove lige).
2. Na **Select Team** listaj: nove lige su na popisu, pod svojim državama.
3. Izaberi klub i igraj.

Nove lige su i u **Kick Off** → League, i u **Database → Competition Info**.

## Korak 8. Neka Mod Studio provjeri je li uspjelo

1. Ugasi igru.
2. U Mod Studiju: **Build** → **4. After a start: check**.

**Trebaš vidjeti:** za svaki modul red koji kaže koliko je liga pročitao iz svijeta, a na kraju
`the world works as built`. Red koji kaže `not loaded` ili `did NOT read the world file`, i zadnji
red `something is wrong -- see the lines above`, kažu ti što ne valja.

---

## Ako nešto ne valja

| Što vidiš | Što napraviti |
|---|---|
| `error: no game tables -- Settings > Unpack the game's tables` | Napravi [Korak 4](#korak-4-raspakiraj-tablice-igre). |
| Nema novih liga na Select Team | Jesi li pokrenuo **novu** Master Ligu? Onda **Build → 4. After a start: check**. Ako u logu piše `world file -- 0 leagues`, recept je bio prazan: opet dodaj paket (Način C) i opet Build. |
| Svijet je napravljen s `0 leagues, 0 clubs` | Isto: recept nije imao liga. Prvo dodaj lige, pa Build. |
| `sider.log is older than the world switched on -- start the game to the main menu, then check again` | Provjera je pokrenuta prije nego si pokrenuo igru. Pokreni je do glavnog izbornika, ugasi je i opet stisni **4. After a start: check**. |
| Svi novi igrači imaju isto lice | **Build → 0. Install the modules** (donosi paket lica), pa opet pokreni igru. |
| Igra se ruši pri pokretanju | Pokreni je još jednom preko launchera (pad u prvih 10 sekundi se događa i bez modova). Ako se i dalje ruši: **Game → Start the game without mods (safe mode)...** i pitaj na Discordu. |
| Hoćeš sve vratiti kako je bilo | **MANAGE → Install mods → Remove the mod** za instalirani svijet; **MANAGE → Restore points** vraća svaku datoteku koju je Mod Studio promijenio. |

**Kad tražiš pomoć:** na [Discordu](https://discord.gg/StQqtk3G3M) pošalji sliku onoga što vidiš i
svoj `sider.log` (**Game → Open sider.log**, ili `SiderAddons\sider.log` u mapi igre).
