---
# Obavezna polja — latex_architect čita iz project.yaml
author_name: ""
course_name: ""
seminar_title: ""
seminar_title_short: ""    # max ~50 znakova za header
professor_title: ""        # npr. "Prof. dr. sc."
professor_name: ""
include_lof: false         # true → \listoffigures se uključuje
include_lot: false         # true → \listoftables se uključuje
max_pages: 12
---

# Struktura FSB seminara

## Naslovnica (automatski iz project.yaml)

```
SVEUČILIŠTE U ZAGREBU
FAKULTET STROJARSTVA I BRODOGRADNJE

{{KOLEGIJ}}

{{NASLOV_SEMINARA}}

Profesor:                    Student:
{{PROFESOR}}                 {{IME_I_PREZIME}}

                Zagreb, {{GODINA}}.
```

## Prednji dio (rimske stranice I, II, III...)

- SADRŽAJ (`\tableofcontents`)
- POPIS SLIKA (`\listoffigures`) — samo ako `include_lof: true`
- POPIS TABLICA (`\listoftables`) — samo ako `include_lot: true`

## Tijelo rada (arapske stranice 1, 2, 3...)

| Razina        | LaTeX                          | Format                  |
|---------------|--------------------------------|-------------------------|
| Poglavlje     | `\section{NASLOV}`             | 14pt Bold UPPERCASE     |
| Podpoglavlje  | `\subsection{Naziv}`           | 12pt Bold               |
| Pod-pod       | `\subsubsection{Naziv}`        | 12pt Bold Italic        |
| Paragraf      | `\paragraph{Naziv}`            | 12pt Italic (runin)     |

### Obavezne sekcije

1. **UVOD** — `\input{chapters/00-uvod}`
2. *(poglavlja po potrebi — writer dodaje `\input{chapters/NN-naziv}`)*
3. **ZAKLJUČAK** — `\input{chapters/zakljucak}`

## Stražnji dio

- **LITERATURA** — `\bibliography{references}` s `\bibliographystyle{unsrt}`

## Pravila citiranja

- Svaka tvrdnja mora imati `\cite{key}`
- PDF izvora mora biti u `data/sources/` PRIJE pisanja (data_fetcher pribavlja)
- Jedina iznimka: rad je paywalled i logiran u `data/SOURCES_LOG.md`
