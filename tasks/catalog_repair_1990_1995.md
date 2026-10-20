# Catalog Repair Ticket: Missing Scrape Years (1990, 1991, 1993, 1995)

**Status:** Isolated Backlog Task (Deferred until primary 63-year evidence engine and pilot are verified)  
**Target:** 4 calendar years (1990, 1991, 1993, 1995) out of 67 target years (1960–2026).  
**Current Active Scope:** 63 active years (1960–1989, 1992, 1994, 1996–2026).

---

## 1. Root Cause Analysis
- The raw JSON files in `data/1990.json`, `data/1991.json`, `data/1993.json`, and `data/1995.json` contain 0 tracks (`total_tracks: 0`).
- The album records contain raw unparsed Wikipedia table markup:
  ```json
  "title": "rowspan=\"1\" align=\"center\" | 12",
  "director": "Pattanamdhan Pogalamadi || C. P. Kolappan || Rahman, Radhika, Rupini || Anitha Cine Productions || Shankar–Ganesh"
  ```
- Cause: Wikipedia table format changed the column offsets due to date `rowspan` cells, shifting the film title into the date/rowspan column and the director/composer/cast into the director column.

---

## 2. Repair Strategy
1. Re-scrape Wikipedia articles:
   - `https://en.wikipedia.org/wiki/List_of_Tamil_films_of_1990`
   - `https://en.wikipedia.org/wiki/List_of_Tamil_films_of_1991`
   - `https://en.wikipedia.org/wiki/List_of_Tamil_films_of_1993`
   - `https://en.wikipedia.org/wiki/List_of_Tamil_films_of_1995`
2. Parse tables with rowspan-aware HTML table normalizer (handling multi-cell spans).
3. Extract film articles and soundtrack tracklistings (e.g. *Baashha*, *Bombay*, *Muthu*, *Aasai* in 1995; *Michael Madana Kama Rajan*, *Anjali*, *Kizhakku Vaasal* in 1990; *Thalapathi*, *Chinna Thambi*, *Gunaa* in 1991; *Gentleman*, *Kizhakku Cheemayile*, *Vedham Pudhithu* in 1993).
4. Ingest into `tamil_discography.db` and generate corresponding `playlists/year/{year}.db`.
5. Update `data/catalog_inventory_manifest.json` from 63 active to 67 target years.
