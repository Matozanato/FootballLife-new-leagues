# FL26 Mod Studio — upute

> [English](../en/mod-studio-guide.md) · **hrvatski** · [español](../es/mod-studio-guide.md) · [português](../pt/mod-studio-guide.md) · [français](../fr/mod-studio-guide.md)

> **Prvi put u Mod Studiju?** Dva vodiča korak po korak, svaki klik redom: [Instaliraj gotov paket](install-a-pack.md)
> (netko ti je dao svijet, modpack ili `.fl26pack`) · [Napravi svoje lige i pakete](make-your-own-leagues.md)
> (sam biraš lige i gradiš ih). Ove upute objašnjavaju svaku stranicu i opciju u dubinu.

> Česta pitanja (ažuriranje, rušenje pri pokretanju, kupovi, ulazak u viši rang, što poslati kad
> nešto ne radi), na engleskom: [faq.md](../../docs/faq.md) · pitanja i pomoć na [Discordu](https://discord.gg/StQqtk3G3M)

FL26 Mod Studio je jedan program za sve što dodaješ u Football Life 2026:

- **modove** koje skineš: stadione, dresove, lopte, semafore, komentar, glazbu, lica, Lua module;
- **content servere** koji ih poslužuju (Stadium Server, Ball Server, Kit Server i ostali), s
  datotekama mape koje uređuješ kao tablicu, a ne ručno;
- same **postavke Sidera**: koje su mape sadržaja i moduli uključeni i kojim redom;
- **nove lige i klubove** (League Builder), tvoje promjene na ligama, klubovima i **igračima**
  same igre, te **pakete liga** koje moder napravi jednom, a svatko ih doda u svoju igru.

Ništa od igre se ne prepisuje. Prije nego program promijeni neku datoteku, sačuva kopiju, a
svaki mod koji instalira može se opet maknuti.

---

## 1. Prije početka

- Instaliran **Football Life 2026** s mapom `SiderAddons` (FL26 dolazi sa Siderom).
- Raspakiraj program bilo gdje, npr. `Documents\FL26 Mod Studio`. Mapa mora ostati na okupu:
  mape `_internal` i `pack` te datoteke `README` stoje pokraj `FL26ModStudio.exe`.
- **Ugasi igru** dok mijenjaš stvari. Sider čita postavke kad se igra pokrene.

Prozor je na engleskom. **Jezik (Language)** na gornjoj traci (ili **Postavke → Jezik
(Language)**) ga prebaci na hrvatski (Hrvatski), španjolski (Español), brazilski portugalski
(Português) ili francuski (Français). Novi jezik se vidi kad idući put pokreneš Mod Studio.

## 2. Prvo pokretanje

**Kratka tura.** Kad prvi put pokreneš 0.2.4, mala kartica ti pokaže gdje je sad sve, jedno po
jedno mjesto, s narančastim okvirom oko onoga o čemu govori: jezik, kućice s onim što je u igri,
**Pokreni igru**, pa **1. Početna** do **5. Postavke** i **Pomoć**. Deset koraka. Dok traje, ništa
se ne mijenja. **Dalje** i **Natrag** idu kroz nju, **Preskoči turu** je zatvori, a **Pomoć →
Kratka tura** je opet pokaže kad god želiš. Na zadnjoj kartici je **Pokaži mi kako instalirati
Modpack**: druga kartica koja te vodi kroz instalaciju Modpacka (zipa svijeta), klik po klik (i u
**Pomoć → Instaliraj Modpack, korak po korak**).

1. **5. Postavke → Mapa igre**: stisni **Pregledaj...**, odaberi mapu u kojoj je `FL_2026.exe`,
   pa **Koristi ovu mapu**. Redak ispod kaže što je nađeno, npr. `Nađeno: FL_2026.exe, Sider u
   SiderAddons, sider.ini.`
2. Tablice igre: Mod Studio ih sam raspakira prvi put (pročita klubove, lige i igrače igre u
   radnu mapu; to traje minutu ili dvije, a donja traka to kaže). Nakon ažuriranja igre Build to
   primijeti i ponudi da ih prvo opet raspakira; **Postavke → Tablice igre → Raspakiraj tablice
   igre** to radi ručno. **Koristi drugu mapu s tablicama...** služi za vlastitu bazu, npr. `pesdb`
   mapu u livecpk: prvo raspakiraj tablice igre, zatim odaberi tu mapu. Njene datoteke idu preko
   igrinih, a igrine daju sve što ona nema. Mod baze koji premješta igrine lige na mjesta drugih
   liga (UML 2026 i slični) je u redu: svaka liga igre dobije državu većine svojih klubova, a
   NewLife Database klub smatra igrinim samo kad ga te tablice imaju (0.2.4).
3. Otvori **1. Početna**. Pokazuje svijet u igri (**U IGRI SADA**, s **Otvori njegove lige** i
   **Promijeni svijet...**, koji otvara **2. Moj svijet**), karticu koja kaže ima li tvoj svijet
   promjene koje igra još nema (**Idi na Gradnju** i **Samo europski kupovi...**) i **Provjera
   spremnosti**: tablicu s jednim retkom po provjeri (igra, Sider, moduli, mape sadržaja ...). Kad
   nešto ne valja, crvena traka imenuje problem i ima gumb koji ga popravi. Kad moduli Mod Studija
   fale, stariji su ili isključeni, redak kaže koji, a **Instaliraj sada** ih postavi. Desno:
   **Brze radnje** (**Instaliraj module**, **Izgradi svijet ponovno**, **Uvezi zip svijeta**,
   **Dodaj paket liga**) i **Zadnje promjene** (najnovije točke vraćanja, **Sve točke vraćanja**).

**Ažuriranja.** Par sekundi nakon pokretanja program pita GitHub je li izašao noviji FL26 Mod
Studio i javi se samo ako jest. **Skini i instaliraj** skine novi zip, provjeri ga prema
kontrolnom zbroju izdanja, zatvori program, stavi nove datoteke preko starih i ponovno ga
pokrene. Tvoje postavke, svjetovi, točke vraćanja i igra ostaju netaknuti. **Pomoć → Provjeri
ažuriranja...** pita u bilo kojem trenutku; makni kvačicu s **Pomoć → Provjeri ažuriranja pri
pokretanju** i program pita samo tada. Ako je program u mapi u koju Windows ne da pisati
(npr. Program Files), otvori se stranica izdanja: raspakiraj zip sam ili premjesti program u
svoju mapu.

**Karijere iz verzija prije 0.2.0.** U 0.2.0 dan u kalendaru prima 792 utakmice umjesto 280, a to mijenja tablice s kojima se karijera sprema: **karijera spremljena starijom verzijom se ne učita** (ostane na ekranu učitavanja). Nakon ažuriranja pokreni novu karijeru. Tvoji svjetovi i Edit podaci ostaju kakvi jesu.

**0.2.4 i tvoja karijera.** Karijera spremljena s 0.2.2 ili 0.2.3 i dalje radi, a učita se i kup
spremljen prije 0.2.4. Jedan popravak traži novi Build: do 0.2.4 golman je bio kapetan svakog
kluba svijeta napravljenog Mod Studiom. **Build** sad svakom klubu i reprezentaciji koji ih nemaju
da kapetana i igrače koji izvode penale, slobodne udarce i kornere. Da ih dobiješ, ponovno
napravi **Build** svog svijeta i pokreni novu karijeru.

**Igranje.** Gumb **Pokreni igru** gore desno (ili **Igra → Pokreni igru**) pokreće igru i prvo
upozori kad su moduli krivim redom. Pored njega oznaka kaže je li sve postavljeno: **SPREMNO ZA
IGRU**, **NIJE SPREMNO** ili **JOŠ NEMA SVIJETA**. **Igra → Pokreni igru bez modova (sigurni
način)...** vraća postavu koju je Mod Studio našao prvi put.

**Zasluge.** Gumb **Zasluge** pored **Pomoć** nabraja sve koji su pomogli napraviti Mod Studio:
testere, one koji su slali prijave i logove, i one čije su ideje u njemu.

**Više Sider mapa?** Sider se ne mora zvati `SiderAddons`. Program traži mapu pokraj
`FL_2026.exe` u kojoj je `sider.ini`, i jednu razinu dublje (`sider\patch 1`, `sider\patch 2` ...
kad jedna mapa drži nekoliko kopija Sidera). Ako ih je više, **Postavke → Sider mapa** bira s
kojom radi; ostale se ne diraju.

**Igra pod Program Files.** Windows tamo dopušta mijenjanje datoteka samo programu pokrenutom
kao administrator. Kad Mod Studio ne može pisati u mapu igre, to kaže (i na **Početna**) i ponudi
**Ponovno pokreni kao administrator**. Ili premjesti igru u svoju mapu.

## 3. Stranice

Na vrhu prozora, slijeva nadesno:

- izbornici **Datoteka**, **Igra**, **Profili**, **Jezik (Language)** i **Pomoć**, te **Zasluge**;
- gumb **Pokreni igru** s oznakom spremnosti pored;
- ispod njih kućice s onim što je sad u igri: **MAPA IGRE**, **SIDER**, **AKTIVNI SVIJET**,
  **MODULI**, **LIGE** i **PAKET**. Crvena kućica imenuje problem; klikni kućicu da odeš na
  stranicu gdje se popravlja;
- onda numerirani dijelovi, a dolje u prozoru traka stanja (spremno ili problem, što program
  radi, **Tvoj svijet je spremljen**, broj točaka vraćanja).

| Dio | Što je u njemu |
|---|---|
| **1. Početna** | Svijet u igri, provjera spremnosti, brze radnje |
| **2. Moj svijet** | Tvoji svjetovi kao kartice, i kartice **Gradnja**, **Lige**, **Klubovi**, **Igrači**, **Dresovi**, **Stadioni** i **Kupovi** (odjeljak 3.1) |
| **3. Sadržaj igre** ▾ | **Lopte**, **Komentar**, **Glazba**, **Ostali sadržaj** |
| **4. Alati** ▾ | **Lua moduli**, **Mape sadržaja**, **Profili**, **Točke vraćanja**, **Dijagnostika** |
| **5. Postavke** | Mapa igre, Sider mapa, jezik, karijere u Master ligi, tablice igre |

**Datoteka** ima **Novi svijet**, **Otvori svijet...**, **Spremi svoj svijet kao...**, **Izmjene u
ovom svijetu...** (sve što tvoj svijet mijenja u igri na jednom popisu; odaberi retke i stisni
**Poništi odabrane izmjene** da ih vratiš), **Dodaj paket liga...** i **Napravi paket liga...**.
**Igra** otvara mapu igre, Sider mapu, `sider.ini` i `sider.log` i pokreće igru. **Pomoć** ima
**Upute**, **Kratka tura**, **Instaliraj Modpack, korak po korak**, **Uredi Modpack, korak po korak**, **Provjeri ažuriranja...** i
**O programu FL26 Mod Studio**.

### 3.1 Moj svijet

**2. Moj svijet** je mjesto za tvoje svjetove. **Svijet** je mapa sadržaja s imenom `_FL26...`
koja drži nove lige, klubove i igrače; igra čita jedan po jedan (poglavlje 8).

**Na vrhu**: **NATJECANJA** (koliko natjecanja, liga i kupova zajedno, ima svijet u igri; igra
ima mjesta za 255), **NOVE DRŽAVE** (koliko država dodaje; mjesta za 99), podsjetnik da **izmjene
traže novu Master League** i stanje otvorenog svijeta. **▾ Svjetovi** sklopi red kartica da
napravi mjesta, i opet ga pokaže.

**Kartice**: jedna kartica za svaki svijet na disku. Svijet u igri je prvi, pa najnoviji; kotačić
miša pomiče red lijevo i desno.

- Svijet u igri je zelen, s **● U IGRI SADA** i **● Aktivan**. Svijet instaliran iz zipa ima
  oznaku **Iz zipa**.
- Svaki drugi izgrađeni svijet (**NIJE U IGRI**) ima **▶ Aktiviraj**: stavi taj svijet u igru
  (uključen u `sider.ini`) i izvadi onaj koji je u igri. Ništa se ne briše: drugi svijet ostaje
  na disku sa svojim karijerama. Nakon toga pokreni novu Master Ligu.
- Svaka kartica ima **Izvezi...** (jedan `.zip` svijeta za drugo računalo, odjeljak 9.1),
  **Preimenuj** i **Obriši**. **Obriši** izvadi svijet iz igre i s diska, ali ga cijelog čuva u
  **Točke vraćanja** (poglavlje 5). Svijet u igri se ne može obrisati: prvo aktiviraj drugi
  svijet.
- **+ Novi svijet** na kraju počinje prazan vlastiti svijet (isto kao **Datoteka → Novi
  svijet**); onda mu dodaj lige na **Lige**.

Ako su dva svijeta uključena odjednom, zelena kartica kaže **▶ Ostavi samo ovaj**: taj svijet
ostavi u igri, a ostale isključi.

**Kartice** ispod reda sa svjetovima mijenjaju otvoreni svijet: **Gradnja** (odjeljak 8.2),
**Lige**, **Klubovi** i **Igrači** (poglavlje 8), **Dresovi** i **Stadioni** (poglavlje 6).
**Kupovi ▾** otvara prozore kupova: **Predsezonski turniri**, **Kupovi naših država**, **Kupovi
država iz igre** i **Imena natjecanja**. Desno:

- **NewLife Database** otvara stranicu NewLife (odjeljak 8.4);
- **+ Dodaj...** je jedan prozor za tri stvari: zip svijeta (Modpack), paket liga (`.fl26pack`)
  i NewLife bazu (mapu ili njene zipove). Ispusti datoteku na njega ili koristi **Odaberi
  datoteku...** / **Odaberi mapu...**. U jednom zelenom retku kaže što je našao; za paket liga
  nabroji lige za označiti i koliko će natjecanja svijet imati. **Dodaj** to preda pravoj
  stranici: zip svijeta na **Uvezi svijet** (poglavlje 4), paket u tvoj svijet, NewLife bazu na
  njenu stranicu. Ništa ne ulazi u igru do **Izgradi i instaliraj**;
- **Više ▾** ima **Paketi liga** (poglavlje 9), **Uvezi zip svijeta** (poglavlje 4), **NewLife
  Database** i **Mape sadržaja** (poglavlje 5).

**Svijet iz zipa** (Modpack) je već izgrađen, pa je **Gradnja** za njega isključena (odjeljak
8.2). Da ga ipak promijeniš, **Omogući uređivanje...** na vrhu Moj svijet ga pretvori u tvoj
vlastiti svijet, na istom mjestu i pod njegovim imenom. Prvo se cijeli kopira u **Točke
vraćanja**. Nakon što ga izgradiš, pokreni novu Master Ligu.
**Pomoć → Uredi Modpack, korak po korak** to pokaže klik po klik.

**Svaki svijet ima svoje karijere u Master ligi** (0.2.4). Karijera je napravljena za jedan
svijet: u drugom svijetu njenih liga i klubova nema. Zato svaki put kad se svijet u igri
promijeni (**Aktiviraj**, **Izgradi i instaliraj** drugog svijeta, Uvezi svijet, Mape sadržaja,
profil), Mod Studio s njim promijeni i igrinu mapu saveova. Karijere svijeta koji odlazi čuvaju
se u `save_<svijet>`, pored `save`, u `Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026`.
Karijere svijeta koji dolazi vrate se u `save`; svijet koji ih još nema počinje s praznom. Cijela
mapa ide sa svijetom (karijere, Become a Legend, Edit podaci), osim tvojih postavki igre, koje
idu s tobom u svaki svijet.

Ništa se ne briše: prije prve promjene Mod Studio kopira cijelu tvoju mapu saveova u
`SiderAddons\ModStudio\backups\saves\<datum>` (**Točke vraćanja** je nabraja), a prvi put ti
kaže kamo su otišle tvoje karijere. Ne mijenja ništa dok igra radi, ni kad mapa `save_<svijet>`
tog imena već postoji: kaže zašto i ništa ne mijenja. **Preimenuj** preimenuje i `save_<svijet>`
tog svijeta; **Obriši** je ne dira (tvoje karijere su tvoje). Ne želiš to? Makni kvačicu s
**Postavke → Svaki svijet ima svoje karijere (mapa saveova mijenja se sa svijetom)**.

**Lige** (kartica Moj svijet) nabraja sve lige, igrine i tvoje, pod njihovim kontinentom; rangovi
svake države stoje zajedno, odozgo prema dolje (Bundesliga, 2. Bundesliga, 3. Liga), dok ligu ne
povučeš mišem negdje drugdje. Filtri **Sve**, **Naše** i **Promijenjeno** i polje za traženje.
Odaberi jednu: tvoja liga ima **Uredi ligu...**, **Dodaj nižu ligu**, **Klubovi i imena**,
**Igrači** i **Ukloni**; liga iz igre ima svoje ime, logo i klubove (poglavlje 8, "Lige iz
igre"). **Dodaj ligu** napravi novu. **Mjesta u Select Teamu** pokazuje kamo je zadnji Build
stavio svaku tvoju ligu. **Više ▾** ima **Predsezonski turniri**, **Kupovi naših država**,
**Kupovi država iz igre**, **Europska mjesta liga iz igre**, **Europski klubovi prve sezone**,
**UEFA poredak**, **Južnoamerička mjesta**, **Imena natjecanja**, **ID-evi natjecanja**, **Poredak
liga**, **Sezone liga iz igre** i **Ime svijeta i datoteka...**. Ovo zadnje otvara stranicu s
imenom svijeta i popisom tvojih liga (starije upute je zovu *Nove lige*).

## 4. Uvezi svijet

**Uvezi svijet** je stranica koja instalira skinuti paket. Do nje dođeš preko **2. Moj svijet →
Više ▾ → Uvezi zip svijeta**, preko **Uvezi zip svijeta** pod **Brze radnje** na **Početna**
(odmah otvori izbor datoteke) ili preko **+ Dodaj...** u Moj svijet.

Ispusti paket na nju (`.zip`, `.7z`, mapa, `.lua`, `.cpk` ili `.fl26pack`), ili koristi
**Odaberi datoteku...** / **Odaberi mapu...**. Kad Mod Studio radi kao administrator, Windows
blokira povlačenje mišem; stranica to kaže: koristi ta dva gumba.

Program pogleda unutra i u jednom retku kaže što je: novija verzija svijeta koji imaš, gotov
svijet za igru, paket liga ili mod, s ligama koje su unutra. Onda jedan gumb, **Instaliraj**
(**Instaliraj svijet** za svijet). Novija verzija svijeta koji imaš zamijeni stariju: pita
jednom, starija se prvo makne da od nje ništa ne ostane, tvoja spremanja se ne diraju, a s novom
pokreneš novu Master Ligu. Ako je svijet istog imena izgrađen na ovom računalu, to kaže prije
nego stisneš Instaliraj i kaže ti da taj svijet prvo preimenuješ na njegovoj kartici u Moj
svijet.

Dijelovi, i kamo koji ide, su pod **Više opcija: koji dijelovi, ime, redoslijed mapa sadržaja,
linije u map datotekama**:

| Dio | Što se dogodi |
|---|---|
| Mapa sadržaja (livecpk) | Kopira se u `SiderAddons\livecpk\<ime>` i doda u `sider.ini`. |
| Datoteke content servera | Kopiraju se u mapu `content` tog servera. Njegova **datoteka mape spaja se s tvojom**: tvoji retci ostaju, a novi retci moda se dodaju. Za klub koji već imaš u mapi odlučuje izbor pod **Više opcija**: *uzmi one iz moda* ili *zadrži moje, dodaj modove iza*. Paket semafora ili izbornika napravljen za drugi svijet ide na natjecanje koje mu ime kaže u tvom svijetu, a stranica kaže koju ligu tvoj svijet nema. |
| Lua modul | Kopira se u `SiderAddons\modules` i uključi na pravo mjesto u redoslijedu. |
| Zapakirani .cpk | Pri instalaciji se raspakira u mapu sadržaja. |
| Paket liga | Dodaje se u tvoj svijet (poglavlje 9). `.fl26pack` ispušten ovdje uđe u njega i **Izgradi i instaliraj** krene sam. |
| Gotov svijet | Izgrađen svijet iz **Izvezi svijet** (odjeljak 9.1), ili kopirana mapa `SiderAddons` s `modules\fl26world.txt`. Mapa svijeta kopira se pod svojim imenom, njegova datoteka svijeta ide u `SiderAddons\modules`, a svijet se stavi u igru s modulima Mod Studija. Završi s **✓ Spremno za igru: pritisni Pokreni igru, pa započni novu Master League** i završnim popisom provjera: svijet, uključen, moduli, paket lica, content serveri koje svijet koristi, domaći stadioni. Ako nešto fali, kaže **Skoro spremno** i što popraviti; crveni redak ispod instalacije (*pogledaj što popraviti*) opet pokaže popis. |
| DLL | **Ne instalira se.** DLL radi s pravima igre; instaliraj ga samo ručno i samo iz izvora kojem vjeruješ. |

U istom sklopivom dijelu možeš maknuti kvačicu s dijela koji ne želiš (recimo s dresova, da
svijet instaliraš bez njih), dati modu ime i odabrati idu li nove mape sadržaja na vrh (one
pobjeđuju) ili na dno. **U igri sada** nabraja svaki paket instaliran programom. **Ukloni** briše
datoteke koje je dodao i vraća one koje je zamijenio.

Instalacija prvo kopira sve datoteke, a retke u map datoteke piše zadnje, pa instalacija koja
stane na pola ne ostavi redak koji pokazuje na datoteku koje nema. Ako se to dogodilo sa starijom
verzijom, **Dijagnostika** imenuje zip ili svijet: instaliraj ga opet (svijet izgrađen na tvom
računalu: izgradi ga opet).

## 5. Mape sadržaja i Lua moduli

**Mape sadržaja** (**4. Alati**) nabraja retke `cpk.root` iz `sider.ini`; svjetovi (`_FL26...`)
se vide kad označiš **Prikaži svjetove (_FL26...)**, a **Samo uključene** sakrije ostale. Svijet
koji igra sad koristi je u zelenom retku, ime mu je podebljano, a u stupcu Napomena piše **U IGRI
SADA**. Sider traži datoteku od vrha prema dnu, pa kad dvije mape imaju istu datoteku, pobjeđuje
ona više na popisu.

- Kvačica uključi ili isključi mapu (redak se pretvori u komentar, nikad se ne briše).
- **Na vrh**, **Gore**, **Dolje** mijenjaju redoslijed; **Dodaj mapu...** doda mapu koju već imaš.
- Za svaku mapu piše veličina i što je unutra (lica, dresovi, stadioni...).
- Tu su i **Osvježi**, **Makni s popisa** i **Obriši s diska...**.
- Ništa se ne zapisuje dok ne stisneš **Primijeni**. **Odbaci** zaboravi promjene.

**Preimenuj svijet...** i **Obriši svijet...** (ispod detalja mape kad je odabran svijet, ili
desni klik na svijet) rade isto što **Preimenuj** i **Obriši** na kartici svijeta u Moj svijet:

- **Obriši svijet...** prvo pita i ništa ne briše zauvijek. Mapa svijeta, njegovi dresovi i
  semafori, njegovi retci u `sider.ini` i u mapama dresova i semafora te zapis o instalaciji idu
  u `SiderAddons\ModStudio\backups\worlds\<svijet>\<datum> deleted`, a **Točke vraćanja → Vrati
  ovu kopiju** vraća sve točno kako je bilo. Čuvaju se zadnje 3 kopije svakog svijeta. Svijet u
  igri (zeleni) ne može se obrisati. Tvoj svijet u Mod Studiju (njegove lige) se ne briše, pa ga
  možeš opet izgraditi. **Obriši s diska...** na retku svijeta radi isto sigurno brisanje.
- **Preimenuj svijet...** mijenja ime svugdje gdje je zapisano: redak u `sider.ini` (isto mjesto,
  uključen ili isključen kako je bio), mape dresova i semafora i njihove retke u mapama, datoteku
  svijeta, tvoje profile i tvoj svijet u Mod Studiju. Novo ime mora počinjati s `_FL26` (slova,
  znamenke, `-` i `_`). Velik svijet se preimenuje u pozadini ("Preimenujem ..." u donjoj traci i
  na njegovoj kartici). Karijera nakon preimenovanja i dalje radi: igra nikad ne vidi ime svijeta,
  samo datoteke u njemu.

**Lua moduli** (**4. Alati**) je isto za retke `lua.module`. Redak na vrhu kaže jesu li moduli
Mod Studija instalirani, ažurni i uključeni; kad nisu, imenuje one koji fale, stariji su ili
isključeni, a **Instaliraj sada** ih popravi. Program zna pravi redoslijed čestih modula
(content serveri iza modula koje koriste) i kaže kad je neki modul na krivom mjestu. Neki moduli
trebaju postavku Sidera (npr. Goal Song Server treba `match-stats.enabled = 1`); program kaže
koju. Vlastiti `fl26...` moduli Mod Studija skriveni su dok ne makneš kvačicu s **Sakrij module
samog Mod Studija (fl26...)**; **Dodaj modul...** doda modul koji imaš.

Vlastiti moduli Mod Studija ostaju redom kojim su postavljeni, zajedno u jednom bloku
`sider.ini` sa svojim naslovom. Stare retke koje je ostavila ručna instalacija (stari caps set,
modul naveden dvaput) isključe **Instaliraj sada** i **Build**.

Od 0.2.0 dvanaest malih zaštita od pada ide kao dvije datoteke, `fl26guards.lua` (osam `fl26nullguard` zaštita) i `fl26lateguards.lua` (`fl26superguard`, `fl26resultsguard`, `fl26ctlguard`, `fl26kitguard`), pa je popis kraći. sider.log i dalje svaku zaštitu piše u svom retku. Build stare pojedinačne retke isključi; ručno ne treba ništa.

**Bez kopija pored tvojih datoteka** (0.2.4). Kad Build, Uključi ili Instaliraj module mijenjaju
datoteku, kopija od prije ide u `SiderAddons\ModStudio\backups` i vidi se u **Točke vraćanja**, a
ne pored datoteke (nema više `map.txt.before-builder` ni `modules\before-builder-<n>`).

**Isključivanje regena** (0.2.0): `fl26regen` daje regenima nova imena, novi potencijal i lice
iz paketa lica za regene. Za igru bez njega makni kvačicu s **Sakrij module samog Mod Studija
(fl26...)** da se naši vide, makni kvačicu s `fl26regen` i pritisni **Primijeni**. Mod Studio to
zapiše u `modules\fl26-off.txt` u mapi Sidera, pa ga **Build**, **Instaliraj module** i promjena
svijeta ostave isključenog umjesto da ga opet uključe, kao što rade sa svim ostalim modulima.
Igra tada sama radi regene: njen potencijal i njena imena, bez lica iz paketa lica za regene.
Vrati kvačicu i **Primijeni** da ga opet uključiš. Samo se `fl26regen` može ovako držati
isključenim.

## 6. Sadržaj igre: content serveri

Svaka od ovih stranica pripada jednom content serveru. **Dresovi** i **Stadioni** su kartice
**2. Moj svijet**; **Lopte**, **Komentar**, **Glazba** i **Ostali sadržaj** su pod **3. Sadržaj
igre**. **Ostali sadržaj** ima po karticu za **Semafori**, **Izbornici**, **Dresovi sudaca**,
**Oznake na rukavu** i **Vrijeme**, te **Moduli za izgled**. SPFL26-ovi vlastiti moduli za dresove, stadione i semafore (`common\kits.lua`, `common\stadiums.lua`, `common\scoreboards.lua`) čitaju iste datoteke iz `content\kits`, `content\stadiums` i `content\scoreboards`; kad sam server nije instaliran, njegova stranica uređuje te (dresovi od 0.1.7, stadioni i semafori od 0.1.8). Svaka stranica ima:

- **redak stanja**: je li modul uključen, postoji li njegova mapa sadržaja;
- karticu za svaku **datoteku mape**, kao tablicu: koje natjecanje, klub ili stadion dobiva
  što. **Dodaj...**, **Promijeni...**, **Kopiraj**, **Uklj. / isklj.** (redak postaje komentar) i
  **Ukloni**; stvari biraš iz knjižnice umjesto da tipkaš ID. **Spremi** zapiše datoteku; kopija
  od prije ide u Točke vraćanja;
- **Knjižnicu**: što je u mapi sadržaja servera, sa slikama gdje ih ima. Označene su stvari koje
  nijedan redak mape ne koristi i retci koji pokazuju na nešto čega nema;
- **Postavke** servera gdje ih ima (omiljeni stadion, lopta, semafor ...).

Prije spremanja program provjeri tablicu: broj gdje ide broj, bez zareza u imenu, stvar koja
postoji. Redak s problemom je obojen: **drži miš iznad njega da vidiš zašto**. **Samo retci s
problemima** pokaže samo njih. Klub naveden dvaput također je označen: vrijedi samo njegov prvi
redak. Najčešći problem, "... nije nađen u knjižnici", znači da redak pokazuje na mapu koje nema u
mapi sadržaja servera, pa igra tamo ne pokaže ništa (crni stadion, stari dres kluba): usmjeri ga na
mapu koju nabraja kartica **Knjižnica** ili makni redak. **Moduli za izgled** (na **Ostali
sadržaj**) uključuje ili isključuje module bez datoteka mape.

Redak natjecanja ide po **fazi** natjecanja, ne po natjecanju: igra content serverima javlja fazu
koja se igra (Konferencijska liga je 186, 1210, 187, 189 i kasnija kola 1213 ... 8381; Liga
prvaka 2, 3, 4 i njezina), pa se redak s brojem samog natjecanja (174) nikad ne koristi. Izbornik
natjecanja svako natjecanje nudi još jednom kao **(sve faze: N)**: odaberi to i za svaku fazu
upiše se po redak (0.1.9). Redak s brojem natjecanja označen je kao problem.

**Semafori svijeta iz zipa.** Gotov svijet (Modpack) donosi semafore svojih liga. Dok je drugi
svijet u igri, njihovi retci ostaju u **Ostali sadržaj → Semafori**, isključeni, i opet se
uključe sa svojim svijetom. Isto vrijedi za teme izbornika koje je svijet donio.

**Uvezi dresove...** (0.1.8, na kartici *Dresovi*): dresovi za mnoge klubove odjednom. Odaberi mapu s gotovim kit-server dresovima -- jedna mapa po klubu, s `p1`, `p2`, `g1` ... i `order.ini`, nazvana po klubu (`Dinamo Zagreb`) ili po njegovom ID-u (`2215`). **Spoji s** bira *Svi klubovi* ili *Novi klubovi svijeta u igri*. Spajanja od 60% ili više imaju kvačicu; provjeri ona bez kvačice i stupac *Podudarnost* prije **U redu** (mapa bez para kaže "nije nađen klub"). Dresovi se kopiraju u kit-server knjižnicu (`Liga\Klub`, kako ih je mapa imala) i svaki klub dobije redak u `map.txt`; **Spremi** ga zapisuje. Klub koji već ima redak zadržava ga, osim ako je označeno **Zamijeni već postavljene dresove**. Dresovi novog kluba idu po ID-u koji mu je dao Build, zato prvo napravi Build svijeta i drži ga u igri. Mapa kluba može umjesto toga imati obične slike dresova (0.2.0): `p1.png`, `p2.png` ... za dresove i `g1.png` za golmana (najbolje 2048 x 2048; rade i `.jpg` i `.dds`). Mod Studio od njih napravi kit-server dresove; brojevi na leđima, brojevi na hlačicama i font imena su zasebne teksture, pa dolaze iz dresa koji već postoji u knjižnici, odabranog u **Brojevi i imena iz** (počinje na prvom dresu iz knjižnice koji ih ima; *nema*: igra zadržava klupske). Boje u `config.txt` čitaju se sa slike. Pretvorbu slika napravio je Xxspedd, iz svog alata za dresove. Mod Studio ne crta dresove: slike daješ ti ili izrađivač dresova.

Ako je tvoj svijet izgrađen s **Obični dresovi za Edit mod** (poglavlje 8), Kit Server ne oblači
nove klubove, pa se uvezeni dresovi na njima ne vide; **Uvezi dresove** to kaže. Makni kvačicu s
te opcije na kartici **Gradnja** i izgradi opet.

## 7. Profili

Profil pamti koje su mape sadržaja i moduli uključeni i kojim redom. Drži jedan za Master Ligu,
jedan za online, jedan za testiranje (**4. Alati → Profili**, ili izbornik **Profili**):

- **Spremi trenutnu postavu...** spremi ono što je sad uključeno pod nekim imenom.
- **Prebaci na njega** stavi tu postavu u `sider.ini` (stari `sider.ini` ide u Točke vraćanja).
- **Osvježi trenutnom postavom** prepiše profil; **Obriši** ga makne.
- **Izvezi...** / **Uvezi...** prenose profil na drugo računalo (`.fl26profile.json`).

## 8. League Builder: nove lige, klubovi i igrači

League Builder dodaje nove lige u igru i mijenja one same igre. Ono što napravi je **svijet**:
mapa sadržaja s imenom `_FL26...` koju igra čita dok je u igri. Radiš na karticama **2. Moj
svijet**.

**Ukloni** (Lige) briše odabranu ligu s njenim klubovima. Za brisanje više njih odjednom otvori
**Više → Ime svijeta i datoteka...**, odaberi ih s Ctrl+klik, Shift+klik ili Ctrl+A, pa **Ukloni**
ili tipka Delete.

**Lige → Dodaj ligu**

| Polje | Što znači |
|---|---|
| **Ime** | Ime lige u igri. Dvije lige ne smiju imati isto ime. |
| **Država** | Daje zastavu i mjesto gdje je liga na popisu. Država za koju igra nema ligu dobije svoj naslov. |
| **Klubovi** | Od 10 do 24 (od 1 do 24 za klubove bez lige). |
| **Klubovi bez lige** | Za jedan klub, ili nekoliko njih, bez lige oko sebe (0.1.8): recimo samo BATE Borisov iz Bjelorusije. Odaberi skupinu u koju idu: *Other European teams*, *Other Latin American teams*, *Other Asia-Oceania teams*, *Other Africa teams* ili *Classic Teams* -- tamo gdje igra drži svoje klubove koji ne igraju ni u jednoj ligi (Dynamo Kyiv, Wydad Casablanca ...). U Select Teamu se vide u toj skupini. Dobiju ime, grb, dresove, trenera, formaciju, igrače i domaći stadion kao svaki novi klub (**Uredi klub**, **Igrači**); ime gore je samo kako ih Mod Studio vodi. Ne igraju ligu, kup ni europsko natjecanje, a sve ostalo u ovom prozoru posivi. Na *Lige* takva skupina pokazuje *bez lige (...)* umjesto ID-a lige. |
| **Format** | *Svi sa svima*, 1 do 4 puta, *dijeli se na pola (kao Škotska)* ili *Apertura i Clausura*: dva turnira u sezoni (rujan do početka siječnja, siječanj do svibnja), svaki od nula bodova, zatim doigravanje 8 ili 4 kluba (ili bez njega). O ulasku i ispadanju odlučuje tablica cijele sezone. Najviše 18 klubova. Podijeljena liga ima najviše 46 kola, prije i poslije podjele zajedno (16 klubova dvaput je 30, pa najveća skupina dvaput smije imati 8 klubova, 14 kola). Zasad se u jednoj državi samo jedna liga smije dijeliti ili igrati Aperturu/Clausuru. **Podjela te Apertura i Clausura su eksperimentalne** (0.2.4): rade, ali još imaju više otvorenih bugova od formata svi sa svima, koji je potpuno testiran. Prozor to kaže ispod formata. Molimo i dalje javljaj što nađeš. |
| **Rang** | *(prvi rang)* ili liga iznad nje: druga nova liga ili liga iz igre. Za novu ligu ispod druge nove lige u jednom koraku: odaberi je i stisni **Dodaj nižu ligu** (preuzme državu, broj klubova, format i gore/dolje od lige iznad; ostaje samo ime). Liga ispod koje je već druga nova liga je siva (0.1.9): igra od lige prati samo jednu vezu prema dolje, pa skupine jednog ranga (tri skupine Serie C ispod Serie B) još nisu moguće. |
| **Gore / Dolje** | Koliko klubova na kraju sezone zamijeni mjesta s ligom iznad. |
| **Sezona** | Samo za prvi rang nove države: *kolovoz do svibanj* (zadano) ili *veljača do prosinac*, kao Brazil, Japan ili Saudijska Arabija: klubovi idu gore i dolje za Novu godinu, a rangovi ispod nje je slijede. Još ne uz podjelu, Aperturu/Clausuru ni ligaški kup -- ni podjelu ili Aperturu/Clausuru na rangu ispod lige od veljače do prosinca, uključujući igrine Liga BetPlay i J1 League. |
| **Europa** | Samo za prvi rang: koje mjesto u ligi ide u koje europsko natjecanje. **Prva liga: 1. kvalifikacije LP, 2. EL, 3. UECL** upiše uobičajena tri (*... kvalifikacije* su kolovoška doigravanja, vidi 8.2); **Dodaj mjesto**, ✕ na retku i **Makni** za sve ostalo. Svako mjesto samo jednom, i samo mjesta koja liga ima. Ispod 1 mjesto glasi **Pobjednik kupa** (0.1.7): pobjednik kupa te države (nova država treba **Nacionalni kup**) -- a kad pobjednik već ima europsko mjesto kroz ligu, mjesto ide niz ligu sljedećem klubu, kao kod UEFA-e. Od 0.2.0 pobjednik kupa može ići i u kupove koje gradi Mod Studio (Copa Sudamericana, CAF Konfederacijski kup, AFC Liga prvaka Two ...); u novoj karijeri, prije nego što itko osvoji kup, i to mjesto ide sljedećem klubu lige. Može ga imati i liga iz igre (*Europska mjesta liga iz igre*). Za niži rang ostavi prazno. Predložak prati državu: Azija dobije AFC Ligu prvaka i AFC Ligu prvaka Two, Južna Amerika Libertadores i Copa Sudamericanu, Afrika CAF Ligu prvaka i CAF Konfederacijski kup, Sjeverna i Srednja Amerika CONCACAF Champions Cup, Oceanija OFC Ligu prvaka. **AFC Challenge League** (0.2.0) je treći kup AFC-a, ispod AFC Lige prvaka Two, kao Konferencijska liga u Europi; dodaje se s **Dodaj mjesto** (*AFC CHL* na popisu Lige). Tih sedam kupova kojih igra nema grade se sa svijetom (odjeljak 8.2). Mjesto u *kvalifikacijama Libertadoresa* zauzme mjesto kluba iz igre u kvalifikacijskom kolu (zadnjeg iz države koja u njemu ima najviše klubova), najviše šest od njegovih osam mjesta; **Provjeri plan** kaže koje lige preko toga ostaju vani. |
| **Logo** | Bilo koja slika (najbolje izgleda PNG s prozirnom pozadinom). Prazno: nacrta se sam. |
| **Zastava države** | Tvoja slika zastave države, razvučena u okvir zastave iz igre. Zamjenjuje igrinu zastavu te države posvuda (Select Team, nacionalnost igrača, naslov države u Database > Competition Info) dok je svijet uključen. Prazno: zastava iz igre. |
| **Kup** | Samo za prvi rang. **Nacionalni kup**: država dobije svoj kup, s imenom koje zadaš (prazno: `<liga> Cup`). Igra puni kup države iz prvog ranga i ranga ispod njega, a veličina kupa slijedi red Nacionalni kup u Granicama (8.3): najveća veličina koju ekran kupa crta i koja stane, pa 22 kluba daju kup od 20, prvo prvi rang. S više od 44 kluba kup zadržava samo prvi rang. Nova druga liga pod državom koju igra već ima (Njemačka, Rusija ...) također ulazi u kup te države, iza klubova prvog ranga, kad kola kupa odgovaraju broju klubova. Nova treća liga ili niža (League One pod Championshipom) ostavlja kup države prvim dvama rangovima iz igre, kao u igri. **Superkup (prvak protiv osvajača kupa)**: uz to i superkup od jedne utakmice prije sezone. Treba nacionalni kup. |
| **Ligaški kup** | Samo za prvi rang. Kup na ispadanje ove lige i lige ispod nje, kako se igra Carabao Cup (0.2.0): jedna utakmica po kolu, i polufinale i finale, u tjednima Carabao Cupa: 27. kolovoza, 23. rujna, 28. listopada, četvrtfinale 23. prosinca, polufinale 14. siječnja i finale u nedjelju 15. ožujka, u svoje dane, nikad na dan nacionalnog kupa ili europski dan. Sudionika ima onoliko klubova dvaju rangova koliko ekran kupa crta, do 44 (20 + 24: cijela Premier League i Championship); gdje to nije 16 ili 32, klubovi ove lige dobiju slobodan prolaz i počinju u drugom kolu. Svaki par se izvlači nasumično. Daj mu ime ili ostavi prazno (`<liga> League Cup`). Svijet izgrađen prije 0.2.0 zadržava stari kup od 16 s dvije utakmice i pretkolom dok ga ne izgradiš opet; karijera započeta prije tog Builda igra stari kup. |
| **Logotipi kupova** | Posebna slika za nacionalni kup, superkup, ligaški kup i doigravanje Apertura/Clausura. Prazno: nacrta se amblem s inicijalima kupa. |
| **Samo za egzibiciju -- nije u Master ligi** | Za Kick Off i egzibicijske utakmice: povijesna liga, legende i slično. Njeni klubovi nikad ne igraju sezonu Master Lige, pa liga stoji sama: bez ranga iznad ili ispod, bez europskih mjesta, bez kupova. I dalje se vidi na popisu momčadi Master Lige; svoj klub izaberi iz druge lige. |
| **Formacija** | Kako se klubovi lige postavljaju. Odaberi jednu od formacija koje igraju klubovi igre (4-2-3-1, 4-1-2-3, 4-3-3, 5-3-2 ...; popis kaže koliko je klubova igre igra): svaki novi klub dobije kopiju taktike kluba iz igre s tom formacijom, a pri Buildu mu se složi najboljih jedanaest. Prazno: Build svakom klubu izabere formaciju kojoj njegov kadar najbolje odgovara (0.2.4; prije fiksni 4-2-3-1): dva jaka napadača igraju s dva naprijed, dobri krilni igrači s tri napadača, tri središnja braniča s tri ili pet straga. Log Builda kaže koje su formacije izabrane. Pojedini klub može imati svoju (**Uredi klub**). |

**Ime svijeta** (Lige → Više → **Ime svijeta i datoteka...**) mora počinjati s `_FL26`. Ta stranica nabraja i tvoje lige: nakon **Builda** njen stupac **ID lige**
pokazuje ID natjecanja svake lige u igri, isti koji nosi datoteka njezina loga. Stupac **#** je mjesto
lige u redoslijedu (**Pomakni gore** / **Pomakni dolje**), a **Select Team** kaže kamo ju je zadnji Build
stavio: *da*, *umjesto* neke skupine igre, ili *nema mjesta (igra se)*. `*` tamo znači da se redoslijed od tada
promijenio: izgradi opet da vidiš kamo ide. Povlačenje lige na kartici **Lige** pomiče je samo među mjestima koja ovdje već drže lige njezina kontinenta (0.2.0; prije je cijeli redoslijed slagalo po kontinentima, pa su lige Sjeverne Amerike i Oceanije uvijek bile zadnje).

**Predsezonski turniri** (Lige → Više, ili Moj svijet → Kupovi): prijateljski kupovi na ispadanje s 4 ili 8 pozvanih klubova u srpnju, prije sezone, u parovima redom kojim ih upišeš (prvi protiv drugog ...). Klub je iz nove lige ili klub igre (njegov ID); barem jedan mora biti iz nove lige, a turnir je u njenoj državi. Karijera počinje u kolovozu, pa se prvi igra u drugoj sezoni. Svaki turnir može imati **Logo**; prazno: nacrta se sam.

**Kupovi naših država** (Lige → Više, ili Moj svijet → Kupovi, 0.2.4): kupovi tvojih liga u jednoj tablici. Za svaki prvi rang: njegov nacionalni kup, superkup i ligaški kup, svaki sa svojim imenom i logom. To su ista polja kao u **Uredi ligu...**, bez otvaranja svake lige.

**Kupovi država iz igre** (Lige → Više, ili Moj svijet → Kupovi): ligaški kup -- recimo Carabao Cup -- za lige iz igre. Označi **Ligaški kup** pored lige: ona i liga ispod nje, do 44 kluba, jedna utakmica po kolu od kraja kolovoza do finala sredinom ožujka, izvlačenje nasumično, klubovi same lige sa slobodnim prolazom u drugo kolo (0.2.0; isti kup kao kod nove lige), u dane koje kalendar liga i kupova iz igre ostavlja slobodnima. **Superkup**, prvak protiv pobjednika kupa, samo gdje ga igra nema (Brazil, Čile, Škotska, Grčka, SAD). To je superkup od jedne utakmice između dva kluba (0.2.4; prije je ispadao kao kup na ispadanje od 16). Igra se krajem srpnja; u državi koja igra od veljače do prosinca (Supercopa de Chile, Supercopa Rei) igra se krajem siječnja, između prvaka i pobjednika kupa upravo završene sezone. Kad pobjednika kupa još nema (prvo ljeto nove karijere), ili je prvak osvojio i kup, igra drugoplasirani u ligi. Prazno ime: ime lige i *League Cup* / *Super Cup*. **Logo** pored svakog imena (0.2.0): slika za taj kup; bez nje, amblem s inicijalima kupa. Promjene ovdje traže **Instaliraj module** (ili Izgradi i instaliraj), novi Build i novu karijeru.

**Europska mjesta liga iz igre** (Lige → Više): koja mjesta Premier Lige, LaLige, Serie A ... idu u koje europsko natjecanje. Popis pokazuje mjesta iz igre; označi **Vlastita mjesta za ovu ligu** da ih promijeniš. Neoznačena liga zadržava mjesta iz igre, označena liga bez redaka ne šalje nikoga.

**UEFA poredak** (Lige → Više, 0.1.7): sve europske lige svijeta -- one iz igre i tvoje nove
prve lige -- na jednom popisu, najjača država prva. Povuci ligu mišem (ili **Gore** / **Dolje**)
da promijeniš redoslijed, makni kvačicu da liga ne dobije europsko mjesto, **Poredak UEFA-e**
vraća popis na UEFA-in poredak saveza za 2026./27. Desno piše što koja liga dobiva, a **U redu**
to zapiše: mjesta UEFA-inog ključa za 2024.-27. -- 1. mjesto ima pet mjesta u Ligi prvaka, 6. dva
i mjesto u doigravanju, 30. jedno mjesto u drugom pretkolu Lige prvaka i tri u pretkolu
Konferencijske lige, i tako dalje, uključujući mjesto pobjednika kupa u Europskoj ligi. Svijet
nikad nema svih 55 UEFA-inih država, pa mjesta rangova kojih nema idu redom sljedećim klubovima
najjačih liga, kolo po kolo, i svako natjecanje ostaje puno: s dvanaest liga 6., 7. i 8. iz
Engleske idu, recimo, u kvalifikacije Lige prvaka. Iza 31. lige nema više mjesta i popis to kaže.
Svako pretkolo prima šesnaest klubova: sa svih 31 rangova u svijetu, mjesta najnižih rangova
iza tih šesnaest ne dobiju ništa (napomene kažu koja; rangovi 26 i niže zapravo počinju u prvom
pretkolu, kojeg Mod Studio nema). Mjesta u kvalifikacijama idu u kola redom ključa, najjača
država u kolo najbliže ligaškoj fazi. Poslije i dalje možeš ručno promijeniti mjesta svake lige
(*Europa* na ligi, *Europska mjesta liga iz igre*): Build uzima mjesta, ne poredak.

**Južnoamerička mjesta** (Lige → Više, 0.1.7, samo za čitanje): za svaku južnoameričku ligu,
četiri iz igre i tvoje, koja mjesta idu u Copa Libertadores, njene kvalifikacije i Copa
Sudamericanu. Mjesta u Libertadoresu za lige iz igre su igrina (Brazil 1.-4. i pobjednik Copa do
Brasil, kvalifikacije 5.-6. i tako dalje -- isto što pokazuje igrin Competition Info); Copa
Sudamericana je od Mod Studija, pa popis pokazuje koliko klubova svaka liga iz igre šalje u nju
kad su tvoja mjesta unutra: prvo tvoje lige, pa Brazil, Argentina, Čile i Kolumbija redom po
jedan klub dok ih ne bude 32. Klub koji je već u Libertadoresu ili njegovim kvalifikacijama
ustupa mjesto sljedećem iz svoje lige. **Provjeri plan** ispiše isti popis kad god svijet ima
mjesto u Libertadoresu ili Sudamericani.

**Imena natjecanja** (Lige → Više, ili Moj svijet → Kupovi): novo ime i logo za kupove, superkupove i kontinentalna natjecanja iz igre -- FA Cup, Ligu prvaka, Libertadores ... -- i za kontinentalne kupove koje svijet gradi (CAF Liga prvaka, Konfederacijski kup, AFC Liga prvaka Two, Copa Sudamericana, CONCACAF Champions Cup, OFC Liga prvaka, AFC Challenge League, CAF Superkup). Ime dobiju sve faze natjecanja. Prazno: ono iz igre. Lige iz igre preimenuju se na *Lige* (odaberi ligu iz igre).

**ID-evi natjecanja** (Lige → Više): svako natjecanje svijeta u igri, lige i kupovi, s njegovim ID-om. Igra ima mjesta za 255; Moj svijet pokazuje koliko ih je zauzeto.

**Poredak liga** (Lige → Više, 0.2.0): poredak država u Select Teamu Master Lige i na popisu momčadi Kick Off / Edit. *Po kontinentima* je poredak igre (Europa, Amerike, Azija, pa Afrika, svaki od A do Ž). *Sve države od A do Ž* stavi ih sve u jedan abecedni niz, a *Moj poredak* ti da da ih složiš kako god želiš (povlačenjem ili Gore / Dolje). Lige jedne države ostaju zajedno, prvi rang prvi, a klupska natjecanja, skupine "Other" i Classic Teams dolaze iza država. Njemačka, SAD i Japan su u Select Teamu u skupinama "Other", pa se pomiču samo u Kick Offu. Nakon toga ponovno izgradi svijet.

**Sezone liga iz igre** (Lige → Više, 0.2.0, eksperimentalno): Japan, Kina, Brazil, Čile i Saudijska Arabija u igri igraju od veljače do prosinca. Označi jednu i njene lige igraju od kolovoza do svibnja kao Europa: sezona počinje u kolovozu, ulazak i ispadanje su ljeti, kupovi idu na datume kolovoz-svibanj, a kontinentalna mjesta dolaze iz tablice završene u svibnju. Tvoj rang ispod jedne od tih liga ide s njom. Kolumbija i SAD igraju Aperturu i Clausuru i ne mogu se pomaknuti. Ponovno izgradi svijet i pokreni novu karijeru.

**Europski klubovi prve sezone** (Lige → Više, 0.1.8): ručno odaberi
klubove ligaške faze Lige prvaka, Europske lige i Konferencijske lige u prvoj sezoni nove karijere.
Tvoji klubovi ulaze prvi, a igra popuni ostalo; od druge sezone odlučuju europska mjesta.

**Klubovi** (kartica Moj svijet): odaberi ligu, pa **Uredi klub** (ime, kratica, grb; ili dvoklik na klub). Sve ostalo je pod **Više ▾**: **Igrači**, **Klub iz igre...**, **NewLife klub...**, **Novi klub ovdje**, **Umetni klub**, **Makni klub**, **Premjesti u drugu ligu...**, **Zalijepi
imena...**, **Učitaj imena iz datoteke...** i **Uvezi grbove...**. Prazno ime postaje `<liga> 01`, `<liga> 02` ...; klub
bez grba dobije numerirani znak. Dresovi se posude od klubova same igre. Takav dres je
licenciran i Edit mod ga ne da mijenjati ("You cannot edit this strip"): označi **Obični dresovi
za Edit mod** na kartici Gradnja (Opcije svijeta) i novi klubovi ne posuđuju nijedan, svaki nosi običan dres
koji Edit > Teams > Strip mijenja kao i svaki drugi, Paste Image uključen.
Uz instaliran Kit Server, **Dresovi u bojama klubova** (kartica Gradnja, Opcije svijeta, uključeno dok ga ne odznačiš, 0.2.1)
svakom novom klubu napravi domaći, gostujući, treći i golmanski dres u bojama njegovog dresa
(NewLifeovim, ili grba kad ih nema), s grbom na prsima i hlačicama, za cijele lige odjednom kad
svijet uđe u igru. Grb koji staviš kasnije (Uvezi grbove) ide na dresove pri idućem uključivanju.
Klub s vlastitim Kit Server dresom, ili samo s numeriranim znakom, ne dobije ga.
Tvoj vlastiti redak za dres u `map.txt` (onaj koji si postavio na kartici *Dresovi*, za dres koji
je u knjižnici) uvijek pobjeđuje: Build za taj klub ne napravi dres, ne stavi mu dres iz paketa i
ostavi tvoj redak uključen (0.2.4; 0.2.3 ga je na svakom Buildu isključivao zbog dresa iz paketa
liga). Imena zadržavaju slova s kvačicama (FK Željezničar); kratica od tri slova ih nema, kao ni u
igri, pa tamo Č, Ž, Đ postaju C, Z, D. Poredak lige od A do Ž u datotekama igre stavlja Đakovo
pod D, a Šibenik pod S (0.2.4). Nakon **Builda** miš iznad imena kluba pokazuje njegov ID u igri
(**ID kluba**).

**Lica iz paketa lica za nove igrače** (kartica Gradnja, Opcije svijeta, zadano uključeno):
svaki novi igrač bez vlastitog lica dobije lice iz paketa lica za regene koje odgovara njegovoj
nacionalnosti. Isključeno: novi igrači zadrže izgled koji im da igra, ili onaj koji si postavio u
igrinom Edit modu. Vrijedi od idućeg Builda.

**Trener**: u **Uredi klub** novog kluba možeš upisati ime trenera. Prazno: izmišljeno ime od igrača države kluba (hrvatski klub dobije ime poput `Tomislav Krovinović`; isto na svakom Buildu), ili numerirano (`FL M0001` ...) za državu iz koje igra ima malo igrača. **Slika trenera** ispod daje treneru sliku (isto kao **Slika trenera...** na kartici Igrači); *Lige* (liga iz igre) > **Uredi klub** ima je i za klubove igre.

**Boje dresova**: **Boje domaćeg dresa** i **Boje gostujućeg dresa** u **Uredi klub**: Build posudi
igrin dres najbliži tim bojama, a **Dresovi u bojama klubova** ih koristi.

**Formacija**: u **Uredi klub** novog kluba možeš mu dati vlastitu formaciju; *Kao liga* zadržava formaciju lige. Teren ispod popisa pokazuje gdje tko stoji.

**Kapetan i izvođači prekida** (0.2.4): Build svakom klubu i reprezentaciji koji ih nemaju da
kapetana (igrača s vještinom Captaincy, inače najjačeg i najiskusnijeg) i izvođače penala,
slobodnih udaraca i kornera, od igrača iz polja među prvih jedanaest. Klub iz igre koji ima svoje
zadržava ih. Svijet izgrađen prije 0.2.4 posvuda ima golmana za kapetana: izgradi ga opet i
pokreni novu karijeru.

**Domaći stadion** (0.1.7): u **Uredi klub** stadion iz knjižnice Stadium Servera za klub; mjesto i ime popune se iz mape, ime možeš promijeniti. Upiše se u `map_teams.txt` Stadium Servera kad svijet uđe u igru (i kad se svijet u igri ponovno izgradi), pa ID novog kluba nikad ne treba tražiti. Tvoj vlastiti redak za isti klub se za to vrijeme isključi, i opet uključi kad klub ovdje više nema stadion. *Lige* (liga iz igre) > **Uredi klub** ima ga i za klubove igre. Mora biti instaliran Stadium Server (kartica *Stadioni*) ili SPFL26-ov vlastiti modul stadiona (`common\stadiums.lua` s mapom `content\stadiums`): od 0.1.8 Mod Studio piše tamo kad Stadium Server nije instaliran. Igrin stadion izabran kao domaći stadion u utakmici je pravilno osvijetljen (0.2.4; prije je mogao biti potpuno mračan): svijet napravljen prije izgradi opet.

**Klubovi koje igra već ima.** Na mjesto u novoj ligi može doći i jedan od igrinih klubova
umjesto novog: odaberi mjesto, pa **Više → Klub iz igre...**, i traži po imenu, kratici ili ID-u
kluba (**Samo klubovi bez lige** suzi popis). Prozor **Klub iz igre** ispod popisa kaže gdje klub
igra. Klub zadržava ime, grb, dresove, trenera i igrače, a igra samo u tvojoj ligi. Kad u igri
igra negdje (liga, kup, Europska liga ...), biraš tko tamo preuzima njegovo mjesto: **Njegovo
mjesto preuzima klub iz igre koji ne igra nigdje:** (izaberi jedan s popisa) ili **Njegovo mjesto
preuzima novi klub, ime:** (upiši ime). **Zadržava mjesta u kontinentalnim natjecanjima** (0.1.8, #84) mu pušta da i dalje igra Ligu prvaka, Libertadores ili AFC Ligu prvaka u kojoj je: klub kojem je kontinent sve što igra u igri tada se samo seli, a onaj koji igra i ligu iz igre klubu kojeg izabereš predaje samo ligu i kupove. Od druge sezone mjesta tvoje lige odlučuju tko ide. Predsezonski turnir (*Pre-season friendly Cups* u SPFL26) se ne broji: klub ga i dalje igra, kao i klubovi Premier Lige (0.1.7). **Uredi klub** na klubu iz igre mijenja ime, grb, sliku trenera i stadion, kao na *Lige* za ligu iz igre (0.1.7). Tako nijedno natjecanje igre ne mijenja broj klubova;
lige iz igre zadržavaju datume samo s brojem za koji su napravljene. Reprezentacije, klasični i
zadani timovi te klubovi s manje od 18 igrača ne mogu se odabrati. **Novi klub ovdje** (u
**Više**) vraća mjesto novom klubu; siv je osim ako je odabrani klub klub iz igre na tom mjestu
(0.2.4). Klub se više ne vidi u skupinama *Other ... clubs* Master Lige.

**NewLife klub...** (0.1.8, #83, u **Više**) stavlja klubove iz NewLife baze, s njihovim kadrovima, na odabrano mjesto i mjesta iza njega: označi jedan ili više klubova (traženje po klubu ili po ligi) i svaki redom zauzme svoje mjesto. Tako liga koju si napravio rukom dobije prave klubove. Koristi NewLife mapu koju si zadnju otvorio; prvi put je otvori na stranici *NewLife Database*.

**Umetni klub** i **Makni klub** dodaju mjesto ispred odabranog kluba ili ga izbacuju (10 do 24
kluba); imena, grbovi, treneri i promjene igrača idu sa svojim klubovima. Provjeri europska mjesta
lige, pa opet **Build**. Svaka promjena klubova lige traži **novu karijeru**.

**Premjesti u drugu ligu...** (0.1.7) odvede odabrani novi klub na kraj druge nove lige, s imenom, kraticom, grbom, trenerom, formacijom, dresovima, NewLife ID-em i promjenama igrača; liga iz koje odlazi ima klub manje. Klub iz igre se seli preko **Klub iz igre**: izvadi ga iz jedne lige, stavi u drugu.

**Lige iz igre** (odaberi jednu na *Lige*): novo ime ili logo, pa **Zadrži promjene lige** (**Poništi promjene lige** vraća natrag); **Uredi klub** za grb, ime, sliku trenera i stadion kluba. Popis Klubovi pokazuje koliko će igrača imati svaki klub: njegov kadar, manje igrači koji su maknuti ili koje je doveo drugi klub, plus dodani i dovedeni. Takva promjena se odmah pamti u datoteci tvog svijeta, kao i svaka druga.

**Uvezi grbove...** (0.1.8, *Klubovi* → Više; za lige igre *Lige* → Više): grbovi za mnoge klubove odjednom. Odaberi mapu sa slikama; svaka se spaja s klubom po imenu datoteke -- imenu kluba (`Alianza Lima.png`, `alianza_lima_r_l.png`) ili ID-u kluba (`2287.png`, `e_2287_r.png` iz paketa grbova). Ime se spaja samo po cijelim riječima, a reprezentacija uzima sliku samo po svom ID-u (0.2.4; prije je "termalica" mogla otići Maliju). Popis pokaže svako spajanje s kvačicom; makni kvačicu s krivog prije **U redu**. **Spoji s** može biti i jedna liga tvog svijeta: spajaju se samo njeni klubovi, a mapa nazvana po ligi tvog svijeta (`Torneo DIMAYOR II`) sama je odabere, pa klub istog imena u drugoj ligi ne dobije ništa. Klub koji već ima grb zadržava ga, osim ako je označeno **Zamijeni grbove koji su već postavljeni**. Slike ostaju u toj mapi i Build ih čita odande, zato je zadrži. (Spajanje po imenu je ideja iz Xxspeddove skripte za grbove.)

**Zamijeni ligu s klubom...** (0.1.7, *Lige*, liga iz igre → Više): dva kluba iz liga igre zamijene mjesta -- klub koji je ušao za onaj koji je ispao, klub lige jedne države za klub druge. Svaki preuzme mjesta drugoga u ligi, kupovima i europskim natjecanjima, pa svaka liga igre zadrži broj klubova. Klub u novoj ligi tvog svijeta ne može se mijenjati. **Poništi izmjene kluba** vraća zamjenu. Zatim opet **Build** i nova karijera.

> **Edit datoteka.** Ako u mapi sa spremanjima igre postoji Edit datoteka (`EDIT00000000`), ona
> ima prednost za imena klubova. Makni je negdje drugdje da vidiš svoja imena.

### Igrači

**Igrači** (kartica Moj svijet) mijenja kadar bilo kojeg kluba: novih klubova tvog svijeta i klubova same igre.
Odaberi klub (ili **Više → Igrači** na Klubovi), pa igrača:

- **Ime**, **broj na dresu**, **pozicija** i pozicije na kojima može igrati (A = prirodna,
  B = može igrati), jača noga, visina, težina, dob, nacionalnost, stil igre;
- sve **sposobnosti** i **vještine** (imena su ona iz igre);
- **Ocjena**: ocjena koju pokazuje igra, izračunata kao u igri iz sposobnosti, s težinama za
  svaku poziciju (najviše bod-dva razlike). Promjena pomiče svaku sposobnost igrača za isti iznos,
  a nekoliko najvažnijih za njegovu poziciju za jedan više, pa ocjena bude baš upisani broj. Igrač novog kluba nema ime dok ga Build ne numerira
  (FL P00001 ...); upiši ime u **Ime** da dobije tvoje; od 0.2.0 takav kadar počinje na razini
  svog ranga (oko 72 u prvoj ligi, do 57 od petog ranga naniže);
- **Lice**: **Odaberi...** mapu s licem (odjeljak 8.1). **Makni** vraća lice iz igre. Novi igrač
  bez njega dobije lice iz paketa lica za regene koje odgovara njegovoj nacionalnosti, s malom
  slikom (0.1.5.5, uz instalirane module i uključen `fl26regen`, poglavlje 5). Lice napravljeno za
  drugog igrača donese i izgled njegova tijela, pa ruke i noge imaju boju kože tog lica (0.1.9);
- **Mala slika**: **Odaberi...** sliku (PNG ili JPG) za malu sliku igrača na popisima momčadi, bez
  vlastitog lica. Build je svodi na 180 x 180; ima prednost pred slikom iz mape lica;
- **Gore u redoslijedu / Dolje u redoslijedu**: redoslijed kadra. Prvih jedanaest počinje
  utakmicu;
- **Dodaj igrača** (kopija igrača kojeg odabereš, s novim ID-om; samo klubovi iz igre),
  **Makni iz kluba** (ponovni pritisak to vraća). Novi klub zadržava barem 18 igrača, računaju
  se i oni dovedeni u njega; klubovi iz igre nemaju minimum;
- **Najboljih jedanaest** stavi najjačeg igrača na svako mjesto (igrač koji može igrati to
  mjesto, ali je registriran negdje drugdje, broji se sa 6 manje, a ostaje za svoje mjesto kad bi
  ono ostalo prazno); **Razina momčadi...** (u **Više**) podigne ili spusti sve sposobnosti cijelog
  kadra;
- **Teren** (novi klubovi): prvih jedanaest u formaciji kluba. Povuci igrača s popisa na mjesto,
  ili povuci jedno mjesto na drugo da ih zamijeniš; klik na mjesto odabere igrača koji tamo stoji.
  Formacija koju je Build izabrao za klub vidi se ovdje; kad promijeniš njen redoslijed, klub
  zadrži tu formaciju;
- **Izvezi CSV... / Uvezi CSV...** (u **Više**): uredi kadar u tabličnom programu. Prvo izvezi,
  promijeni ćelije, pa uvezi iste stupce natrag.
- **Uvezi momčad iz tablice...** (u **Više**): bilo koja tablica igrača postaje kadar kluba --
  ručno upisana, popis momčadi kopiran sa stranice ili izvoz iz druge nogometne igre. Stupci se
  prepoznaju po imenu (ime, pozicija, dob ili datum rođenja, nacionalnost, visina, noga, broj na
  dresu, ukupna ocjena i bilo koje ocjene) i prikažu se da ispraviš krivo prepoznat. Ono čega u
  tablici nema dolazi od igrača iz igre iste pozicije i ocjene; ocjene na skali 1-20 rastežu se
  na igrinu 40-99. Igrači iz tablice zauzimaju mjesta u klubu redom kadra: novi klub zadržava
  svojih 30 mjesta (manje igrača = ostali odlaze, najviše do 18), klub iz igre dobije ili izgubi
  igrače da se poklopi.

Svaka promjena zapiše se u svijet kad napraviš **Build**; datoteke igre ostaju kakve jesu.
**Poništi promjene ovog igrača** i **Poništi sve promjene ovog kluba** vraćaju ono iz igre.

Popis klubova ima i **Reprezentacije** i **Ostali klubovi (bez lige)**: momčadi koje igra drži izvan svih liga (reprezentacije, klubovi koji igraju samo kup ili kontinentalno natjecanje). Njihovi igrači uređuju se na isti način.

#### Transferi, reprezentacije, ID-evi, slika trenera

- **Dovedi igrače...** (klub): popis svih igrača igre i tvojih novih klubova, s filtrom po
  nacionalnosti i traženjem po imenu; više njih biraš s Ctrl ili Shift. Prelaze u ovaj klub, a
  stari ih klub gubi (transfer). **Transfer u...** radi isto s druge strane: odabrani igrač
  prelazi u klub koji izabereš. Na popisu piše *iz: ...* kod kluba koji ga dobiva i *u: ...* kod
  kluba koji napušta; **Makni iz kluba** na bilo kojem od ta dva retka otkazuje transfer. Klub
  ima najviše 40 igrača. Ako klub završi s više od 40 (reprezentacija s više od 26), Build
  zadrži prvih 40 i nastavi, a log Builda imenuje klub i igrače koji su ostali vani; kad je klub
  u tvom svijetu dvaput, imenuje obje lige.
- **Pozovi igrače...** (reprezentacija: u popisu liga odaberi *Reprezentacije*): popis se otvara
  na državi te reprezentacije. Igrači ulaze u reprezentaciju **i ostaju u svojim klubovima**,
  kao u igri. **Makni iz kluba** miče igrača iz reprezentacije (ne iz kluba). Reprezentacija ima
  najviše 26 igrača; igrač je u jednoj reprezentaciji u isto vrijeme. Tvoj popis upisuje se u
  podatke igre, ali u karijeri Master Lige igra sama bira reprezentacije, pa tamo tvoji pozivi
  ne ostaju.
- Igrač koji dođe ide na kraj redoslijeda kadra sa slobodnim brojem na dresu; kadar iz kojeg je
  otišao zatvara redoslijed iza njega.
- Stupac **ID igrača**: ID svakog igrača -- igrin, onaj koji si upisao ili onaj koji je novom
  igraču dao zadnji **Build** (izgradi jednom prije nego radiš minifaces ili lica za nove igrače).
  **Izvezi CSV...** ga zapisuje kao `player_id`; Uvezi CSV taj stupac preskače.
- **ID kluba** (pokraj kluba) i **ID igrača** (kartica Osnovno): samo za tvoje **nove** klubove i
  igrače. Prazno = sljedeći slobodan ID pri Buildu. Upiši ga kad je paket dresova, grbova ili lica
  rađen za određeni ID. ID kluba: od prvog iza klubova igre (71578) do 81919; ID igrača: iznad
  najvećeg u igri do 399999; nikad onaj koji već ima igra ili drugi novi klub ili igrač. ID se
  koristi svugdje gdje svijet spominje klub ili igrača (kadrovi, natjecanja, dresovi, grbovi,
  trener, lica). Klubovi i igrači igre zadržavaju svoje ID-eve: njeni dresovi, lica i tvoji
  saveovi vezani su uz njih.
- **Igrači zadržavaju ID-eve kad opet gradiš** (0.2.4). Build svakog igrača svijeta nađe po tome
  tko je (po NewLife ID-u, inače po imenu i datumu rođenja) prije nego po mjestu u kadru, pa igrač
  koji se pomaknuo u kadru ili promijenio klub zadrži svoj ID, a stara karijera ga ne pokaže kao
  nekog drugog.
- **Slika trenera...**: PNG ili JPG za trenera kluba. Build je svodi na 256 x 256 i stavlja u
  `common/render/symbol/coach/coach_<ID trenera>.png`, gdje igra drži slike trenera. Ponovni
  pritisak miče sliku.

### 8.1 Lica

Mod s licem je mapa ovakva (kako ih autori lica dijele):

```
<bilo koje ime>\
    #Win\face.fpk
    #Win\face.fpkd
    sourceimages\#windx11\*.ftex
    portrait.dds            (ili <id>.dds, nije obavezno)
```

Tu mapu odaberi za igrača. Pri **Buildu** lice se kopira u svijet i usmjeri na tog igrača, pa
radi i za novog igrača čiji ID nije postojao kad je lice napravljeno, i nikad ne zamijeni lice
iz igre. Bez male slike slika igrača u izbornicima ostaje prazan obris; samo lice se svejedno
vidi. Mapa s više lica unutra se odbija: odaberi točno ono jedno koje misliš.

### 8.2 Izgradi, uključi, igraj

**Zadrži vlastiti Team.bin svijeta.** On je u mapi svijeta i drži klubove i doigravanja svijeta. Zamijeniš li ga Team.bin-om iz igre, i jedno i drugo nestane, a sastavi izgledaju popravljeni samo zato što klubova svijeta više nema (GitHub #75). Radije svijet izgradi ponovno.

**Gradnja** je prva kartica **2. Moj svijet**. Napomena na vrhu kaže da je za moddere: za
igranje gotovog modpacka ne treba ti. Ispod nje: datoteka u kojoj se tvoj svijet čuva, gumbi
**Novi svijet**, **Otvori svijet...** i **Dodaj lige** (za vlastiti svijet) i veliki gumb
**Izgradi i instaliraj**.

**Izgradi i instaliraj** napravi 0, 2 i 3 odozdo jednim klikom, pa pokaže što je ostalo: prozor
**Build gotov** s kvačicom za **Svijet izgrađen**, **Lige i klubovi**, **Moduli instalirani i
uključeni** i **U igri**, a pod **Prije igre** podsjetnik da pokreneš novu Master Ligu. Može i
**Makni Edit save u stranu** (Edit save od prije Builda skriva nova imena i kadrove) i **Zatvori
igru**. Kartica na Početna ima gumb **Idi na Gradnju** koji te dovede ovamo. Dok se svijet gradi,
redak stanja Moj svijet i donja traka pokazuju dosadašnje vrijeme i korak na kojem je
(`Gradim... 3:12 · squads: filling them`), a prozor se može slobodno koristiti. Ili korak po
korak, pod **Korak po korak i Izvezi svijet** na kartici **Gradnja**:

0. **Postavi module** — jednom, i opet nakon nove verzije programa. Datoteke koje zamijeni
   čuvaju se u **Točke vraćanja**.
1. **Provjeri plan** — što će se napraviti; ništa se ne zapisuje.
2. **Izgradi svijet**.
3. **Uključi ga** — stavi ga u igru (aktivni svijet u `sider.ini`).
4. Pokreni igru, vrati se i stisni **Nakon pokretanja: provjeri**. Pročita `sider.log` i kaže,
   modul po modul, je li svijet preuzet.

**Aktiviraj** na kartici drugog svijeta u Moj svijet napravi korak 3 za taj svijet (i zamijeni
mapu saveova, odjeljak 3.1). Svijet u igri umjesto toga pokazuje **● Aktivan**. Pokreni novu
Master Ligu nakon što aktiviraš drugi svijet.

**Novi logo ili grb gradi se u sekundama** (0.2.4). Kad su se od zadnjeg Builda promijenile samo
slike (logo lige ili kupa, grb kluba, zastava države), Build nacrta samo njih ponovno, a ostatak
svijeta ostavi kakav jest. Svaka druga promjena (ime, klub, igrač) je puni Build. Svijet iz zipa
se na tvom računalu jednom izgradi cijeli; nakon toga su i njegove promjene slika brze.

**Gotov svijet se ovdje ne gradi** (0.2.4). Svijet instaliran iz zipa je već izgrađen, a Build
bi ga zamijenio svijetom otvorenim u Mod Studiju. Zato su, dok je gotov svijet u igri, koraci
gradnje sivi s napomenom, Početna kaže **Spremno za igru**, a Gradnja objasni što umjesto toga:
stisni **Pokreni igru**, ili prvo stavi svoj svijet u igru (**Aktiviraj** na njegovoj kartici).
Drugi svijet (NewLife, novi svijet) se i dalje može izgraditi dok je gotov uključen: Build prvo
pita i kaže da gotov svijet isključuje; **Aktiviraj** na njegovoj kartici ga vraća, s njegovim
karijerama. Da promijeniš sam gotov svijet: **Omogući uređivanje...** (odjeljak 3.1).

**Uključi Konferencijsku ligu** (kartica Gradnja, pod Opcije svijeta, zadano uključeno) izgradi i
Konferencijsku ligu: ligašku fazu od 36 klubova i veljačko doigravanje, kao kod druga dva
natjecanja. Liga prvaka i Europska liga dobivaju ligašku fazu od 36 i veljačko doigravanje u
svakom slučaju. Isključeno: bez Konferencijske lige. (Mod Studio 0.1.3 i starije verzije su uz
isključenu opciju ostavljale Ligu prvaka i Europsku ligu u igrinim skupinama po četiri, koje mod
ne zna voditi -- pa su se kvarile; Provjere označe takav svijet: izgradi ga ponovno.) **Logo
Konferencijske lige** pored toga: tvoja slika za nju; prazno: nacrta se UECL amblem (igra ga
nema). **Ime Konferencijske lige** ispod: kako je igra zove, *FL Conference League* kad je prazno
(upiši *UEFA Conference League* ako želiš); novo ime traži ponovnu izgradnju svijeta. Oboje
koristi i **Izgradi samo europske kupove...**.

> **Europska mjesta.** Mjesta koja daš svojim ligama dolaze iza mjesta liga same igre. Svako
> natjecanje prima 36 klubova; mjesta iza 36. ne dobiju ništa, i **Provjeri plan** to kaže.
> Nove lige bez mjesta nikoga ne šalju u Europu, i Početna na to upozori. Branitelji naslova
> idu prvi: pobjednici Lige prvaka i Europske lige uzimaju dva izravna mjesta u Ligi prvaka,
> pobjednik Konferencijske lige jedno u Europskoj ligi. Ždrijeb ligaške faze prati UEFA-ina
> pravila: nijedan klub ne igra protiv kluba iz svoje države, i najviše dva protivnika dolaze
> iz iste druge države.
>
> **Kolovoške kvalifikacije.** Mjesto u *kvalifikacijama* šalje klub u kolovoške kvalifikacije
> tog natjecanja: do tri kola (0.1.7) -- 2. pretkolo (dani 220 i 225), 3. pretkolo (229 i 236) i
> doigravanje (243 i 250; Liga prvaka 244 i 251) -- svako od 16 klubova, dvije utakmice; osam
> najjačih momčadi je nositelj (uzvrat doma), dva kluba iste države se ne sastaju. Pobjednici idu
> u sljedeće kolo, iz doigravanja u ligašku fazu. Poraženi padaju kao kod UEFA-e: iz
> *kvalifikacija Lige prvaka* poraženi u doigravanju idu u Europsku ligu, u 3. pretkolu u
> doigravanje Europske lige, u 2. pretkolu u 3. pretkolo Europske lige; iz *kvalifikacija
> Europske lige* isto tako u Konferencijsku; poraženi u *kvalifikacijama Konferencijske lige*
> ispadaju. Prva mjesta na popisu idu u doigravanje, kasnija u ranija kola. Koliko kola svijet
> dobije ovisi o mjestima, a svako kolo Konferencijske lige traži 8 klubova više: 116 mjesta u
> Europi za samo tri doigravanja, 132 za svih devet kola. S mjestima same igre to su samo
> doigravanja; sažetak Builda kaže koja kola svijet dobiva (*August qualifying*). Svako
> doigravanje uzme 8 izravnih mjesta natjecanjima u koja idu njegovi pobjednici i poraženi: sa
> sva tri Liga prvaka prima 28 klubova izravno, Europska i Konferencijska liga po 20. Mjesto iza
> toga igra se u kvalifikacijama tog natjecanja. Mjesta tvojih liga u kvalifikacijama dolaze
> prije mjesta iz igre (Portugal, Škotska, Grčka, Danska ...).

Onda **započni novu karijeru Master Lige** (ili Become a Legend). Nove lige su pod svojom
državom u Select Teamu i Kick Offu. U popisima Kick Offa i Edita nova azijska država dolazi
prije *Other Clubs (Asia)*, južnoamerička uz one iz igre (iza Kolumbije, prije MLS-a, 0.1.7),
CONCACAF država iza MLS-a, a afričke i oceanijske (igra za njih nema odjeljak) iza Azije.

> **Kupovi drugih kontinenata.** Kad tvoje lige šalju klubove u CAF Ligu prvaka, CAF
> Konfederacijski kup, AFC Ligu prvaka Two, AFC Challenge League, Copa Sudamericanu, CONCACAF
> Champions Cup ili OFC Ligu prvaka (zadnja tri su nova u 0.2.0), **Build** napravi i te kupove.
> Svaki dobije 32, 16, 8 ili 4 kluba: prvo mjesta tvojih liga, zatim ga popune igrine lige s tog
> kontinenta (Azija, Južna Amerika, a za CONCACAF kup MLS); za AFC Challenge League to su 11.-14.
> iz J1 League, 10.-13. iz kineske Super lige i 11.-14. iz saudijske Pro lige. S 8 ili više igraju
> se skupine po četiri pa nokaut; ispod 8 samo nokaut. CONCACAF Champions Cup je uvijek nokaut, s
> najviše 16 klubova, kao pravi, a dva kluba iste lige ne sastaju se u njegovom prvom kolu kad se
> to može izbjeći. Pune se krajem kolovoza, iz tablica liga. Klub koji već igra Copa
> Libertadores, njene kvalifikacije ili AFC Ligu prvaka ne ulazi u njihov ždrijeb. CAF ili OFC
> kup s manje od 4 mjesta prvo uzme mjesta sljedećeg CAF kupa (s dva i dva CAF Liga prvaka dobije
> sva četiri), zatim sljedeća mjesta tvojih liga. **CAF Superkup** (kartica Gradnja, Opcije
> svijeta, zadano uključen) spoji pobjednike dvaju CAF kupova u jednoj utakmici krajem srpnja, od
> druge sezone karijere.
>
> Liga koja može poslati klub u Copa Libertadores, AFC Ligu prvaka ili Svjetsko klupsko prvenstvo
> drži se podalje od njihovih dana utakmica (0.2.4): nema kola lige dan prije ni dan poslije.

> **Ždrijeb kupa države** (kartica Gradnja, Opcije svijeta) odlučuje kako se izvlače nacionalni
> kupovi tvojih liga. *Nositelji* (zadano): klubovi prvog ranga dobiju slobodne prolaze i kasnija
> kola, ravnomjerno su raspoređeni u obje polovice ždrijeba i u ranim kolima igraju protiv klubova
> nižih liga, a ne jedni protiv drugih. *Nasumično*: slijepi ždrijeb. *Isključeno*: igra puni
> ždrijeb redom popisa, što sve najjače klubove stavi na jednu stranu. U datoteci svijeta to je
> redak `cupdraw seeded|random|off`; `cupdraw <cup regulation> seeded|random|off` postavlja jedan
> kup.

> **Spremanja pripadaju svijetu.** Karijera spremljena s jednim svijetom u igri treba isti taj
> svijet da se učita. Kad je uključeno **Svaki svijet ima svoje karijere** (zadano, odjeljak 3.1),
> Mod Studio umjesto tebe drži karijere svakog svijeta odvojeno.

**Tvoj svijet se sam sprema** trenutak nakon svake promjene (donja traka kaže **Tvoj svijet je
spremljen**): u svoju `.json` datoteku kad je ima, inače u
`%APPDATA%\FL26ModStudio\recipes\<svijet>.json`, a Mod Studio ga pri pokretanju opet otvori.
**Datoteka → Spremi svoj svijet kao...** sprema kopiju pod drugim imenom, **Datoteka → Otvori
svijet...** vraća neki svijet, a **Datoteka → Novi svijet** počinje prazan.

**Izgradi samo europske kupove...** (kartica Gradnja, Opcije svijeta; **Samo europski kupovi...** na Početna) gradi svijet samo s novom Ligom
prvaka i Europskom ligom -- ligaška faza od 36 i veljačko doigravanje -- te Konferencijskom ligom
kad je označeno **Uključi Konferencijsku ligu**. Bez novih liga; klubovi i lige igre ostaju kakvi
jesu, a tvoj svijet se ne mijenja. Pita za ime svijeta (zadano `_FL26Euro`), izgradi ga i ponudi
da ga aktivira. U igri može biti samo jedan svijet, pa je ovo umjesto svijeta s novim ligama:
svijet s novim ligama već ima novi format.

> **Egzibicijske lige i Master Liga.** Liga označena kao *Samo za egzibiciju* nikad ne igra sezonu
> Master Lige, ali igra ima jedan popis momčadi za Kick Off i Master Ligu, pa se njeni klubovi
> i dalje vide kad biraš klub za novu karijeru. Ne počinji karijeru s nekim od njih. **Provjeri
> plan** i **Build** to i kažu.

### 8.3 Granice

| | |
|---|---|
| Novih liga po svijetu | Nema stalnog broja. Svaka liga, kup i superkup svijeta uzima jedno od 255 igrinih natjecanja (sama igra koristi oko 90); **2. Moj svijet** pokazuje koliko ih je zauzeto. Naš testni svijet igra 86 novih liga. |
| Novih država | 99 |
| Klubova po ligi | 10 – 24 |
| Novih klubova ukupno | oko 1.500 (redak na dnu stranice NewLife Database kaže koliko ih stane u tvoju igru) |
| Koliko puta se klubovi sretnu | 1 – 4 |
| Liga koje se dijele na pola | 2 po svijetu |
| Rangova u jednoj državi | do 7. |
| Igrača po novom klubu | 30 na početku (vrlo velik svijet dobije manje kadrove, nikad ispod 22); makni do 18; dovedeni igrači do 40 |
| Igrača po reprezentaciji | 26 |
| Nacionalni kup | prvi rang i rang ispod, do 44 kluba. Do 32 veličine su 2-16, 18, 20, 24, 28, 30 i 32 -- najveća koja stane (22 kluba daju kup od 20); 33 do 43 postanu 32; 44, ili veličina koju ima neki kup iz igre, ostaje; više od 44: samo prvi rang |

### 8.4 NewLife Database: pravi klubovi i igrači

NewLife baza (NewLife Database) je zaseban download s pravim klubovima i igračima za nove lige:
imena, datumi rođenja, pozicije i ocjene na skali igre te boje klubova. Svaki klub i igrač u njoj
ima svoj ID, isti u svakoj verziji baze. Nije na GitHubu: nabavi je s NewLife kanala našeg
[Discorda](https://discord.gg/StQqtk3G3M). Dolazi u dijelovima, jedan po kontinentu (velik u više
njih), plus *Free agents*, svaki manji od 10 MB. Skini samo dijelove koje želiš.

1. Stavi skinute dijelove u jednu mapu. Ne raspakiravaj ih: Mod Studio čita zipove takve kakvi
   jesu. (To su LZMA zipovi: 7-Zip ih otvara, Windowsov preglednik zipova ne.)
2. **2. Moj svijet → NewLife Database** (gumb desno od kartica), pa **Otvori NewLife
   Database...** i odaberi tu mapu. (Ili ispusti mapu na **+ Dodaj...**.) Popis pokazuje sve lige
   iz tih dijelova: državu, klubove, klubove koje igra već ima (*U igri*), igrače i razinu. Klikni
   ligu da vidiš njene klubove. Klik na naslov stupca (Liga, Država, Klubovi, Igrači, Razina) slaže
   popis po njemu, drugi klik obrne redoslijed (0.2.0); popis se otvara složen po državi.
3. Odaberi jednu ili više liga (Ctrl ili Shift za više) i stisni **Dodaj u svoj svijet**. Svaka
   postaje nova liga sa svojim klubovima i njihovim kadrovima, prvi rang svoje države. Rang,
   format, europska mjesta i ostalo mijenjaš na *Lige*, kao za svaku drugu ligu.
4. **Izgradi i instaliraj** i pokreni novu karijeru (odjeljak 8.2).

- **Vlastiti sastav lige** (0.1.7): makni kvačicu klubu u popisu desno da ostane vani, a
  **Dodaj klub iz druge lige...** dovodi klubove bilo koje lige iz izdanja -- recimo, prva liga
  ove sezone je prošlosezonska s dva kluba koja su ušla. Redak lige dobije `*`. Klub može biti
  samo u jednoj ligi tvog svijeta. Ako je već u nekoj od tvojih liga pod drugim imenom, poruka
  imenuje tu ligu i ime koje klub tamo ima.
- Liga prima 10 do 24 kluba, nove i igrine zajedno; ostale su sive. Liga same igre (Premier League, Championship ...) je isto siva (0.1.9): već je u igri, dovedi je u NewLife sezonu s **Više → Dovedi lige igre u ovu sezonu...** niže. Redak na dnu broji nove klubove
  tvog svijeta prema broju koji igra prima.
- Klubovi koje igra već ima ulaze u novu ligu kao klubovi iz igre (poglavlje 8, *Klubovi koje
  igra već ima*), na zadnja mjesta, sa svojim imenom, grbom, dresovima i igračima. Onaj koji
  igra i neko natjecanje igre (Basel i Young Boys igraju Europsku ligu) treba klub koji tamo
  preuzima njegovo mjesto: *Klubovi*, odaberi ga, **Više → Klub iz igre...**. Do tada Build kaže
  koji su to. Klub kojem je jedino natjecanje igre kontinentalno (Ludogorets u kvalifikacijama
  Lige prvaka) sam ga nastavlja igrati (0.1.9).
- Igrač kojeg igra već ima (isti igrač pod istim imenom, recimo Urbański u Górniku u igri i u
  Legiji u NewLifeu) prelazi u NewLife klub umjesto da nastane drugi put (0.1.7): zadržava lice,
  ime i ID, a uzima NewLifeovu poziciju i ocjene. Ostaje gdje jest kad bi njegov stari klub pao
  ispod 18 igrača ili kad ga je već uzela ranija liga; tada ga NewLife klub nema, ne kopira se
  (0.1.8).
- NewLife klub dobiva vlastiti ID u svijetu (0.1.8), u bloku koji igra čita za klubove, iza
  ID-eva koje graditelj daje svojim klubovima. Miš iznad njegova imena na *Klubovi* ga pokazuje
  (**ID kluba**), a Kit Serverov `map.txt` je vezan uz njega. Svijet izgrađen prije 0.1.8 treba
  izgraditi ponovno i započeti novu karijeru da dresovi prate. Od 0.1.8 klub zadržava ID svog
  prvog Builda (tvoj svijet ga pamti): micanje, dodavanje ili ažuriranje druge lige ga više ne
  pomiče.
- **Novija verzija NewLifea** (0.1.8): stavi njene dijelove u mapu (ne pomiješane sa starima),
  **Otvori NewLife Database...** na toj mapi i stisni **Više → Ažuriraj moje lige na ovu
  verziju**. Svaka liga dodana iz starije verzije je na popisu s onim što se mijenja (*sada 16
  klubova, 18 u NewLife 1.3 (5 novih, 3 kojih nema)*) i kućicom **Zadrži moje klubove**:
  označeno, liga zadržava svoje klubove; neoznačeno, dobiva klubove koje ima u novoj verziji.
  Kadrovi u oba slučaja dolaze iz nove verzije, a liga zadržava ime, rang, format, europska
  mjesta i kupove; klub koji ostaje zadržava trenera i grb koji si izabrao, a tvoji vlastiti
  klubovi koje si stavio u ligu ostaju. Sposobnosti, pozicije i ostalo u kadrovima dolaze iz nove
  verzije; lice koje si povezao ili mala slika koju si izabrao na *Igrači* ostaju uz igrača koji
  je još u klubu (0.2.0, #111). Klub iz igre čije je mjesto otišlo drugom klubu ostaje novi klub
  u tvojoj ligi (0.2.4). Zatim Build i nova karijera.
- **Lige same igre u NewLife sezoni** (0.1.8): s otvorenom NewLife bazom stisni **Više → Dovedi
  lige igre u ovu sezonu...**. Svaka liga igre koju izdanje ima je na popisu s onim što joj se
  događa, svaka s kućicom. Klub koji je ušao ili ispao između dviju liga igre mijenja mjesto s
  klubom koji ide obrnuto (Burnley u Championship, Coventry u Premier League), kao što radi
  *Zamijeni ligu s klubom...*. Klub koji je ispao iz liga igre (Leicester u League One) postaje
  klub koji je ušao na njegovo mjesto (Bolton): njegovo ime, kratica, grb i kadar; dres, stadion i
  trener ostaju. Kad baza za taj klub nema grb, mjesto dobije štit u bojama dresa novog kluba
  (0.2.4). Svaki klub označenih liga dobiva NewLife kadar: igrači koje igra ima dolaze iz starog
  kluba, oni kojih nema se dodaju, a igrači koje NewLife ima u drugom klubu odlaze. Igrač kojeg
  NewLife još ima u ovom klubu ostaje, dok god klub ima mjesta (najviše 40; 0.2.4); log Builda
  imenuje svakoga za koga nije bilo mjesta. Ocjene se stavljaju na skalu igre, mjereno na
  igračima koje imaju oboje, pa zvijezda završi gdje je igra ocjenjuje (0.2.0; prije je vrh bio
  2 do 4 više). Lige zadržavaju broj klubova, format i kupove. Klubovi koje si već mijenjao rukom
  (zamjena, novo ime, klub nove lige, promjene igrača) ostaju kakvi jesu. Ponovno s novijom
  verzijom zamjenjuje ono što je napravila starija; **Više → Poništi lige igre** vraća sve. Build
  i nova karijera.
- NewLife klub dobiva grb u obliku štita u svojim bojama i igrin dres najbližih boja, dok mu ne
  daš svoje (**Uredi klub**).

## 9. Paketi liga: podijeli cijelu ligu

Moder napravi ligu jednom — klubove, imena, grbove, logotipe, kadrove, lica — i podijeli **jednu
datoteku `.fl26pack`**. Svatko je doda u svoj svijet i izgradi.

Stranica **Paketi liga** je pod **2. Moj svijet → Više ▾ → Paketi liga**. Nabraja pakete u tvom
svijetu, s **Dodaj paket...**, **Napravi paket...** i **Ukloni iz svog svijeta**.

**Napravi paket** (**Napravi paket...** na toj stranici, ili **Datoteka → Napravi paket liga...**):

1. Ime, autor, verzija i kratak opis.
2. Označi lige koje idu unutra (**Označi sve** / **Odznači sve** iznad popisa). Liga ispod
   druge nove lige mora ići s njom.
3. Po želji i **moje promjene postojećih liga, klubova i igrača**.
4. **Što ide unutra** (0.1.8): sve je označeno; makni kvačicu s onoga što ne želiš dijeliti --
   **Kadrovi**, **Lica i portreti igrača**, **Grbovi i logotipi liga**, **Treneri**, **Boje
   dresova**, **Domaći stadioni** (linija za Stadium Server, ne sam stadion) i (0.2.1)
   **Dresovi** (Kit Server dresovi klubova) i **Scoreboardi** (Scoreboard Server scoreboard svake
   lige). Dresovi i scoreboardi uzimaju se iz tvoje igre kakav je svijet sada: što god
   kit-server\map.txt i scoreboard-server\map_competitions.txt daju njegovim klubovima i ligama.
   Paket bez kadrova ide preko baze kadrova koja se ažurira zasebno, kao NewLife, bez vraćanja
   starih kadrova.
5. **Spremi paket...**. Datoteka (`.fl26pack`) nosi slike, lica, dresove i scoreboarde, a ne
   putanje na tvom računalu. Tko ga doda, dobije dresove i scoreboarde na mjestu sa svojim ID-evima
   klubova i liga kad napravi Build (Kit Server / Scoreboard Server moraju biti instalirani); klub
   kojem je na kartici *Dresovi* dao vlastiti redak za dres zadrži taj dres (0.2.4), a dres iz
   paketa ostaje sa svojim klubom kad se klub makne, umetne ili premjesti, ili kad se liga ažurira
   na noviji NewLife. Dresovi dodaju oko 10 MB po ligi, a scoreboard oko 7 MB, pa je takav paket
   često preko Discordovog limita od 10 MB: podijeli ga preko cloud servisa (Google Drive,
   Dropbox, MEGA ...); program to kaže kad je datoteka veća.

**Dodaj paket** (**Dodaj paket...** na toj stranici, **Dodaj paket liga** pod **Brze radnje** na
Početna, **Datoteka → Dodaj paket liga...**, **+ Dodaj...** u Moj svijet, ili ga ispusti na
**Uvezi svijet**, gdje onda **Izgradi i instaliraj** krene sam):

1. Program pokaže što je unutra i pita. Paket s više liga ih nabroji, sve označene: makni kvačicu
   onima koje ne želiš (0.2.1). Liga ispod druge lige iz paketa povlači i tu ligu. Pod **Što
   uzeti** možeš maknuti kvačicu i s dijelova paketa (scoreboardi, dresovi, grbovi, lica ...),
   npr. da scoreboarde uzmeš iz drugog paketa.
2. Liga s imenom koje već imaš: program pita i doda je kao `Ime (Paket)` (ne: ništa se ne doda).
   Paket napravljen bez kadrova umjesto toga ide na tu ligu: grbovi i treneri sjednu na klubove
   istog imena, tvoji igrači ostaju, a program kaže koliko je klubova našao.
   Paket koji tvoj svijet već ima (isto ime) zamijeni nova verzija (0.1.7): lige, klubovi i
   promjene igrača starog izlaze, a novog ulaze.
3. **Izgradi i instaliraj**.

ID-evi se dodjeljuju kad svaka osoba gradi, prema onome što ima njena igra, pa paket radi uz
druge pakete i uz tvoje vlastite lige. **Ukloni iz svog svijeta** opet izvadi paket, zajedno s
promjenama koje je napravio na klubovima igre. Ako paket mijenja klub koji tvoj svijet već
mijenja (recimo NewLife klub), igrač kojeg dodaju oba doda se jednom, a dovođenja i micanja iz
paketa dođu s njim (0.2.4).

Liga smještena ispod jedne od liga igre radi svima s istom verzijom igre.

### 9.1 Izvezi svijet: izgrađeni svijet za drugo računalo

Paket traži da druga osoba gradi. Da predaš svijet točno kakav si ga izgradio, stisni
**Izvezi...** na kartici svijeta u **2. Moj svijet**, ili **Izvezi svijet...** pod **Korak po
korak i Izvezi svijet** na kartici Gradnja (nakon što je svijet izgrađen). Spremi jedan `.zip`:

- `SiderAddons\livecpk\<svijet>\...`: cijela mapa svijeta, s njegovom **datotekom svijeta**
  `fl26world.txt`. Retci `newfaces` / `faceapp` u toj datoteci nabrajaju nove igrače koji dobiju
  generirano lice. Bez njih svaki novi igrač izgleda isto.
- `SiderAddons\content\kit-server\<svijet>\...` i `...\scoreboard-server\<svijet>\...`:
  **dresovi** svijeta (Kit Server dresovi njegovih klubova, i oni napravljeni iz boja i grbova) i
  **semafori**, svaki s `map.txt` / `map_competitions.txt` samo s retcima ovog svijeta. Uvezi
  svijet doda te retke u mape primatelja (njegov redak za isti klub se isključi i vrati kad se mod
  makne). Dresovi idu u Kit Server koji igra primatelja učitava (`content\kits` za SPFL26-ov
  vlastiti). Klub svijeta koji na tvom računalu nosi dres iz drugog paketa (SPFL26-ov Other
  Europe, modpack) ponese kopiju tog dresa, u `<svijet>\_kits\`, pa primatelju taj paket ne
  treba.
- `SiderAddons\content\scoreboard-server\<svijet>\_packs\...`: **semafori drugih paketa** koje
  uključeni retci mapa na tvom računalu daju natjecanjima svijeta (semafori modpacka za njegove
  lige, kupove i superkupove). Dolaze sa svojim retcima mape, usmjerenima na `<svijet>\_packs\`,
  pa primatelju ni taj paket ne treba. Teme izbornika nisu dio zipa svijeta: ostaju igrini
  izbornici, čak i kad je na tvom računalu uključena tema nekog paketa.
- `READ ME - FL26 world.txt` i `fl26worldpack.json`: što primatelj treba.

**Primatelj treba module Mod Studija s paketom lica** (`modules\fl26regen_faces.bin`):
instaliranje zipa na **Uvezi svijet** ih stavi (ili **Početna → Instaliraj sada**). Lica dolaze
iz tog paketa, pa ih zip ne nosi.

Za instalaciju ispusti zip na **Uvezi svijet** i stisni **Instaliraj svijet**. Mod Studio
instalira svoje module, kopira svijet, stavi `fl26world.txt` u `SiderAddons\modules` (gdje ga
`fl26regen` čita) i stavi svijet u igru; novija verzija svijeta koji imaš zamijeni stariju.
Završi sa **Spremno za igru** i završnim popisom provjera. Onda pokreni novu karijeru Master
Lige. **Ukloni** (pod **U igri sada**) opet izvadi svijet i vrati prethodnu datoteku svijeta.

Modpack imenuje domaće stadione svojih klubova po mapama stadionskog paketa svog autora. Kad tvoj
paket stadiona drži stadion u drugoj mapi, Mod Studio ga nađe po imenu; stadion koji nemaš ostaje
vani (klub igra gdje ga igra stavi), a završna provjera kaže koliko klubova ima svoj.

**Mijenjanje instaliranog svijeta.** `fl26worldpack.json` drži samo ime svijeta i što mu treba,
ali mapa svijeta nosi `leaguebuilder-plan.json`. Kad se Mod Studio pokrene s tim svijetom u igri i
raspakiranim tablicama igre, od tog plana napravi tvoj svijet i otvori ga, pa primatelj vidi lige
svijeta. Da ga promijeni i opet izgradi na svojim tablicama, prvo stisne **Omogući uređivanje...**
u Moj svijet (odjeljak 3.1).
Blizu je originalu, ali nije isto: lige, klubovi, imena, grbovi, Europa, kupovi, promjene igrača
i Konferencijska liga se vrate; predsezonski turniri, kupovi država iz igre, imena natjecanja,
europska mjesta liga iz igre, poredak liga i europski klubovi prve sezone ne. Slike i lica
pokazuju na računalo pošiljatelja: Build za sliku koja fali nacrta znak i kaže koje.
Mod Studio ne instalira preko svijeta istog imena koji je izgrađen na tom računalu: prvo
preimenuj taj svijet na njegovoj kartici.

## 10. Alati

**Dijagnostika** (**4. Alati**) **— Pokreni provjere** pogleda cijelu postavu: uključene mape
sadržaja kojih nema, module na krivom mjestu ili uključene dvaput, retke mape koji ne pokazuju ni
na što, svijet u igri (kartica **Tvoj svijet u igri**; uključen smije biti samo jedan svijet) i
zadnji `sider.log`. **Kopiraj izvještaj** stavi sve u međuspremnik, da ga zalijepiš u objavu na
forumu ili prijavu greške.

**Točke vraćanja** (**4. Alati**): svaka datoteka koju je program promijenio, s kopijom od prije.
**Vrati ovu kopiju** je vrati. Kopije su u `SiderAddons\ModStudio\backups`. **Počisti...** makne
stare, a uvijek čuva najstariju kopiju datoteke (onu od prije Mod Studija). Ovdje su i obrisani
i preimenovani svjetovi i kopija tvoje mape saveova.

**Vrati Sider kakav je bio prije Mod Studija...** (Točke vraćanja, i izbornik **Igra**) vraća
sve: svaku datoteku koju je Mod Studio promijenio vrati kakva je bila na početku (`sider.ini`,
CommonLib, datoteke mape) i izvadi ono što je donio (svoje module, paket lica, svjetove i modove
instalirane s njim). Ništa se ne briše: čuva se u `SiderAddons\ModStudio\reset-<time>`, a
**Poništi zadnje vraćanje** to vraća.

**Postavke** (**5. Postavke**): **Mapa igre**, **Sider mapa** (kad ih ima više), **Jezik
(Language)**, **Karijere u Master ligi** (**Svaki svijet ima svoje karijere (mapa saveova mijenja
se sa svijetom)**, odjeljak 3.1), **Tablice igre** (**Raspakiraj tablice igre**, **Koristi drugu
mapu s tablicama...**, poglavlje 2) i **Otvori mapu s postavkama programa**.

## 11. Kad nešto ne radi

| Što vidiš | Što napraviti |
|---|---|
| *sider.ini not found* | Postavke → Mapa igre: odaberi mapu s `FL_2026.exe`. |
| *nema tablica igre* | Postavke → Raspakiraj tablice igre. |
| *Access is denied*, ili Mod Studio kaže da ne može pisati u mapu igre | Igra je pod Program Files: stisni **Ponovno pokreni kao administrator**, ili premjesti igru u svoju mapu. |
| Mod Studio kaže da fali DLL njegovih modula (`fl26swiss.dll` ...) | Uzeo ga je antivirus. Dodaj mapu `SiderAddons` kao iznimku u antivirusu, pa opet **Instaliraj sada**. |
| Mod se ne vidi u igri | Dijagnostika → Pokreni provjere. Mapa sadržaja više na popisu možda ima istu datoteku. |
| Igra se ne pokrene nakon promjene | Točke vraćanja → vrati `sider.ini`, ili se prebaci na profil koji je radio. |
| Nove lige nema u Select Teamu | Započni *novu* karijeru; stare karijere zadrže stare lige. |
| Moje karijere su nestale nakon promjene svijeta | U `save_<svijet>` su, pored mape saveova: opet aktiviraj taj svijet (odjeljak 3.1). |
| Golman je kapetan svakog novog kluba | Svijet je izgrađen prije 0.2.4: izgradi ga opet i pokreni novu karijeru. |
| Grb na hlačicama nacrtanog dresa stoji bočno | Dres je nacrtan prije 0.2.4. Obriši datoteke `kitmaker.txt` u `SiderAddons\content\kit-server\<tvoj svijet>` i opet stisni **Izgradi i instaliraj**: dresovi se nacrtaju ponovno, s ispravno okrenutim grbom. |
| Imena klubova su igrina | Edit datoteka ima prednost (poglavlje 8). |
| *tvoje lige nikoga ne šalju u Europu* | Lige → odaberi prvi rang → **Uredi ligu...** → Europa (gumb **Prva liga** upiše uobičajena tri), pa opet izgradi. |
| *Konferencijska liga je uključena, ali njezinih tablica nema* | Opet izgradi svijet: izgrađen je prije te opcije, ili s njom isključenom. |
| Koraci gradnje su sivi | U igri je gotov svijet iz zipa. Prvo **Aktiviraj** svoj svijet, ili **Omogući uređivanje...** (odjeljak 8.2). |
| Lice se ne vidi | Mapa mora imati `#Win\face.fpk`; nakon odabira opet izgradi. |
| Bilo što drugo | Dijagnostika → **Kopiraj izvještaj**, i objavi ga sa `SiderAddons\sider.log`. |
