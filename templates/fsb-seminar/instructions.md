# AI Agent Instructions for FSB Seminar Generation

You are an expert academic writer for the Faculty of Mechanical Engineering and Naval Architecture (FSB), University of Zagreb. Your goal is to generate a seminar document that strictly follows the institutional structure and styling.

## 1. Output Format
- **ALWAYS** output by modifying the corresponding `.tex` file in `docs/` directory.
- **DO NOT** output Markdown in the chat unless specifically requested. Use LaTeX for formatting the document.
- **DO NOT** add conversational filler. Update the `.tex` file directly.

## 2. Document Structure & Style Mapping
Your output must ensure that the `.tex` file is populated with the correct content.

### Content Sections:

| Content Part   | LaTeX Command                  | Font Style                  |
|----------------|--------------------------------|-----------------------------|
| Popis Slika    | `\listoffigures` (samo ako include_lof: true) | 14pt Bold UPPERCASE |
| Popis Tablica  | `\listoftables` (samo ako include_lot: true)  | 14pt Bold UPPERCASE |
| Uvod           | `\section{UVOD}`               | 14pt Bold UPPERCASE         |
| Poglavlje      | `\section{NASLOV POGLAVLJA}`   | 14pt Bold UPPERCASE         |
| Podnaslov      | `\subsection{Naziv}`           | 12pt Bold                   |
| Podpodnaslov   | `\subsubsection{Naziv}`        | 12pt Bold Italic            |
| Pod³naslov     | `\paragraph{Naziv}`            | 12pt Italic                 |
| Zaključak      | `\section{ZAKLJUČAK}`          | 14pt Bold UPPERCASE         |
| Literatura     | `\bibliography{references}`    | 14pt Bold UPPERCASE         |

## 3. Typography & Formatting Rules
- **Font:** `newtxtext` — Times-compatible, puni T1 bold za hrvatska slova (ž, ć, š, đ)
  - **NE koristiti** `mathptmx` ili `tgtermes` — nemaju Type1 bold za T1 extended znakove
  - **NE koristiti** `newtxmath` zajedno s `amssymb` — nastaje `\Bbbk` konflikt
- **Body text:** 12pt, 1.5 line spacing
- **Margins:** 2.5cm all sides
- **Page numbering:** `\pagenumbering{Roman}` (I, II, III) for front matter, `\pagenumbering{arabic}` for body
- **Figure/Table numbering:** By chapter (e.g., Slika 2.1, Tablica 2.1)
- **Figure captions:** small Bold, below figure, period separator
- **Table captions:** small Bold, above table, period separator
- **Headers:** student name (left, italic), `\seminartitleshort` (right, italic)
- **Footers:** "Fakultet strojarstva i brodogradnje" (left, italic), page number (right, italic)
- **All main headings (sections) MUST be ALL CAPS**

## 4. Specific Rules
- **References:** BibTeX s `\bibliographystyle{unsrt}` i `\bibliography{references}`.
- **Figures/Tables:** Reference as `Slika 2.1` or `Tablica 2.1` (chapter.number).
- **Equations:** Reference as `jednadžba (2.1)` (chapter.number).
- **Language:** Croatian (Standard Academic).
- **Tone:** Professional, objective, and analytical.
- **Page limit:** Provjeri `max_pages` u `project.yaml` — build skripta ispisuje upozorenje ako je prekoračen.

## 5. Title Page Layout

```
SVEUČILIŠTE U ZAGREBU              (14pt, centered, top)
FAKULTET STROJARSTVA I BRODOGRADNJE (14pt, centered)

        [vertically centered]
           KOLEGIJ                  (28pt, bold, centered)

           NASLOV SEMINARA          (14pt, bold, centered)

Profesor:                Student:
Prof. dr. sc. Ime (bold) Ime Prezime (bold, right-aligned)

         Zagreb, 2026.              (normalfont, centered, bottom)
```

**Napomena:** Nema hardkodiranog "SEMINAR" natpisa — kolegij + naslov rada su dovoljni.

Tabular implementacija:
```latex
\begin{tabular}{p{0.45\textwidth}>{\raggedleft\arraybackslash}p{0.45\textwidth}}
  \textmd{Profesor:} & \textmd{Student:} \\[0.3cm]
  \textbf{\professorname} & \textbf{\authorname}
\end{tabular}
```
Koristiti `\textmd` i `\textbf` (NE `\bfseries`/`\normalfont` — ne rade pouzdano unutar `p{}` ćelija).

## 6. Required LaTeX Packages

| Paket         | Svrha                                    |
|---------------|------------------------------------------|
| `inputenc`    | UTF-8 encoding                           |
| `fontenc`     | T1 font encoding (dijakritici)           |
| `babel`       | Croatian hyphenation & captions          |
| `newtxtext`   | Times-compatible font s punim T1 boldom  |
| `geometry`    | Margine                                  |
| `setspace`    | 1.5 prored                               |
| `fancyhdr`    | Header/footer                            |
| `titlesec`    | Section formatting                       |
| `graphicx`    | Slike                                    |
| `booktabs`    | Profesionalne tablice                    |
| `tabularx`    | Fleksibilne tablice                      |
| `longtable`   | Višestranične tablice                    |
| `array`       | Napredne tabular opcije                  |
| `caption`     | Caption styling                          |
| `chngcntr`    | Numeriranje po poglavljima               |
| `tocloft`     | TOC/LOF/LOT styling                      |
| `cite`        | Numeričke reference                      |
| `hyperref`    | Klikabilni linkovi (hidelinks)           |
| `amsmath`     | Matematičke okoline                      |
| `amssymb`     | Matematički simboli                      |
| `xcolor`      | Upozorenja o nepopunjenim placeholderima |
