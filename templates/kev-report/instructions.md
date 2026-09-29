# AI Agent Instructions for KEV Report Generation

You are an expert technical writer for KONČAR – Električna vozila d.d. (KEV). Your goal is to generate an internal technical report that strictly follows the KEV corporate Word template (title page with document block, running header, ownership footer box).

## 1. Output Format
- **ALWAYS** output by modifying the corresponding `.tex` file in `docs/` directory.
- **DO NOT** output Markdown in the chat unless specifically requested. Use LaTeX for formatting the document.
- **DO NOT** add conversational filler. Update the `.tex` file directly.
- **Engine:** Tectonic / XeLaTeX only (fontspec). pdfLaTeX is NOT supported.

## 2. Document Structure & Style Mapping

| Content Part   | LaTeX Command                  | Font Style                                   |
|----------------|--------------------------------|----------------------------------------------|
| Sadržaj        | `\tableofcontents`             | Verdana* Bold 16pt, KEV plava                |
| Poglavlje      | `\section{Naslov}`             | Verdana* Bold ~11.5pt plava, „1.“ + razmak 12.7 mm |
| Podnaslov      | `\subsection{Naziv}`           | Verdana* Bold ~10.5pt plava, uvučeno 5 mm, „2.1 Naziv“ |
| Podpodnaslov   | `\subsubsection{Naziv}`        | Verdana* Bold 10pt plava                     |
| Paragraf       | `\paragraph{Naziv}`            | Calibri* Bold, run-in                        |
| Literatura     | `\bibliography{references}`    | kao `\section*`                              |

\* Verdana → **DejaVu Sans**, Calibri → **Carlito** (metrički kompatibilan klon). Oba fonta su u `docs/fonts/`.

## 3. Typography & Formatting Rules
- **Body text:** Carlito 11pt, prored ≈ Word 1.15, obostrano poravnato, bez rastavljanja riječi, razmak 8pt između odlomaka, bez uvlake.
- **Boje:** KEV plava `kevblue` #0082CA (naslovi, header, footer, naslovnica); opisi `kevcaption` #44546A; zaglavlje tablice `kevtablehead` #51A5EE.
- **Margins:** 25 mm lijevo/desno (širina teksta 160 mm).
- **Header (bez crte):** lijevo kratki naslov (Verdana* Bold plava), desno „KONČAR – ELEKTRIČNA VOZILA d.d“.
- **Footer:** okvir 1.5pt preko cijele širine — „Ovaj dokument je vlasništvo **KONČAR – ELEKTRIČNA VOZILA d.d.**“ / „Neovlašteno kopiranje nije dozvoljeno!“, desno „Stranica: x/N“.
- **Page numbering:** arapski, kontinuirano od naslovnice (naslovnica = 1, sadržaj = 2). Naslovnica prikazuje ukupan broj stranica (`lastpage`).
- **Captions:** „Tablica 1. Naslov“ IZNAD tablice, „Slika 1. Naslov“ ISPOD slike; mali kurziv #44546A, lijevo poravnato, numeracija kontinuirana (ne po poglavljima).
- **Zaglavlje tablice:** svaka ćelija kroz `\kevth{...}` (svijetloplavi tekst). Booktabs (`\toprule`/`\midrule`) je dozvoljen.
- **Nova stranica po poglavlju:** opcijski, `kev_section_newpage: true` u `project.yaml`.

## 4. Specific Rules
- **References:** BibTeX s `\bibliographystyle{unsrt}` i `\bibliography{references}`.
- **Figures/Tables:** Reference as `slika 2` / `tablica 2` (kontinuirano).
- **Language:** Croatian (Standard Technical).
- **Tone:** Professional, objective, and analytical.
- **Logo:** `docs/figures/kev_logo.png` — ne mijenjati i ne skalirati izvan naslovnice.

## 5. Title Page Layout

```
[KONČAR logo 49 mm]                                TEHNIKA   (kev_department, bold plavo)

| Datoteka: <kev_file_name> |            | Broj dokumenta: <kev_doc_number> |   (isprekidani separatori)

                  NASLOV DOKUMENTA   (26pt bold plavo, vertikalno centrirano)

| Datum:     | Izdanje: | Izradio:     | Pregledao:        | Odobrio:        |
| kev_date   | kev_issue| kev_author   | kev_reviewed_by   | kev_approved_by |
[ Ovaj dokument je vlasništvo KONČAR – ELEKTRIČNA VOZILA d.d.      Ukupno     ]
[ Neovlašteno kopiranje nije dozvoljeno!                          stranica: N ]
```

Naslovnicu generira makro `\kevtitlepage` — NE pisati je ručno.

## 6. Required LaTeX Packages

| Paket         | Svrha                                         |
|---------------|-----------------------------------------------|
| `fontspec`    | Carlito / DejaVu Sans iz `docs/fonts/` (Path=) |
| `babel`       | Croatian hyphenation & captions (Slika/Tablica) |
| `xcolor`      | KEV boje                                      |
| `geometry`    | Margine, header/footer pozicija               |
| `setspace`    | Prored                                        |
| `enumitem`    | Zbijene liste                                 |
| `fancyhdr`    | Header / footer okvir                         |
| `titlesec`    | Naslovi                                       |
| `tocloft`     | Sadržaj (točkice, podebljani brojevi podnaslova) |
| `caption`     | Opisi slika/tablica                           |
| `tikz`        | Redak „Datoteka / Broj dokumenta“             |
| `lastpage`    | Ukupan broj stranica                          |
| `graphicx`, `booktabs`, `tabularx`, `longtable`, `array`, `float` | Slike i tablice |
| `amsmath`, `amssymb` | Matematika                             |
| `cite`, `hyperref` | Reference i linkovi (hidelinks)          |

## 7. Fonts & Licences
- `Carlito-*.ttf` — SIL Open Font License 1.1 (`fonts/OFL-Carlito.txt`), izvor google/fonts `ofl/carlito`.
- `DejaVuSans*.ttf` — Bitstream Vera licence + public domain izmjene (`fonts/LICENSE-DejaVu.txt`).
