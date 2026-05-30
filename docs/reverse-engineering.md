# Reverse-engineered interface — erowid.org

Erowid publishes no JSON API. The structured data returned by `pyerowid` is
recovered entirely from the site's own server-side query endpoints and the HTML
they emit. This document records every endpoint used, the query parameters the
server accepts, how result sets are navigated, and the fields extracted from each
page type — grounded strictly in the source code (`pyerowid/reports.py`,
`pyerowid/parse.py`).

---

## Endpoints

### 1. Experience report — `GET /experiences/exp.php`

The primary content endpoint. Each experience report has a numeric ID; the ID
range known to be populated runs from 1 to at least 111 451 (constant
`MAX_EXPERIENCE_ID` in `reports.py`).

| Query param | Type | Meaning |
|---|---|---|
| `ID` | integer | Experience report identifier |

**Example URL:**
```
https://erowid.org/experiences/exp.php?ID=1
```

The server returns a full HTML page when the ID exists and has a published
report, or a page with an empty `div.title` for deleted / unpublished IDs.

**Parsed fields** (from `parse_experience`):

| Field | Source in HTML |
|---|---|
| `name` | `div.title` text |
| `author` | `div.author` text |
| `substance` | `div.substance` text (lowercased; `/` → `, `) |
| `text` | Content between `<!-- Start Body -->` / `<!-- End Body -->` comments, `<br>` → newline |
| `year` | First line of `table.footdata` text, prefix `exp year:` stripped |
| `gender` | Second line of `table.footdata`, prefix `gender:` stripped |
| `age` | Third line of `table.footdata`, prefix `age at time of experience:` stripped |
| `date` | Fourth line of `table.footdata`, prefix `published:` stripped, `views:` suffix dropped |
| `dosage` | Rows of `table.dosechart`; one `DosageEntry` per row (see below) |

**`DosageEntry` fields** (one per dose-chart row):

| Field | CSS selector |
|---|---|
| `time` | `td[align=right]` — prefix `dose:` stripped |
| `amount` | `td.dosechart-amount` |
| `method` | `td.dosechart-method` |
| `substance` | `td.dosechart-substance` |
| `form` | `td.dosechart-form` |

An ID is considered to have no report (returns `None`) when `div.title` is
absent or empty.

---

### 2. Full-text search — `GET /experiences/exp.cgi`

The experience search endpoint. Erowid exposes this as a form submission on the
site; the parameters below were recovered from the form action and the sort
links in the result table.

| Query param | Type | Meaning |
|---|---|---|
| `Str` | string | Search term (substance name, keyword, etc.) |
| `OldSort` | string | Sort order — see values below |

**`OldSort` values recovered from the sort links in result pages:**

| Value | Meaning |
|---|---|
| `SA` | Sort by substance (default) |
| `PDD` | Sort by date, descending (most recent first) |
| `PDA` | Sort by date, ascending (oldest first) |
| `RA` | Sort by rating |

The `pyerowid.search_reports` function accepts a friendlier `order` alias
(`"substance"`, `"recent"`, `"old"`, `"rating"`) and maps it to these values;
a raw `OldSort` value can also be passed directly.

**Pagination:** The server supports offset-based pagination via two additional
query parameters:

| Query param | Type | Meaning |
|---|---|---|
| `Start` | integer | 0-based offset into the result set |
| `Max` | integer | results per page (100 is the largest value observed) |

When `Start`/`Max` are omitted the server returns its own default page. A
`table.results-table` in the response carries a banner like *"Page 1 of 3 /
232 reports returned"* — the page count is parsed by
`parse_search_page_count`. Additional parameters observed in pagination links:

| Parameter | Observed value | Effect |
|---|---|---|
| `ShowViews` | ``0`` | hides view counts (link-generated; safe to omit) |
| `Cellar` | ``0`` | unknown filter; safe to omit |

