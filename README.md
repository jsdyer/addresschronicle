# Address Chronicle

[Search historical directories](https://coolcode.ca/addresschronicle/) for a Vancouver or Halifax street, house number, person or business. Search runs on your device against real, page-indexed OCR, with direct links to original scans.

<!-- coolcode:guide -->
Start with a street such as Granville or Barrington, then add a number or surname. OCR errors, changed street numbering and selective directory coverage can hide a match. Open the original scan and confirm the printed city heading before treating an excerpt as evidence.
<!-- /coolcode:guide -->

## Current collection

- Vancouver: The Elite Directory (1908), a selective social/club directory; Henderson's Greater Vancouver City Directory (1922), covering the city and surrounding municipalities.
- Halifax: the 1860, 1861 and 1862 Provincial Wesleyan Almanacks, which include business directories and provincial material; Bards & Co's 1900 business directory, which includes Halifax, Dartmouth and many other cities.

This is not a complete residential history, and it does not promise a 1925 edition or every inhabitant. Multi-city and almanac matches can relate to places outside Halifax. Results repeat each source's coverage note. Editions are taken from the actual volume/title evidence: Henderson's general catalogue date 1919 does not override its volume 1922; the 1861 almanack's title takes precedence over its catalogue publication date 1860. These distinctions are recorded in `web/data/catalogue.json`.

## Using the tool

Choose a collection and edition, enter an address/street/person/business and select **Search directories**. By default, Halifax searches use reviewed business-directory page ranges. Enable **Include surrounding almanac and other-city pages** to search the entire indexed volume. This avoids confusing Barrington township with Barrington Street while preserving access to advertisements and wider context. The browser downloads only the selected editions, in JSON parts below 750 KB, then searches them in a Web Worker. Searches match words within up to three neighbouring OCR lines, or an exact phrase after normalizing punctuation/case. A result can cross a column boundary: the scan remains authoritative.

Results show a source edition, OCR excerpt, printed page where available and reader scan number. **Save evidence** keeps an excerpt locally. Saved entries retain their original source/date even if the collection later changes. **Export results** produces a CSV with excerpts and citations. **Copy citation** provides a plain-text source reference. Saved evidence is limited to 200 excerpts to bound browser storage; export before clearing it.

A verified example: search **520 Granville** in the 1908 Vancouver edition. The original OCR includes “520 Granville Street, Vancouver, B.C., Canada”. This is source leaf 12, reader index 11 and printed page 4: [open the original scan](https://archive.org/details/31383021405025/page/n11/mode/1up). This is a printed address occurrence, not automatically a resident entry. The collector keeps leaf number, zero-based reader index and printed page separate; blank scanned pages still count toward the reader index. This mapping was checked against Internet Archive's BookReaderJSIA page list.

## Sources, publication and dates

The source catalogue names each Internet Archive identifier, contributing library, source title/date/volume, reviewed edition year, OCR download URL, SHA-256 of the source XML, retrieval timestamp, page count and index parts. OCR is extracted from the published DjVu XML page/line/word structure. Printed labels come from the corresponding scandata when supplied. Historical source scans remain with Internet Archive.

The **Browser tool · Check and publish** workflow refreshes on the **second day of each month at 08:17 UTC** and on manual dispatch. Ordinary pushes and PRs build offline. Collection validates every volume into staging before replacing the local snapshot. Download failures, oversized data or invalid page references fail collection; the previous deployed snapshot remains unchanged. Git retains previous published snapshots. The separate schedule guard protects this workflow and itself against inactivity disablement; it is not a freshness signal.

Freshness endpoint: `data/status.json`, `checked_at`, suggested tolerance 40 days. It measures a successful check/index generation, not a new historic edition. Central watchdog/catalogue integration is supplied separately because this round does not authorize edits to existing repositories.

## Expand or customize

Edit `config/collections.json`. Add an Internet Archive book with a public `Djvu XML` file and a reviewed historical edition year, for example another city directory:

```json
{
  "id": "ACTUAL_ARCHIVE_IDENTIFIER",
  "city": "City name",
  "year": 1910,
  "title": "Actual directory title, 1910",
  "edition_evidence": "Describe the title-page or metadata evidence for this edition.",
  "scope": "Describe the actual coverage and its limits."
}
```

Do not use the example identifier literally. Use a real verified source; check its scanning order and rights before adding it. Collections support up to 50 volumes and reviewed years 1700–1930. Those bounds are operational starting points in `scripts/refresh.py`, not a claim that other editions are unavailable. `directory_leaf_ranges` optionally identifies reviewed business-directory sections using source leaf numbers; `range_evidence` records the review. Reader indexes are never renumbered when applying these filters. Filters and counts derive from the catalogue. `examples` in the same file supplies optional starting searches; visitors can search any text in the indexed collection. Add historical street-name variants as separate example searches with a source, rather than silently replacing modern names.

Run:

```sh
python3 scripts/refresh.py
node --test tests/*.test.mjs
python3 -m unittest discover -s tests -v
python3 scripts/build.py
```

Commit config and generated `web/data/` together, then push to `main`. Alternatively dispatch **Browser tool · Check and publish** after the config edit; it refreshes, tests, commits the validated generated data and publishes the same build. Failed refreshes do not replace good deployments. The generated data directory is managed by the collector; do not store manual notes there.

## Privacy and requirements

Queries stay in memory and are not sent to Internet Archive. Local searches only request public index files from this site. Excerpts are stored only when explicitly saved, under `coolcode:addresschronicle:evidence`. **Clear saved evidence** removes them. Opening a scan visits Internet Archive; copy/export actions stay local. No account, API key, Worker route or server installation is required.

Python 3.12+ and Node 24+ run collection/tests/build. The app has no runtime package dependencies. CI checks the browser workflow, persistence, export, safe text and mobile layout at a project subpath. Only `dist/` is deployed; do not commit it or add a CNAME. The main catalogue record is `tool.json`; homepage, sitemap and watchdog registrations remain a separate integration step, not implied by successful app publication.
