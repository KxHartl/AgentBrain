---
domain: citation_workflow
type: gotcha
author: AgentRealm
verified: "2026-06, FSB semestar_10/humanoidna-seminar"
---
# Writer zaobilazi data_fetcher — cita radove bez PDF-a u data/sources/

## Simptom

`data/sources/` je prazan, ali `references.bib` ima puno stavki i seminar je
"gotov". U references.bib pojavljuju se stavke s `TODO-AUTORI` ili autori koji
su djelomično netočni.

## Uzrok

Writer agent ima (ili je imao) korak "ako ključ ne postoji u references.bib,
dodaj ga via `add_citation.py --doi`". Ovo dozvoljava writeru da:
1. Generira sadržaj iz training knowlegea (nije grounded u stvarnim dokumentima)
2. Doda citat po DOI-u bez provjere autora, stranica i detalja u PDF-u
3. Preskoci `data_fetcher` — cijeli sources pipeline se ne pokreće

Rezultat: potencijalno fabricirani ili netočni sadržaj koji izgleda legitimno.

## Uzrok propusta u humanoidna-seminar (2026-06)

Dva rada imala su nedostupne autore via DOI lookup:
- `humanoid_safety_review2025` (Electronics, MDPI)
- `scirobotics2026beyond` (Science Robotics, 2026)

Bez PDF-a, AI nije mogao verificirati autore → ručno insertirani `TODO-AUTORI`.

## Ispravno ponašanje

**Pipeline redoslijed je obvezan:**
```
data_fetcher (preuzmi PDF + generiraj BibTeX) → ONDA writer (piši + citiraj)
```

Writer NIKAD ne zove `add_citation.py` sam. Writer NIKAD ne piše sadržaj
koji citira rad čiji PDF nije u `data/sources/`.

Jedina iznimka: rad je paywalled i `data_fetcher` ga je logirao kao takvog
u `data/SOURCES_LOG.md` — tada writer može koristiti DOI-generirani BibTeX
uz napomenu da autori nisu verificirani.

## Kako spriječiti

- writer.md: quality gate zabranjuje writer-u pozivanje `add_citation.py`
- qa_reviewer.md: CRITICAL check — data/sources/ mora imati PDF za svaki \cite{}
- Pred početak pisanja: provjeri `ls data/sources/` — ako je prazan, pozovi data_fetcher
