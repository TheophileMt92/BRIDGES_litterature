# BRIDGES pipeline — user guide

How to run each stage of the review pipeline. Read the *Before you start*
section first: the scripts have a working-directory requirement that will
otherwise cause them to fail immediately.

---

## Before you start

### Working directory

All five Python scripts refer to their input and output files by bare filename,
with no directory component. `unpaywall_check.py` opens
`BRIDGES_pdf_a_recuperer.xlsx` from wherever it is run.

They must therefore be run from a directory containing their inputs, not from
the folder where the script lives. Each section below states the required
working directory.

The practical approach is a scratch working folder outside the repository:

```bash
mkdir -p ~/bridges_run
cd ~/bridges_run
```

Copy in the inputs a stage needs, run the script from there, then copy outputs
back into the repository. Alternatively, edit the path constants at the top of
each script to absolute paths.

### Python environment

```bash
pip install pandas requests openpyxl anthropic pymupdf
```

### Anthropic API access

**Stage 4 cannot be run without a paid Anthropic API account.** Both extraction
scripts (`extraction_claude.py`, `fiche_modeles_claude.py`) send text to the
Anthropic API and will not run otherwise. Stages 1, 2, 3 and 5 have no such
requirement.

To set this up:

1. Create an account at [console.anthropic.com](https://console.anthropic.com).
   This is separate from a Claude.ai subscription: a Claude Pro plan does not
   include API access, and API usage is billed independently.
2. Add credit to the account. The API is prepaid.
3. Generate a key under **API Keys**. It is shown once; store it somewhere safe.
4. Make it available to the scripts:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

Add that line to `~/.zshrc` or `~/.bashrc` to persist it across sessions. Never
commit a key to the repository, and revoke it in the console if it is ever
exposed.

**Cost.** Extraction of the 207 articles cost a few euros in total, at roughly
15,000 input tokens per article (the scripts truncate at 60,000 characters).
Documenting the ~30 model frameworks cost under one euro. Both scripts print
progress per item, so a run can be stopped if something looks wrong. Current
rates are at
[anthropic.com/pricing](https://www.anthropic.com/pricing).

**Model version.** Both scripts specify `claude-sonnet-4-6`. Model names change
over time; if a run fails with a model-not-found error, update the `MODEL`
constant near the top of each script to a current model identifier.

### Email for Unpaywall

`unpaywall_check.py` sends an email address to the Unpaywall API as a usage
identifier — it is required by their terms. The address is currently hardcoded
at line 30; change it to your own.

---

## Stage 1 — Search and corpus construction

Run in Web of Science, not from a script. The query files are in
`01_search/queries_130226/` (the version used for the final corpus) and
`01_search/queries_260126/` (an earlier iteration).

The queries are split across several files because of Web of Science export
limits; results are concatenated. `01_search/corpus/BRIDGES_full_audit_trail.xlsx`
records how the merged corpus was filtered — by publication year (2010 onwards)
and subject category — down to the 3,013 records taken forward.

Output: `01_search/corpus/BRIDGES_asreview_3686.csv`, the ASReview input file.

---

## Stage 2 — Title and abstract screening

Uses [ASReview LAB v2](https://asreview.nl/), which prioritises records by
predicted relevance using active learning (TF-IDF features, SVM classifier).

Setup:

1. Create a new project in ASReview LAB.
2. Import `01_search/corpus/BRIDGES_asreview_3686.csv`.
3. Import prior knowledge from `02_screening/asreview/asreview_prior_100.csv` —
   100 records labelled in advance to train the initial model.
4. Screen. ASReview presents records in decreasing predicted relevance.

Export the results when finished. The export includes an `asreview_time` column
giving the timestamp of each decision; sorting on it recovers the order in which
records were presented, which the diversity accumulation analysis relies on.

The current export is at `03_fulltext/asreview_relevant_BRIDGES.csv` — 816
included records.

**Calibration.** Before full screening, four screeners independently coded
samples of 33, 67 and 100 records to establish agreement. Individual scores are
in `02_screening/calibration/Scores from individual authors/`, consensus
decisions in `Consensus scoring/`. Agreement statistics are computed by
`05_analysis/kappa.R`.

---

## Stage 3 — Full-text retrieval

Three scripts, run in sequence. Working directory must contain the input
spreadsheets and, for the second and third, a `PDF/` subfolder.

### 3.1 Check open-access status

```bash
python unpaywall_check.py
```

Reads `BRIDGES_pdf_a_recuperer.xlsx` (needs a `DOI` column) and queries the
Unpaywall API for each DOI. Writes `BRIDGES_pdf_a_recuperer_unpaywall.xlsx`
with four added columns: `is_oa`, `oa_status`, `oa_pdf_url`, `oa_landing_url`.

Downloads nothing. Rate-limited at roughly five requests a second; around 800
DOIs takes about three minutes.

### 3.2 Download open-access PDFs

```bash
python download_pdfs_v2.py
```

Reads `BRIDGES_pdf_a_recuperer_unpaywall.xlsx` and writes PDFs into `PDF/`,
named from the `Nom de fichier` column (format `YYYY_AuthorInitials_NNN.pdf`).

For each record it tries the direct PDF URL first, then the landing page,
scraping it for a `citation_pdf_url` meta tag or a `.pdf` link. It constructs
PDF URLs directly for PubMed Central, arXiv, bioRxiv and medRxiv.

Resumable: files already present and larger than 1 KB are skipped, so it can be
re-run after an interruption. Progress is written to
`BRIDGES_telechargement_suivi_v2.xlsx` with a status per record — *Téléchargé*,
*Déjà présent*, *Pas d'URL OA*, *HTTP 403*, and so on.

One second pause between records; expect roughly 15 minutes for 800 records.
Publisher blocking means the success rate is well below the number flagged as
open access.

### 3.3 List what is still missing

```bash
python liste_solde.py
```

Compares the record list against the contents of `PDF/` and writes
`BRIDGES_a_recuperer_manuellement.xlsx` with two sheets: *A récupérer* (full
metadata for missing articles) and *DOI seuls* (a bare DOI list, convenient for
a library request).

These are retrieved through institutional access. Draft request emails are in
`archive/`.

---

## Stage 4 — Data extraction

Two scripts. Both call the Anthropic API and cost money — see the estimates
below.

### 4.1 Article extraction

Working directory must contain `PDF/` and
`extraction_articles_BRIDGES_v17.xlsx`.

```bash
python extraction_claude.py
```

For each PDF: extracts text with PyMuPDF, truncates to 60,000 characters, sends
it to Claude with a prompt constraining output to the controlled vocabulary of
template v17, and parses the JSON response.

The response has two parts — extracted values, and a confidence rating (*haute*,
*moyenne*, *basse*) for each field. Both are written to
`extraction_articles_BRIDGES_REMPLIE.xlsx`: one row per field, one column per
article, each column followed by a `[confiance]` column.

**Test first.** Set `LIMITE = 5` at line 47 to process five PDFs, check the
output, then set `LIMITE = 0` for the full run.

Roughly 20 seconds per article. 207 articles takes around 70 minutes and costs
a few euros at current API rates.

Scanned PDFs with no text layer are skipped and flagged *texte illisible*.

### 4.2 Model documentation

Working directory must contain `extraction_articles_BRIDGES_REMPLIE.xlsx`.

```bash
python fiche_modeles_claude.py
```

Reads the `Modele_utilise` row from the article extraction, groups model name
variants (its `normalize()` function at line 108 handles EwE, Atlantis, OSMOSE,
bioeconomic models and SDMs), and produces one record per distinct framework
describing its theoretical capabilities.

Output: `fiche_modeles_BRIDGES_REMPLIE.xlsx`, same layout as the article file.

**A caveat that matters for interpretation.** This script prompts the model from
the framework's *name* alone, with no source document. The output reflects the
model's general knowledge of each framework, not anything extracted from
literature. It is a starting point to check against official documentation, not
a sourced result. Confidence tends to be low for less common frameworks.

Around 30 frameworks, under a euro, a couple of minutes.

### 4.3 Validation

Neither output is usable as-is. The intended process:

1. Sort fields by confidence; check everything marked *basse* and *moyenne*.
2. Spot-check a sample of *haute* fields against the source PDFs to estimate the
   error rate.
3. Verify model capabilities against official documentation rather than the
   generated text.
4. Resolve entries falling into `AUTRE / à classer` in the harmonisation.

This validation has not yet been carried out.

---

## Stage 5 — Analysis

Open `BRIDGES_litterature.Rproj` in RStudio, then render
`05_analysis/extraction_analyses.qmd`.

The document covers: model name harmonisation into canonical frameworks;
geographic distribution by ocean basin; publication timeline; realised-versus-
theoretical capability radars; a capability heatmap; PCA ordination of model
families; and framework diversity accumulation with a Chao1 completeness
estimate.

**Paths need updating.** The `here()` calls still point to the folder layout
that existed before the repository was reorganised — for example
`here("Full text articles", "extraction_articles_BRIDGES_REMPLIE.xlsx")`, which
is now at `04_extraction/outputs/`. Update these before rendering.

The mapping chunk needs the GOaS shapefile (see the README). It disables
spherical geometry with `sf_use_s2(FALSE)` and simplifies the polygons, both
necessary to avoid errors and long run times.

`kappa.R` and `screening_analyses.qmd` cover the screening stage and read from
`02_screening/`.

---

## Troubleshooting

**`FileNotFoundError` on a spreadsheet** — wrong working directory. Check the
required location for that stage above.

**`AuthenticationError` from the Anthropic API** — `ANTHROPIC_API_KEY` is not
set in the shell running the script. Verify with `echo $ANTHROPIC_API_KEY`.

**Many `HTTP 403` in the download log** — publisher blocking, common for
Elsevier and Wiley. Those articles need institutional access; use
`liste_solde.py` to list them.

**`JSONDecodeError` during extraction** — the model returned something other
than clean JSON. Affected articles are flagged in the output; re-running usually
resolves it.

**`Edge crosses edge` from `sf`** — invalid shapefile geometry. Run
`sf_use_s2(FALSE)` and `st_make_valid()` before any union operation.

**Mapping chunk hangs** — polygon union at full resolution. Simplify first with
`st_simplify(dTolerance = 0.1)`, or avoid the union entirely by colouring native
polygons.
