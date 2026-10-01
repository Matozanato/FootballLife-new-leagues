# FL26 Mod Studio — upute

> Česta pitanja (ažuriranje, rušenje pri pokretanju, kupovi, promocija, što poslati kad nešto ne
> radi), na engleskom: [faq.md](faq.md) · pitanja i pomoć na [Discordu](https://discord.gg/StQqtk3G3M)

FL26 Mod Studio je jedan program za sve što dodaješ u Football Life 2026:

- **modove** koje skineš: stadione, dresove, lopte, semafore, komentar, glazbu, face, Lua module;
- **content servere** koji ih poslužuju (Stadium Server, Ball Server, Kit Server i ostali), s
  datotekama mape koje uređuješ kao tablicu, a ne ručno;
- **postavke Sidera**: koje su mape sadržaja i moduli uključeni i kojim redom;
- **nove lige i klubove** (League Builder), tvoje promjene na postojećim ligama, klubovima i
  **igračima**, te **pakete liga** koje moder napravi jednom, a svatko ih može dodati u svoju igru.

Ništa od igre se ne prepisuje. Prije nego program promijeni neku datoteku, sačuva kopiju, a
svaki mod koji instalira može se opet maknuti.

---

## 1. Prije početka

- Instaliran **Football Life 2026** s mapom `SiderAddons` (FL26 dolazi sa Siderom).
- Raspakiraj program bilo gdje, npr. `Documents\FL26 Mod Studio`. Mapa mora ostati na okupu:
  mape `_internal` i `pack` te datoteke `README` stoje pokraj `FL26ModStudio.exe`.
- **Ugasi igru** dok mijenjaš stvari. Sider čita postavke kad se igra pokrene.

Prozor je na engleskom. **Settings → Language → Hrvatski** ga prebaci na hrvatski (ima i
španjolski i francuski).

## 2. Prvo pokretanje

1. **Postavke → Mapa igre**: stisni `...` i odaberi mapu u kojoj je `FL_2026.exe`. Redak
   ispod kaže je li pronađen `SiderAddons\sider.ini`. Sider se može zvati i drukčije ili biti
   razinu dublje (`sider\patch 1` ...); ako ih ima više, **Settings → Sider folder** bira s kojim program radi.
2. Ako želiš nove lige ili promjene igrača: **Postavke → Raspakiraj tablice igre**. Pročita
   klubove, lige i igrače igre u radnu mapu (par sekundi). Ponovi samo nakon nadogradnje igre.
3. Otvori **Pregled**. Pokazuje cijelu postavu na jednom mjestu i popis problema. Dvoklik na
   problem otvara stranicu koja ga rješava.

**Ažuriranja.** Par sekundi nakon pokretanja program pita GitHub je li izašao noviji FL26 Mod
Studio i javi se samo ako jest. **Skini i instaliraj** skine novi zip, provjeri ga prema
kontrolnom zbroju izdanja, zatvori program, stavi nove datoteke preko starih i ponovno ga
pokrene. Postavke, projekti, točke vraćanja i igra ostaju netaknuti. **Pomoć → Provjeri
ažuriranja** pita u bilo kojem trenutku; makni kvačicu s **Pomoć → Provjeri ažuriranja pri
pokretanju** i program pita samo tada. Ako je program u mapi u koju Windows ne da pisati
(npr. Program Files), otvori se stranica izdanja: raspakiraj zip sam ili premjesti program u
svoju mapu.

**Zasluge.** Gumb **Zasluge** pored **Pomoć** nabraja sve koji su pomogli napraviti Mod Studio:
testere, one koji su slali prijave i logove, i one čije su ideje u njemu.

**Više Sider mapa?** Sider se ne mora zvati `SiderAddons`. Program traži mapu pokraj
`FL_2026.exe` u kojoj je `sider.ini`; ako ih je više, **Postavke → Sider mapa** bira s kojom radi.

## 3. Stranice

Popis s lijeve strane ima četiri skupine.

| Skupina | Stranice |
|---|---|
| **Upravljanje** | Pregled, Instaliraj modove, Mape sadržaja, Lua moduli, Profili, Točke vraćanja |
| **Sadržaj igre** | Stadioni, Dresovi, Lopte, Komentar, Glazba, Ostali sadržaj |
| **League Builder** | NewLife Database, Nove lige, Novi klubovi, Postojeće lige i klubovi, Igrači, Paketi liga, Izgradnja |
| **Alati** | Dijagnostika, Postavke |

## 4. Instaliranje modova

Ispusti skinuti mod na **Instaliraj modove** (`.zip`, `.7z`, mapa, `.lua`, `.cpk` ili
`.fl26pack`), ili stisni **Odaberi datoteku...**.

Program pogleda unutra i nabroji svaki dio: što je i kamo ide.

| Dio | Što se dogodi |
|---|---|
| Mapa sadržaja (livecpk) | Kopira se u `SiderAddons\livecpk\<ime>` i doda u `sider.ini`. |
| Datoteke content servera | Kopiraju se u mapu `content` tog servera. Njegova **datoteka mape spaja se s tvojom**: tvoji retci ostaju, novi retci moda se dodaju. Za klub koji već imaš u mapi odlučuje izbor pokraj **Instaliraj**: *uzmi one iz moda* ili *zadrži moje, dodaj modove iza*. |
| Lua modul | Kopira se u `SiderAddons\modules` i uključi na pravo mjesto u redoslijedu. |
| Zapakirani .cpk | Pri instalaciji se raspakira u mapu sadržaja. |
| Paket liga | Dodaje se u tvoj recept League Buildera (poglavlje 9). |
| DLL | **Ne instalira se.** DLL radi s pravima igre; instaliraj ga samo ručno i samo iz izvora kojem vjeruješ. |

Daj modu ime, odaberi idu li nove mape sadržaja na vrh (one pobjeđuju) ili na dno, označi što
želiš i stisni **Instaliraj**. Popis ispod pokazuje svaki mod instaliran programom. **Makni mod**
briše datoteke koje je dodao i vraća one koje je zamijenio.

## 5. Mape sadržaja i Lua moduli

**Mape sadržaja** pokazuje svaki redak `cpk.root` iz `sider.ini`. Sider traži datoteku od vrha
prema dnu, pa kad dvije mape imaju istu datoteku, pobjeđuje ona više na popisu.

- Kvačica uključi ili isključi mapu (redak se pretvori u komentar, nikad se ne briše).
- **Na vrh**, **Gore**, **Dolje** mijenjaju redoslijed; **Dodaj mapu...** doda mapu koju već imaš.
- Za svaku mapu piše veličina i što je unutra (face, dresovi, stadioni...).
- Ništa se ne zapisuje dok ne stisneš **Primijeni**. **Odbaci** zaboravi promjene.

**Lua moduli** je isto za retke `lua.module`. Program zna pravi redoslijed čestih modula
(content serveri iza modula koje koriste) i kaže kad je neki modul na krivom mjestu. Neki
moduli trebaju postavku Sidera (npr. Goal Song Server treba `match-stats.enabled = 1`); program
kaže koju.

Moduli League Buildera ostaju redom kojim su postavljeni.

## 6. Sadržaj igre: content serveri

**Stadioni, Dresovi, Lopte, Glazba, Komentar** i **Ostali sadržaj** (semafori, izbornici,
dresovi sudaca, oznake na rukavu i vrijeme) pripadaju svaki jednom content serveru. Svaka
stranica ima:

- **redak stanja**: je li modul uključen, postoji li njegova mapa sadržaja;
- karticu za svaku **datoteku mape**, kao tablicu: koje natjecanje, klub ili stadion dobiva
  što. Dodaj, promijeni, isključi (redak postaje komentar) ili obriši retke; stvari biraš iz
  knjižnice umjesto da tipkaš ID. **Spremi** zapiše datoteku; kopija od prije ide u Točke
  vraćanja;
- **Knjižnicu**: što je u mapi sadržaja servera, sa slikama gdje ih ima. Označene su stvari koje
  nijedan redak mape ne koristi i retci koji pokazuju na nešto čega nema;
- **Postavke** servera gdje ih ima (omiljeni stadion, lopta, semafor ...).

Prije spremanja program provjeri tablicu: broj gdje ide broj, bez zareza u imenu, stvar koja
postoji.

## 7. Profili

Profil pamti koje su mape sadržaja i moduli uključeni i kojim redom. Drži jedan za Master
League, jedan za online, jedan za testiranje:

- **Spremi trenutnu postavu...** spremi ono što je sad uključeno pod nekim imenom.
- **Prebaci na njega** stavi tu postavu u `sider.ini` (stari `sider.ini` ide u Točke vraćanja).
- **Osvježi trenutnom postavom** prepiše profil.

## 8. League Builder: nove lige, klubovi i igrači

League Builder dodaje nove lige u igru i mijenja postojeće. Ono što napravi je **svijet**: mapa
sadržaja s imenom `_FL26...` koju igra čita dok je uključena.

**Nove lige → Dodaj ligu**

| Polje | Što znači |
|---|---|
| **Ime** | Ime lige u igri. Dvije lige ne smiju imati isto ime. |
| **Država** | Daje zastavu i mjesto gdje je liga na popisu. Država za koju igra nema ligu dobije svoj naslov. |
| **Klubovi** | Od 10 do 24. |
| **Format** | *Svi sa svima*, 1 do 4 puta, *dijeli se na pola (kao Škotska)* ili *Apertura i Clausura*: dva turnira u sezoni (rujan–početak siječnja, siječanj–svibanj), svaki od nula bodova, zatim doigravanje 8 ili 4 kluba (ili bez njega). O ulasku i ispadanju odlučuje ukupna tablica sezone. Najviše 18 klubova. Podijeljena liga ima najviše 46 kola, prije i poslije podjele zajedno (16 klubova dvaput je 30, pa najveća skupina dvaput smije imati 8 klubova, 14 kola). Zasad se u jednoj državi samo jedna liga smije dijeliti ili igrati Aperturu/Clausuru. |
| **Rang** | *(prvi rang)* ili liga iznad nje: druga nova liga ili liga iz igre. Za novu ligu ispod druge nove lige u jednom koraku: odaberi je i stisni **Dodaj nižu ligu** (preuzme državu, broj klubova, format i gore/dolje od lige iznad; ostaje samo ime). |
| **Gore / dolje** | Koliko klubova na kraju sezone zamijeni mjesta s ligom iznad. |
| **Sezona** | Samo za prvi rang nove države: *kolovoz do svibanj* (zadano) ili *veljača do prosinac*, kao Brazil, Japan ili Saudijska Arabija: klubovi idu gore i dolje za Novu godinu, a lige ispod nje je slijede. Još ne uz podjelu, Aperturu/Clausuru, nacionalni kup ni liga kup. |
| **Europa** | Samo za prvi rang: koje mjesto u ligi ide u koje europsko natjecanje. **Prva liga: 1. kvalifikacije LP, 2. EL, 3. UECL** upiše uobičajena tri (*... (kvalifikacije)* su kolovoška doigravanja, vidi 8.2); **Dodaj mjesto**, **Makni mjesto** i **Makni** za sve ostalo. Svako mjesto samo jednom, i samo mjesta koja liga ima. Ispod 1 mjesto glasi **Pobjednik kupa** (0.1.7): pobjednik kupa te države (nova država treba **Nacionalni kup**) -- a kad pobjednik već ima europsko mjesto kroz ligu, mjesto ide niz ligu sljedećem klubu, kao kod UEFA-e. Može ga imati i liga iz igre (*Europska mjesta liga iz igre*). Za niži rang ostavi prazno. Predložak prati državu: Azija dobije AFC Ligu prvaka i AFC Ligu prvaka Two, Južna Amerika Libertadores i Copa Sudamericana, Afrika CAF Ligu prvaka i CAF Konfederacijski kup. Ta četiri kupa kojih igra nema grade se sa svijetom (odjeljak 8.2). Mjesto u *kvalifikacijama Libertadoresa* zauzme mjesto kluba iz igre u kvalifikacijskom kolu (zadnjeg iz države koja u njemu ima najviše klubova), najviše šest od njegovih osam mjesta; **Provjeri plan** kaže koje lige preko toga ostaju bez mjesta. |
| **Logo** | Bilo koja slika (najbolje izgleda PNG s prozirnom pozadinom). Prazno: nacrta se sam. |
| **Zastava države** | Tvoja slika zastave države, razvučena u okvir zastave iz igre. Zamjenjuje zastavu te države posvuda u igri (Select Team, nacionalnost igrača, naslov države u Database > Competition Info) dok je svijet uključen. Prazno: zastava iz igre. |
| **Kup** | Samo za prvi rang. **Nacionalni kup**: država dobije svoj kup, s imenom koje zadaš (prazno: `<liga> Cup`). Igra puni kup države iz prvog ranga i ranga ispod njega, i kup ih uzima sve, u bilo kojem broju do 44: kola su ona kupa iz igre iste veličine, ili inače engleskog kupa, a kad broj nije 8, 16, 32 ili 64, neki klubovi slobodno prolaze prvo kolo, kao u pravom FA kupu. S više od 44 kluba kup zadržava samo prvi rang. Nova druga liga pod državom koju igra već ima (Njemačka, Rusija ...) također ulazi u kup te države, iza klubova prvog ranga, kad kola kupa odgovaraju broju klubova. Nova treća liga ili niža (League One pod Championshipom) ostavlja kup države prvim dvjema ligama iz igre, kao u igri. **Superkup**: uz to i superkup od jedne utakmice prije sezone, prvak protiv osvajača kupa. |
| **Ligaški kup** | Samo za prvi rang. Kup na ispadanje sa 16, 8 ili 4 kluba ove lige i lige ispod nje, po poretku, najjači protiv najslabijeg: dvije utakmice po kolu, finale jedna, od rujna do prosinca. Klubovi iza 16, 8 ili 4 prvo igraju pretkolo (0.1.7): zadnja mjesta, najjači protiv najslabijeg, dvije utakmice 4. i 7. rujna; pobjednici uzimaju zadnja mjesta kupa, protiv njegovih najjačih klubova. Liga od 20: 1. do 12. ravno u osminu finala, 13. do 20. u četiri para pretkola. Daj mu ime ili ostavi prazno (`<liga> League Cup`). |
| **Logotipi kupova** | Posebna slika za nacionalni kup, superkup, ligaški kup i doigravanje Apertura/Clausura. Prazno: nacrta se amblem s inicijalima kupa. |
| **Samo za egzibiciju -- nije u Master ligi** | Za Kick Off i prijateljske utakmice: povijesna liga, legende i slično. Njeni klubovi nikad ne igraju sezonu Master lige, pa liga stoji sama: bez lige iznad ili ispod, bez europskih mjesta, bez kupova. I dalje se vidi na popisu momčadi u Master ligi; svoj klub izaberi iz druge lige. |
| **Formacija** | Kako se klubovi lige postavljaju na terenu. Odaberi jednu od formacija koje igraju klubovi igre (4-2-3-1, 4-1-2-3, 4-3-3, 5-3-2 ...; popis kaže koliko ih klubova igre igra): svaki novi klub dobije kopiju taktike kluba iz igre s tom formacijom, a pri izgradnji mu se po njoj složi najboljih jedanaest. Prazno: zadano u igri, fiksni 4-2-3-1. Pojedini klub može imati svoju (**Uredi klub**). |

**Ime svijeta** (na istoj stranici) mora počinjati s `_FL26`. Nakon **Izgradnje** stupac **ID lige**
pokazuje ID natjecanja svake lige u igri, isti koji nosi datoteka njezina loga.

**Predsezonski turniri** (gumb na istoj stranici): prijateljski kupovi na ispadanje s 4 ili 8 pozvanih klubova u srpnju, prije sezone, u parovima redom kojim ih upišeš (prvi protiv drugog ...). Klub je iz nove lige ili klub igre (njegov ID); barem jedan mora biti iz nove lige, a turnir je u njenoj državi. Karijera počinje u kolovozu, pa se prvi igra u drugoj sezoni. Svaki turnir može imati **Logo**; prazno: nacrta se sam.

**Kupovi država iz igre** (gumb na istoj stranici): ligaški kup -- recimo Carabao Cup -- za lige iz igre. Označi **Ligaški kup** pored lige: 16 klubova te lige i one ispod nje, po poretku (klubovi iza 16. kroz pretkolo početkom rujna, 0.1.7), jedna utakmica po kolu od kraja rujna do prosinca, u dane koje kalendar liga i kupova iz igre ostavlja slobodnima. **Superkup**, prvak protiv pobjednika kupa krajem srpnja, samo gdje ga igra nema (Brazil, Čile, Škotska, Grčka, SAD); nova karijera još nema pobjednika kupa, pa se prvi igra u drugom ljetu. Prazno ime: ime lige i *League Cup* / *Super Cup*.

**Europska mjesta liga iz igre** (gumb na istoj stranici): koja mjesta Premier Lige, LaLige, Serie A ... idu u koje europsko natjecanje. Popis pokazuje mjesta iz igre; označi **Vlastita mjesta za ovu ligu** da ih promijeniš. Neoznačena liga zadržava mjesta iz igre, označena liga bez redova ne šalje nikoga.

**UEFA poredak** (ista stranica, 0.1.7): sve europske lige svijeta -- one iz igre i tvoje nove
prve lige -- na jednom popisu, najjača država prva. Povuci ligu mišem (ili **Gore** / **Dolje**)
da promijeniš redoslijed, makni kvačicu da liga ne dobije europsko mjesto, **Poredak UEFA-e**
vraća popis na UEFA-in poredak saveza za 2026./27. Desno piše što koja liga dobiva, a **OK** to
zapiše: mjesta UEFA-inog ključa za 2024.-27. -- 1. mjesto ima pet mjesta u Ligi prvaka, 6. dva i
mjesto u doigravanju, 30. jedno mjesto u drugom pretkolu Lige prvaka i tako dalje, uključujući
mjesto pobjednika kupa u Europskoj ligi. Svijet nikad nema svih 55 UEFA-inih država, pa mjesta
rangova kojih nema idu redom sljedećim klubovima najjačih liga, kolo po kolo, i svako natjecanje
ostaje puno: s dvanaest liga 6., 7. i 8. iz Engleske idu, recimo, u kvalifikacije Lige prvaka.
Iza 30. lige nema više mjesta i popis to kaže. Mjesta u kvalifikacijama idu u kola redom ključa,
najjača država u kolo najbliže ligaškoj fazi. Poslije i dalje možeš ručno promijeniti mjesta
svake lige (*Europa* na ligi, *Europska mjesta liga iz igre*): Izgradnja uzima mjesta, ne
poredak.

**Južnoamerička mjesta** (ista stranica, 0.1.7, samo za čitanje): za svaku južnoameričku ligu,
četiri iz igre i tvoje, koja mjesta idu u Copa Libertadores, njene kvalifikacije i Copa
Sudamericana. Mjesta u Libertadoresu za lige iz igre su igrina (Brazil 1.-4. i pobjednik Copa do
Brasil, kvalifikacije 5.-6. i tako dalje -- isto što pokazuje igrin Competition Info); Copa
Sudamericana je od Mod Studija, pa popis pokazuje koliko klubova svaka liga iz igre šalje u nju
kad su tvoja mjesta unutra: prvo tvoje lige, pa Brazil, Argentina, Čile i Kolumbija redom po
jedan klub dok ih ne bude 32. Klub koji je već u Libertadoresu ili njegovim kvalifikacijama
ustupa mjesto sljedećem iz svoje lige. **Provjeri plan** ispiše isti popis kad god svijet ima
mjesto u Libertadoresu ili Sudamericani.

**Imena natjecanja** (gumb na istoj stranici): novo ime i logo za kupove, superkupove i kontinentalna natjecanja iz igre -- FA Cup, Ligu prvaka, Libertadores ... -- i za kontinentalne kupove koje svijet gradi (CAF Liga prvaka, Kup konfederacija, AFC Liga prvaka Two, Copa Sudamericana, CAF Superkup). Ime dobiju sve faze natjecanja. Prazno: ono iz igre. Lige iz igre preimenuju se na stranici *Game's leagues and clubs*.

**Novi klubovi**: odaberi ligu, pa **Uredi klub** (ime, kratko ime, grb), **Zalijepi imena...**
ili **Učitaj imena iz datoteke...**. Prazno ime postaje `<liga> 01`, `<liga> 02` ...; klub bez
grba dobije grb s brojem. Dresovi se posude od klubova iz igre. Takav dres je licenciran i Edit
mode ga ne da mijenjati ("You cannot edit this strip"): označi **Dresovi koje možeš uređivati u
igri** na stranici Izgradnja i novi klubovi ne posuđuju nijedan; svaki nosi jednostavan dres koji
Edit > Teams > Strip mijenja kao i svaki drugi, Paste Image uključen.
Imena zadržavaju kvačice (FK Željezničar); kratko ime od tri slova ih nema, kao ni u igri,
pa tamo Č, Ž, Đ postaju C, Z, D. Nakon **Izgradnje** stupac **ID kluba** pokazuje ID svakog
kluba u igri.

**Trener**: u **Uredi klub** novog kluba možeš upisati ime trenera. Prazno: numerirano ime (`FL M0001` ...). **Slika trenera** ispod daje treneru sliku (isto kao **Slika trenera...** na stranici Igrači); *Postojeće lige i klubovi* > **Uredi klub** ima je i za klubove igre.

**Formacija**: u **Uredi klub** novog kluba možeš mu dati vlastitu formaciju; *Kao liga* zadržava formaciju lige. Teren ispod popisa pokazuje gdje tko stoji.

**Domaći stadion** (0.1.7): u **Uredi klub** stadion iz biblioteke Stadium Servera za klub; mjesto i ime popune se iz mape, ime možeš promijeniti. Upiše se u `map_teams.txt` Stadium Servera kad se svijet uključi (i kad se živi svijet ponovno izgradi), pa id novog kluba ne treba tražiti. Tvoj vlastiti redak za isti klub se za to vrijeme isključi, i opet uključi kad klub ovdje više nema stadion. *Postojeće lige i klubovi* > **Uredi klub** ima ga i za klubove igre. Stadium Server mora biti instaliran (stranica *Stadioni*).

**Klubovi koje igra već ima.** Na mjesto u novoj ligi može doći i klub iz igre umjesto novog:
odaberi mjesto, pa **Klub iz igre...**, i traži po imenu ili ID-u kluba (**Samo klubovi bez lige**
suzi popis). Klub zadržava ime, grb, dresove, trenera i igrače, a igra samo u tvojoj ligi. Ako u
igri igra negdje (liga, kup, Europska liga ...), biraš tko tamo preuzima njegovo mjesto: klub iz
igre koji ne igra nigdje ili novi klub kojem daš ime. Predsezonski turnir (*Pre-season friendly Cup* u SPFL26) se ne broji: klub ga i dalje igra, kao i klubovi Premier lige (0.1.7). **Uredi klub** na klubu iz igre mijenja ime, grb, sliku trenera i stadion, kao na *Postojeće lige i klubovi* (0.1.7). Tako nijedno natjecanje igre ne mijenja broj
klubova; lige iz igre zadržavaju datume samo s brojem za koji su napravljene. Reprezentacije,
klasični i zadani timovi te klubovi s manje od 18 igrača ne mogu se odabrati. **Novi klub ovdje**
vraća mjesto novom klubu. Klub se više ne pojavljuje u grupama *Other ... clubs* u Master League karijeri.

**Umetni klub** i **Makni klub** dodaju mjesto ispred odabranog kluba ili ga izbacuju (10 do 24
kluba); imena, grbovi, treneri i promjene igrača idu sa svojim klubovima. Provjeri europska mjesta
lige, pa ponovno **Izgradi**. Svaka promjena klubova lige traži **novu karijeru**.

**Premjesti u drugu ligu...** (0.1.7) odvede odabrani novi klub na kraj druge nove lige, s imenom, kratkim imenom, grbom, trenerom, formacijom, dresovima, NewLife id-em i izmjenama igrača; liga iz koje odlazi ima klub manje. Klub iz igre se seli preko **Klub iz igre**: makni ga iz jedne lige, stavi u drugu.

**Postojeće lige i klubovi**: nova imena, logotipi i grbovi za ono što igra već ima.

**Zamijeni ligu s klubom...** (0.1.7): dva kluba iz liga igre zamijene mjesta -- klub koji je ušao za onaj koji je ispao, klub lige jedne države za klub druge. Svaki preuzme mjesta drugoga u ligi, kupovima i europskim natjecanjima, pa svaka liga igre zadrži broj klubova. Klub koji igra u novoj ligi recepta ne može se i mijenjati. **Poništi izmjene kluba** vraća zamjenu. Zatim ponovno **Izgradi** i počni novu karijeru.

> **Edit datoteka.** Ako u mapi sa spremanjima igre postoji Edit datoteka (`EDIT00000000`), ona
> ima prednost za imena klubova. Makni je negdje drugdje da vidiš svoja imena.

### Igrači

**Igrači** mijenja momčad bilo kojeg kluba: novih klubova iz recepta i klubova iz igre. Odaberi
klub (ili stisni **Igrači** na Novim klubovima), pa igrača:

- **ime**, **broj na dresu**, **pozicija** i pozicije na kojima može igrati (A = prirodna,
  B = može igrati), jača noga, visina, težina, dob, državljanstvo, stil igre;
- sve **sposobnosti** i **vještine** (imena su ista kao u igri, na engleskom);
- **Ocjena**: ocjena s popisa, od sposobnosti na koje se pozicija oslanja. Promjena pomiče
  svaku sposobnost igrača za isti iznos. Igrač novog kluba nema ime dok mu ga izgradnja ne
  da s brojem (FL P00001 ...); upiši ga u **Ime** i dobit će tvoje;
- **Lice**: **Odaberi...** mapu s facom (poglavlje 8.1). **Makni** vraća facu iz igre. Novi igrač
  bez nje dobije facu iz paketa lica za regene koja paše njegovoj nacionalnosti, sa slikom
  (0.1.5.5, uz instalirane module);
- **Mala slika**: **Odaberi...** sliku (PNG ili JPG) za malu sliku igrača na popisima momčadi, bez
  vlastite face. Build je svodi na 180 x 180; ima prednost pred slikom iz mape lica;
- **Gore / Dolje u redoslijedu**: redoslijed u momčadi. Prvih jedanaest počinje utakmicu;
- **Dodaj igrača** (kopija igrača kojeg odabereš, s novim ID-om; samo klubovi iz igre),
  **Makni iz kluba** (novi klub zadržava barem 18 igrača);
- **Najboljih jedanaest** stavi najjačeg igrača na svako mjesto; **Razina momčadi...** podigne
  ili spusti sve sposobnosti cijele momčadi;
- **Teren** (novi klubovi): prvih jedanaest u formaciji kluba. Odaberi igrača na popisu, pa
  klikni mjesto da ga staviš tamo; tko je ondje stajao, uzima njegovo mjesto u redoslijedu momčadi;
- **Izvezi CSV... / Uvezi CSV...**: uredi momčad u tabličnom programu. Prvo izvezi, promijeni
  ćelije, pa uvezi iste stupce natrag.
- **Uvezi momčad iz tablice...**: bilo koja tablica igrača postaje momčad kluba -- ručno
  upisana, popis momčadi kopiran sa stranice, izvoz iz Football Managera ili EA FC-a. Stupci
  se prepoznaju po imenu (ime, pozicija, dob ili datum rođenja, državljanstvo, visina, noga,
  broj dresa, ukupna ocjena i bilo koje ocjene) i prikažu se da ispraviš krivo prepoznat.
  Ono čega u tablici nema dolazi od igrača iz igre iste pozicije i ocjene; ocjene 1-20 iz
  Football Managera rastežu se na 40-99 kao u igri. Igrači iz tablice zauzimaju mjesta u
  klubu redom momčadi: novi klub zadržava svojih 30 mjesta (manje igrača = ostali odlaze,
  najviše do 18), klub iz igre dobije ili izgubi igrače da se poklopi.

Svaka promjena zapiše se u svijet kad stisneš **Izgradnja**; datoteke igre ostaju kakve jesu.
**Poništi promjene ovog igrača** i **Poništi sve promjene ovog kluba** vraćaju ono iz igre.

Popis klubova ima i **Reprezentacije** i **Ostali klubovi (bez lige)**: momčadi koje igra drži izvan svih liga (reprezentacije, klubovi koji igraju samo kup ili kontinentalno natjecanje). Njihovi igrači uređuju se na isti način.

#### Transferi, reprezentacije, ID-evi, slika trenera

- **Dovedi igrače...** (klub): popis svih igrača igre i tvojih novih klubova, s filtrom po
  državljanstvu i traženjem po imenu; više njih biraš s Ctrl ili Shift. Prelaze u ovaj klub, a
  stari ih klub gubi (transfer). **Transfer u...** radi isto s druge strane: odabrani igrač
  prelazi u klub koji izabereš. Na popisu piše *iz: ...* kod kluba koji ga dobiva i *u: ...* kod
  kluba koji napušta; **Makni iz kluba** na bilo kojem od ta dva retka otkazuje transfer. Klub
  ima najviše 40 igrača.
- **Pozovi igrače...** (reprezentacija: u popisu liga odaberi *Reprezentacije*): popis se otvara
  na državi te reprezentacije. Igrači ulaze u reprezentaciju **i ostaju u svojim klubovima**,
  kao u igri. **Makni iz kluba** miče igrača iz reprezentacije (ne iz kluba). Reprezentacija ima
  najviše 26 igrača; igrač je u jednoj reprezentaciji u isto vrijeme. Tvoj popis upisuje se u
  podatke igre, ali u karijeri Master League igra sama bira reprezentacije, pa tamo tvoji pozivi
  ne ostaju.
- Igrač koji dođe ide na kraj redoslijeda momčadi sa slobodnim brojem dresa; momčad iz koje je
  otišao zatvara redoslijed iza njega.
- Stupac **ID igrača**: ID svakog igrača -- igrin, onaj koji si upisao ili onaj koji je novom
  igraču dao zadnji **Build** (izgradi jednom prije nego radiš minifaces ili lica za nove igrače).
  **Izvezi CSV...** ga zapisuje kao `player_id`; Uvezi CSV taj stupac preskače.
- **ID kluba** (pokraj kluba) i **ID igrača** (kartica Osnovno): samo za tvoje **nove** klubove i
  igrače. Prazno = sljedeći slobodan ID pri Buildu. Upiši ga kad je paket dresova, grba ili lica
  rađen za određeni ID. ID kluba: od prvog iza klubova igre (71578) do 81919; ID igrača: iznad
  najvećeg u igri do 399999; nikad onaj koji već ima igra ili drugi novi klub ili igrač. ID se
  koristi svugdje gdje svijet spominje klub ili igrača (momčadi, natjecanja, dresovi, grbovi,
  trener, lica). Klubovi i igrači igre zadržavaju svoje ID-eve: dresovi, lica i tvoji saveovi
  vezani su uz njih.
- **Slika trenera...**: PNG ili JPG za trenera kluba. Build je svodi na 256 x 256 i stavlja u
  `common/render/symbol/coach/coach_<ID trenera>.png`, gdje igra drži slike trenera. Ponovni
  pritisak miče sliku.

### 8.1 Face

Mod s facom je mapa ovakva (kako ih autori faca dijele):

```
<bilo koje ime>\
    #Win\face.fpk
    #Win\face.fpkd
    sourceimages\#windx11\*.ftex
    portrait.dds            (ili <id>.dds, nije obavezno)
```

Tu mapu odaberi za igrača. Pri **Izgradnji** faca se kopira u svijet i usmjeri na tog igrača, pa
radi i za novog igrača čiji ID nije postojao kad je faca napravljena, i nikad ne zamijeni facu
iz igre. Bez portreta mala slika igrača u izbornicima ostaje prazan obris; sama faca se
svejedno vidi. Mapa s više faca unutra se odbija: odaberi točno onu jednu koju misliš.

### 8.2 Izgradi, uključi, igraj

**Izgradnja**:

0. **Postavi module** — jednom, i opet nakon nove verzije programa. Datoteke koje zamijeni
   čuvaju se u `SiderAddons\modules\before-builder-1\`.
1. **Provjeri plan** — što će se napraviti; ništa se ne zapisuje.
2. **Izgradi svijet**.
3. **Uključi ga** — postane aktivni svijet u `sider.ini`.
4. Pokreni igru, vrati se i stisni **Nakon pokretanja: provjeri**. Pročita `sider.log` i kaže,
   modul po modul, je li svijet preuzet.

**Uključi Konferencijsku ligu** (na stranici Izgradnja, zadano uključeno) izgradi i
Konferencijsku ligu: ligašku fazu od 36 klubova i veljačko doigravanje, kao kod druga dva
natjecanja. Liga prvaka i Europska liga dobivaju ligašku fazu od 36 i veljačko doigravanje u
svakom slučaju. Isključeno: bez Konferencijske lige. (Mod Studio 0.1.3 i starije verzije su uz isključenu opciju
ostavljale Ligu prvaka i Europsku ligu u skupinama po četiri, koje mod ne zna voditi -- pa su se
kvarile; Provjere označe takav svijet: izgradi ga ponovno.) **Logo Konferencijske lige** pored toga:
tvoja slika za nju; prazno: nacrta se UECL amblem (igra ga nema). **Ime Konferencijske lige**
ispod: kako je igra zove, prazno *FL Conference League* (upiši *UEFA Conference League* ako
želiš); novo ime traži ponovnu izgradnju svijeta. Oboje koristi i **Samo nova europska
natjecanja...**.

> **Europska mjesta.** Mjesta koja daš svojim ligama dolaze iza mjesta liga iz igre. Svako
> natjecanje prima 36 klubova; mjesta iza 36. ne dobiju ništa, i **Provjeri plan** to kaže.
> Nove lige bez mjesta nikoga ne šalju u Europu, i Pregled na to upozori. Branitelji naslova
> idu prvi: pobjednici Lige prvaka i Europske lige uzimaju dva izravna mjesta u Ligi prvaka,
> pobjednik Konferencijske lige jedno u Europskoj ligi. Ždrijeb ligaške faze prati UEFA-ina
> pravila: nijedan klub ne igra protiv kluba iz svoje države, i najviše dva protivnika dolaze
> iz iste druge države.
>
> **Kolovoška pretkola.** Mjesto *(kvalifikacije)* šalje klub u kolovoške kvalifikacije tog
> natjecanja: do tri kola (0.1.7) -- 2. pretkolo (dani 220 i 225), 3. pretkolo (229 i 236) i
> doigravanje (243 i 250; Liga prvaka 244 i 251) -- svako 16 klubova, dvije utakmice; osam
> najjačih momčadi je nositelj (uzvrat doma), dva kluba iste države se ne sastaju. Pobjednici idu
> u sljedeće kolo, iz doigravanja u ligašku fazu. Poraženi padaju kao kod UEFA-e: iz *Lige prvaka
> (kvalifikacije)* poraženi u doigravanju idu u Europsku ligu, u 3. pretkolu u doigravanje
> Europske lige, u 2. pretkolu u 3. pretkolo Europske lige; *Europska liga (kvalifikacije)* isto
> tako u Konferencijsku; poraženi u *Konferencijskoj ligi (kvalifikacije)* ispadaju. Prva mjesta na
> popisu idu u doigravanje, kasnija u ranija kola. Koliko kola svijet dobije ovisi o mjestima, a
> svako kolo Konferencijske lige traži 8 klubova više: 116 mjesta u Europi za samo tri
> doigravanja, 132 za svih devet kola. S mjestima same igre to su samo doigravanja; Buildov
> sažetak kaže koja kola svijet dobiva (*pretkola u kolovozu*). Svako doigravanje uzme 8 izravnih
> mjesta natjecanjima u koja idu njegovi pobjednici i poraženi: sa sva tri Liga prvaka prima 28
> klubova izravno, Europska i Konferencijska po 20. Mjesto iza toga igra se u kvalifikacijama tog
> natjecanja. Mjesta tvojih liga u kvalifikacijama dolaze prije mjesta iz igre (Portugal,
> Škotska, Grčka, Danska ...).

Onda **započni novu Master League** (ili Become a Legend) karijeru. Nove lige su pod svojom
državom u Select Team i Kick Off. U popisima Kick Offa i Edita nova azijska država dolazi
prije *Other Clubs (Asia)*, južnoamerička uz one iz igre (iza Kolumbije, prije MLS-a, 0.1.7),
CONCACAF država iza MLS-a, a afričke i oceanijske (igra za njih nema
odjeljak) iza Azije.

> **Kupovi drugih kontinenata.** Kad tvoje lige šalju klubove u CAF Ligu prvaka, CAF
> Konfederacijski kup, AFC Ligu prvaka Two ili Copa Sudamericana, **Izgradnja** napravi i te
> kupove. Svaki dobije 32, 16, 8 ili 4 kluba: prvo mjesta tvojih liga, zatim ga popune lige iz
> igre s tog kontinenta (Azija i Južna Amerika). S 8 ili više igraju se skupine po četiri pa
> nokaut; ispod 8 samo nokaut. Pune se krajem kolovoza, iz tablica liga. Klub koji već igra
> Copa Libertadores, njezine kvalifikacije ili AFC Ligu prvaka ne ulazi u njihov ždrijeb. CAF
> kup s manje od 4 mjesta prvo uzme mjesta sljedećeg CAF kupa (s dva i dva CAF Liga prvaka
> dobije sva četiri), zatim sljedeća mjesta tvojih liga. **CAF Superkup** (stranica Izgradnja,
> zadano uključen) spoji pobjednike dvaju CAF kupova u jednoj utakmici krajem srpnja, od druge
> sezone karijere.

> **Spremanja pripadaju svijetu.** Karijera spremljena s jednim svijetom treba isti taj svijet
> da se učita.

**Datoteka → Spremi recept** spremi sve u `.json` datoteku; otvaranje recepta to vraća.
**Izgradnja** usput sprema kopiju recepta u `%APPDATA%\FL26ModStudio\recipes\<svijet>.json`,
a Mod Studio pri pokretanju otvara zadnji recept, pa zatvaranje bez spremanja ne gubi ništa što
je izgrađeno.

**Samo nova europska natjecanja...** (stranica Izgradnja) gradi svijet samo s novom Ligom
prvaka i Europskom ligom -- ligaška faza od 36 i veljačko doigravanje -- te Konferencijskom ligom
kad je označeno **Uključi Konferencijsku ligu**. Bez novih liga; klubovi i lige igre ostaju kakvi
jesu, a tvoj recept se ne mijenja. Pita za ime svijeta (zadano `_FL26Euro`), izgradi ga i ponudi
da ga uključi. Uključen može biti samo jedan svijet, pa je ovo umjesto svijeta s novim ligama:
svijet s novim ligama već ima novi format.

> **Egzibicijske lige i Master liga.** Liga označena kao *Samo za egzibiciju* nikad ne igra sezonu
> Master lige, ali igra ima jedan popis momčadi za Kick Off i Master ligu, pa se njezini klubovi
> i dalje vide kad biraš klub za novu karijeru. Ne počinji karijeru s nekim od njih. **Provjeri
> plan** i **Izgradnja** to i napišu.

### 8.3 Granice

| | |
|---|---|
| Novih liga po svijetu | 39 |
| Klubova po ligi | 10 – 24 |
| Novih klubova ukupno | 793 |
| Koliko puta se klubovi sretnu | 1 – 4 |
| Liga koje se dijele na pola | 2 po svijetu |
| Rangova u jednoj državi | do 7. |
| Igrača po novom klubu | 30 na početku; makni do 18; dovedeni igrači do 40 |
| Igrača po reprezentaciji | 26 |
| Nacionalni kup | prvi rang i rang ispod, do 44 kluba; više: samo prvi rang |

### 8.4 NewLife Database: pravi klubovi i igrači

NewLife Database je zasebno preuzimanje s pravim klubovima i igračima za nove lige: imena, datumi
rođenja, pozicije i ocjene na ljestvici igre te boje klubova. Svaki klub i igrač u njoj ima svoj
ID, isti u svakoj verziji baze. Nije na GitHubu: preuzmi je s NewLife kanala našeg
[Discorda](https://discord.gg/StQqtk3G3M). Dolazi u dijelovima, jedan po kontinentu (veliki u
više njih), plus *Free agents*, svaki manji od 10 MB. Preuzmi samo dijelove koje trebaš.

1. Stavi preuzete dijelove u jednu mapu. Ne raspakiravaj ih: Mod Studio čita zipove takve kakvi
   jesu. (To su LZMA zipovi: 7-Zip ih otvara, Windowsov preglednik zipova ne.)
2. **League Builder > NewLife Database > Otvori NewLife Database...** i odaberi tu mapu. Popis
   pokazuje sve lige iz tih dijelova: državu, klubove, klubove koje igra već ima (*U igri*),
   igrače i razinu. Klikni ligu da vidiš njene klubove.
3. Odaberi jednu ili više liga (Ctrl ili Shift za više) i pritisni **Dodaj u recept**. Svaka
   postaje nova liga sa svojim klubovima i njihovim kadrovima, prva liga svoje države. Rang,
   format, europska mjesta i ostalo mijenjaš na *Nove lige*, kao za svaku drugu ligu.
4. **Izgradi**, uključi svijet i pokreni novu karijeru (poglavlje 8.2).

- **Vlastiti sastav lige** (0.1.7): makni kvačicu klubu u popisu desno da ostane vani, a
  **Dodaj klub iz druge lige...** dovodi klubove bilo koje lige iz baze -- recimo prva liga ove
  sezone je prošlogodišnja s dva kluba koja su ušla. Redak lige dobije `*`. Klub može biti samo
  u jednoj ligi recepta.
- Liga prima 10 do 24 kluba, nove i one iz igre zajedno; ostale su sive. Redak na dnu broji nove klubove recepta prema 793
  koliko svijet prima.
- Klubovi koje igra već ima ulaze u novu ligu kao klubovi iz igre (odjeljak 8, *Klubovi koje
  igra već ima*), na zadnja mjesta, sa svojim imenom, grbom, dresovima i igračima. Onaj koji
  igra i neko natjecanje igre (Basel i Young Boys igraju Europa ligu) treba klub koji ga tamo
  mijenja: *Novi klubovi*, odaberi ga, **Klub iz igre**. Do tada Build javlja koji su to.
- Igrač kojeg igra već ima (isti igrač pod istim imenom, recimo Urbański u Górniku u igri i u
  Legiji u NewLifeu) prelazi u NewLife klub umjesto da nastane drugi put (0.1.7): zadržava lice,
  ime i ID, a uzima NewLifeovu poziciju i ocjene. Ostaje gdje jest kad bi njegov stari klub pao
  ispod 18 igrača; tada NewLife napravi svoju kopiju, kao prije.
- NewLife klubovi u igri zadržavaju svoj NewLife ID (98304 i više), pa svaki paket liga napravljen
  s bazom daje klubu isti ID.
- NewLife klub dobiva grb u obliku štita u svojim bojama i dres igre najbližih boja, dok mu ne
  daš svoje (**Uredi klub**).

## 9. Paketi liga: podijeli cijelu ligu

Moder napravi ligu jednom — klubove, imena, grbove, logotipe, momčadi, face — i podijeli **jednu
datoteku `.fl26pack`**. Svatko je doda u svoj recept i izgradi.

**Napravi paket** (Paketi liga → **Napravi paket...**, ili Datoteka → Napravi paket liga...):

1. Ime, autor, verzija i kratak opis.
2. Označi lige koje idu unutra (**Označi sve** / **Odznači sve** iznad popisa). Liga ispod
   druge nove lige mora ići s njom.
   Paket koji recept već ima (isto ime) zamijeni nova verzija (0.1.7): lige, klubovi i promjene
   igrača starog izlaze, a novog ulaze.
3. Po želji i **moje promjene na postojećim ligama, klubovima i igračima**.
4. Spremi. Datoteka nosi slike i face, a ne putanje na tvom računalu.

**Dodaj paket** (Paketi liga → **Dodaj paket...**, Datoteka → Dodaj paket liga..., ili ga
ispusti na Instaliraj modove):

1. Program pokaže što je unutra i pita.
2. Liga s imenom koje već imaš doda se kao `Ime (Paket)`.
3. **Spremi recept**, pa **Izgradnja**.

ID-evi se dodijele kad svaka osoba gradi, prema onome što ima njena igra, pa paket radi uz
druge pakete i uz tvoje lige. **Makni iz recepta** opet izvadi paket, zajedno s promjenama koje
je napravio na klubovima igre.

Liga smještena ispod jedne od liga igre radi svima s istom verzijom igre.

## 10. Alati

**Dijagnostika — Pokreni provjere** pogleda cijelu postavu: uključene mape sadržaja kojih nema,
module na krivom mjestu ili uključene dvaput, retke mape koji ne pokazuju ni na što, svjetove
League Buildera (uključen smije biti samo jedan) i zadnji `sider.log`. **Kopiraj izvještaj**
stavi sve u međuspremnik, da ga zalijepiš u objavu na forumu ili prijavu greške.

**Točke vraćanja**: svaka datoteka koju je program promijenio, s kopijom od prije. **Vrati ovu
kopiju** je vrati. Kopije su u `SiderAddons\ModStudio\backups`. **Počisti...** makne stare.

## 11. Kad nešto ne radi

| Što vidiš | Što napraviti |
|---|---|
| *sider.ini not found* | Postavke → Mapa igre: odaberi mapu s `FL_2026.exe`. |
| *no game tables* | Postavke → Raspakiraj tablice igre. |
| Mod se ne vidi u igri | Dijagnostika → Pokreni provjere. Mapa sadržaja više na popisu možda ima istu datoteku. |
| Igra se ne pokrene nakon promjene | Točke vraćanja → vrati `sider.ini`, ili se prebaci na profil koji je radio. |
| Nove lige nema u Select Team | Započni *novu* karijeru; stare karijere zadrže stare lige. |
| Imena klubova su iz igre | Edit datoteka ima prednost (poglavlje 8). |
| *tvoje lige nikoga ne šalju u Europu* | Nove lige → Uredi prvi rang → Europa (gumb **Prva liga** upiše uobičajena tri), pa ponovno izgradi. |
| *Konferencijska liga je uključena, ali njezinih tablica nema* | Ponovno izgradi svijet: izgrađen je prije te opcije, ili s njom isključenom. |
| Faca se ne vidi | Mapa mora imati `#Win\face.fpk`; nakon odabira ponovno izgradi. |
| Bilo što drugo | Dijagnostika → **Kopiraj izvještaj**, i pošalji ga sa `SiderAddons\sider.log`. |
