# Instaliraj gotov paket: svaki klik, redom

> [English](../en/install-a-pack.md) · **hrvatski** · [español](../es/install-a-pack.md) · [português](../pt/install-a-pack.md) · [français](../fr/install-a-pack.md)

> Drugi vodič korak po korak: [Napravi svoje lige i pakete](make-your-own-leagues.md)
> · sve stranice objašnjene: [mod-studio-guide.md](mod-studio-guide.md)
> · pitanja: [faq.md](../../docs/faq.md) (na engleskom) · pomoć: [Discord](https://discord.gg/StQqtk3G3M)

Ova stranica je za nekoga tko Mod Studio nikad nije otvorio, a dobio je nešto gotovo za igranje:
svijet, modpack ili paket liga. Ne objašnjava kako stvari rade. Kaže samo što kliknuti, kojim
redom i što trebaš vidjeti nakon svakog koraka. Radi korake redom i ne preskači nijedan. Ako
vidiš nešto drugo nego što korak kaže, stani tu i idi na [Ako nešto ne valja](#ako-nešto-ne-valja).

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
2. Pod **Assets** klikni `FL26ModStudio-<version>.zip` (npr. `FL26ModStudio-0.2.4.zip`).
3. Desni klik na skinuti zip → **Extract All...** → izaberi mapu, npr.
   `Documents\FL26 Mod Studio` → **Extract**.

   Ne pokreći program iz zipa. Ne vadi `FL26ModStudio.exe` iz njegove mape: mape `_internal`
   i `pack` moraju ostati uz njega.

4. Otvori tu mapu i dvaput klikni `FL26ModStudio.exe`.

**Trebaš vidjeti:** tamni prozor. Gore: izbornici **Datoteka, Igra, Profili, Jezik (Language),
Pomoć**, gumb **Zasluge** i zeleni gumb **Pokreni igru** desno. Ispod njih kućice s onim što je
sad u igri (**MAPA IGRE**, **SIDER**, **AKTIVNI SVIJET** ...), pa dijelovi **1. Početna**,
**2. Moj svijet**, **3. Sadržaj igre**, **4. Alati** i **5. Postavke**.

Prvi put te mala kartica provede kroz prozor u deset koraka (kratka tura). Čitaj je s **Dalje**
ili je zatvori s **Preskoči turu**. Ništa ne mijenja. **Pomoć → Kratka tura** je opet pokaže.

Ako Windows kaže "Windows protected your PC": klikni **More info** → **Run anyway**.

Želiš prozor na drugom jeziku? Gore **Jezik (Language)** → Hrvatski, Español, Português ili Français, pa
ponovno pokreni Mod Studio.

## Korak 3. Reci mu gdje ti je igra

1. Klikni **5. Postavke**.
2. Pored mape igre klikni **Pregledaj...**.
3. Izaberi mapu u kojoj je `FL_2026.exe` (npr. `D:\Games\Football Life 2026`). Ne `SiderAddons`,
   ne neku podmapu: baš mapu u kojoj je `FL_2026.exe`.
4. Klikni **Koristi ovu mapu**.

**Trebaš vidjeti:** ispod mape red koji počinje s `Nađeno: FL_2026.exe` i imenuje mapu Sidera i
`sider.ini`.

(Isto je i gore: **Igra → Odaberi mapu igre...**.)

Više ništa ne treba postavljati. Kad zna gdje ti je igra, Mod Studio sam raspakira tablice igre
(njen popis klubova, liga i igrača), samo prvi put. To traje minutu ili dvije. Moduli Mod
Studija uđu s **Instaliraj svijet** (način A) ili s **Izgradi i instaliraj** (način C). Nove
lige rade samo s tim modulima, a u njima je i paket lica koji novim igračima daje lica. Ako
**1. Početna** ikad kaže da fale ili da su stariji, klikni tamo **Instaliraj sada**.

Sad izaberi način koji odgovara tvojoj datoteci.

---

## Način A: gotov svijet (jedan .zip)

Za kad ti je netko dao svijet kao zip (modpack, izvezeni svijet).

**A1.** Ne raspakiravaj ga sam.

**A2.** Klikni **2. Moj svijet**, pa **+ Dodaj...** (desno, pored kartica).

**A3.** Klikni **Odaberi datoteku...** i izaberi zip. (Ili ga povuci mišem na taj prozor.)
Zeleni red počinje s `Pronađeno: zip svijeta`. Klikni **Dodaj**: otvori se stranica **Uvezi
svijet** s tim zipom.

(Još dva puta do iste stranice: **1. Početna → Uvezi zip svijeta**, ili **2. Moj svijet → Više ▾ →
Uvezi zip svijeta**, pa izaberi zip.)

**A4. Trebaš vidjeti:** jedan red koji kaže što je to, npr. `gotov svijet za igru
(_FL26Modpack)`, ili `novija verzija svijeta _FL26Modpack koji imaš` kad imaš stariju verziju,
a ispod koliko je liga unutra. Dijelovi (svijet, dresovi, semafori ...) su pod **Više opcija:
koji dijelovi, ime, redoslijed mapa sadržaja, linije u map datotekama**, svi označeni
kvačicom. Tako i ostavi. (Da ga instaliraš bez dresova, tamo makni kvačicu dresovima.)

**A5.** Klikni **Instaliraj svijet**. Ako je starija verzija istog svijeta već instalirana
(raniji Modpack), pita da je zamijeni: **Da**. Stara se prvo makne, pa ništa od nje ne ostaje;
tvoja spremanja se ne diraju. Pričekaj dok ne kaže da je gotovo. Mod Studio instalira svoje
module (ove verzije), kopira svijet, stavi njegovu datoteku svijeta gdje je moduli čitaju i
stavi svijet u igru.

**Trebaš vidjeti:** `✓ Spremno za igru: pritisni Play i pokreni novu Master League` (Play je
gumb **Pokreni igru**) i prozor **Spremno za igru** s popisom kvačica (svijet, moduli, paket
lica ...). Ako umjesto toga kaže **Skoro spremno**, nabroji što treba popraviti.

U **2. Moj svijet** svijet sad ima zelenu karticu na kojoj piše **● U IGRI SADA**, s oznakom
**Iz zipa**.

Gotov svijet ne treba Build: već je izgrađen. Dok je u igri, koraci gradnje su ugašeni. Za
svoje lige kasnije prvo stavi svoj svijet u igru (**Aktiviraj** na njegovoj kartici u **2. Moj
svijet**). Idi na [Korak 4](#korak-4-pokreni-igru).

---

## Način B: napravi svoje lige

Biranje pravih liga iz NewLife baze, ili pravljenje vlastitih liga, ima svoj vodič, sa svakim
poljem objašnjenim: [Napravi svoje lige i pakete](make-your-own-leagues.md).

---

## Način C: paket liga (.fl26pack)

**C1.** Klikni **2. Moj svijet**, pa **+ Dodaj...** (desno, pored kartica).

**C2.** Klikni **Odaberi datoteku...** i izaberi datoteku `.fl26pack`. (Ili je povuci mišem na
taj prozor.)

**C3. Trebaš vidjeti:** zeleni red `Pronađeno: paket liga "..."` s brojem liga i klubova, i
njegove lige na popisu, svaka označena kvačicom. Makni kvačicu ligi koju ne želiš. Ispod popisa:
koliko će natjecanja imati tvoj svijet (igra ima mjesta za 255) i da ništa ne ulazi u igru do
**Izgradi i instaliraj**. Klikni **Dodaj**.

(Drugi putovi: **2. Moj svijet → Više ▾ → Paketi liga → Dodaj paket...**, ili **Datoteka → Dodaj
paket liga...**. Oni pokažu prozor **Dodaj paket liga**: tamo pod **Što uzeti** možeš odznačiti
i dijelove, npr. semafore. Ako nisi siguran, ostavi sve označeno i klikni **U redu**.)

Ako paket ima ligu s imenom koje već imaš, pita da je doda pod novim imenom: klikni **Da**.

**Trebaš vidjeti:** karticu **Lige**, s ligama paketa na popisu, a dolje u prozoru: "Dodan ...
Izgradi i instaliraj stavlja njegove lige u igru."

Ništa ne trebaš spremati: tvoj svijet se sam spremi trenutak nakon svake promjene (dolje piše
**Tvoj svijet je spremljen**).

**C4.** Kartica **Gradnja** (prva kartica u **2. Moj svijet**) → veliki **Izgradi i instaliraj** →
**Da**.

To odjednom stavi module Mod Studija, izgradi tvoj svijet i stavi ga u igru. Traje od par sekundi
do par minuta; donja traka pokazuje dokle je stigao.

(Ako `.fl26pack` ispustiš na **Uvezi svijet**, dogodi se isto: nakon prozora **Dodaj paket liga**
paket uđe u tvoj svijet i **Izgradi i instaliraj** krene sam.)

**Trebaš vidjeti:** prozor **Build gotov** s kvačicama (Svijet izgrađen, Lige i klubovi, Moduli
instalirani i uključeni, U igri). Klikni **Gotovo**. U okviru dolje na kartici Gradnja nema reda
koji počinje s `error:`.

---

## Korak 4. Pokreni igru

Klikni zeleni gumb **Pokreni igru** gore desno (ili **Igra → Pokreni igru**). Pričekaj izbornik
igre.

## Korak 5. Pokreni NOVU Master Ligu

1. **Master League** → **New game** (ne Continue: stara karijera ne dobije nove lige).
2. Na **Select Team** listaj: nove lige su na popisu, pod svojim državama.
3. Izaberi klub i igraj.

Nove lige su i u **Kick Off** → League, i u **Database → Competition Info**.

Svaki svijet ima svoje karijere. Kad u igru staviš drugi svijet, Mod Studio tvoje karijere
skloni uz svijet kojem pripadaju i vrati ih kad je taj svijet opet u igri. Ništa se ne briše.

## Korak 6. Neka Mod Studio provjeri je li uspjelo

1. Ugasi igru.
2. U Mod Studiju: **2. Moj svijet** → kartica **Gradnja** → **Korak po korak i Izvezi svijet** →
   **4. Nakon pokretanja: provjeri**.

**Trebaš vidjeti:** za svaki modul red koji kaže koliko je liga pročitao iz svijeta, a na kraju
`the world works as built`. Red koji kaže `not loaded` ili `did NOT read the world file`, i zadnji
red `something is wrong -- see the lines above`, kažu ti što ne valja.

---

## Ako nešto ne valja

| Što vidiš | Što napraviti |
|---|---|
| `error: nema tablica igre -- Postavke > Raspakiraj tablice igre` | **5. Postavke → Raspakiraj tablice igre**. |
| Nema novih liga na Select Team | Jesi li pokrenuo **novu** Master Ligu? Onda **4. Nakon pokretanja: provjeri** ([Korak 6](#korak-6-neka-mod-studio-provjeri-je-li-uspjelo)). Ako u logu piše `world file -- 0 leagues`, tvoj svijet je bio prazan: opet dodaj paket (Način C) i opet izgradi. |
| Svijet je izgrađen s `0 leagues, 0 clubs` | Isto: tvoj svijet nije imao liga. Prvo dodaj lige, pa izgradi. |
| `sider.log is older than the world switched on -- start the game to the main menu, then check again` | Provjera je pokrenuta prije nego si pokrenuo igru. Pokreni je do glavnog izbornika, ugasi je i opet stisni **4. Nakon pokretanja: provjeri**. |
| **Izgradi i instaliraj** je siv | Otvoren je gotov svijet iz zipa (Način A). Ne treba Build. Za svoje lige prvo klikni **Aktiviraj** na kartici svog svijeta u **2. Moj svijet**. |
| Moja stara karijera je nestala | Čuva se uz svijet u kojem je napravljena. Klikni **Aktiviraj** na kartici tog svijeta u **2. Moj svijet** i vrati se. |
| Svi novi igrači imaju isto lice | **1. Početna → Instaliraj sada** (kad Početna kaže da moduli fale ili su stariji), ili **2. Moj svijet → Gradnja → Korak po korak i Izvezi svijet → 0. Postavi module**: donosi paket lica. Pa opet pokreni igru. |
| Igra se ruši pri pokretanju | Pokreni je još jednom preko launchera (pad u prvih 10 sekundi se događa i bez modova). Ako se i dalje ruši: **Igra → Pokreni igru bez modova (sigurni način)...** i pitaj na Discordu. |
| Hoćeš sve vratiti kako je bilo | **Uvezi svijet** (**2. Moj svijet → Više ▾ → Uvezi zip svijeta**) → označi ga pod **U igri sada** → **Ukloni** vadi instalirani svijet. **4. Alati → Točke vraćanja → Vrati Sider kakav je bio prije Mod Studija...** (i u izborniku **Igra**) vraća svaku datoteku koju je Mod Studio promijenio i vadi ono što je donio. Ništa se ne briše: čuva se u `SiderAddons\ModStudio\reset-<time>`, a **Poništi zadnje vraćanje** to vraća. |

**Kad tražiš pomoć:** na [Discordu](https://discord.gg/StQqtk3G3M) pošalji sliku onoga što vidiš i
svoj `sider.log` (**Igra → Otvori sider.log**, ili `SiderAddons\sider.log` u mapi igre).
