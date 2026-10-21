# Napravi svoje lige i pakete: svaki klik, redom

> [English](../en/make-your-own-leagues.md) · **hrvatski** · [español](../es/make-your-own-leagues.md) · [português](../pt/make-your-own-leagues.md) · [français](../fr/make-your-own-leagues.md)

> Drugi vodič korak po korak: [Instaliraj gotov paket](install-a-pack.md)
> · sve stranice i opcije objašnjene: [mod-studio-guide.md](mod-studio-guide.md)
> · pitanja: [faq.md](../../docs/faq.md) (na engleskom) · pomoć: [Discord](https://discord.gg/StQqtk3G3M)

Ova stranica te vodi od nule do tvojih liga u igri: pravih liga s pravim klubovima i igračima iz
**NewLife baze** (NewLife Database), postavljenih kako želiš, izgrađenih, odigranih i podijeljenih
s drugima. Kaže što kliknuti, točno ime svakog gumba i polja kako ga Mod Studio pokazuje i što
trebaš vidjeti nakon svakog koraka. Radi korake redom. Ako vidiš nešto drugo nego što korak kaže,
stani tu i pogledaj u [Ako nešto ne valja](#ako-nešto-ne-valja).

Tri riječi koje ćeš stalno sretati:

- **Tvoj svijet**: tvoj popis liga i sve što si za njih postavio. Mijenjaš ga na karticama
  **2. Moj svijet** i sam se sprema trenutak nakon svake promjene. To je samo plan: ništa ne
  ulazi u igru dok ne pokreneš **Build**.
- **Mapa svijeta**: ono što Build napravi od tvog svijeta, mapa čije ime počinje s `_FL26`
  (`_FL26MyWorld` ako ga ne promijeniš). Igra je čita dok je ona u igri (kućica **AKTIVNI
  SVIJET** na vrhu prozora pokazuje njeno ime).
- **Build**: gumb koji od tvog svijeta napravi tu mapu i stavi je u igru.

**Sadržaj**

- [Prije početka: postavljanje jednom](#prije-početka-postavljanje-jednom)
- [Korak 1. Nabavi NewLife bazu](#korak-1-nabavi-newlife-bazu)
- [Korak 2. Otvori je na stranici NewLife Database](#korak-2-otvori-je-na-stranici-newlife-database)
- [Korak 3. Izaberi lige](#korak-3-izaberi-lige)
- [Korak 4. Izaberi klubove lige](#korak-4-izaberi-klubove-lige)
- [Korak 5. Dodaj u svoj svijet](#korak-5-dodaj-u-svoj-svijet)
- [Korak 6. Stranica Lige: sve postavke lige](#korak-6-stranica-lige-sve-postavke-lige)
- [Korak 7. Primjer: država s dva ranga](#korak-7-primjer-država-s-dva-ranga)
- [Korak 8. Kartica Klubovi: imena, grbovi, dresovi, klubovi iz igre](#korak-8-kartica-klubovi-imena-grbovi-dresovi-klubovi-iz-igre)
- [Korak 9. Stranica Igrači](#korak-9-stranica-igrači)
- [Korak 10. Granice koje zaustave Build](#korak-10-granice-koje-zaustave-build)
- [Korak 11. Tvoj svijet se sam sprema](#korak-11-tvoj-svijet-se-sam-sprema)
- [Korak 12. Build](#korak-12-build)
- [Korak 13. Igraj: NOVA Master Liga, pa provjera](#korak-13-igraj-nova-master-liga-pa-provjera)
- [Korak 14. Kad kasnije nešto mijenjaš](#korak-14-kad-kasnije-nešto-mijenjaš)
- [Korak 15. Podijeli što si napravio](#korak-15-podijeli-što-si-napravio)
- [Ako nešto ne valja](#ako-nešto-ne-valja)

---

## Prije početka: postavljanje jednom

Prvo jednom odradi korake 1 do 3 drugog vodiča:
[ugasi igru](install-a-pack.md#korak-1-ugasi-igru),
[skini Mod Studio](install-a-pack.md#korak-2-skini-mod-studio) i
[reci mu gdje ti je igra](install-a-pack.md#korak-3-reci-mu-gdje-ti-je-igra).
Onda se vrati ovamo. Mod Studio sam raspakira tablice igre, a **Izgradi i instaliraj**
(Korak 12) stavi njegove module.

Igra neka bude ugašena cijelo vrijeme dok radiš u Mod Studiju.

Ako je sad u igri gotov svijet iz zipa (Modpack), u redu je: svoj svijet možeš izgraditi pored
njega. Build prvo pita i makne gotov svijet iz igre dok je tvoj u njoj. Njegova kartica u
**2. Moj svijet** ostaje, a **Aktiviraj** ga vraća.

---

## Korak 1. Nabavi NewLife bazu

NewLife baza je zaseban download s pravim klubovima i igračima: imena, datumi rođenja, pozicije,
ocjene na skali igre i boje klubova. Nije na GitHubu.

1. Otvori naš [Discord](https://discord.gg/StQqtk3G3M) i idi na kanal **#newlife**.
2. Skini dijelove koje želiš. Ima jedan dio po kontinentu (velik kontinent dolazi u više
   dijelova), plus *Free agents*. Svaki dio je `.zip` datoteka s imenom `NewLife-...zip`.
3. Napravi mapu za njih, npr. `Documents\NewLife`, i stavi **sve** dijelove u tu jednu mapu.
4. **Ne raspakiravaj ih.** Mod Studio čita zipove takve kakvi jesu. (Windowsov preglednik zipova
   ih ionako ne može otvoriti; to je normalno.)

Kad izađe novija verzija NewLifea, stavi njene dijelove u **novu** mapu. Nikad ne miješaj dvije
verzije u jednoj mapi.

## Korak 2. Otvori je na stranici NewLife Database

1. Klikni **2. Moj svijet**, pa **NewLife Database** (gumb desno, pored kartica).
2. Klikni **Otvori NewLife Database...** na vrhu.
3. Izaberi mapu iz Koraka 1 (mapu, ne zip u njoj) i potvrdi.
4. Pričekaj par sekundi dok čita.

(Ili: **2. Moj svijet → + Dodaj...**, **Odaberi mapu...**, izaberi mapu, pa **Dodaj**.)

**Trebaš vidjeti:** iznad popisa verziju NewLifea i mapu, a ispod njih `Dijelovi:` s dijelovima
koje je našao. Ispod toga dug popis liga.

Mod Studio pamti mapu: idući put je stranica otvori sama.

**Traženje.** Polje iznad popisa, *Traži lige ili države*, ostavi samo lige čije ime ili država
sadrži ono što upišeš. Upiši npr. `brazil` ili `liga`. Isprazni polje da opet vidiš sve.

**Stupci.** Klikni naslov stupca da poredaš po njemu, klikni opet da okreneš redoslijed.

| Stupac | Što ti kaže |
|---|---|
| **Liga** | Ime lige. `*` iza imena znači da si mijenjao njene klubove (Korak 4). |
| **Država** | Gdje ide u igri. |
| **Klubovi** | Koliko će klubova imati, kako si sad postavio. |
| **U igri** | Koliko njenih klubova igra već ima (zadrže svoja imena, grbove, dresove i igrače). |
| **Igrači** | Koliko igrača njeni klubovi imaju u NewLifeu. |
| **Razina** | Koliko je liga jaka. Više je jače. |
| (zadnji stupac) | Zašto se siva liga ne može dodati. Prazno za ligu koju možeš dodati. |

**Zašto su neke lige sive.** Siva liga se ne može dodati, a zadnji stupac kaže zašto:

- `liga ima 10 do 24 klubova`: liga u igri ima 10 do 24 kluba, nove i igrine zajedno. Ova ih
  ima manje ili više. Još je možeš popraviti u Koraku 4 (dodaj ili izostavi klubove) dok ne
  stane.
- `igrina vlastita liga: Dovedi lige igre u ovu sezonu`: igra već ima ovu ligu (Premier League,
  Championship ...). Ne dodaje se drugi put. **Više ▾ → Dovedi lige igre u ovu sezonu...** na vrhu
  umjesto toga daje igrinim ligama klubove i kadrove ove NewLife sezone; vidi
  [8.4 u punim uputama](mod-studio-guide.md#84-newlife-database-pravi-klubovi-i-igrači).

Ako stranica kaže da Mod Studio nema tablice igre i ponudi da otvori Postavke: klikni **Da**, pa
tamo **Raspakiraj tablice igre**.

## Korak 3. Izaberi lige

1. Klikni ligu na popisu da je označiš. Njen red se istakne.
2. Za više njih: drži **Ctrl** i klikni svaku. (Ili klikni prvu, drži **Shift** i klikni zadnju
   da uzmeš sve između.)

**Trebaš vidjeti:** dolje na stranici red poput
`Novi klubovi u tvom svijetu: 0 od 1544 koliko igra prima.  Odabrano: još 18.`

- **Prvi** broj je koliko novih klubova tvoj svijet već ima.
- **Drugi** je koliko novih klubova ukupno stane u igru (oko 1.500). Mod Studio ga izračuna iz
  tablica tvoje igre, pa na drugoj verziji igre može biti malo drukčiji.
- **Odabrano** je koliko novih klubova bi dodale lige koje si izabrao.

Ako su tvoj svijet i odabir zajedno više nego što igra prima, **Dodaj u svoj svijet** ostaje
siv: izaberi manje liga.

## Korak 4. Izaberi klubove lige

Ovaj korak nije obavezan. Preskoči ga ako želiš ligu točno kakvu je ima NewLife.

Označi **jednu** ligu (samo jednu). Popis desno pokazuje njene klubove: **Klub** i **Igrači**
(koliko igrača mu daje NewLife). Klub koji igra već ima je siv, s `u igri` umjesto broja.

- **Izostavi klub:** klikni njegovu kućicu da makneš kvačicu.
- **Dovedi klub iz druge lige** (npr. prva liga ove sezone je prošlosezonska s dva kluba koja
  su ušla): klikni **Dodaj klub iz druge lige...** ispod popisa.
  1. Otvori se prozor sa svim klubovima NewLife dijelova koje si otvorio, svaki sa svojom ligom
     u zagradi.
  2. Upiši u polje za traženje da nađeš klub ili ligu.
  3. Označi jedan ili više klubova. Red ispod popisa kaže koliko si ih izabrao.
  4. Klikni **U redu**.

  **Trebaš vidjeti:** klub na kraju popisa, s `iz: <njegova liga>` pored.

**Trebaš vidjeti:** red lige na popisu sad ima `*`, a broj u **Klubovi** se promijenio. Siva
liga koja sad ima 10 do 24 kluba postane normalna.

Klub može igrati samo u jednoj ligi. Ako ga dodaš u dvije, Mod Studio te zaustavi u Koraku 5.

## Korak 5. Dodaj u svoj svijet

Dok su tvoja liga ili lige označene, klikni **Dodaj u svoj svijet** na vrhu.

**Trebaš vidjeti:** zeleni red ispod naslova stranice. Što koji red znači:

| Zeleni red | Što znači |
|---|---|
| `Dodano: <lige>. Mijenjaj ih na stranicama Lige, Klubovi i Igrači, pa pokreni Build.` | Lige su u tvom svijetu, svaka kao prvi rang svoje države, svi sa svima dvaput. U igri još nema ničega. |
| `<klubovi> igraju i u nekom natjecanju igre: na stranici Klubovi odaberi svakog i preko Klub iz igre izaberi klub koji ga tamo mijenja.` | Ovi klubovi tvoje nove lige su klubovi koje igra već ima, a igraju i negdje u igri (liga, kup, Europska liga ...). Klub igra samo u jednoj ligi, pa njegovo staro mjesto treba drugi klub. Taj klub biraš u [Koraku 8](#klubovi-koje-igra-već-ima). Dok to ne napraviš, Build stane s greškom koja imenuje klub. |
| `<n> igrača ostaje u svom klubu iz igre (njihov klub bi imao premalo igrača).` | Igrači koje igra već ima inače prelaze u NewLife klub. Ovi ostaju, da njihov stari klub zadrži barem 18 igrača. Ništa ne trebaš raditi. |
| `<n> igrača nije dodano: druga liga ih već ima.` | Liga koju si dodao ranije već je uzela te igrače. Ništa ne trebaš raditi. |

Ako prozor s greškom kaže `<klub> bi igrao u dvije lige (<liga> i <liga>).`, makni kvačicu tom
klubu u jednoj od dvije lige (Korak 4) i pokušaj opet.

Želiš lige s drugih kontinenata? Označi i njih i opet klikni **Dodaj u svoj svijet**. Svaki klik
dodaje; nikad ne miče ono što već postoji.

---

## Korak 6. Stranica Lige: sve postavke lige

1. **2. Moj svijet**, kartica **Lige**.
2. Iznad popisa klikni **Naše**: popis pokazuje samo lige tvog svijeta. (**Sve** pokazuje svaku
   ligu, i igrine; **Promijenjeno** igrine lige koje si mijenjao.) Lige su grupirane po
   kontinentu.
3. Klikni svoju ligu.

**Trebaš vidjeti:** desno `NAŠE`, ime i logo lige i retke **Država**, **Klubovi**, **Format**,
**Rang**, **Gore / Dolje**, **Europa** i **ID lige** (`nije izgrađena` do prvog Builda), pa
grbove njenih klubova. Ispod njih gumbe **Uredi ligu...**, **Dodaj nižu ligu**, **Klubovi i
imena**, **Igrači** i **Ukloni**.

Popis ide po državama, rangovi svake države odozgo prema dolje (Bundesliga, 2. Bundesliga,
3. Liga). Ligu možeš povući mišem gore ili dolje po popisu da posložiš lige kontinenta.

4. Klikni **Uredi ligu...**.

**Trebaš vidjeti:** prozor **Liga** s poljima ispod, odozgo prema dolje. Sivo polje se ne može
koristiti s onim što si postavio iznad njega (npr. kup za drugi rang). **?** pored **U redu**
ukratko objašnjava prozor. Ništa nije obavezno: zadane vrijednosti rade, a **Odustani** ništa ne
mijenja.

| Polje | Što je i što napraviti |
|---|---|
| **Ime** | Ime lige u igri. Dvije lige ne mogu imati isto ime. Neka bude kraće od otprilike 38 znakova: duže ime se u Kick Offovom popisu liga vidi kao prazan red. |
| **Država** | Upiši par slova i izaberi s popisa (`korea` nađe obje Koreje). Daje zastavu i mjesto gdje je liga popisana u igri. |
| **Klubovi** | 10 do 24. Za NewLife ligu ostavi kako je: manji broj izbaci zadnje klubove, veći doda izmišljene klubove na kraj. |
| **Klubovi bez lige** | Ostavi na `(ne -- liga)`. Ostali izbori (*Other European teams* ...) su za jedan klub, ili par njih, bez lige oko sebe; idu u igrine skupine "Other ...", a većina polja ispod posivi. [Više](mod-studio-guide.md#8-league-builder-nove-lige-klubovi-i-igrači). |
| **Format** | Izaberi jedno: **svi sa svima, broj krugova:** i broj (1 do 4; 2 je doma i u gostima); **dijeli se na pola (kao Škotska)**, s `prvo` *n* `x, zatim skupine` *6/6* *n* `x` (skupine moraju dati broj klubova); ili **Apertura i Clausura, zatim doigravanje:** *8 klubova*, *4 kluba* ili *bez doigravanja* (dva kratka turnira u sezoni, najviše 18 klubova). Podjela te Apertura i Clausura su **eksperimentalni**: rade, ali još imaju više bugova od formata svi sa svima, koji je potpuno testiran. Prozor to kaže ispod formata. Za prvi svijet uzmi svi sa svima. |
| **Rang** | `(prvi rang)` = najbolja liga svoje države. Za drugi rang izaberi ligu jedan rang iznad: tvoje nove lige su na vrhu popisa, pa igrine lige s brojem u zagradi. `= 2. rang` pored pokazuje rang. Liga koja već ima ligu ispod sebe je siva (`-- ispod nje: ...`): jedna liga može imati jednu ligu ispod. Vidi [Korak 7](#korak-7-primjer-država-s-dva-ranga). |
| **Samo za egzibiciju -- nije u Master ligi** | Ostavi isključeno. Uključeno: liga je samo za Kick Off i egzibicijske utakmice (legende, povijesna sezona); nikad ne igra sezonu Master Lige, a rang, kupovi i Europa posive. Ne počinji karijeru s nekim njenim klubom. |
| **Sezona** | Samo prvi rang: **kolovoz do svibanj** (kao Europa) ili **veljača do prosinac** (kao Brazil ili Japan). Rang ispod prati ligu iznad. Veljača do prosinac još ne može imati podjelu, Aperturu/Clausuru ni ligaški kup; nacionalni kup je u redu. |
| **Gore / Dolje** | 1 do 6: koliko klubova na kraju sezone mijenja mjesta s ligom iznad. Ima smisla samo za rang ispod nekog drugog. |
| **Logo** | **Odaberi sliku...** PNG ili JPG za ligu (PNG s prozirnom pozadinom izgleda najbolje). **Makni** ga uklanja. Prazno: `(napravi sam)`, logo se nacrta pri Buildu. |
| **Zastava države** | Tvoja slika zastave države. Prazno: `(iz igre)`. Ostavi prazno osim ako igra nema dobru zastavu. |
| **Kup** | Samo prvi rang. Označi **Nacionalni kup** da država dobije kup na ispadanje (ova liga i rang ispod nje). Polje pored je ime kupa; prazno = ime lige + Cup. |
| **Superkup (prvak protiv osvajača kupa)** | Jedna utakmica prije sezone. Treba označen **Nacionalni kup**. |
| **Ligaški kup** | Samo prvi rang. Drugi kup na ispadanje, kao engleski Carabao Cup: ova liga i ona ispod, do 44 kluba. Polje je njegovo ime; prazno = ime lige + League Cup. |
| **Logotipi kupova** | Po jedna slika za **Kup**, **Superkup**, **Ligaški kup** i **Doigravanje**. Prazno: amblem s inicijalima kupa. |
| **Formacija** | Kako se postavljaju klubovi lige. Izaberi s popisa, ili ostavi prazno pa Build svakom klubu izabere onu koja najbolje odgovara njegovom kadru. Pojedini klub može imati svoju (Korak 8). |
| **Europa** | Samo prvi rang: koje mjesto na tablici ide u koje kontinentalno natjecanje. Gumb koji počinje s **Prva liga:** popuni uobičajena mjesta za kontinent države (za Europu: `Prva liga: 1. kvalifikacije LP, 2. EL, 3. UECL`). **Dodaj mjesto** doda red: izaberi **Mjesto u ligi** (ispod 1 piše **Pobjednik kupa**) i **Natjecanje**. **✕** u redu ga briše, **Makni** briše sve. Za drugi rang ostavi prazno. |

5. Klikni **U redu**.

**Trebaš vidjeti:** prozor se zatvori, a retci desno pokazuju što si postavio.

NewLife liga dolazi bez europskih mjesta. Ako želiš njene klubove u Ligi prvaka i ostalima,
postavi sad **Europa**; inače te **1. Provjeri plan** podsjeti s
`no European places: the new leagues send nobody to Europe`.

Značenje svakog formata, kupa i europskog mjesta u detalje (datumi, pretkola, veličine kupova):
[poglavlje 8 punih uputa](mod-studio-guide.md#8-league-builder-nove-lige-klubovi-i-igrači)
i [8.2](mod-studio-guide.md#82-izgradi-uključi-igraj).

**Više ▾** (na vrhu kartice Lige) ima alate za cijeli svijet: **Predsezonski turniri**, **Kupovi
naših država** (kupovi svih tvojih liga u jednoj tablici), **Kupovi država iz igre**, **Europska
mjesta liga iz igre**, **Europski klubovi prve sezone**, **UEFA poredak**, **Južnoamerička
mjesta** (s kućicom **Moderna natjecanja CONMEBOL-a**, 0.2.5), **Zemlje CONMEBOL-a bez lige**, **Imena natjecanja** (nova imena i logotipi za kupove i kontinentalna natjecanja),
**ID-evi natjecanja**, **Poredak liga**, **Sezone liga iz igre** i **Ime svijeta i datoteka...**
(ime mape svijeta; mora počinjati s `_FL26`). Za prvi svijet ne trebaš nijedan od njih. Prozori
kupova su i pod **Kupovi ▾**, pored kartica.

**Liga bez NewLife klubova.** **Dodaj ligu** na vrhu kartice Lige otvara isti prozor **Liga** za
ligu napravljenu od nule: daj joj **Ime**, **Država** i broj **Klubovi**, a Build napravi klubove
s punim kadrovima i trenerom. Imena im daješ na kartici **Klubovi** (Korak 8), gdje u nju
**NewLife klub...** može staviti i prave klubove.

## Korak 7. Primjer: država s dva ranga

Recimo da tvoji NewLife dijelovi imaju prvi i drugi rang neke države, ovdje *Prva liga* i *Druga
liga*. Želiš ulazak i ispadanje između njih.

1. **NewLife Database**: označi *Prva liga* i klikni **Dodaj u svoj svijet**. (Prvo gornju.)
2. Označi *Druga liga* i klikni **Dodaj u svoj svijet**.

   **Trebaš vidjeti:** zeleni red `Dodano:` svaki put. Obje su sad prvi rang iste države, što još
   nije ono što želiš.

3. **Lige** → **Naše** → klikni *Druga liga* → **Uredi ligu...**.
4. **Rang**: otvori popis i izaberi *Prva liga* (tvoje lige su na vrhu).

   **Trebaš vidjeti:** `= 2. rang` pored. **Kup**, **Ligaški kup**, **Sezona** i gumb **Prva
   liga** posive: oni pripadaju prvom rangu.

5. **Gore / Dolje**: koliko klubova ide gore i dolje između njih dvije, npr. `3`.
6. **Europa**: ako ima redaka, klikni **Makni**. Drugi rang nikoga ne šalje u Europu.
7. Klikni **U redu**.

   **Trebaš vidjeti:** desno **Rang** `2  (ispod: Prva liga)` i **Gore / Dolje**
   `3 s ligom Prva liga iznad`. Klikni *Prva liga*: njen **Gore / Dolje** kaže
   `3 s ligom Druga liga ispod`.

8. Klikni *Prva liga* → **Uredi ligu...** i postavi ono što pripada prvom rangu: **Europa**
   (gumb **Prva liga**) i, ako želiš, **Nacionalni kup**, **Superkup** i **Ligaški kup**.
   Klikni **U redu**.

Treći rang radi isto: njegov **Rang** je *Druga liga*. Igra ide do 7. ranga.

**Jedna liga ispod jedne lige.** Dvije lige ne mogu stajati ispod iste lige (npr. tri regionalne
skupine ispod jednog drugog ranga). Druga se u popisu **Rang** vidi siva.

**Ispod igrine lige.** Tvoja nova liga može ići i ispod lige koju igra ima: izaberi igrinu ligu u
**Rang** (one s brojem u zagradi). Onda s njom igra ulazak i ispadanje.

**Bez NewLifea.** Na **Lige** klikni svoju prvu ligu, pa **Dodaj nižu ligu**: otvori se prozor
**Liga** s već popunjenom državom, klubovima, formatom i rangom. Daj joj **Ime** i klikni
**U redu**.

---

## Korak 8. Kartica Klubovi: imena, grbovi, dresovi, klubovi iz igre

1. **2. Moj svijet**, kartica **Klubovi** (ili **Klubovi i imena** na kartici Lige).
2. Na vrhu, **Liga**: izaberi jednu od svojih liga.

**Trebaš vidjeti:** njene klubove sa stupcima **#**, **Ime**, **Kratica** i **Igrači
promijenjeni**; drži miš iznad imena da vidiš njegov **ID kluba** (`pri Buildu` do prvog Builda)
i datoteku grba. NewLife klubovi već imaju imena, kratice i grbove. Klub bez imena se vidi kao
`<liga> 01`, `<liga> 02` ... u sivom. Iznad popisa: **Uredi klub** i **Više ▾**.

### Ime, grb, dresovi, trener

1. Dvaput klikni klub (ili ga označi i klikni **Uredi klub**).

**Trebaš vidjeti:** prozor **Klub** s:

| Polje | Što napraviti |
|---|---|
| **Ime** | Ime kluba. Slova s kvačicama (Željezničar) su u redu. |
| **Kratica** | Tri slova ili znamenke. Prazno = napravi se od imena. Č, Ž, Đ ... postanu C, Z, D, kao u igri. |
| **Grb** | **Odaberi sliku...** PNG ili JPG. **Makni** ga uklanja. Klub bez grba dobije numerirani znak. |
| **Domaći stadion** | Samo kad je Stadium Server instaliran: **Odaberi stadion...** iz tvog paketa stadiona, ili **Iz igre**. |
| **Trener** | Ime trenera. Prazno: ime složeno od igrača iz države kluba. |
| **Slika trenera** | PNG ili JPG; igra je pokazuje u Edit modu i u Master Ligi. |
| **Formacija** | `Kao liga (...)` zadrži formaciju lige; ili izaberi jednu za ovaj klub. |
| **Boje domaćeg dresa**, **Boje gostujućeg dresa** | Klikni dva kvadratića boje (dres, druga boja) da izabereš boje; **Ništa** = Build sam izabere dres. Build klubu da igrin dres najbliži tim bojama. |

2. Klikni **U redu**.

**Trebaš vidjeti:** novo ime i grb na popisu.

**Dresovi.** Novi klub posudi dres igrinog kluba u svojim bojama. Dvije opcije na kartici
**Gradnja**, pod **Opcije svijeta**, to mijenjaju: **Dresovi u bojama klubova** (uključeno
zadano, treba instaliran Kit Server: svaki novi klub dobije domaći, gostujući, treći i golmanski
dres napravljen u svojim bojama, sa svojim grbom) i **Obični dresovi za Edit mod** (svaki novi
klub nosi običan dres koji možeš promijeniti u igrinom Edit modu).
[Više u punim uputama](mod-studio-guide.md#8-league-builder-nove-lige-klubovi-i-igrači).

**Kapetan i prekidi.** Ne moraš ih birati: Build svakom klubu da kapetana i igrače koji izvode
penale, slobodne udarce i kornere.

**Puno klubova odjednom.** **Više ▾** ima **Zalijepi imena...** i **Učitaj imena iz datoteke...**
(jedno ime po retku, redom) i **Uvezi grbove...** (mapa slika, spojenih s klubovima po imenu
datoteke). Ima i **Igrači**, **Klub iz igre...**, **NewLife klub...**, **Novi klub ovdje**,
**Umetni klub**, **Makni klub** i **Premjesti u drugu ligu...**.

### Klubovi koje igra već ima

NewLife liga može imati klubove koje igra već ima. Na popisu se vide s igrinim imenom (miš iznad
pokaže njihov **ID kluba**). Ako je zeleni red u Koraku 5 rekao da *igraju i u nekom natjecanju
igre*, napravi ovo za **svakog** od njih:

1. Klikni klub na popisu.
2. Klikni **Više ▾ → Klub iz igre...**.

**Trebaš vidjeti:** prozor **Klub iz igre**, s označenim klubom, a ispod popisa red poput
`<klub> igra u: <natjecanja>. Svako od tih natjecanja zadržava broj klubova: odaberi tko tamo
preuzima njegovo mjesto.`

3. Izaberi tko preuzima njegovo staro mjesto:
   - **Njegovo mjesto preuzima klub iz igre koji ne igra nigdje:** i izaberi klub s popisa ispod;
     ili
   - **Njegovo mjesto preuzima novi klub, ime:** i upiši ime. Build napravi taj klub.
4. Ako klub igra u kontinentalnom natjecanju (Liga prvaka, Libertadores ...), ima i **Zadržava
   mjesta u kontinentalnim natjecanjima**. Označeno, nastavlja igrati to natjecanje i nitko tamo
   ne mora preuzeti njegovo mjesto.
5. Klikni **U redu**.

Ista stavka izbornika stavlja bilo koji klub iz igre na mjesto u tvojoj ligi: označi mjesto,
**Više ▾ → Klub iz igre...**, traži po imenu, kratici ili ID-u kluba (**Samo klubovi bez lige**
suzi popis). **Novi klub ovdje** (u **Više ▾**) vraća mjesto novom klubu; siv je osim ako mjesto
drži klub iz igre.

**NewLife klub...** (u **Više ▾**) stavlja NewLife klubove, s njihovim kadrovima, na označeno
mjesto i mjesta iza njega: označi jedan ili više u prozoru koji se otvori, pa **U redu**. Tako
liga koju si napravio rukom dobije prave klubove.

## Korak 9. Stranica Igrači

NewLife klubovi dolaze s punim kadrovima, pa ovu stranicu ne moraš dirati. Tu je ako želiš
promijeniti kadar.

1. **2. Moj svijet**, kartica **Igrači** (ili označi klub na kartici **Klubovi** i klikni
   **Više ▾ → Igrači**).
2. Na vrhu izaberi **Liga** i **Klub**. (Ili upiši u *Nađi klub...*.)

**Trebaš vidjeti:** kadar sa stupcima **Redoslijed**, **Br.**, **Ime**, **Poz.**, **Dob**,
**Ocjena**, **Noga**, **Promijenjeno** i **ID igrača**, a ispod njega prvih jedanaest na terenu.
Klikni igrača: desna strana ga pokazuje, na karticama **Osnovno**, **Pozicije**, **Sposobnosti**
i **Vještine**.

- Promijeni ime, broj, poziciju, ocjenu ili sposobnost desno. Promjena se odmah pamti.
- **Gore u redoslijedu** / **Dolje u redoslijedu**: redoslijed kadra. Prvih jedanaest počinje
  utakmicu. Ili povuci igrača na mjesto na terenu. **Najboljih jedanaest** stavi najjačeg igrača
  na svako mjesto.
- **Dovedi igrače...** dovodi igrače iz drugih klubova; **Transfer u...** šalje označenog igrača
  u drugi klub.
- **Poništi promjene ovog igrača** i **Poništi sve promjene ovog kluba** vraćaju natrag.

Sve na ovoj stranici je u [Igrači u punim uputama](mod-studio-guide.md#igrači).

---

## Korak 10. Granice koje zaustave Build

| Granica | Gdje je vidiš |
|---|---|
| Novih klubova ukupno (oko 1.500): broj u redu `Novi klubovi u tvom svijetu: X od Y koliko igra prima.` | Stranica NewLife Database: **Dodaj u svoj svijet** ostaje siv. Build: `error: <n> new clubs, but the game has room for <m> more (a full squad each)`. |
| 10 do 24 kluba u ligi | NewLife Database: siva liga, `liga ima 10 do 24 klubova`. Kartica Klubovi: `Liga ima od 10 do 24 klubova.` |
| Novih liga po svijetu: nema stalnog broja. Svaka liga i kup uzima jedno od 255 igrinih natjecanja; **2. Moj svijet** pokazuje koliko ih je zauzeto (**NATJECANJA**). Naš testni svijet igra 86 novih liga. | Build: `error: <n> leagues, but the game has room for <m> ...` |
| Jedna liga ispod jedne lige | Popis **Rang**: sivo. Build: `... are all under ...; the game follows one link down from a league ...` |
| Rangovi do 7. | Build: `error: <league>: division 8 -- the rank field stops at 7`. |
| 2 lige s podjelom po svijetu; jedna podjela ili Apertura/Clausura po državi | Build: `error: at most 2 split leagues for now ...`, `... only one league of a country can be split or Apertura/Clausura`. |
| Klub samo u jednoj ligi | Build: `error: <club> is in <league> and in <league>: a club plays in one league`. |
| Klub iz igre koji negdje igra treba zamjenu | Build: `error: <league>, club <n>: <club> plays in <...> -- pick the club that takes its place there`. Napravi [Klubovi koje igra već ima](#klubovi-koje-igra-već-ima). |

Svi brojevi: [8.3 Granice](mod-studio-guide.md#83-granice).

## Korak 11. Tvoj svijet se sam sprema

Ništa ne trebaš spremati rukom: Mod Studio spremi tvoj svijet trenutak nakon svake promjene.

**Trebaš vidjeti:** dolje u prozoru **Tvoj svijet je spremljen**.

**Datoteka → Spremi svoj svijet kao...** spremi kopiju pod drugim imenom, u mapu koju izabereš
(npr. `Documents\FL26 Mod Studio`): tu datoteku možeš naći i kopirati. **Datoteka → Otvori
svijet...** opet otvara spremljeni. **Datoteka → Novi svijet** počinje prazan.

Mod Studio pri pokretanju opet otvori tvoj svijet, pa se ono što si napravio nikad ne izgubi.

## Korak 12. Build

1. **2. Moj svijet**, kartica **Gradnja** (prva kartica).

**Trebaš vidjeti:** napomenu da je Build za moddere, pa veliki gumb **Izgradi i instaliraj** i
ispod njega dva sklopiva dijela: **Opcije svijeta: europski kupovi, nacionalni kupovi, dresovi i
lica novih klubova** (dvije kartice, **Europski kupovi** i **Novi klubovi**, s opcijama) i
**Korak po korak i Izvezi svijet** (red **0. Postavi module**, **1. Provjeri plan**, **2. Izgradi
svijet**, **3. Uključi ga**, **4. Nakon pokretanja: provjeri** i **Izvezi svijet...**). Onda red
poput `Svijet _FL26MyWorld: nije izgrađena · moduli Mod Studija: postavljeni` i okvir za log
dolje. Dok se svijet gradi, red na vrhu **2. Moj svijet** i donja traka pokazuju dosadašnje
vrijeme i korak na kojem je (`Gradim... 3:12 · squads: filling them`).

2. Otvori **Korak po korak i Izvezi svijet** i prvo klikni **1. Provjeri plan**. Ništa ne
   mijenja; samo čita tvoj svijet.

**Trebaš vidjeti:** u okviru red `world _FL26MyWorld: 2 new leagues, ...` i red za svaku ligu s
njenim klubovima, rangom i formatom (`18 clubs x2` je 18 klubova, svi sa svima dvaput;
`division 2  below ... (3 up/down)` je drugi rang) i njena `European places:`. Red koji počinje s
`error:` kaže što prvo popraviti; vidi tablicu na kraju.

3. Klikni **Izgradi i instaliraj**. Pita `Izgraditi _FL26MyWorld i staviti ga u igru? ...`:
   klikni **Da**.

   Ako su tablice igre starije od igre, prvo pita da ih ponovno raspakira: klikni **Da** (minuta
   ili dvije).

   To odjednom stavi module Mod Studija, izgradi tvoj svijet i stavi ga u igru. Traje od par
   sekundi do par minuta. Kad su se od zadnjeg Builda promijenile samo slike (logo, grb, zastava),
   traje par sekundi.

**Trebaš vidjeti:** prozor **Build gotov** s kvačicom u svakom redu: **Svijet izgrađen**, **Lige i
klubovi** (`2 leagues · 36 new clubs`), **Moduli instalirani i uključeni**, **U igri** i
**Pokreni igru i igraj**. Pod **Prije igre**: `Započni novu karijeru u Master ligi: ranije
spremljena karijera zadržava stari svijet.` Klikni **Gotovo**.

Ako kaže **An Edit save from before this Build is in the game's save folder**: klikni **Makni Edit
save u stranu**. Stari Edit save skriva nova imena i kadrove.

U **2. Moj svijet** kartica tvog svijeta je sad zelena: **● U IGRI SADA**.

**Korak po korak umjesto velikog gumba** (isti rezultat, pod **Korak po korak i Izvezi svijet**):

1. **1. Provjeri plan**: kao gore.
2. **2. Izgradi svijet**: gradi ga. Ako svijet postoji, pita `... već postoji. Izgraditi ga
   ponovno?`: **Da**. Log završi sa `Sljedeće: 3. Uključi ga, pa pokreni igru.`
3. **3. Uključi ga**: pita `Staviti _FL26MyWorld u igru (uključiti ga u sider.ini)?`: **Da**. Log
   završi sa `Pokreni igru, pa 4. provjeri.`

**Što znače redovi u logu:**

| Red | Značenje |
|---|---|
| `instaliram module ...`, `modules: ... copied, ... already there` | Moduli Mod Studija se stavljaju na mjesto. |
| `world ...: N new leagues, changes to ... of the game's leagues and ... of its clubs` | Sažetak tvog svijeta. |
| `<league>  reg ...  comp ...  division 1  18 clubs x2` | Jedna liga: njeni ID-evi u igri, rang i format. |
| `European places: 1st Champions League qualifying, ...` | Kamo idu njeni najbolji klubovi. |
| `no European places: the new leagues send nobody to Europe` | Upozorenje, ne greška: postavi **Europa** na prvom rangu ako to želiš. |
| `gradim ...` | Svijet se zapisuje. |
| `livecpk: _FL26MyWorld (... files), sider.ini loads it` | Svijet je u igri. |
| `error: ...` | Build je stao i u igri se ništa nije promijenilo. Popravi što kaže (tablica na kraju) i izgradi opet. |

Opcije pod **Opcije svijeta** (**Uključi Konferencijsku ligu**, **Ždrijeb kupa države**,
**Dresovi u bojama klubova** ...) objašnjene su u [8.2](mod-studio-guide.md#82-izgradi-uključi-igraj).
Zadane vrijednosti su u redu.

## Korak 13. Igraj: NOVA Master Liga, pa provjera

1. Klikni zeleni gumb **Pokreni igru** gore desno (ili **Igra → Pokreni igru**).
2. U igri: **Master League** → **New game**. Ne Continue: ranije spremljena karijera zadržava
   stari svijet.
3. Na **Select Team** listaj: tvoje lige su na popisu, pod svojim državama.
4. Izaberi klub i igraj.

Svaki svijet ima svoje karijere: kad drugi svijet uđe u igru, Mod Studio skloni karijere ovog
svijeta i vrati ih kad je ovaj svijet opet u igri. Ništa se ne briše.
([Više](mod-studio-guide.md#31-moj-svijet).)

Onda neka Mod Studio provjeri je li igra uzela svijet:

1. Ugasi igru (ili je barem jednom pokreni do glavnog izbornika).
2. U Mod Studiju: **2. Moj svijet** → kartica **Gradnja** → **Korak po korak i Izvezi svijet** →
   **4. Nakon pokretanja: provjeri**.

**Trebaš vidjeti:** za svaki modul red koji kaže koliko je liga pročitao iz datoteke svijeta, a
na kraju `the world works as built`. Red `not loaded` ili `did NOT read the world file`, a na
kraju `something is wrong -- see the lines above`, znače da nešto nije uspjelo: vidi tablicu na
kraju.

## Korak 14. Kad kasnije nešto mijenjaš

1. Ugasi igru.
2. Otvori Mod Studio. Sam otvori tvoj svijet (ili **Datoteka → Otvori svijet...**).
3. Promijeni što želiš na stranici **NewLife Database** ili na karticama **2. Moj svijet**:
   **Lige**, **Klubovi** ili **Igrači**. Sam se sprema.
4. **Izgradi i instaliraj** (kartica **Gradnja**) → **Da**.

**Treba li nova karijera?** Da: pokreni novu Master Ligu nakon svake promjene koju izgradiš.
Karijera pri početku uzme svoju kopiju liga, klubova i kadrova, pa karijera u kojoj već jesi
zadrži stare. A karijera spremljena s jednim svijetom treba baš taj svijet da se učita, pa drži
taj svijet u igri dok je igraš.

**Nakon što ažuriraš Mod Studio.** Izgradi svoj svijet još jednom novom verzijom i pokreni novu
karijeru. S 0.2.4 je to važno: svijet izgrađen prije nje ima golmana za kapetana svakog kluba.
Build sad svakom klubu da kapetana i izvođače prekida.

**Novija verzija NewLifea.** Stavi njene dijelove u novu mapu, **Otvori NewLife Database...** tu
mapu, pa **Više ▾ → Ažuriraj moje lige na ovu verziju**. Svaka liga zadrži ime, rang, format,
europska mjesta i kupove; klubovi i kadrovi dolaze iz nove verzije (kućica **Zadrži moje
klubove** čuva tvoj vlastiti sastav klubova). Izgradi opet i pokreni novu karijeru.
[Više](mod-studio-guide.md#84-newlife-database-pravi-klubovi-i-igrači).

**Makni ligu.** **Lige** → **Naše** → klikni je → **Ukloni** → **Da**. Njeni klubovi i promjene
njihovih igrača idu s njom.

## Korak 15. Podijeli što si napravio

Postoje dva načina. Izaberi jedan:

| | Paket liga (`.fl26pack`) | Izvezeni svijet (`.zip`) |
|---|---|---|
| Što sadrži | Tvoje lige, spremne za dodavanje u drugi svijet: klubovi, imena, grbovi, logotipi, kadrovi, lica, a po želji dresovi i semafori. | Svijet točno kakav si ga izgradio. |
| Druga osoba | Doda ga u svoj svijet i izgradi, pa radi pored njenih liga i drugih paketa. | Instalira ga i igra. Ništa se ne gradi, ali zamijeni svaki drugi svijet koji ima u igri. |
| Kako ga instalira | [Način C u Instaliraj gotov paket](install-a-pack.md#način-c-paket-liga-fl26pack) | [Način A u Instaliraj gotov paket](install-a-pack.md#način-a-gotov-svijet-jedan-zip) |

### Paket liga

1. **2. Moj svijet → Više ▾ → Paketi liga → Napravi paket...** (ili gore: **Datoteka → Napravi
   paket liga...**).

**Trebaš vidjeti:** prozor **Napravi paket liga**.

2. Popuni **Ime** (obavezno), **Autor**, **Verzija** (`1.0` za početak) i **Opis**.
3. Pod **Lige** označi lige koje idu unutra (**Označi sve** / **Odznači sve**). Liga ispod druge
   lige mora ići s njom.
4. **I moje promjene postojećih liga, klubova i igrača** (samo ako si ih mijenjao): označi da i
   njih staviš unutra.
5. Pod **Što ide unutra** sve je označeno: **Kadrovi**, **Lica i portreti igrača**, **Grbovi i
   logotipi liga**, **Treneri**, **Boje dresova**, **Dresovi**, **Scoreboardi** i **Domaći
   stadioni**. Makni kvačicu onome što ne želiš dijeliti. Dresovi dodaju oko 10 MB po ligi, a
   scoreboard oko 7 MB.
6. Klikni **Spremi paket...**. Otvori se prozor za spremanje **Spremi paket** s imenom poput
   `<ime>-1.0.fl26pack`. Izaberi mapu koju ćeš opet naći (Radna površina, Dokumenti ...) i klikni
   **Spremi**.

**Trebaš vidjeti:** `Saved <file>` s brojem liga, klubova i lica u njemu. Tu jednu datoteku
dijeliš. Ako je veća od 10 MB, Mod Studio to kaže: Discord je neće primiti, pa je podijeli preko
Google Drivea, Dropboxa, MEGA-e ili sličnog, ili makni kvačicu s **Dresovi** i **Scoreboardi**,
ili napravi jedan paket po ligi.

Više: [9. Paketi liga](mod-studio-guide.md#9-paketi-liga-podijeli-cijelu-ligu).

### Cijeli svijet (zip)

1. Prvo Build (Korak 12). Svijet mora biti izgrađen.
2. **2. Moj svijet** → **Izvezi...** na kartici svijeta. (Ili kartica **Gradnja** → **Korak po
   korak i Izvezi svijet** → **Izvezi svijet...**.)
3. Otvori se prozor za spremanje s imenom svijeta kao imenom datoteke (`_FL26MyWorld.zip`), prvi
   put u tvojoj korisničkoj mapi (poslije u mapi koju si zadnju koristio). Izaberi mapu i klikni
   **Spremi**.

**Trebaš vidjeti:** nakon trenutka `Saved <file>` i koliko novih igrača dobije generirano lice.
Zip sadrži mapu svijeta, njenu datoteku svijeta i read-me.

Tko ga instalira treba module Mod Studija s paketom lica; instaliranje zipa na **Uvezi svijet**
ih stavi. Bez njih svaki novi igrač izgleda isto. Read-me u zipu to kaže.

Više: [9.1 Izvezi svijet](mod-studio-guide.md#91-izvezi-svijet-izgrađeni-svijet-za-drugo-računalo).

---

## Ako nešto ne valja

Poruke se pojave u prozoru s greškom, u zelenom ili crvenom redu ispod naslova stranice, ili u
logu Builda iza `error:`. `<...>` stoji za ime ili broj.

| Što vidiš | Što napraviti |
|---|---|
| `no NewLife Database here: put the NewLife-....zip parts you downloaded in one folder (no need to unpack them) and open that folder` | Izabrao si krivu mapu ili si raspakirao dijelove. Otvori mapu u kojoj su same datoteke `NewLife-...zip`. |
| `the parts in this folder are of different versions (...): keep one version's parts only` | Pomiješane su dvije verzije NewLifea. U mapi ostavi dijelove samo jedne verzije. |
| `<file> is not a NewLife part (...) -- download it again` | Download se pokvario. Skini taj dio opet. |
| Siva liga, `liga ima 10 do 24 klubova` | Dodaj ili izostavi klubove (Korak 4) dok nema 10 do 24. |
| Siva liga, `igrina vlastita liga: Dovedi lige igre u ovu sezonu` | Igra je već ima. Koristi **Dovedi lige igre u ovu sezonu...**. |
| **Dodaj u svoj svijet** ostaje siv | Nije označeno ništa što se može dodati, ili bi odabir prešao granicu novih klubova (red dolje). |
| `<klub> bi igrao u dvije lige (<liga> i <liga>).` | Makni kvačicu klubu u jednoj od njih. |
| `<liga> nema državu koju igra poznaje.` | Ova liga se ne može dodati. |
| `Liga treba ime i državu.` / `Odaberi državu s popisa.` | U **Uredi ligu...** popuni **Ime** i izaberi **Država** s popisa umjesto da je upisuješ cijelu. |
| `Već postoji liga koja se zove <ime>.` | Daj ligi drugo ime. |
| `European places: position <n> -- the league has <m> clubs` | Red u **Europa** pokazuje iza zadnjeg kluba. Promijeni ga ili obriši. |
| `European places: position <n> is listed twice` | Dva reda imaju isto mjesto. Obriši jedan. |
| `European places: a cup winner's place, but the country has no cup` | Označi **Nacionalni kup** ili obriši red **Pobjednik kupa**. |
| `Klubovi, broj krugova i skupine moraju biti brojevi.` | Pod **dijeli se na pola** upiši skupine kao brojeve, npr. `6/6`. |
| `Liga koja igra od veljače do prosinca još nema podjelu, Apertura/Clausura ni ligaški kup.` | Postavi **Sezona** na **kolovoz do svibanj**, ili makni podjelu, Aperturu/Clausuru ili ligaški kup. |
| `Ova liga igra od veljače do prosinca kao liga iznad nje, a liga koja igra od veljače do prosinca još nema podjelu ni Aperturu/Clausuru.` | Daj ovom rangu **svi sa svima**. |
| `Klubovi bez lige su svi novi klubovi: prvo maknite klubove iz igre (Uredi klub).` | Liga ima klubove iz igre. Na kartici **Klubovi** označi svakog i koristi **Više ▾ → Novi klub ovdje**, pa opet postavi **Klubovi bez lige**. |
| `<liga> je ispod ove lige; klubovi bez lige nemaju ništa ispod sebe.` (ili `egzibicijska liga nema ligu ispod.`) | Druga liga ima ovu kao svoj **Rang**. Prvo promijeni tu ligu. |
| `Liga ima od 10 do 24 klubova.` (kartica Klubovi) | Umetni klub / Makni klub bi ostavio ligu izvan 10 do 24. |
| `Prvo otvori NewLife Database na stranici NewLife.` | **NewLife klub...** treba NewLife mapu: otvori je jednom na **NewLife Database**. |
| `Odaberi klub koji preuzima njegovo mjesto.` / `Daj novom klubu ime.` / `Klub ne može preuzeti vlastito mjesto.` | U **Klub iz igre** izaberi klub koji ga mijenja, ili upiši ime novog. |
| `error: nema tablica igre -- Postavke > Raspakiraj tablice igre` | **5. Postavke → Raspakiraj tablice igre**. |
| `error: nema mape igre -- Igra > Odaberi mapu igre` | **Igra → Odaberi mapu igre...**. |
| `error: ime svijeta mora počinjati s _FL26` | **Lige → Više ▾ → Ime svijeta i datoteka...**: ime koje počinje s `_FL26`. |
| `error: nema se što graditi: dodaj ligu ili promijeni neku postojeću` | Tvoj svijet je prazan. Dodaj lige (Koraci 3 do 5). |
| `error: <league>, club <n>: <club> plays in <...> -- pick the club that takes its place there` | Napravi [Klubovi koje igra već ima](#klubovi-koje-igra-već-ima) za taj klub. |
| `error: <league>, club <n>: the new club taking <club>'s place needs a name` | Isti prozor: upiši ime pored **Njegovo mjesto preuzima novi klub, ime:**. |
| `error: <club> is in <league> and in <league>: a club plays in one league` | Izvadi klub iz jedne lige (**Novi klub ovdje** na kartici Klubovi, ili mu makni kvačicu prije dodavanja). |
| `error: <n> new clubs, but the game has room for <m> more (a full squad each)` | Previše novih klubova. Makni ligu ili klubove. |
| `error: <n> leagues, but the game has room for <m> ...` | Previše novih liga. Makni neke. |
| `error: <league> has <n> leagues below it; the game follows one link` / `... are all under ...` | Ispod lige može biti samo jedna liga. Promijeni **Rang** ostalima. |
| `error: <league>: division 8 -- the rank field stops at 7` | Država ide do 7. ranga. |
| `error: at most 2 split leagues for now ...` / `... only one league of a country can be split or Apertura/Clausura` | Daj ostalim ligama **svi sa svima**. |
| `Tablice igre koje Mod Studio koristi starije su od igre: ... Prvo ih ponovno raspakirati?` | Klikni **Da**. |
| Koraci gradnje i **Izgradi i instaliraj** su sivi | Otvoren je gotov svijet iz zipa: već je izgrađen. Otvori ili napravi svoj svijet (**+ Novi svijet** u **2. Moj svijet**, ili **Aktiviraj** na kartici svog svijeta), ili gotov svijet pretvori u svoj s **Omogući uređivanje...**. |
| `<svijet> još nije izgrađen: prvo 2. Izgradi svijet.` (Izvezi svijet) | Prvo Build, pa izvoz. |
| `Daj paketu ime.` / `Označi barem jednu ligu.` / `Tvoj svijet još nema liga.` | U **Napravi paket liga** popuni **Ime** i označi ligu; tvoj svijet prvo treba lige. |
| Nema novih liga na Select Team | Pokreni **novu** Master Ligu. Onda **4. Nakon pokretanja: provjeri** (Korak 13). |
| `sider.log is older than the world switched on -- start the game to the main menu, then check again` | Pokreni igru do glavnog izbornika, ugasi je, provjeri opet. |
| `<module> not loaded` / `did NOT read the world file` | **2. Moj svijet → Gradnja → Korak po korak i Izvezi svijet → 0. Postavi module**, pa **3. Uključi ga**, opet pokreni igru i opet provjeri. I dalje ne valja: pitaj na Discordu. |
| Imena klubova su igrina, ne tvoja | Stari Edit save ih skriva: **Makni Edit save u stranu** u prozoru **Build gotov**, ili makni `EDIT00000000` iz igrine mape sa saveovima. |
| Golman je kapetan svakog novog kluba | Svijet je izgrađen prije 0.2.4. Izgradi ga opet i pokreni novu karijeru. |
| Grb na hlačicama nacrtanog dresa stoji bočno | Dres je nacrtan prije 0.2.4. Obriši datoteke `kitmaker.txt` u `SiderAddons\content\kit-server\<tvoj svijet>` i opet stisni **Izgradi i instaliraj**: dresovi se nacrtaju ponovno, s ispravno okrenutim grbom. |
| Svi novi igrači imaju isto lice | **1. Početna → Instaliraj sada** (kad Početna kaže da moduli fale ili su stariji), ili **2. Moj svijet → Gradnja → Korak po korak i Izvezi svijet → 0. Postavi module**: donosi paket lica. Pa opet pokreni igru. |

**Kad tražiš pomoć:** na [Discordu](https://discord.gg/StQqtk3G3M) pošalji sliku onoga što vidiš,
tekst loga Builda i svoj `sider.log` (**Igra → Otvori sider.log**).
