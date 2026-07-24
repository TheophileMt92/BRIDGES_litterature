# BRIDGES - Scoping review of socio-ecological modelling tools

Literature review of socio-ecological modelling tools for spatial management and
decision support in marine and coastal systems, carried out for the BRIDGES-Avatar
project (WP4).

This repository contains the search strategy, screening records, full-text
retrieval pipeline, AI-assisted extraction scripts and analysis code produced
during the review.

**See [`docs/user_guide.md`](docs/user_guide.md) for instructions on running the pipeline.**

---

## Status of the data

The extraction outputs in `04_extraction/outputs/` were produced by an
AI-assisted pipeline (Claude Sonnet, Anthropic API) and **have not yet been
validated by hand**. Every field carries a confidence flag; fields marked
*basse* or *moyenne* are the priority for human review. These files should not
be treated as final results.

Coverage at the time of writing: 3,013 records screened at title/abstract stage
in ASReview, of which 1,001 have been screened and 816 retained; 207 full texts
retrieved and extracted.

---

## Repository structure

The five numbered folders follow the order of the review pipeline.

### `01_search/` - Search strategy and corpus construction

| Path | Contents |
|---|---|
| `queries_260126/` | Web of Science queries, first iteration (26 Jan 2026) |
| `queries_130226/` | Web of Science queries, second iteration (13 Feb 2026), plus calibration samples |
| `corpus/` | Corpus exports, audit trail, excluded-record list, DOI list for Zotero |
| `openalexR.qmd`, `openalexR.R` | Exploratory search via the OpenAlex API |
| `wos_queries.qmd` | Documentation of the query construction |

`corpus/BRIDGES_full_audit_trail.xlsx` records how the corpus was assembled and
filtered. `corpus/BRIDGES_asreview_3686.csv` is the export fed into ASReview.

### `02_screening/` - Title and abstract screening

| Path | Contents |
|---|---|
| `asreview/` | ASReview project export (`.asreview`, 1,001 records screened as of 22 June 2026), prior-knowledge sets (33 and 100 records), per-screener distribution files |
| `calibration/` | Inter-rater calibration exercise: individual scores from four screeners, consensus scoring, screening criteria |
| `outputs/` | Screening results (2,481 records), Rayyan export, pre-filled article list |

The calibration exercise supports the inter-rater agreement analysis in
`05_analysis/kappa.R` (Fleiss and Cohen kappas).

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
| `screening_analyses.qmd` | Screening statistics |
| `kappa.R` | Inter-rater agreement (Fleiss, Cohen) |
| `harmonisation_modeles.R` | Model name harmonisation |
| `_template/` | Quarto theme (CSS, header, footer) |

Rendered HTML sits alongside each `.qmd`.

### Other folders

| Path | Contents |
|---|---|
| `docs/` | Screening criteria, model guide, feasibility note, workload estimate, paper outline |
| `outputs/figures/` | Figures for the manuscript, including the PRISMA diagram |
| `archive/` | Superseded template versions, early extraction batches, earlier drafts |

---

## Requirements

**Python** 3.9 or later:

```
pip install pandas requests openpyxl anthropic pymupdf
```

**R** 4.2 or later, with Quarto. Packages: `tidyverse`, `here`, `readxl`,
`ggplot2`, `sf`, `rnaturalearth`, `vegan`, `ggrepel`, `forcats`, `irr`.

**API key.** The extraction scripts require an Anthropic API key in the
`ANTHROPIC_API_KEY` environment variable.

---

## Known limitations

The scripts use relative paths and expect to be run from the directory holding
their input files. See the user guide for the working directory each one needs.

The Quarto analysis file still refers to the pre-reorganisation folder layout in
its `here()` calls; these paths need updating.

`extraction_claude.py` truncates article text at 60,000 characters, so material
in the closing sections of very long papers may not reach the extraction step.

Extraction output is unvalidated (see *Status of the data* above).

---

## Contact

Théophile L. Mouton - work carried out under IRD purchase order 4500288125,
BRIDGES-Avatar project, January–June 2026.
