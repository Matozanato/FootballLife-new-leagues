# FL Mod Studio 0.4.0 — brzi početak (FL26 i FL27)

> [English](../en/quick-start-0.4.0.md) · **hrvatski** · [español](../es/quick-start-0.4.0.md) · [português](../pt/quick-start-0.4.0.md) · [français](../fr/quick-start-0.4.0.md)

Sve što trebaš za početak s 0.4.0, redom. Svaka stranica i opcija u dubinu je u
[uputama](mod-studio-guide.md); gotov zip svijeta je u [Instaliraj gotov paket](install-a-pack.md).
Dolaziš s 0.2.5.1 ili starije? Pročitaj i [brzi početak za 0.3.0](quick-start-0.3.0.md).

## 1. Prije ažuriranja

- **Spremi kopiju mape sa saveovima i stare mape Mod Studija**, kao i uvijek.
- **Nakon ažuriranja ponovno instaliraj module: 1. Početna → Instaliraj sada.** Puno popravaka
  je u našim modulima u igri.
- **Karijera koja traje zadržava ono što ima u svom saveu.** Nove lige, kupovi i klubovi
  ažuriranog svijeta dolaze samo u novoj Master League. Tvoja karijera ide dalje s ligama koje ima.
- **Nova licenca.** Od 0.4.0 Mod Studio je pod licencom FL Mod Studio License (`LICENSE.txt` u
  zipu). I dalje ga smiješ besplatno koristiti, mijenjati i dijeliti. Prodavati ga i micati oznaku
  "Powered by FL ModStudio" nije dopušteno. 0.3.0 i starije ostaju pod licencom MIT.

## 2. Nabavi 0.4.0

**Imaš 0.3.0:** **Pomoć → Provjeri ažuriranja...** → **Skini i instaliraj**. Mod Studio se
zatvori, stavi nove datoteke u svoju mapu i ponovno se pokrene.

**Prvi put, ili ručno:** skini `FL26ModStudio-0.4.0.zip` sa
[zadnjeg izdanja](https://github.com/Matozanato/FootballLife-new-leagues/releases/latest) i
raspakiraj ga u zasebnu mapu (na primjer `Documents\FL26 Mod Studio`). Ne pokreći ga iz zipa, a
`_internal` i `pack` ostaju uz `FL26ModStudio.exe`. Dvoklikni `FL26ModStudio.exe`. Ako Windows
kaže "Windows protected your PC": **More info** → **Run anyway**. Tvoje postavke, svjetovi i
recepti su u `%APPDATA%\FL26ModStudio`, pa ostaju.

**Izaberi igru:** **5. Postavke → Pregledaj...** → mapa s `FL_2026.exe` (FL26) ili
`FL_2027.exe` (FL27), ne `SiderAddons` → **Koristi ovu mapu**. Prvi put Mod Studio raspakira
tablice igre: minutu-dvije, pričekaj.

## 3. Tvoj svijet iz 0.3.0

1. **1. Početna → Instaliraj sada** (moduli iz 0.4.0).
2. Svijet koji sam gradiš: **2. Moj svijet → Izgradi i instaliraj** jednom. Puno popravaka iz
   0.4.0 traži novi Build.
3. Učitaj karijeru i igraj dalje. Nove lige, kupovi i klubovi dolaze samo u novoj Master League.

Gotovom svijetu iz zipa (GigaPack, Modpack) ne treba Build. Kad ti autor da novu verziju,
instaliraj novi zip isto kao prvi put (odjeljak 4).

## 4. GigaPack (Football Life 2027)

GigaPack by MatoZanato 1.0 je gotov svijet za **Football Life 2027**: 317 liga i 5.239 klubova, u
jednom zipu, instalira ga Mod Studio, bez Builda. Preuzimanja, md5, što još ne može i poznati
problemi: [GigaPack](../../docs/gigapack.md) (na engleskom).

Ukratko (trebaš FL27 s **updateom 1.1**; prvo zatvori igru i njen launcher):

1. Mod Studio 0.4.0 i mapa igre s `FL_2027.exe` (odjeljak 2).
2. Ne raspakiravaj GigaPack. **1. Početna → Uvezi zip svijeta** → odaberi `GigaPack-1.0.zip` →
   **Instaliraj svijet**. Pričekaj **Spremno za igru**. Ako piše **Skoro spremno**, nabraja što
   treba popraviti.
3. Zeleni **Pokreni igru** u Mod Studiju (ili launcher FL27, ne izravno `FL_2027.exe`) →
   **Master League** → **New game**. Nove lige dobiva samo nova Master League.

## 5. Novo u 0.4.0 i gdje je naći

| Što | Gdje |
|---|---|
| GigaPack 1.0, gotov svijet od 317 liga za FL27 | [GigaPack](../../docs/gigapack.md) (odjeljak 4) |
| Zip svijeta ulazi odmah | **2. Moj svijet → + Dodaj... → Odaberi datoteku...** → zip → **Instaliraj svijet** |
| Uvezi svijet kaže je li zip novija, starija ili ista verzija tvog svijeta | **1. Početna → Uvezi zip svijeta** |
| Update svijeta koji dijeliš čuva karijere njegovih igrača: izvoz traži verziju | **Izvezi...** na kartici svijeta u **2. Moj svijet**; FAQ (na engleskom): [Updating a shared world without breaking careers](../../docs/faq.md#updating-a-shared-world-without-breaking-careers) |
| Kartica za kupove: domaći kupovi i kontinentalna natjecanja | **2. Moj svijet → Kupovi**: **Game Countries**, **Our Countries**, **Continental**. **Primijeni**, pa **Izgradi i instaliraj** |
| Pehari, i u FL27 (u FL27 još nije provjereno u igri) | **3. Sadržaj igre → Pehari** |
| Treći kup za niže lige (FL27) | **Lige → Uredi ligu... → Treći kup (kao EFL Trophy)**, svoji datumi u **Datumi kupova** |
| Lige do 32 kluba (od 29 do 32 igraju jednom međusobno); FL27 uzima i 8 i 9. Još nisu odigrane kroz cijelu sezonu u igri | **Lige → Uredi ligu... → Klubovi** |
| Svoj redoslijed klubova lige u Select Teamu (FL27) | **2. Moj svijet → Klubovi → Više → Redoslijed u Select Team...** |
| Gumb **Spremi** za igrača | **2. Moj svijet → Igrači**, pored **Poništi promjene ovog igrača** |
| FL27: ID-evi natjecanja do 1023 (FL26 ostaje na 255) | **NATJECANJA** gore na **2. Moj svijet**, nakon **1. Početna → Instaliraj sada** |
| Animacije, i kako ih ugasiti | **5. Postavke → Program → Animacije (stranice, gumbi i dijalozi pojavljuju se glatko)** |

Sve ostalo, s popravcima: [changelog 0.4.0](../../docs/changelog/changelog-0.4.0.md) (na engleskom).

## 6. Nešto ne valja?

1. **4. Alati → Dijagnostika → Pokreni provjere → Kopiraj izvještaj.**
2. Na našem [Discordu](https://discord.gg/StQqtk3G3M): **#support** → **Open a support ticket** u
   prikvačenoj poruci, s izvještajem, skrinšotom, `sider.log` i `sider.ini` (oba otvara izbornik
   **Igra**).

Poznato u 0.4.0: [poznati problemi](../../docs/known-issues.md#open-in-mod-studio-040-2026-11-21) ·
što se promijenilo: [changelog 0.4.0](../../docs/changelog/changelog-0.4.0.md) ·
česta pitanja: [FAQ](../../docs/faq.md)
