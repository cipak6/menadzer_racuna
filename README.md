# Bitno

NISAM PROGRAMER, trebao mi je alat za određeni posao i napravio sam ga, ako može još nekome da pomogne, biće mi drago, sve je open source baš zbog toga.
Logika za parsiranje fiskalnih računa bazirana na radu [@ivang5](https://github.com/ivang5/Moji-Racuni) — hvala!

# Menadžer računa

Desktop aplikacija za Windows i Mac koja automatski preuzima podatke sa srpskih fiskalnih računa sa purs.gov.rs, čuva ih u Excel tabeli i generiše digitalne slike računa sa QR kodom.

---

## Funkcija

- Dodaj račun skeniranjem QR koda (slika ili PDF) ili uz pomoć linka sa purs.gov.rs
- Ručni unos za račune koji se ne mogu skenirati
- Automatski generiše digitalnu sliku svakog računa sa QR kodom na dnu
- Sve se čuva u Excel tabeli (jedan red po računu + poseban sheet za stavke)
- Pretraga i pregled svih računa u aplikaciji
- Radi na Windows i Mac

---

## Pokretanje

```bash
# 1. Kloniraj repo
git clone https://github.com/cipak6/racuni_app.git
cd racuni_app

# 2. Venv
python3 -m venv venv
source venv/bin/activate        # Mac
# ili: venv\Scripts\activate    # Windows

# 3. Instaliraj requirements
pip install -r requirements.txt

# 4. Na Macu je potreban zbar za QR dekodiranje
brew install zbar

# 5. Pokretanje
python app.py
```

---

## Build

### Windows (.exe)
Build se automatski pravi preko GitHub Actions kada pushuješ na `main`. Skinuti artifact iz Actions taba — folder `Racuni/` sa `Racuni.exe` unutra.

### Mac (.app)
```bash
pip install pyinstaller
pyinstaller racuni_mac.spec
```
App će biti u `dist/Racuni.app`.

---

## Gde se čuvaju podaci

Sve ide u `~/Racuni/` folder:

```
~/Racuni/
  invoices.db          ← baza podataka
  invoices.xlsx        ← Excel export
  invoice_images/
    20260125_1500_00.png
    20260203_600_00.png
    ...
```

Slike se imenuju po formatu `YYYYMMDD_IZNOS.png`.

---

## Excel struktura

**Sheet "Invoices"** — jedan red po računu:
`Datum | Kompanija | Detalji | Prodajno mesto | Adresa | Grad | Iznos | PDV | Broj stavki | Broj računa | URL | Slika`

**Sheet "Items"** — jedan red po stavki:
`Datum | Kompanija | Prodajno mesto | Naziv | Jedinica | Količina | Cena | Ukupno | PDV% | URL`

---

## Paketi

| Paket | Za šta se koristi |
|---|---|
| `customtkinter` | UI |
| `requests` + `beautifulsoup4` + `lxml` | Scraping purs.gov.rs |
| `srtools` | Ćirilica → latinica |
| `openpyxl` | Excel |
| `zxing-cpp` | QR dekodiranje |
| `pymupdf` | Čitanje PDF fajlova |
| `Pillow` | Generisanje slika računa |
| `qrcode` | QR kod na slici računa |

---

## Licenca

MIT — open source