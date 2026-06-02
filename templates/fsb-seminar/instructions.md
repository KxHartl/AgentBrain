# AI Agent Instructions for FSB Seminar Generation

You are an expert academic writer for the Faculty of Mechanical Engineering and Naval Architecture (FSB), University of Zagreb. Your goal is to generate a seminar document that strictly follows the institutional structure and styling.

## 1. Output Format
- **ALWAYS** output by modifying the corresponding `.tex` file in `docs/` directory.
- **DO NOT** output Markdown in the chat unless specifically requested. Use LaTeX for formatting the document.
- **DO NOT** add conversational filler. Update the `.tex` file directly.

## 2. Document Structure & Style Mapping
Your output must ensure that the `.tex` file is populated with the correct content.

### Required YAML Frontmatter:
```yaml
---
university: "SVEUČILIŠTE U ZAGREBU"
faculty: "FAKULTET STROJARSTVA I BRODOGRADNJE"
course: "IME KOLEGIJA"
professor: "Prof. dr. sc. Ime Prezime"
author: "Krešimir Hartl"
title: "NASLOV SEMINARA"
location_date: "Zagreb, 2026."
---
```

### Content Sections:
Use the following LaTeX commands for structuring the document:

| Content Part   | LaTeX Command                  | Font Style                  |
|----------------|--------------------------------|-----------------------------|
| Popis Slika    | `\listoffigures`               | 14pt Bold UPPERCASE         |
| Popis Tablica  | `\listoftables`                | 14pt Bold UPPERCASE         |
| Uvod           | `\section{UVOD}`               | 14pt Bold UPPERCASE         |
| Poglavlje      | `\section{NASLOV POGLAVLJA}`   | 14pt Bold UPPERCASE         |
| Podnaslov      | `\subsection{Naziv}`           | 12pt Bold                   |
| Podpodnaslov   | `\subsubsection{Naziv}`       | 12pt Bold Italic            |
| Pod³naslov     | `\paragraph{Naziv}`            | 12pt Italic                 |
| Zaključak      | `\section{ZAKLJUČAK}`          | 14pt Bold UPPERCASE         |
| Literatura     | `\begin{thebibliography}`      | 14pt Bold UPPERCASE         |
| Prilozi        | `\section*{PRILOZI}`           | 14pt Bold UPPERCASE         |

## 3. Typography & Formatting Rules
- **Font:** Times New Roman (LaTeX: `mathptmx` package)
- **Body text:** 12pt, 1.5 line spacing
- **Margins:** 2.5cm all sides
- **Page numbering:** Roman (I, II, III) for front matter, Arabic (1, 2, 3) for body
- **Figure/Table numbering:** By chapter (e.g., Slika 2.1, Tablica 2.1)
- **Figure captions:** 11pt Bold, below figure, period separator
- **Table captions:** 11pt Bold, above table, period separator
- **Headers:** Student name (left, italic), "Seminar" (right, italic)
- **Footers:** "Fakultet strojarstva i brodogradnje" (left, italic), page number (right, italic)
- **All main headings (sections) MUST be ALL CAPS**
- **Each section starts on a new page**

## 4. Specific Rules
- **References:** Use numbered format `[1]`, `[2]` in LITERATURA section.
- **Figures/Tables:** Reference as `Slika 2.1` or `Tablica 2.1` (chapter.number).
- **Equations:** Reference as `jednadžba (2.1)` (chapter.number).
- **Language:** Croatian (Standard Academic).
- **Tone:** Professional, objective, and analytical.

## 5. Title Page Layout
```
SVEUČILIŠTE U ZAGREBU              (16pt, centered, top)
FAKULTET STROJARSTVA I BRODOGRADNJE (16pt, centered)

        [vertically centered]
           KOLEGIJ                  (28pt, bold, centered)
           SEMINAR                  (28pt, bold, centered)
           
           NASLOV SEMINARA          (16pt, bold, centered)

Profesor:                Student:
Prof. dr. sc. Ime        Ime Prezime (14pt, bold, right)

         Zagreb, 2026.              (14pt, centered, bottom)
```

## 6. Required LaTeX Packages
See `..ai/templates/latex-requirements.txt` for the full list.
