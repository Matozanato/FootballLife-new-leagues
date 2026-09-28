# FL26 Mod Studio — upute

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
  mapa `pack` i datoteke `README` stoje pokraj `FL26ModStudio.exe`.
- **Ugasi igru** dok mijenjaš stvari. Sider čita postavke kad se igra pokrene.

Prozor je na engleskom. **Settings → Language → Hrvatski** ga prebaci na hrvatski.

## 2. Prvo pokretanje

1. **Postavke → Mapa igre**: stisni `...` i odaberi mapu u kojoj je `FL_2026.exe`. Redak
   ispod kaže je li pronađen `SiderAddons\sider.ini`.
2. Ako želiš nove lige ili promjene igrača: **Postavke → Raspakiraj tablice igre**. Pročita
   klubove, lige i igrače igre u radnu mapu (par sekundi). Ponovi samo nakon nadogradnje igre.
3. Otvori **Pregled**. Pokazuje cijelu postavu na jednom mjestu i popis problema. Dvoklik na
   problem otvara stranicu koja ga rješava.

**Ažuriranja.** Par sekundi nakon pokretanja program pita GitHub je li izašao noviji FL26 Mod
Studio i javi se samo ako jest. **Skini i instaliraj** skine novi zip, provjeri ga prema
kontrolnom zbroju izdanja, zatvori program, stavi nove datoteke preko starih i ponovno ga
pokrene. Postavke, projekti, točke vraćanja i igra ostaju netaknuti. **Pomoć → Provjeri
ažuriranja** pita u bilo kojem trenutku. Ako je program u mapi u koju Windows ne da pisati
(npr. Program Files), otvori se stranica izdanja: raspakiraj zip sam ili premjesti program u
svoju mapu.

## 3. Stranice

Popis s lijeve strane ima četiri skupine.

| Skupina | Stranice |
|---|---|
| **Upravljanje** | Pregled, Instaliraj modove, Mape sadržaja, Lua moduli, Profili, Točke vraćanja |
| **Sadržaj igre** | Stadioni, Dresovi, Lopte, Komentar, Glazba, Ostali sadržaj |
| **League Builder** | Nove lige, Novi klubovi, Postojeće lige i klubovi, Igrači, Paketi liga, Izgradnja |
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
| **Format** | *Svi sa svima*, 1 do 4 puta, ili *dijeli se na pola (kao Škotska)*. |
| **Rang** | *(prvi rang)* ili liga iznad nje: druga nova liga ili liga iz igre. |
| **Gore / dolje** | Koliko klubova na kraju sezone zamijeni mjesta s ligom iznad. |
| **Europa** | Samo za prvi rang: koje mjesto u ligi ide u koje europsko natjecanje. **Prva liga: 1. LP, 2. EL, 3. KL** upiše uobičajena tri; **Dodaj mjesto**, **Makni mjesto** i **Makni** za sve ostalo. Svako mjesto samo jednom, i samo mjesta koja liga ima. Za niži rang ostavi prazno. |
| **Logo** | Bilo koja slika (najbolje izgleda PNG s prozirnom pozadinom). Prazno: nacrta se sam. |

**Ime svijeta** (na istoj stranici) mora počinjati s `_FL26`.

**Novi klubovi**: odaberi ligu, pa **Uredi klub** (ime, kratko ime, grb), **Zalijepi imena...**
ili **Učitaj imena iz datoteke...**. Prazno ime postaje `<liga> 01`, `<liga> 02` ...; klub bez
grba dobije grb s brojem. Dresovi se posude od klubova iz igre.
Imena zadržavaju kvačice (FK Željezničar); kratko ime od tri slova ih nema, kao ni u igri,
pa tamo Č, Ž, Đ postaju C, Z, D. Nakon **Izgradnje** stupac **ID kluba** pokazuje ID svakog
kluba u igri.

**Postojeće lige i klubovi**: nova imena, logotipi i grbovi za ono što igra već ima.

> **Edit datoteka.** Ako u mapi sa spremanjima igre postoji Edit datoteka (`EDIT00000000`), ona
> ima prednost za imena klubova. Makni je negdje drugdje da vidiš svoja imena.

### Igrači

**Igrači** mijenja momčad bilo kojeg kluba: novih klubova iz recepta i klubova iz igre. Odaberi
klub (ili stisni **Igrači** na Novim klubovima), pa igrača:

- **ime**, **broj na dresu**, **pozicija** i pozicije na kojima može igrati (A = prirodna,
  B = može igrati), jača noga, visina, težina, dob, državljanstvo, stil igre;
- sve **sposobnosti** i **vještine** (imena su ista kao u igri, na engleskom);
- **Lice**: **Odaberi...** mapu s facom (poglavlje 8.1). **Makni** vraća facu iz igre;
- **Gore / Dolje u redoslijedu**: redoslijed u momčadi. Prvih jedanaest počinje utakmicu;
- **Dodaj igrača** (kopija igrača kojeg odabereš, s novim ID-om), **Makni iz kluba**;
- **Najboljih jedanaest** stavi najjačeg igrača na svako mjesto; **Razina momčadi...** podigne
  ili spusti sve sposobnosti cijele momčadi;
- **Izvezi CSV... / Uvezi CSV...**: uredi momčad u tabličnom programu. Prvo izvezi, promijeni
  ćelije, pa uvezi iste stupce natrag.

Svaka promjena zapiše se u svijet kad stisneš **Izgradnja**; datoteke igre ostaju kakve jesu.
**Poništi promjene ovog igrača** i **Poništi sve promjene ovog kluba** vraćaju ono iz igre.

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
Konferencijsku ligu, a Ligi prvaka i Europskoj ligi da ligašku fazu od 36 klubova, uz veljačko
doigravanje sva tri natjecanja. Isključeno: europski kupovi kakvi su u igri.

> **Europska mjesta.** Mjesta koja daš svojim ligama dolaze iza mjesta liga iz igre. Svako
> natjecanje prima 36 klubova; mjesta iza 36. ne dobiju ništa, i **Provjeri plan** to kaže.
> Nove lige bez mjesta nikoga ne šalju u Europu, i Pregled na to upozori.

Onda **započni novu Master League** (ili Become a Legend) karijeru. Nove lige su pod svojom
državom u Select Team i Kick Off.

> **Spremanja pripadaju svijetu.** Karijera spremljena s jednim svijetom treba isti taj svijet
> da se učita.

**Datoteka → Spremi recept** spremi sve u `.json` datoteku; otvaranje recepta to vraća.

### 8.3 Granice

| | |
|---|---|
| Novih liga po svijetu | 39 |
| Klubova po ligi | 10 – 24 |
| Novih klubova ukupno | 793 |
| Koliko puta se klubovi sretnu | 1 – 4 |
| Liga koje se dijele na pola | 2 po svijetu |
| Rangova u jednoj državi | do 7. |
| Igrača po novom klubu | 30 na početku; dodaj i makni koliko želiš |

## 9. Paketi liga: podijeli cijelu ligu

Moder napravi ligu jednom — klubove, imena, grbove, logotipe, momčadi, face — i podijeli **jednu
datoteku `.fl26pack`**. Svatko je doda u svoj recept i izgradi.

**Napravi paket** (Paketi liga → **Napravi paket...**, ili Datoteka → Napravi paket liga...):

1. Ime, autor, verzija i kratak opis.
2. Označi lige koje idu unutra. Liga ispod druge nove lige mora ići s njom.
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
