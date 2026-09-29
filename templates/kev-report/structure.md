---
# Obavezna polja — latex_architect čita iz project.yaml
author_name: ""
course_name: ""              # interno (npr. "IFTS — interna procjena"); nije na naslovnici
seminar_title: ""            # naslov dokumenta (naslovnica + PDF metapodaci)
seminar_title_short: ""      # header lijevo, max ~40 znakova
professor_name: ""           # validacija (npr. "Uprava")
# Opcijska kev_* polja (render_template.py → naslovnica)
kev_department: "TEHNIKA"    # gore desno
kev_doc_number: ""           # Broj dokumenta
kev_issue: "A"               # Izdanje
kev_date: ""                 # prazno → današnji datum dd.mm.yyyy.
kev_author: ""               # Izradio; prazno → author_name
kev_reviewed_by: ""          # Pregledao
kev_approved_by: ""          # Odobrio
kev_file_name: ""            # Datoteka; prazno → ime izlaznog PDF-a (main.pdf)
kev_section_newpage: false   # true → svaki \section na novoj stranici
include_lof: false
include_lot: false
---

# Struktura KEV izvještaja

## Naslovnica (automatski iz project.yaml, `\kevtitlepage`) — stranica 1

```
[logo KONČAR – Električna vozila]                    {{KEV_ODJEL}}
| Datoteka: {{KEV_DATOTEKA}} |   | Broj dokumenta: {{KEV_BROJ_DOKUMENTA}} |

                     {{NASLOV_SEMINARA}}

| Datum: {{KEV_DATUM}} | Izdanje: {{KEV_IZDANJE}} | Izradio: {{KEV_IZRADIO}} | Pregledao: {{KEV_PREGLEDAO}} | Odobrio: {{KEV_ODOBRIO}} |
[ Ovaj dokument je vlasništvo KONČAR – ELEKTRIČNA VOZILA d.d. ...   Ukupno stranica: N ]
```

## Prednji dio (arapske stranice, kontinuirano)

- Sadržaj (`\tableofcontents`) — stranica 2
- Popis slika / tablica — samo ako `include_lof` / `include_lot: true`

## Tijelo rada

| Razina        | LaTeX                          | Format                                  |
|---------------|--------------------------------|-----------------------------------------|
| Poglavlje     | `\section{Naslov}`             | Verdana* Bold plava, „1.“ + razmak      |
| Podpoglavlje  | `\subsection{Naziv}`           | Verdana* Bold plava, uvučeno 5 mm       |
| Pod-pod       | `\subsubsection{Naziv}`        | Verdana* Bold plava, manji              |
| Paragraf      | `\paragraph{Naziv}`            | Calibri* Bold (runin)                   |

### Obavezne sekcije

1. **Uvod** — `\input{chapters/00-uvod}`
2. *(poglavlja po potrebi — writer dodaje `\input{chapters/NN-naziv}`)*
3. **Zaključak** — `\input{chapters/zakljucak}`

## Stražnji dio

- **Literatura** — `\bibliography{references}` s `\bibliographystyle{unsrt}`

## Datoteke koje `--scaffold` kopira

- `assets/kev_logo.png` → `docs/figures/kev_logo.png`
- `fonts/*` (Carlito, DejaVu Sans + licence) → `docs/fonts/`

## Pravila citiranja

- Svaka tvrdnja mora imati `\cite{key}`
- PDF izvora mora biti u `data/sources/` PRIJE pisanja (data_fetcher pribavlja)
- Jedina iznimka: rad je paywalled i logiran u `data/SOURCES_LOG.md`
