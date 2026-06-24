#!/usr/bin/env python3
"""
BRIDGES - Téléchargement des PDF en accès libre
================================================

Lit le fichier enrichi par Unpaywall (BRIDGES_pdf_a_recuperer_unpaywall.xlsx),
sélectionne les articles disposant d'une URL de PDF en accès libre, et
télécharge chaque PDF dans le dossier PDF/ en le nommant proprement.

Caractéristiques :
  - Relançable : saute les PDF déjà présents (ne re-télécharge pas).
  - Robuste : une erreur sur un article n'arrête pas le script.
  - Traçable : écrit un fichier de suivi avec le statut de chaque téléchargement.
  - Vérifie que le fichier reçu est bien un PDF (et pas une page HTML).

PRÉREQUIS
---------
    pip install pandas requests openpyxl

UTILISATION
-----------
    python download_pdfs.py

Les PDF sont enregistrés dans un sous-dossier PDF/.
Le fichier de suivi BRIDGES_telechargement_suivi.xlsx récapitule les résultats.
"""

import pandas as pd
import requests
import os
import time
import re

# --- À PERSONNALISER si besoin ---
INPUT  = "BRIDGES_pdf_a_recuperer_unpaywall.xlsx"
OUTDIR = "PDF"
SUIVI  = "BRIDGES_telechargement_suivi.xlsx"
PDF_URL_COL  = "oa_pdf_url"        # colonne URL produite par Unpaywall
FNAME_COL    = "Nom de fichier"    # colonne nom de fichier préparée
# ----------------------------------

os.makedirs(OUTDIR, exist_ok=True)
df = pd.read_excel(INPUT)

HEADERS = {"User-Agent": "Mozilla/5.0 (BRIDGES research; mailto:theophile.mouton92@gmail.com)"}
session = requests.Session()

def safe_name(name, idx):
    """Nettoie le nom de fichier et garantit l'extension .pdf."""
    if not isinstance(name, str) or not name.strip():
        name = f"article_{idx:03d}.pdf"
    name = re.sub(r'[^\w\-.]', '_', name.strip())
    if not name.lower().endswith(".pdf"):
        name += ".pdf"
    return name

results = []
n_ok = n_skip = n_fail = n_nourl = 0

for i, row in df.iterrows():
    idx = i + 1
    url = str(row.get(PDF_URL_COL, "") or "").strip()
    fname = safe_name(row.get(FNAME_COL, ""), idx)
    path = os.path.join(OUTDIR, fname)
    status = ""

    if not url or url.lower() == "nan":
        status = "Pas d'URL OA"
        n_nourl += 1
    elif os.path.exists(path) and os.path.getsize(path) > 1024:
        status = "Déjà téléchargé"
        n_skip += 1
    else:
        try:
            r = session.get(url, headers=HEADERS, timeout=40, allow_redirects=True)
            ctype = r.headers.get("Content-Type", "").lower()
            # accepter si content-type pdf OU si le contenu commence par %PDF
            is_pdf = ("pdf" in ctype) or r.content[:5].startswith(b"%PDF")
            if r.status_code == 200 and is_pdf and len(r.content) > 1024:
                with open(path, "wb") as f:
                    f.write(r.content)
                status = "Téléchargé"
                n_ok += 1
            elif r.status_code == 200:
                status = "Pas un PDF (page HTML ?)"
                n_fail += 1
            else:
                status = f"Erreur HTTP {r.status_code}"
                n_fail += 1
        except Exception as e:
            status = f"Erreur: {type(e).__name__}"
            n_fail += 1
        time.sleep(0.5)   # rester poli avec les serveurs

    results.append({"ID": idx, "Nom de fichier": fname,
                    "URL": url, "Statut téléchargement": status})

    if idx % 25 == 0:
        print(f"{idx}/{len(df)} traités... (ok:{n_ok} sautés:{n_skip} échecs:{n_fail})")

# fichier de suivi
suivi = pd.DataFrame(results)
suivi.to_excel(SUIVI, index=False)

print("\n=== Résumé ===")
print(f"Téléchargés         : {n_ok}")
print(f"Déjà présents       : {n_skip}")
print(f"Sans URL OA         : {n_nourl}")
print(f"Échecs              : {n_fail}")
print(f"\nPDF enregistrés dans : {OUTDIR}/")
print(f"Suivi détaillé       : {SUIVI}")
print("\nLes échecs et les articles sous paywall sont à récupérer via ton accès IRD/Ifremer.")
print("Tu peux relancer ce script : il ne re-téléchargera que ce qui manque.")
