# Prvi koraci s FL26 Mod Studiom: svaki klik, redom

> [English](first-steps.md) · cijeli vodič kroz sve stranice: [mod-studio-guide.hr.md](mod-studio-guide.hr.md)
> · pitanja: [faq.md](faq.md) · pomoć: [Discord](https://discord.gg/StQqtk3G3M)

Ova stranica je za nekoga tko Mod Studio nikad nije otvorio. Ne objašnjava kako stvari rade,
samo što kliknuti, kojim redom i što trebaš vidjeti nakon svakog koraka. Radi korake redom i
ne preskači nijedan. Ako vidiš nešto drugo nego što korak kaže, stani tu i idi na
[Ako nešto ne valja](#ako-nešto-ne-valja).

Do novih liga se dolazi na tri načina. Koraci 1 do 5 su isti za sve. Onda izaberi jedan:

- **Način A: gotov svijet koji ti je netko poslao** kao jedan `.zip` (modpack, svijet od
  prijatelja). Najbrže: ništa se ne gradi.
- **Način B: prave lige iz NewLife baze.** Ti izabereš lige, Mod Studio ih napravi.
- **Način C: paket liga** (datoteka `.fl26pack` koju je netko napravio).

---

## Korak 1. Ugasi igru

Igra mora biti ugašena dok bilo što mijenjaš. Sider čita postavke samo kad se igra pali.
Pogledaj traku dolje: nema prozora Football Lifea, nema launchera.

## Korak 2. Skini Mod Studio

1. Otvori [zadnje izdanje](https://github.com/Matozanato/FootballLife-new-leagues/releases/latest).
2. Pod **Assets** klikni `FL26ModStudio-<verzija>.zip` (npr. `FL26ModStudio-0.2.1.zip`).
3. Desni klik na skinuti zip → **Extract All...** (Izdvoji sve) → izaberi mapu, npr.
   `Documents\FL26 Mod Studio` → **Extract**.

   Ne pokreći program iz zipa. Ne vadi `FL26ModStudio.exe` iz njegove mape: mape `_internal`
   i `pack` moraju ostati uz njega.

4. Otvori tu mapu i dvaput klikni `FL26ModStudio.exe`.

**Trebaš vidjeti:** tamni prozor. Gore: **File, Game, Profiles, Language, Help, Credits** i
zeleni gumb **Play** desno. Lijevo: **Home**, pa skupine **LEAGUE BUILDER**, **GAME CONTENT**
i **MANAGE**.

Ako Windows kaže "Windows protected your PC": klikni **More info** → **Run anyway**.

Prozor na hrvatskom: gore **Language** → Hrvatski. (Ovaj vodič piše engleske nazive gumba.)

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
2. Klikni **0. Install the modules**.

**Trebaš vidjeti:** u okviru dolje popis instaliranih modula.

Nove lige rade samo s tim modulima. U njima je i paket lica koji novim igračima daje lica.
To se radi jednom, i ponovno nakon svake nove verzije Mod Studija.

Sad izaberi **jedan** od tri načina.

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

## Način B: prave lige iz NewLife baze

**B1. Skini bazu.** Nije na GitHubu. Nađeš je u NewLife kanalu na našem
[Discordu](https://discord.gg/StQqtk3G3M). Dolazi u dijelovima (po kontinentima, plus *Free
agents*). Skini dijelove koje želiš.

**B2.** Stavi sve dijelove u **jednu** mapu, npr. `Documents\NewLife`. **Ne raspakiravaj ih.**
Mod Studio čita zipove takve kakvi jesu.

**B3.** Lijevo, pod **LEAGUE BUILDER**: klikni **NewLife Database**.

**B4.** Klikni **Open NewLife Database...** i izaberi mapu iz B2.

**Trebaš vidjeti:** popis liga sa stupcima League, Country, Clubs, In game, Players, Level.

**B5.** Klikni ligu da je označiš. Za više liga drži **Ctrl** i klikni svaku. Sive lige se ne
mogu dodati (igra ih već ima, ili su premale ili prevelike).

**B6.** Klikni **Add to the recipe**.

**Trebaš vidjeti:** "Added: ... Change them on Leagues, New clubs and Players, then Build."

**B7.** Lijevo: klikni **Leagues**. Tvoje nove lige su na popisu (gumb **Ours** pokaže samo njih).
Klikni jednu da vidiš i promijeniš klubove, rang, europska mjesta. Ništa od toga nije obavezno;
zadane postavke rade.

**B8.** Gore: **File → Save recipe**. Daj mu ime. (Recept je tvoj popis liga. Spremi ga da ga
kasnije možeš mijenjati.)

**B9.** Lijevo: klikni **Build**. Klikni veliki plavi **Build and install**. Odgovori **Yes**.

To odjednom instalira module, napravi svijet i upali ga. Traje od par sekundi do par minuta.

**Trebaš vidjeti:** u okviru dolje odrađene korake i nijedan red koji počinje s `error:`.

(Umjesto velikog gumba korak po korak: **1. Check the plan** → **2. Build the world** →
**3. Switch it on**. Isti rezultat.)

Idi na [Korak 6](#korak-6-pokreni-igru).

---

## Način C: paket liga (.fl26pack)

**C1.** Lijevo, pod **LEAGUE BUILDER**: klikni **League packages**.

**C2.** Klikni **Add a package...** i izaberi `.fl26pack` datoteku. (Ili gore: **File → Add a
league package...**.)

**C3.** Pokaže što je unutra i pita. Klikni **OK** / **Yes**.

**C4.** Gore: **File → Save recipe**.

**C5.** Lijevo: **Build** → **Build and install** → **Yes**.

**Trebaš vidjeti:** odrađene korake i nijedan red koji počinje s `error:`.

---

## Korak 6. Pokreni igru

Klikni zeleni **Play** gore desno (ili **Game → Start the game**). Pričekaj izbornik igre.

## Korak 7. Pokreni NOVU Master Ligu

1. **Master League** → **New game** (ne Continue: stara karijera ne dobije nove lige).
2. Na **Select Team** listaj: nove lige su na popisu.
3. Izaberi klub i igraj.

Nove lige su i u **Kick Off** → League, i u **Database → Competition Info**.

## Korak 8. Neka Mod Studio provjeri je li uspjelo

1. Ugasi igru.
2. U Mod Studiju: **Build** → **4. After a start: check**.

**Trebaš vidjeti:** modul po modul, da je svijet preuzet. Crveni red kaže što ne valja.

---

## Ako nešto ne valja

| Što vidiš | Što napraviti |
|---|---|
| `error: no game tables -- Settings > Unpack the game's tables` | Napravi [Korak 4](#korak-4-raspakiraj-tablice-igre). |
| Nema novih liga na Select Team | Jesi li pokrenuo **novu** Master Ligu? Onda **Build → 4. After a start: check**. Ako u logu piše `world file -- 0 leagues`, recept je bio prazan: dodaj lige (Način B ili C) i opet Build. |
| Svijet je napravljen s `0 leagues, 0 clubs` | Isto: recept nije imao liga. Prvo dodaj lige, pa Build. |
| Svi novi igrači imaju isto lice | **Build → 0. Install the modules** (donosi paket lica), pa opet pokreni igru. |
| Igra se ruši pri pokretanju | Pokreni je još jednom preko launchera (pad u prvih 10 sekundi se događa i bez modova). Ako se i dalje ruši: **Game → Start the game without mods (safe mode)...** i pitaj na Discordu. |
| Hoćeš sve vratiti kako je bilo | **MANAGE → Install mods → Remove the mod** za instalirani svijet; **MANAGE → Restore points** vraća svaku datoteku koju je Mod Studio promijenio. |

**Kad tražiš pomoć:** na [Discordu](https://discord.gg/StQqtk3G3M) pošalji sliku onoga što vidiš i
svoj `sider.log` (**Game → Open sider.log**, ili `SiderAddons\sider.log` u mapi igre).