`search_all_reports` auto-iterates all pages. `search_reports` exposes `start`
and `page_size` for manual paging.

**Parsed fields** (from `parse_search`, one `Report` per row):

| Field | Source in HTML |
|---|---|
| `exp_id` | Integer extracted from the `href` of the row's `<a>` tag matching `ID=(\d+)` |
| `url` | `https://erowid.org/experiences/` + that `href` |
| `name` | Last-four cells of `tr.exp-list-row` — cell 0 |
| `author` | Last-four cells — cell 1 |
| `substance` | Last-four cells — cell 2 |
| `date` | Last-four cells — cell 3 |

The result set lives in `table.exp-list-table`. Rows are `tr.exp-list-row` in
the crafted test fixture; on the **live site and Wayback snapshots the rows
carry no CSS class** — the parser detects both cases (explicit class first,
then any `<tr>` with an `ID=` link as fallback).

**Example URL:**
```
https://erowid.org/experiences/exp.cgi?Str=LSD&OldSort=PDD
```

---

### 3. Category index pages — `GET /{category}/`

The vault index for each substance category. These are standard CMS pages, not
parameterised query endpoints, but their HTML structure is consistent enough to
be parsed reliably.

| Base URL | Category |
|---|---|
| `https://erowid.org/pharms/` | Pharmaceuticals |
| `https://erowid.org/chemicals/` | Chemicals |
| `https://erowid.org/plants/` | Plants |
| `https://erowid.org/herbs/` | Herbs |
| `https://erowid.org/smarts/` | Smart products |
| `https://erowid.org/animals/` | Animals |

**Parsed fields** (from `parse_substance_list`, one `SubstanceListing` per row):

| Field | Source in HTML |
|---|---|
| `name` | `td.topic-name` text (lowercased) |
| `url` | Base URL + `href` of the `<a>` inside `td.topic-name` |
| `other_names` | `td.topic-common` text (lowercased) |
| `effects` | `td.topic-desc` text (lowercased) |

Rows are `tr.topic-surround` inside `table.topic-chart-surround`; the first row
is a header and is skipped.

---

### 4. Experience-category list — `GET /experiences/exp_list.shtml`

A static overview page listing experience-report categories. Categories are
extracted from HTML comments of the form `<!-- Start <Category Name> -->`.
Used by `get_categories()`.

---

### 5. Substance vault summary pages — `GET /{category}/{slug}/{slug}.shtml`

Individual substance topic-card pages (e.g.
`https://erowid.org/pharms/acetaminophen/acetaminophen.shtml`). These are
static HTML files, not query endpoints.

**Parsed fields** (from `parse_page`, into `SubstanceInfo`):

| Field | Source in HTML | Present for |
|---|---|---|
| `name` | `div.title-section` text | all |
| `picture` | `img` inside `div.summary-card-topic-image`, `src` relative to base | all |
| `other_names` | `div.sum-common-name` text, split on `;` | all |
| `description` | `div.sum-description` text | all |
| `info` | `<a>` tags inside `div.summary-card-icon-surround` — `{img.alt: href}` | all |
| `chem_name` | `div.sum-chem-name` | `/chem`, `/pharms`, `/smarts` |
| `effects` | `div.sum-effects` | chemicals, pharms, smarts, plants, animals |
| `family` | `div.fgs-row[0] div.family` | plants, animals |
| `genus` | `div.fgs-row[1] div.genus` | plants, animals |
| `species` | `div.fgs-row[2] div.species` | plants, animals |
| `uses` | `div.sum-uses` | herbs only |

---

## Caveats

All parsing is HTML-structure-dependent. Erowid is a manually maintained site;
markup can be inconsistent between pages, especially older entries. Missing
`div.title`, absent `table.footdata` rows, or a missing dose chart are handled
gracefully (fields default to empty strings / empty lists). The ID space is
sparse — many IDs in the 1–111 451 range return empty pages.
