---
domain: latex_fonts
type: gotcha
author: AgentRealm
verified: "2026-06, FSB semestar_10/humanoidna-seminar"
---
# mathptmx ne renderira bold za T1 dijakritike (ž, ć, š, đ)

## Kontekst

MiKTeX + pdflatex + `\usepackage{mathptmx}` + `\usepackage[T1]{fontenc}`

## Simptom

`\textbf{Krešimir}` izgleda isto kao normalfont — nema vizualne razlike u bold
weightu. Kompilacija prolazi bez greške ili upozorenja. Inspektiranjem log-a
vide se `tcrm` (regular) EC bitmap fontovi umjesto `tcrb` bold varijante.

## Uzrok

`mathptmx` mapira T1 proširene znakove (> ASCII 127) na EC bitmap fontove koji
nemaju zasebnu bold Type1 varijantu. Rezultat: `\bfseries` i `\textbf{}` padaju
nazad na regular weight za sve znakove s dijakriticima.

## Rješenje

Zamijeni `mathptmx` s `newtxtext`:

```latex
% UKLONI:
\usepackage{mathptmx}

% DODAJ:
\usepackage{newtxtext}
```

**Upozorenje**: NE koristiti `newtxmath` zajedno s `\usepackage{amssymb}` —
nastaje `\Bbbk` konflikt. Samo `newtxtext` je siguran uz standardne
`amsmath`/`amssymb` pakete.

## Alternativa

`tgtermes` ima isti problem na nekim MiKTeX distribucijama. `newtxtext` je
najpouzdaniji izbor za pdflatex + T1 + hrvatska slova.
