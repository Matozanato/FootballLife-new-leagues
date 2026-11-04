# FL Mod Studio 0.3.0 — brzi početak (FL26 i FL27)

> [English](../en/quick-start-0.3.0.md) · **hrvatski** · [español](../es/quick-start-0.3.0.md) · [português](../pt/quick-start-0.3.0.md) · [français](../fr/quick-start-0.3.0.md)

Sve što trebaš za početak s 0.3.0, redom. Svaka stranica i opcija u dubinu je u
[uputama](mod-studio-guide.md); gotov svijet ili Modpack zip je u [Instaliraj gotov paket](install-a-pack.md).

> [!WARNING]
> **0.3.0 je više testna verzija.** Ako ti 0.2.5.1 radi i ne trebaš FL27, nema žurbe: ostani na
> njoj dok se 0.3.0 neko vrijeme ne izigra. Ako si u dugoj karijeri, prije ažuriranja spremi kopiju
> mape sa saveovima i stare mape Mod Studija.

## 1. Nabavi 0.3.0

**Imaš 0.2.5.1:** **Pomoć → Provjeri ažuriranja...** → **Skini i instaliraj**. Ili zatvori Mod
Studio i raspakiraj `FL26ModStudio-0.3.0.zip` preko stare mape (zamijeni sve). Tvoje postavke,
svjetovi i recepti ostaju.

**Prvi put:** skini `FL26ModStudio-0.3.0.zip` sa
[zadnjeg izdanja](https://github.com/Matozanato/FootballLife-new-leagues/releases/latest), raspakiraj
ga u zasebnu mapu (`_internal` i `pack` ostaju uz exe) i pokreni `FL26ModStudio.exe`.
Ako Windows kaže "Windows protected your PC": **More info** → **Run anyway**.

Na prozoru sad piše **FL Mod Studio**: to je isti program, preimenovan jer radi i s FL27.
Exe, mapa iz zipa i `%APPDATA%\FL26ModStudio` zadržavaju svoja imena.

## 2. Izaberi igru: FL26 ili FL27

1. **5. Postavke → Mapa igre → Pregledaj...** → mapa s `FL_2026.exe` (FL26) ili
   `FL_2027.exe` (FL27) → **Koristi ovu mapu**.
2. Kad prvi put izabereš igru, Mod Studio raspakira tablice te igre (minutu-dvije; traka dolje to
   piše). FL26 i FL27 imaju svoje tablice i svoje saveove, pa možeš prelaziti s jedne na drugu:
   mapu druge igre izabereš na isti način.
3. **1. Početna**: kad provjera spremnosti kaže da moduli nedostaju ili su stariji, stisni
   **Instaliraj sada**.

## 3. Tvoj svijet iz 0.2.5.1 (FL26)

Tvoji svjetovi i dalje rade. Nakon ažuriranja:

1. **1. Početna → Instaliraj sada** (moduli iz 0.3.0).
2. **2. Moj svijet → Izgradi i instaliraj** jednom.
3. Učitaj karijeru i igraj dalje. Neki popravci vide se tek u novoj Master League: novac za
   transfere malih klubova, NewLife momčadi i lige na mjestima 76, 77 i 80 u Select Teamu.

## 4. Pravi klubovi: NewLife Database 1.6b4

Skini NewLife 1.6b4 s kanala **#newlife** na našem [Discordu](https://discord.gg/StQqtk3G3M).
**U FL27 koristi 1.6b4** (ili 1.6b3): starije verzije su rađene za klubove FL26.

1. Stavi dijelove (`NewLife-1.6b4-Europe.zip` ...) u jednu novu mapu, ne pomiješane sa starijima.
   Ne raspakiravaj dijelove.
2. **2. Moj svijet → NewLife Database → Otvori NewLife Database...** → ta mapa.
3. **Nove lige:** odaberi jednu ili više → **Dodaj u svoj svijet**. Liga države u kojoj igra već
   ima ligu (Greek Super League 2, Scottish Championship ...) ulazi kao rang ispod lige igre, s
   ulaskom u viši rang i ispadanjem; stranica kaže koja.
4. **Lige koje si dodao iz starijeg NewLifea:** **Više → Ažuriraj moje lige na ovu verziju**.
5. **Lige same igre** ostaju kako ih igra ima. **Više → Dovedi lige igre u ovu sezonu...** seli
   njihove klubove i momčadi u NewLife sezonu, ako to želiš. Označi **Samo igrini igrači** da
   dobiješ samo transfere i ocjene, bez novih igrača.
6. **Izgradi i instaliraj**, pa pokreni **novu** Master League: stari save ne preuzima nove
   momčadi.

## 5. Napravi svoj svijet

Cijeli put, klik po klik: [Napravi svoje lige i pakete](make-your-own-leagues.md). Ukratko:

1. **2. Moj svijet → Lige**: dodaj ligu (ili NewLife lige, korak 4), postavi njenu državu, klubove,
   **Rang**, europska mjesta i kupove s **Uredi ligu...**.
2. **Rang** sad može biti i jedna od podijeljenih liga igre (Scottish Premiership, 3F Superliga,
   Jupiler Pro League): tvoja liga ide ispod nje, s ulaskom u viši rang i ispadanjem.
3. **Izgradi i instaliraj**, pa nova Master League.

## 6. Igraj

- **Pokreni igru** (gore desno) pokreće igru sa svime na mjestu.
- **FL27: uvijek ga pokreći preko njegovog launchera** (**FL 2027 start.exe**, njegov prečac ili
  **Pokreni igru** u Mod Studiju). FL_2027.exe pokrenut sam za sebe može se zatvoriti dok se
  stvara nova Master League ili u njenim prvim danima.
- U FL27 su Liga prvaka i Europska liga iz samog FL27; Mod Studio odlučuje tko ulazi iz tvojih
  liga i igra ljetne kvalifikacije; Konferencijsku ligu radi Mod Studio.

## 7. Novo u 0.3.0 i gdje je naći

| Što | Gdje |
|---|---|
| Podrška za FL27 | **5. Postavke → Mapa igre** |
| Klubovi lige (s grbovima) u Select Teamu | u igri: Team Info, League mode ... s kursorom na ligi |
| Obojena mjesta u tablicama liga (Liga prvaka, Europska liga, Konferencijska liga, gore, doigravanje, dolje) | u igri, nakon **Izgradi i instaliraj** |
| Liga umjesto jedne od igrinih skupina "Other ..." u Select Teamu | **2. Moj svijet → Lige → Mjesta u Select Teamu** (svaka liga: *Automatski* ili *umjesto* skupine), pa Build |
| Liga ispod podijeljenih liga igre | **Lige → Uredi ligu... → Rang** |
| NewLife liga ispod lige igre iz njene države | automatski na **Dodaj u svoj svijet**; mijenjaš je u **Rang** |
| Lige siječanj-prosinac nove države: ulazak u viši rang i ispadanje za Novu godinu, i njihov kup | automatski nakon Builda |

## 8. Nešto ne valja?

1. **4. Alati → Dijagnostika → Pokreni provjere → Kopiraj izvještaj.**
2. Objavi to u **#support** na [Discordu](https://discord.gg/StQqtk3G3M) (jedna tema po problemu)
   sa skrinšotom i `SiderAddons\sider.log` (otvara ga izbornik **Igra**).

Poznato u 0.3.0: [changelog](../../docs/changelog/changelog-0.3.0.md#known) ·
česta pitanja: [FAQ](../../docs/faq.md)
