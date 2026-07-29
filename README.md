# BRIDGES - Scoping review of socio-ecological modelling tools

Literature review of socio-ecological modelling tools for spatial management and
decision support in marine and coastal systems, carried out for the BRIDGES-Avatar
project (WP4).

This repository contains the search strategy, screening records, full-text
retrieval pipeline, AI-assisted extraction scripts, the validation of that
extraction, and the analysis code produced during the review.

**See [`docs/user_guide.md`](docs/user_guide.md) for instructions on running the pipeline.**

---

## Status of the data

The extraction outputs in `04_extraction/outputs/` were produced by an
AI-assisted pipeline (Claude Sonnet, Anthropic API) and validated against blind
manual coding on a stratified sample of 30 articles and 12 fields (see
`06_validation/`). Overall concordance is 82.8 %; agreement on the binary
`Util_` fields is 85.1 % (Gwet's AC1 = 0.750, 95 % CI 0.629 to 0.851).

Three caveats apply before these files are used as results:

- `Util_social`, `Util_economique` and `Util_scenarios` show a systematic
  directional gap and need an operational definition followed by recoding
  before their prevalences are reported.
- 5 of the 30 sampled articles were not usable research articles (one
  retraction, two correction notices, two out of scope), all extracted at high
  confidence. A full-text screening step is required upstream of extraction.
- The per-cell confidence flag does not discriminate within usable documents
  and must not be used as a triage threshold. At document level, a *basse* flag
  did point only to documents that were later excluded, so it can prioritise
  the full-text screening queue, but its absence is not a validation.

Coverage at the time of writing: 3,013 records at title/abstract stage in
ASReview, 1,001 screened and 816 retained; 207 full texts retrieved and
extracted; 30 articles validated by hand.

---

## Repository structure

The six numbered folders follow the order of the review pipeline.

### `01_search/` - Search strategy and corpus construction

| Path | Contents |
|---|---|
| `queries_130226/` | Web of Science queries (13 Feb 2026), plus calibration samples |
| `corpus/` | Corpus exports, audit trail, excluded-record list |
| `wos_queries.qmd` | Documentation of the query construction and corpus filtering |

`corpus/BRIDGES_full_audit_trail.xlsx` records how the corpus was assembled and
filtered. `corpus/BRIDGES_asreview_3686.csv` is the export fed into ASReview.

An earlier search strategy based on the OpenAlex API was explored and set aside
in favour of Web of Science; those files are in `archive/`.

### `02_screening/` - Title and abstract screening

| Path | Contents |
|---|---|
| `asreview/` | ASReview project export (`.asreview`, 1,001 records screened as of 22 June 2026), prior-knowledge sets (33 and 100 records), per-screener distribution files |
| `calibration/` | Inter-rater calibration exercise: individual scores from four screeners, consensus scoring, screening criteria |
| `outputs/` | Screening results (2,481 records), Rayyan export, pre-filled article list |

The calibration exercise supports the inter-rater agreement analysis in
`05_analysis/screening_analyses.qmd` (Fleiss and Cohen kappas).

### `03_fulltext/` - Full-text retrieval

| Path | Contents |
|---|---|
| `scripts/unpaywall_check.py` | Queries the Unpaywall API for open-access status and PDF URLs |
| `scripts/download_pdfs_v2.py` | Downloads open-access PDFs; resumable |
| `scripts/liste_solde.py` | Lists articles still missing, for library request |
| `tracking/` | Retrieval tracking spreadsheets and snowballing DOI lists |
| `asreview_relevant_BRIDGES.csv` | The 816 included records with ASReview decision timestamps |

**PDFs are not stored in this repository.** The 207 retrieved full texts are
publisher-copyrighted and are held on the Ifremer cloud. `tracking/` records
what was retrieved and how.

### `04_extraction/` - Data extraction

| Path | Contents |
|---|---|
| `scripts/extraction_claude.py` | Extracts structured data from each PDF via the Anthropic API |
| `scripts/fiche_modeles_claude.py` | Documents each distinct modelling framework's theoretical capabilities |
| `templates/extraction_articles_BRIDGES_v17.xlsx` | Article extraction template (current version) |
| `templates/fiche_modeles_BRIDGES_v8.xlsx` | Model template (current version) |
| `outputs/` | Filled extraction files and the model name harmonisation table |

Both output files are laid out with one row per field and one column per
article or model, each followed by a `[confiance]` column.

The two templates capture different things. The article template records how a
model was *used* in a given paper (`Util_*` fields, Yes/No). The model template
records what a model *can* do in principle (`Cap_*` fields, Yes/Optional/No).
The analysis compares the two.

### `05_analysis/` - Analysis and reporting

| Path | Contents |
|---|---|
| `extraction_analyses.qmd` | Main analysis: model typology, geographic distribution, capability radars, heatmap, PCA ordination, diversity accumulation |
| `screening_analyses.qmd` | Screening statistics and inter-rater agreement (Fleiss, Cohen) |
| `_template/` | Quarto theme (CSS, header, footer) |

Rendered HTML sits alongside each `.qmd`.

### `06_validation/` - Validation of the AI-assisted extraction

| Path | Contents |
|---|---|
| `Agreement_analyses.qmd` | Agreement analysis between the pipeline and blind manual coding |
| `BRIDGES_validation_feuille_codage.xlsx` | Blind coding sheet: instructions plus 30 articles x 12 fields |

Sample of 30 articles (14.5 % of the 207 extracted), stratified on the
pipeline's declared confidence with a fixed seed: the 9 articles carrying at
least one *basse* field were included exhaustively, the remaining 21 drawn at
random. The sample therefore over-represents the least confident extractions,
which makes the reported agreement conservative but prevents extrapolating the
proportion of ineligible documents to the corpus.

This step applies upstream of `05_analysis/`, despite its folder number.

### Other folders

| Path | Contents |
|---|---|
| `docs/` | Screening criteria, model guide, feasibility note, workload estimate, paper outline, user guide |
| `outputs/figures/` | Figures for the manuscript, including the PRISMA diagram |
| `archive/` | Superseded template versions, early extraction batches, earlier drafts, the OpenAlex exploration and the first query iteration |

---

## Requirements

**Python** 3.9 or later:

pip install pandas requests openpyxl anthropic pymupdf

**R** 4.2 or later, with Quarto. Packages: `tidyverse`, `here`, `readxl`,
`ggplot2`, `sf`, `rnaturalearth`, `vegan`, `ggrepel`, `forcats`, `irr`,
`knitr`, `stringi`, `bibliometrix`, `writexl`.

**API key.** The extraction scripts require an Anthropic API key in the
`ANTHROPIC_API_KEY` environment variable. `unpaywall_check.py` requires an
email address in `UNPAYWALL_EMAIL`.

---

## Known limitations

The Python scripts use relative paths and expect to be run from a directory
holding their input files. See the user guide for the working directory each
one needs.

`extraction_claude.py` truncates article text at 60,000 characters, so material
in the closing sections of very long papers may not reach the extraction step.

The PRISMA diagram in `outputs/figures/` was generated during the OpenAlex
exploration and reports figures from that search, not from the Web of Science
corpus used for the review.

Validation covers 12 of the 27 extraction fields, on 30 of the 207 articles,
against a single reference coder. The reported figures measure concordance
between the pipeline and that coder, not absolute accuracy.

---

## Contact

Théophile L. Mouton - work carried out under IRD purchase order 4500288125,
BRIDGES-Avatar project, January–July 2026.