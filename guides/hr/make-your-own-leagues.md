# Napravi svoje lige i pakete: svaki klik, redom

> [English](../en/make-your-own-leagues.md) · **hrvatski** · [español](../es/make-your-own-leagues.md) · [português](../pt/make-your-own-leagues.md)

> Drugi vodič korak po korak: [Instaliraj gotov paket](install-a-pack.md)
> · sve stranice i opcije objašnjene: [mod-studio-guide.md](mod-studio-guide.md)
> · pitanja: [faq.md](../../docs/faq.md) (na engleskom) · pomoć: [Discord](https://discord.gg/StQqtk3G3M)

Ova stranica te vodi od ničega do tvojih vlastitih liga u igri: pravih liga s pravim klubovima i
igračima iz **NewLife baze** (NewLife Database), postavljenih kako želiš, izgrađenih, odigranih i
podijeljenih s drugima. Kaže što kliknuti, točno ime svakog gumba i polja kako ga Mod Studio
pokazuje, i što trebaš vidjeti nakon svakog koraka. Radi korake redom. Ako vidiš nešto drugo
nego što korak kaže, stani tu i pogledaj u [Ako nešto ne valja](#ako-nešto-ne-valja).

Vodič piše engleske nazive gumba, kako ih Mod Studio pokazuje. (Prozor možeš prebaciti na
hrvatski: gore **Language** → Hrvatski.)

Tri riječi koje ćeš stalno sretati:

- **Recept**: tvoj popis liga i sve što si za njih postavio. Mijenjaš ga na stranicama
  **LEAGUE BUILDER**. To je samo plan: ništa ne stiže u igru dok ne stisneš **Build**.
- **Svijet**: ono što Build napravi od recepta, mapa čije ime počinje s `_FL26`
  (`_FL26MyWorld` ako ga ne promijeniš). Igra ga čita dok je uključen.
- **Build**: gumb koji od recepta napravi svijet i stavi ga u igru.

**Sadržaj**

- [Prije početka: postavljanje jednom](#prije-početka-postavljanje-jednom)
- [Korak 1. Nabavi NewLife bazu](#korak-1-nabavi-newlife-bazu)
- [Korak 2. Otvori je na stranici NewLife Database](#korak-2-otvori-je-na-stranici-newlife-database)
- [Korak 3. Izaberi lige](#korak-3-izaberi-lige)
- [Korak 4. Izaberi klubove lige](#korak-4-izaberi-klubove-lige)
- [Korak 5. Dodaj u recept](#korak-5-dodaj-u-recept)
- [Korak 6. Stranica Leagues: sve postavke lige](#korak-6-stranica-leagues-sve-postavke-lige)
- [Korak 7. Primjer: država s dva ranga](#korak-7-primjer-država-s-dva-ranga)
- [Korak 8. Stranica New clubs: imena, grbovi, dresovi, klubovi iz igre](#korak-8-stranica-new-clubs-imena-grbovi-dresovi-klubovi-iz-igre)
- [Korak 9. Stranica Players](#korak-9-stranica-players)
- [Korak 10. Granice koje zaustave Build](#korak-10-granice-koje-zaustave-build)
- [Korak 11. Spremi recept](#korak-11-spremi-recept)
- [Korak 12. Build](#korak-12-build)
- [Korak 13. Igraj: NOVA Master Liga, pa provjera](#korak-13-igraj-nova-master-liga-pa-provjera)
- [Korak 14. Kad kasnije nešto mijenjaš](#korak-14-kad-kasnije-nešto-mijenjaš)
- [Korak 15. Podijeli što si napravio](#korak-15-podijeli-što-si-napravio)
- [Ako nešto ne valja](#ako-nešto-ne-valja)

---

## Prije početka: postavljanje jednom

Prvo jednom odradi korake 1 do 5 drugog vodiča:
[ugasi igru](install-a-pack.md#korak-1-ugasi-igru),
[skini Mod Studio](install-a-pack.md#korak-2-skini-mod-studio),
[reci mu gdje ti je igra](install-a-pack.md#korak-3-reci-mu-gdje-ti-je-igra),
[raspakiraj tablice igre](install-a-pack.md#korak-4-raspakiraj-tablice-igre) i
[instaliraj module Mod Studija](install-a-pack.md#korak-5-instaliraj-module-mod-studija).
Onda se vrati ovamo.

Drži igru ugašenu cijelo vrijeme dok radiš u Mod Studiju.

---

## Korak 1. Nabavi NewLife bazu

NewLife baza je zasebno preuzimanje s pravim klubovima i igračima: imena, datumi rođenja,
pozicije, ocjene na ljestvici igre i boje klubova. Nije na GitHubu.

1. Otvori naš [Discord](https://discord.gg/StQqtk3G3M) i idi u kanal **#newlife**.
2. Skini dijelove koje želiš. Ima jedan dio po kontinentu (veliki kontinent dolazi u više
   dijelova), plus *Free agents*. Svaki dio je `.zip` datoteka s imenom `NewLife-...zip`.
3. Napravi mapu za njih, npr. `Documents\NewLife`, i stavi **sve** dijelove u tu jednu mapu.
4. **Ne raspakiravaj ih.** Mod Studio čita zipove takve kakvi jesu. (Windowsov preglednik zipova
   ih ionako ne može otvoriti; to je normalno.)

Kad izađe novija verzija NewLifea, stavi njene dijelove u **novu** mapu. Nikad ne miješaj dvije
verzije u jednoj mapi.

## Korak 2. Otvori je na stranici NewLife Database

1. Lijevo, pod **LEAGUE BUILDER**: klikni **NewLife Database**.
2. Klikni **Open NewLife Database...** gore.
3. Izaberi mapu iz Koraka 1 (mapu, ne zip u njoj) i potvrdi.
4. Pričekaj par sekundi dok čita.

**Trebaš vidjeti:** iznad popisa verziju NewLifea i mapu, a ispod njih `Parts:` s dijelovima koje
je našao. Ispod toga dugačak popis liga.

Mod Studio pamti mapu: idući put je stranica sama otvori.

**Traženje.** Okvir iznad popisa, *Search leagues or countries*, ostavi samo lige čije ime ili
država sadrži ono što upišeš. Upiši recimo `brazil` ili `liga`. Isprazni okvir da opet vidiš sve.

**Stupci.** Klikni naslov stupca da složiš popis po njemu, klikni opet da obrneš redoslijed.

| Stupac | Što ti kaže |
|---|---|
| **League** | Ime lige. `*` iza imena znači da si joj mijenjao klubove (Korak 4). |
| **Country** | Gdje ide u igri. |
| **Clubs** | Koliko će klubova imati, kako si sad postavio. |
| **In game** | Koliko njenih klubova igra već ima (oni zadržavaju svoja imena, grbove, dresove i igrače). |
| **Players** | Koliko igrača njeni klubovi imaju u NewLifeu. |
| **Level** | Koliko je liga jaka. Veće je jače. |
| (zadnji stupac) | Zašto se siva liga ne može dodati. Prazno za ligu koju možeš dodati. |

**Zašto su neke lige sive.** Siva liga se ne može dodati, a zadnji stupac kaže zašto:

- `a league takes 10 to 24 clubs`: liga u igri ima od 10 do 24 kluba, nove i one iz igre
  zajedno. Ova ih ima manje ili više. Još je možeš popraviti u Koraku 4 (dodaj klubove ili ih
  ostavi vani) dok ne stane.
- `the game's own league: Bring the game's leagues to this season`: igra već ima ovu ligu
  (Premier League, Championship ...). Ne dodaje se drugi put. Gumb
  **Bring the game's leagues to this season...** gore umjesto toga daje ligama same igre klubove i
  kadrove ove NewLife sezone; vidi
  [8.4 u cijelom vodiču](mod-studio-guide.md#84-newlife-database-pravi-klubovi-i-igrači).

Ako stranica kaže da Mod Studio nema tablica igre i ponudi da otvori Settings: klikni **Yes** i
napravi [Raspakiraj tablice igre](install-a-pack.md#korak-4-raspakiraj-tablice-igre).

## Korak 3. Izaberi lige

1. Klikni ligu na popisu da je označiš. Njen redak se istakne.
2. Za više njih: drži **Ctrl** i klikni svaku. (Ili klikni prvu, drži **Shift** i klikni
   zadnju da uzmeš sve između.)

**Trebaš vidjeti:** dolje na stranici red poput
`New clubs in the recipe: 0 of the 793 the game takes.  Selected: 18 more.`

- **Prvi** broj je koliko novih klubova tvoj recept već ima.
- **Drugi** je koliko novih klubova ukupno stane u igru. Mod Studio ga izračuna iz tablica tvoje
  igre, pa na drugoj verziji igre može biti malo drukčiji.
- **Selected** je koliko bi novih klubova dodale lige koje si izabrao.

Ako recept i odabir zajedno prelaze ono što igra prima, **Add to the recipe** ostaje siv: izaberi
manje liga.

## Korak 4. Izaberi klubove lige

Ovaj korak nije obavezan. Preskoči ga da uzmeš ligu točno onakvu kakvu je NewLife ima.

Označi **jednu** ligu (samo jednu). Popis desno pokazuje njene klubove: **Club** i **Players**
(koliko igrača joj NewLife daje). Klub koji igra već ima je siv, s `in the game` umjesto broja.

- **Ostavi klub vani:** klikni njegovu kvačicu da je makneš.
- **Dovedi klub iz druge lige** (recimo prva liga ove sezone je prošlogodišnja s dva kluba koja
  su ušla): klikni **Add a club from another league...** ispod popisa.
  1. Otvori se prozor sa svim klubovima NewLife dijelova koje si otvorio, svaki sa svojom ligom u
     zagradi.
  2. Upiši u okvir za traženje da nađeš klub ili ligu.
  3. Označi jedan ili više klubova. Red ispod popisa kaže koliko si ih izabrao.
  4. Klikni **OK**.

  **Trebaš vidjeti:** klub na kraju popisa, s `from <its league>` pored.

**Trebaš vidjeti:** redak lige na popisu sad ima `*`, a broj **Clubs** se promijenio. Siva liga
koja sad ima 10 do 24 kluba postane normalna.

Klub može igrati samo u jednoj ligi. Ako ga dodaš u dvije, Mod Studio te zaustavi u Koraku 5.

## Korak 5. Dodaj u recept

S označenom ligom ili ligama klikni **Add to the recipe** gore.

**Trebaš vidjeti:** zeleni red ispod naslova stranice. Što koji red znači:

| Zeleni red | Što znači |
|---|---|
| `Added: <leagues>. Change them on Leagues, New clubs and Players, then Build.` | Lige su u tvom receptu, svaka kao prvi rang svoje države, svi sa svima dvaput. U igri još nema ništa. |
| `<clubs> also play in a competition of the game: on New clubs pick each one and use Club of the game to choose the club that takes its place there.` | Ovi klubovi tvoje nove lige su klubovi koje igra već ima, a igraju i negdje u igri (liga, kup, Europska liga ...). Klub igra samo u jednoj ligi, pa njegovo staro mjesto treba drugi klub. Taj klub biraš u [Koraku 8](#klubovi-koje-igra-već-ima). Dok to ne napraviš, Build staje s greškom koja imenuje klub. |
| `<n> players stay at their game club (their club would have too few players).` | Igrači koje igra već ima inače prelaze u NewLife klub. Ovi ostaju, da njihov stari klub zadrži barem 18 igrača. Ništa ne trebaš raditi. |
| `<n> players are not added: another league already has them.` | Liga koju si dodao ranije već je uzela te igrače. Ništa ne trebaš raditi. |

Ako prozor s greškom kaže `<club> would play in two leagues (<league> and <league>).`, makni
kvačicu tom klubu u jednoj od dvije lige (Korak 4) i probaj opet.

Želiš lige s drugih kontinenata? Označi i njih i opet klikni **Add to the recipe**. Svaki klik
dodaje; nikad ne miče ono što je već tamo.

---

## Korak 6. Stranica Leagues: sve postavke lige

1. Lijevo: klikni **Leagues**.
2. Iznad popisa klikni **Ours**: popis pokazuje samo lige tvog recepta. (**All** pokazuje sve
   lige, i one iz igre; **Changed** lige iz igre koje si promijenio.) Lige su složene po
   kontinentima.
3. Klikni svoju ligu.

**Trebaš vidjeti:** desno `OURS`, ime i logo lige, i redove **Country**, **Clubs**, **Format**,
**Division**, **Up / down**, **Europe** i **League ID** (`not built yet` do prvog Builda), pa
grbove njenih klubova. Ispod njih gumbe **Edit league...**, **Add lower tier**, **Clubs and
names**, **Players** i **Remove**.

Ligu možeš povući gore ili dolje po popisu da složiš lige jednog kontinenta.

4. Klikni **Edit league...**.

**Trebaš vidjeti:** prozor **League** s poljima ispod, odozgo prema dolje. Sivo polje se ne može
koristiti uz ono što si postavio iznad njega (npr. kup na drugom rangu). **?** pored **OK**
ukratko objašnjava prozor. Ništa nije obavezno: zadane postavke rade, a **Cancel** ništa ne
mijenja.

| Polje | Što je to i što napraviti |
|---|---|
| **Name** | Ime lige u igri. Dvije lige ne mogu imati isto ime. Drži ga ispod otprilike 38 znakova: duže ime se u popisu liga Kick Offa vidi kao prazan red. |
| **Country** | Upiši par slova i izaberi s popisa (`korea` nađe obje Koreje). Daje zastavu i mjesto gdje je liga na popisu u igri. |
| **Clubs** | 10 do 24. Za NewLife ligu ostavi kako jest: manji broj izbaci zadnje klubove, veći doda izmišljene klubove na kraj. |
| **Clubs in no league** | Ostavi na `(no -- a league)`. Ostali izbori (*Other European teams* ...) su za jedan klub, ili nekoliko njih, bez lige oko sebe; idu u igrine grupe "Other ...", a većina polja ispod postane siva. [Više](mod-studio-guide.md#8-league-builder-nove-lige-klubovi-i-igrači). |
| **Format** | Izaberi jedno: **everyone plays everyone, times:** i broj (1 do 4; 2 je doma i u gostima); **splits in two (Scottish style)**, s `first` *n* `x, then groups` *6/6* *n* `x` (skupine zajedno moraju dati broj klubova); ili **Apertura and Clausura, then playoffs of:** *8 clubs*, *4 clubs* ili *no playoffs* (dva kratka turnira u sezoni, najviše 18 klubova). |
| **Division** | `(top division)` = najbolja liga svoje države. Za drugi rang izaberi ligu jedan rang iznad: tvoje nove lige su na vrhu popisa, pa lige iz igre s brojem u zagradi. `= division 2` pored pokazuje rang. Liga koja već ima ligu ispod sebe je siva (`-- under it: ...`): jedna liga može imati jednu ligu ispod sebe. Vidi [Korak 7](#korak-7-primjer-država-s-dva-ranga). |
| **Exhibition only -- not in Master League** | Ostavi isključeno. Uključeno: liga je samo za Kick Off i prijateljske utakmice (legende, povijesna sezona); nikad ne igra sezonu Master Lige, a rang, kupovi i Europa postanu sivi. Ne počinji karijeru s nekim od njenih klubova. |
| **Season** | Samo prvi rang: **August to May** (kao Europa) ili **February to December** (kao Brazil ili Japan). Rang ispod prati ligu iznad. February to December još ne može imati podjelu, Aperturu/Clausuru ni kupove države. |
| **Up / down** | 1 do 6: koliko klubova na kraju sezone zamijeni mjesta s ligom iznad. Znači nešto samo za rang ispod drugog. |
| **Logo** | **Pick picture...** PNG ili JPG za ligu (najbolje izgleda PNG s prozirnom pozadinom). **Clear** ga makne. Prazno: `(made for you)`, logo se nacrta pri Buildu. |
| **Country flag** | Tvoja slika zastave države. Prazno: `(the game's own)`. Ostavi prazno osim ako igra nema dobru zastavu. |
| **Cup** | Samo prvi rang. Označi **National cup** da država dobije kup na ispadanje (ova liga i rang ispod nje). Okvir pored je ime kupa; prazno = ime lige + Cup. |
| **Super cup (champion v cup winner)** | Jedna utakmica krajem srpnja. Treba označen **National cup**. |
| **League cup** | Samo prvi rang. Drugi kup na ispadanje, kao engleski Carabao Cup: ova liga i ona ispod, do 44 kluba. Okvir je njegovo ime; prazno = ime lige + League Cup. |
| **Cup logos** | Po slika za **Cup**, **Super cup**, **League cup** i **Playoffs**. Prazno: amblem s inicijalima kupa. |
| **Formation** | Kako se klubovi lige postavljaju. Izaberi jednu s popisa, ili ostavi prazno za zadanu 4-2-3-1 iz igre. Pojedini klub može imati svoju (Korak 8). |
| **Europe** | Samo prvi rang: koje mjesto u tablici ide u koje kontinentalno natjecanje. Gumb koji počinje s **Top flight:** upiše uobičajena mjesta za kontinent države (za Europu: `Top flight: 1st UCL qualifying, 2nd UEL, 3rd UECL`). **Add place** doda red: izaberi **League position** (ispod 1 glasi **Cup winner**) i **Competition**. **✕** na redu ga makne, **Clear** makne sve. Za drugi rang ostavi prazno. |

5. Klikni **OK**.

**Trebaš vidjeti:** prozor se zatvori, a redovi desno pokazuju što si postavio.

NewLife liga dolazi bez europskih mjesta. Ako želiš njene klubove u Ligi prvaka i ostalom,
postavi **Europe** sad; inače te **1. Check the plan** podsjeti s
`no European places: the new leagues send nobody to Europe`.

Značenje svakog formata, kupa i europskog mjesta u detalje (datumi, pretkola, veličine kupova):
[poglavlje 8 cijelog vodiča](mod-studio-guide.md#8-league-builder-nove-lige-klubovi-i-igrači)
i [8.2](mod-studio-guide.md#82-izgradi-uključi-igraj).

**More ▾** (gore na stranici Leagues) ima alate za cijeli svijet: **Pre-season cups**,
**Cups of the game's countries**, **European places of the game's leagues**, **UEFA ranking**,
**South American places**, **Competition names** (nova imena i logotipi za kupove i kontinentalna
natjecanja) i **World name and recipe...** (ime mape svijeta; mora počinjati s `_FL26`). Za prvi
svijet ne trebaš nijedan od njih.

**Liga bez NewLife klubova.** **Add league** gore na stranici Leagues otvori isti prozor
**League** za ligu napravljenu od nule: daj joj **Name**, **Country** i broj **Clubs**, a Build
napravi klubove s punim kadrovima i trenerom. Imena im daješ na **New clubs** (Korak 8), gdje
**NewLife club...** u nju može staviti i prave klubove.

## Korak 7. Primjer: država s dva ranga

Recimo da tvoji NewLife dijelovi imaju prvu i drugu ligu jedne države, ovdje nazvane *First
League* i *Second League*. Želiš ulazak i ispadanje između njih.

1. **NewLife Database**: označi *First League* i klikni **Add to the recipe**. (Prvo onu gornju.)
2. Označi *Second League* i klikni **Add to the recipe**.

   **Trebaš vidjeti:** zeleni red `Added:` svaki put. Obje su sad prvi rang iste države, što još
   nije ono što želiš.

3. **Leagues** → **Ours** → klikni *Second League* → **Edit league...**.
4. **Division**: otvori popis i izaberi *First League* (tvoje lige su na vrhu).

   **Trebaš vidjeti:** `= division 2` pored. **Cup**, **League cup**, **Season** i gumb
   **Top flight** postanu sivi: to pripada prvom rangu.

5. **Up / down**: koliko klubova ide gore i dolje između njih, npr. `3`.
6. **Europe**: ako ima redova, klikni **Clear**. Drugi rang nikoga ne šalje u Europu.
7. Klikni **OK**.

   **Trebaš vidjeti:** desno **Division** `2  (below First League)` i **Up / down**
   `3 with First League above`. Klikni *First League*: njen **Up / down** kaže
   `3 with Second League below`.

8. Klikni *First League* → **Edit league...** i postavi ono što pripada prvom rangu: **Europe**
   (gumb **Top flight**), a ako želiš i **National cup**, **Super cup** i **League cup**. Klikni
   **OK**.

Treći rang radi isto: njegov **Division** je *Second League*. Igra ide do 7. ranga.

**Jedna liga ispod jedne lige.** Dvije lige ne mogu stajati ispod iste lige (recimo tri
regionalne skupine ispod jedne druge lige). Druga je siva na popisu **Division**.

**Ispod lige iz igre.** Tvoja nova liga može ići i ispod lige koju igra ima: izaberi ligu iz
igre u **Division** (one s brojem u zagradi). Tada s njom igra ulazak i ispadanje.

**Bez NewLifea.** Na **Leagues** klikni svoju prvu ligu, pa **Add lower tier**: otvori se prozor
**League** s već upisanom državom, klubovima, formatom i rangom. Daj joj **Name** i klikni **OK**.

---

## Korak 8. Stranica New clubs: imena, grbovi, dresovi, klubovi iz igre

1. Lijevo: klikni **New clubs** (ili **Clubs and names** na stranici Leagues).
2. Gore, **League**: izaberi jednu od svojih liga.

**Trebaš vidjeti:** njene klubove sa stupcima **#**, **Name**, **Short name**, **Team ID**
(`at Build` do prvog Builda), **Crest** i **Players changed**. NewLife klubovi već imaju imena,
kratka imena i grbove. Klub bez imena pokazuje `<league> 01`, `<league> 02` ... sivo.

### Ime, grb, dresovi, trener

1. Dvaput klikni klub (ili ga označi i klikni **Edit club**).

**Trebaš vidjeti:** prozor **Club** s:

| Polje | Što napraviti |
|---|---|
| **Name** | Ime kluba. Slova s kvačicama (Željezničar) su u redu. |
| **Short name** | Tri slova ili znamenke. Prazno = napravi se od imena. Č, Ž, Đ ... postanu C, Z, D, kao u igri. |
| **Crest** | **Pick picture...** PNG ili JPG. **Clear** ga makne. Klub bez grba dobije grb s brojem. |
| **Home stadium** | Samo kad je instaliran Stadium Server: **Choose stadium...** iz tvog paketa stadiona, ili **Game's own**. |
| **Manager** | Ime trenera. Prazno: ime izmišljeno od igrača države kluba. |
| **Manager picture** | PNG ili JPG; igra ga pokazuje u Edit modu i Master Ligi. |
| **Formation** | `As the league (...)` zadržava formaciju lige; ili izaberi jednu za ovaj klub. |
| **Home kit colours**, **Away kit colours** | Klikni dva kvadratića boje (dres, druga boja) da izabereš boje; **None** = Build sam izabere dres. Build klubu da dres iz igre najbliži tim bojama. |

2. Klikni **OK**.

**Trebaš vidjeti:** novo ime i grb na popisu.

**Dresovi.** Novi klub posudi dres kluba iz igre u svojim bojama. Dvije opcije na stranici
**Build** to mijenjaju: **Make kits for the new clubs** (zadano uključeno, treba instaliran Kit
Server: svaki novi klub dobije domaći, gostujući, treći i golmanski dres napravljen u svojim
bojama, sa svojim grbom) i **Kits you can edit in the game** (svaki novi klub nosi jednostavan
dres koji možeš mijenjati u Edit modu igre).
[Više u cijelom vodiču](mod-studio-guide.md#8-league-builder-nove-lige-klubovi-i-igrači).

**Puno klubova odjednom.** **More ▾** ima **Paste names...** i **Load names from file...** (jedno
ime po redu, redom) i **Import crests...** (mapa sa slikama, spojenim s klubovima po imenu
datoteke). Ima i **Insert club**, **Remove club**, **New club here** i **Move to another
league...**.

### Klubovi koje igra već ima

NewLife liga može uključivati klubove koje igra već ima. Na popisu se vide s imenom iz igre,
svojim **Team ID** i `(the game's)` pod **Crest**. Ako je zeleni red u Koraku 5 rekao da *also
play in a competition of the game* (igraju i u natjecanju igre), napravi ovo za **svaki** od njih:

1. Klikni klub na popisu.
2. Klikni **Club of the game...**.

**Trebaš vidjeti:** prozor **Club of the game**, s označenim klubom i ispod popisa red poput
`<club> plays in <competitions>. Every one of those competitions keeps its
number of clubs: pick who takes its place there.`

3. Izaberi tko preuzima njegovo staro mjesto:
   - **Its place goes to a club of the game that plays in nothing:** i izaberi klub s popisa
     ispod; ili
   - **Its place goes to a new club, named:** i upiši ime. Build napravi taj klub.
4. Ako klub igra kontinentalno natjecanje (Liga prvaka, Libertadores ...), tu je i
   **It keeps its places in continental competitions**. Označeno, nastavlja igrati to natjecanje
   i nitko tamo ne mora preuzeti njegovo mjesto.
5. Klikni **OK**.

Isti gumb stavlja bilo koji klub iz igre na mjesto u tvojoj ligi: označi mjesto,
**Club of the game...**, traži po imenu, kratkom imenu ili ID-u kluba (**Only clubs in no league**
suzi popis). **New club here** (u **More ▾**) vraća mjesto novom klubu.

**NewLife club...** stavlja NewLife klubove, s njihovim kadrovima, na označeno mjesto i mjesta iza
njega: označi jedan ili više u prozoru koji se otvori, pa **OK**. Tako liga koju si napravio
ručno dobije prave klubove.

## Korak 9. Stranica Players

NewLife klubovi dolaze s punim kadrovima, pa ovu stranicu ne moraš dirati. Tu je ako želiš
promijeniti kadar.

1. Lijevo: klikni **Players** (ili označi klub na New clubs i klikni **Players**).
2. Gore izaberi **League** i **Club**. (Ili upiši u *Find a club...*.)

**Trebaš vidjeti:** kadar sa stupcima **Order**, **No.**, **Name**, **Pos**, **Age**,
**Rating**, **Foot**, **Changed** i **Player ID**, a ispod prvih jedanaest na terenu. Klikni
igrača: desna strana ga pokazuje, na karticama **Basics**, **Positions**, **Abilities** i
**Skills**.

- Promijeni ime, broj, poziciju, ocjenu ili sposobnost desno. Promjena se odmah pamti.
- **Order up** / **Order down**: redoslijed u kadru. Prvih jedanaest počinje utakmicu. Ili povuci
  igrača na mjesto na terenu. **Best eleven** stavi najjačeg igrača na svako mjesto.
- **Sign players...** dovodi igrače iz drugih klubova; **Transfer to...** šalje označenog igrača
  u drugi klub.
- **Undo changes to this player** i **Undo all changes of this club** vraćaju natrag.

Sve na ovoj stranici je u [Igrači u cijelom vodiču](mod-studio-guide.md#igrači).

---

## Korak 10. Granice koje zaustave Build

| Granica | Gdje je vidiš |
|---|---|
| Novih klubova ukupno: broj u redu `New clubs in the recipe: X of the Y the game takes.` | Stranica NewLife Database: **Add to the recipe** ostaje siv. Build: `error: <n> new clubs, but the game has room for <m> more (a full squad each)`. |
| 10 do 24 kluba u ligi | NewLife Database: siva liga, `a league takes 10 to 24 clubs`. New clubs: `A league has 10 to 24 clubs.` |
| Novih liga po svijetu (39 u našim testovima) | Build: `error: <n> leagues, but the game has room for <m> ...` |
| Jedna liga ispod jedne lige | Popis **Division**: sivo. Build: `... are all under ...; the game follows one link down from a league ...` |
| Rangovi do 7. | Build: `error: <league>: division 8 -- the rank field stops at 7`. |
| 2 podijeljene lige po svijetu; jedna podjela ili Apertura/Clausura po državi | Build: `error: at most 2 split leagues for now ...`, `... only one league of a country can be split or Apertura/Clausura`. |
| Klub samo u jednoj ligi | Build: `error: <club> is in <league> and in <league>: a club plays in one league`. |
| Klub iz igre koji negdje igra treba zamjenu | Build: `error: <league>, club <n>: <club> plays in <...> -- pick the club that takes its place there`. Napravi [Klubovi koje igra već ima](#klubovi-koje-igra-već-ima). |

Svi brojevi: [8.3 Granice](mod-studio-guide.md#83-granice).

## Korak 11. Spremi recept

1. Gore: **File → Save recipe**.
2. Prvi put se otvori prozor **Save recipe as...**. Predloži ime svijeta, npr.
   `_FL26MyWorld.json`. Izaberi mapu koju ćeš opet naći (npr.
   `Documents\FL26 Mod Studio\recipes`) i klikni **Save**.

**Trebaš vidjeti:** dolje u prozoru `Recipe saved: <file>`.

Nakon toga **File → Save recipe** sprema u istu datoteku bez pitanja. **File → Save recipe
as...** spremi kopiju pod drugim imenom. **File → Open recipe...** opet otvori spremljeni recept
(upozori ako imaš nespremljenih promjena). **File → New recipe** počne prazan.

Build i sam čuva kopiju recepta, a Mod Studio pri pokretanju otvara zadnji recept, pa ono što si
izgradio nikad ne propada. Svejedno spremi: tvoja vlastita datoteka je ona koju možeš naći i
kopirati.

## Korak 12. Build

1. Lijevo: klikni **Build**.

**Trebaš vidjeti:** veliki plavi gumb **Build and install**, red **0. Install the
modules**, **1. Check the plan**, **2. Build the world**, **3. Switch it on**, **4. After a
start: check** i **Export the world...**, dvije kartice (**European cups** i **New clubs**) s
opcijama, red poput `World _FL26MyWorld: not built yet · builder modules: installed`, i okvir za
log dolje.

2. Prvo klikni **1. Check the plan**. Ne mijenja ništa; samo čita tvoj recept.

**Trebaš vidjeti:** u okviru red `world _FL26MyWorld: 2 new leagues, ...` i red za svaku ligu s
njenim klubovima, rangom i formatom (`18 clubs x2` je 18 klubova, svi sa svima dvaput;
`division 2  below ... (3 up/down)` je drugi rang), i njen `European places:`. Red koji počinje
s `error:` kaže što prvo popraviti; vidi tablicu na kraju.

3. Klikni **Build and install**. Pita `Build _FL26MyWorld and make it the live world? ...`:
   klikni **Yes**.

   Ako su tablice igre starije od igre, prvo pita da ih opet raspakira: klikni **Yes** (oko
   minute).

   To odjednom instalira module, napravi svijet i upali ga. Traje od par sekundi do par minuta.

**Trebaš vidjeti:** prozor **Build finished** s kvačicom na svakom redu: **World built**,
**Leagues and clubs** (`2 leagues · 36 new clubs`), **Modules installed and switched on**,
**Switched on in sider.ini** i **Start the game to play it**. Pod **Before you play**:
`Start a new Master League career: a career saved before keeps the old world.` Klikni **Done**.

Ako kaže **An Edit save from before this Build is in the game's save folder**: klikni **Move
the Edit save aside**. Stari Edit save skriva nova imena i kadrove.

**Korak po korak umjesto velikog gumba** (isti rezultat):

1. **1. Check the plan**: kao gore.
2. **2. Build the world**: izgradi ga. Ako svijet postoji, pita `... exists. Build it again?`:
   **Yes**. Log završi s `Next: 3. Switch it on, then start the game.`
3. **3. Switch it on**: pita `Make _FL26MyWorld the live world in sider.ini?`: **Yes**. Log
   završi s `Start the game, then 4. check.`

**Što znače redovi u logu:**

| Red | Značenje |
|---|---|
| `installing the modules ...`, `modules: ... copied, ... already there` | Moduli Mod Studija se stavljaju na mjesto. |
| `world ...: N new leagues, changes to ... of the game's leagues and ... of its clubs` | Sažetak tvog recepta. |
| `<league>  reg ...  comp ...  division 1  18 clubs x2` | Jedna liga: njeni ID-evi u igri, rang i format. |
| `European places: 1st Champions League qualifying, ...` | Kamo idu njeni najbolji klubovi. |
| `no European places: the new leagues send nobody to Europe` | Upozorenje, ne greška: postavi **Europe** na prvom rangu ako to želiš. |
| `building ...` | Svijet se zapisuje. |
| `livecpk: _FL26MyWorld (... files), sider.ini loads it` | Svijet je uključen. |
| `error: ...` | Build je stao i ništa se u igri nije promijenilo. Popravi što kaže (tablica na kraju) i opet Build. |

Opcije na karticama (**Include the Conference League**, **Country cup draw**, **Make kits
for the new clubs** ...) objašnjene su u [8.2](mod-studio-guide.md#82-izgradi-uključi-igraj).
Zadane postavke su u redu.

## Korak 13. Igraj: NOVA Master Liga, pa provjera

1. Klikni zeleni gumb **Play** gore desno (ili **Game → Start the game**).
2. U igri: **Master League** → **New game**. Ne Continue: karijera spremljena prije zadržava
   stari svijet.
3. Na **Select Team** listaj: tvoje lige su na popisu, pod svojim državama.
4. Izaberi klub i igraj.

Onda neka Mod Studio provjeri je li igra preuzela svijet:

1. Ugasi igru (ili je barem jednom pokreni do glavnog izbornika).
2. U Mod Studiju: **Build** → **4. After a start: check**.

**Trebaš vidjeti:** za svaki modul red koji kaže koliko je liga pročitao iz datoteke svijeta, a na
kraju `the world works as built`. Red `not loaded` ili `did NOT read the world file`, i na kraju
`something is wrong -- see the lines above`, znače da nešto nije uspjelo: vidi tablicu na kraju.

## Korak 14. Kad kasnije nešto mijenjaš

1. Ugasi igru.
2. Otvori Mod Studio. Sam otvori tvoj zadnji recept (ili **File → Open recipe...**).
3. Promijeni što želiš na **NewLife Database**, **Leagues**, **New clubs** ili **Players**.
4. **File → Save recipe**.
5. **Build** → **Build and install** → **Yes**.

**Treba li ti nova karijera?** Da: pokreni novu Master Ligu nakon svake promjene koju izgradiš.
Karijera kad počne uzme vlastitu kopiju liga, klubova i kadrova, pa karijera u kojoj već jesi
zadržava stare. A karijera spremljena s jednim svijetom treba isti taj svijet da se učita, pa
drži svijet uključen dok je igraš.

**Novija verzija NewLifea.** Stavi njene dijelove u novu mapu, **Open NewLife Database...** na
toj mapi, pa klikni **Update my leagues to this version**. Svaka liga zadržava ime, rang, format,
europska mjesta i kupove; klubovi i kadrovi dolaze iz nove verzije (kvačica **Keep my clubs**
zadržava tvoj vlastiti sastav klubova). Opet Build i pokreni novu karijeru.
[Više](mod-studio-guide.md#84-newlife-database-pravi-klubovi-i-igrači).

**Izbaci ligu.** **Leagues** → **Ours** → klikni je → **Remove** → **Yes**. Njeni klubovi i
njihove promjene igrača idu s njom.

## Korak 15. Podijeli što si napravio

Postoje dva načina. Izaberi jedan:

| | Paket liga (`.fl26pack`) | Izvezeni svijet (`.zip`) |
|---|---|---|
| Što sadrži | Tvoje lige kao recept: klubovi, imena, grbovi, logotipi, kadrovi, lica, a ako želiš i dresovi i scoreboardi. | Svijet točno onakav kakvog si izgradio. |
| Druga osoba | Doda ga u svoj recept i izgradi, pa radi uz njene vlastite lige i druge pakete. | Instalira ga i igra. Ništa se ne gradi, ali zamijeni bilo koji drugi svijet koji ima uključen. |
| Kako ga instalira | [Način C iz Instaliraj gotov paket](install-a-pack.md#način-c-paket-liga-fl26pack) | [Način A iz Instaliraj gotov paket](install-a-pack.md#način-a-gotov-svijet-jedan-zip) |

### Paket liga

1. Lijevo: **League packages** → **Make a package...** (ili gore: **File → Make a league
   package...**).

**Trebaš vidjeti:** prozor **Make a league package**.

2. Upiši **Name** (obavezno), **Author**, **Version** (`1.0` za početak) i **Description**.
3. Pod **Leagues** označi lige koje idu unutra (**Select all** / **Select none**). Liga ispod
   druge lige mora ići s njom.
4. **Also my changes to the game's own leagues, clubs and players** (samo ako si nešto
   mijenjao): označi da i to ide unutra.
5. Pod **What goes in** sve je označeno: **Squads**, **Player faces and portraits**,
   **Crests and league logos**, **Managers**, **Kit colours**, **Kits**, **Scoreboards** i
   **Home stadiums**. Odznači što ne želiš dijeliti. Dresovi dodaju oko 10 MB po ligi, a
   scoreboard oko 7 MB.
6. Klikni **Save the package...**. Otvori se prozor za spremanje **Save the package** s imenom
   poput `<name>-1.0.fl26pack`. Izaberi mapu koju ćeš opet naći (Desktop, Documents ...) i klikni
   **Save**.

**Trebaš vidjeti:** `Saved <file>` s brojem liga, klubova i lica unutra. Ta jedna datoteka je ono
što dijeliš. Ako je preko 10 MB, Mod Studio to kaže: Discord je neće primiti, pa je podijeli preko
Google Drivea, Dropboxa, MEGA-e ili sličnog, ili odznači **Kits** i **Scoreboards**, ili napravi
jedan paket po ligi.

Više: [9. Paketi liga](mod-studio-guide.md#9-paketi-liga-podijeli-cijelu-ligu).

### Cijeli svijet (zip)

1. Prvo Build (Korak 12). Svijet mora biti izgrađen.
2. Lijevo: **Build** → **Export the world...**.
3. Otvori se prozor za spremanje s imenom svijeta kao imenom datoteke (`_FL26MyWorld.zip`), prvi
   put u tvojoj korisničkoj mapi (nakon toga u mapi koju si zadnju koristio). Izaberi mapu i klikni
   **Save**.

**Trebaš vidjeti:** nakon trenutka `Saved <file>` i koliko novih igrača dobije generirano lice.
Zip sadrži mapu svijeta, njegovu datoteku svijeta i upute (read-me).

Osoba koja ga instalira treba module Mod Studija s paketom lica (**Build → 0. Install
the modules**); bez njih svaki novi igrač izgleda isto. Upute u zipu to kažu.

Više: [9.1 Export the world](../en/mod-studio-guide.md#91-export-the-world-a-built-world-for-another-pc)
(na engleskom).

---

## Ako nešto ne valja

Poruke se pojave u prozoru s greškom, u zelenom ili crvenom redu ispod naslova stranice, ili u
logu Builda iza `error:`. `<...>` stoji umjesto imena ili broja.

| Što vidiš | Što napraviti |
|---|---|
| `no NewLife Database here: put the NewLife-....zip parts you downloaded in one folder (no need to unpack them) and open that folder` | Izabrao si krivu mapu, ili si raspakirao dijelove. Otvori mapu u kojoj su same datoteke `NewLife-...zip`. |
| `the parts in this folder are of different versions (...): keep one version's parts only` | Pomiješane su dvije verzije NewLifea. Ostavi u mapi dijelove samo jedne verzije. |
| `<file> is not a NewLife part (...) -- download it again` | Preuzimanje se pokvarilo. Skini taj dio ponovno. |
| Siva liga, `a league takes 10 to 24 clubs` | Dodaj klubove ili ih ostavi vani (Korak 4) dok nema 10 do 24. |
| Siva liga, `the game's own league: Bring the game's leagues to this season` | Igra je već ima. Koristi **Bring the game's leagues to this season...**. |
| **Add to the recipe** ostaje siv | Nije označeno ništa što se može dodati, ili bi odabir prešao granicu novih klubova (red na dnu). |
| `<club> would play in two leagues (<league> and <league>).` | Makni kvačicu klubu u jednoj od njih. |
| `<league> has no country the game knows.` | Ova liga se ne može dodati. |
| `A league needs a name and a country.` / `Pick the country from the list.` | U **Edit league...** upiši **Name** i izaberi **Country** s popisa umjesto da ga cijelog upisuješ. |
| `There is already a league called <name>.` | Daj ligi drugo ime. |
| `European places: position <n> -- the league has <m> clubs` | Red u **Europe** pokazuje iza zadnjeg kluba. Promijeni ga ili makni. |
| `European places: position <n> is listed twice` | Dva reda imaju isto mjesto. Makni jedan. |
| `European places: a cup winner's place, but the country has no cup` | Označi **National cup**, ili makni red **Cup winner**. |
| `Clubs, times and groups must be numbers.` | Pod **splits in two** upiši skupine kao brojeve, npr. `6/6`. |
| `A league playing February to December has no split, Apertura/Clausura, national cup or league cup yet.` | Postavi **Season** na **August to May**, ili makni podjelu, Aperturu/Clausuru ili kupove. |
| `This division plays February to December with the league above it, and a league playing February to December has no split or Apertura/Clausura yet.` | Daj ovom rangu **everyone plays everyone**. |
| `Clubs in no league are all new clubs: take the clubs of the game out first (Edit club).` | Liga ima klubove iz igre. Na **New clubs** označi svaki i koristi **More ▾ → New club here**, pa opet postavi **Clubs in no league**. |
| `<league> is below this league; clubs in no league have none.` (ili `an exhibition league has none.`) | Druga liga ima ovu kao svoj **Division**. Prvo promijeni tu ligu. |
| `A league has 10 to 24 clubs.` (New clubs) | Insert club / Remove club bi ostavio ligu izvan 10 do 24. |
| `Open the NewLife Database on the NewLife page first.` | **NewLife club...** treba NewLife mapu: otvori je jednom na **NewLife Database**. |
| `Pick the club that takes its place.` / `Give the new club a name.` / `A club cannot take its own place.` | U **Club of the game** izaberi klub zamjenu, ili upiši ime za novi. |
| `error: no game tables -- Settings > Unpack the game's tables` | **Settings → Unpack the game's tables**. |
| `error: no game folder -- Game > Choose the game folder` | **Game → Choose the game folder...**. |
| `error: the world name must start with _FL26` | **Leagues → More ▾ → World name and recipe...**: ime koje počinje s `_FL26`. |
| `error: nothing to build: add a league or change one of the game's ...` | Recept je prazan. Dodaj lige (Koraci 3 do 5). |
| `error: <league>, club <n>: <club> plays in <...> -- pick the club that takes its place there` | Napravi [Klubovi koje igra već ima](#klubovi-koje-igra-već-ima) za taj klub. |
| `error: <league>, club <n>: the new club taking <club>'s place needs a name` | Isti prozor: upiši ime pored **Its place goes to a new club, named:**. |
| `error: <club> is in <league> and in <league>: a club plays in one league` | Izbaci klub iz jedne lige (**New club here** na New clubs, ili mu makni kvačicu prije dodavanja). |
| `error: <n> new clubs, but the game has room for <m> more (a full squad each)` | Previše novih klubova. Makni ligu, ili klubove. |
| `error: <n> leagues, but the game has room for <m> ...` | Previše novih liga. Makni neke. |
| `error: <league> has <n> leagues below it; the game follows one link` / `... are all under ...` | Samo jedna liga može biti ispod lige. Promijeni **Division** ostalima. |
| `error: <league>: division 8 -- the rank field stops at 7` | Država ide do 7. ranga. |
| `error: at most 2 split leagues for now ...` / `... only one league of a country can be split or Apertura/Clausura` | Daj ostalim ligama **everyone plays everyone**. |
| `The game's tables Mod Studio uses are older than the game: ... Unpack them again first?` | Klikni **Yes**. |
| `<world> is not built yet: 2. Build the world first.` (Export the world) | Prvo Build, pa izvezi. |
| `Give the package a name.` / `Tick at least one league.` / `The recipe has no leagues yet.` | U **Make a league package** upiši **Name** i označi ligu; recept prvo treba lige. |
| Nema novih liga na Select Team | Pokreni **novu** Master Ligu. Onda **Build → 4. After a start: check**. |
| `sider.log is older than the world switched on -- start the game to the main menu, then check again` | Pokreni igru do glavnog izbornika, ugasi je, opet provjeri. |
| `<module> not loaded` / `did NOT read the world file` | **Build → 0. Install the modules**, pa **3. Switch it on**, opet pokreni igru i opet provjeri. I dalje ne valja: pitaj na Discordu. |
| Imena klubova su ona iz igre, ne tvoja | Skriva ih stari Edit save: **Move the Edit save aside** u prozoru **Build finished**, ili makni `EDIT00000000` iz mape sa spremanjima igre. |
| Svi novi igrači imaju isto lice | **Build → 0. Install the modules** (donosi paket lica), pa opet pokreni igru. |

**Kad tražiš pomoć:** na [Discordu](https://discord.gg/StQqtk3G3M) pošalji sliku onoga što vidiš,
tekst loga Builda i svoj `sider.log` (**Game → Open sider.log**).
