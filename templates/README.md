# LaTeX Predlošci

Akademski predlošci za FSB (Fakultet strojarstva i brodogradnje), Sveučilište u Zagrebu, i korporativni predložak KONČAR – Električna vozila (KEV).

## Dostupni predlošci

| Predložak | Direktorij | Format | Namjena |
|---|---|---|---|
| **Seminar** | `fsb-seminar/` | 12pt, A4 | Seminarski radovi |
| **Diplomski rad** | `fsb-thesis/` | 12pt, A4 | Diplomski/završni rad |
| **Paper** | `fsb-paper/` | 10pt, dva stupca | Znanstveni/konferencijski rad |
| **KEV izvještaj** | `kev-report/` | 11pt, A4, XeLaTeX | Interni tehnički izvještaj KONČAR – Električna vozila (logo, blok dokumenta, footer vlasništva) |

## Kako koristiti

1. Odaberi predložak prema tipu rada.
2. Kopiraj sadržaj iz `<predložak>/latex/` u `docs/` direktorij projekta.
3. Prilagodi naslov, autora i sadržaj.
4. Kompajliraj s `build-docs` skriptom.

## Sadržaj svakog predloška

```
predložak/
├── latex/          # LaTeX source files (.tex)
├── demo.pdf        # compiled example
├── instructions.md # AI agent instructions for this format
├── structure.md    # document skeleton
├── assets/         # (opcijski) slike → docs/figures/ pri --scaffold (npr. kev_logo.png)
└── fonts/          # (opcijski) fontovi → docs/fonts/ pri --scaffold (kev-report: Carlito, DejaVu Sans)
```

> `word/` directories exist in some templates as legacy reference only. Agents **never** use Word files — LaTeX only.

## LaTeX paketi

Potrebni paketi su navedeni u `latex-requirements.txt`.
