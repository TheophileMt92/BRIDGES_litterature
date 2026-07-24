#!/usr/bin/env python3
"""
BRIDGES - Repérage des PDF en accès libre via Unpaywall
=======================================================

Ce script interroge l'API Unpaywall (gratuite et légale) pour chaque DOI
de la liste des articles "relevant", et indique :
  - si l'article est en open access (is_oa)
  - l'URL du PDF en accès libre quand elle existe (best_oa_location)
  - le type d'open access (gold, green, hybrid, bronze)

Il NE télécharge rien automatiquement : il enrichit ta liste de travail.
Les articles non-OA devront être récupérés via ton accès institutionnel
(IRD / Ifremer).

PRÉREQUIS
---------
    pip install pandas requests openpyxl

UTILISATION
-----------
    python unpaywall_check.py

Avant de lancer, définis ton email dans la variable d'environnement
UNPAYWALL_EMAIL. Unpaywall l'exige comme identifiant d'usage de l'API.

    export UNPAYWALL_EMAIL="ton.email@exemple.fr"
"""

import pandas as pd
import requests
import time
import os

# --- À PERSONNALISER ---
EMAIL = os.environ.get("UNPAYWALL_EMAIL", "")
if not EMAIL:
    raise SystemExit("Définis UNPAYWALL_EMAIL avant de lancer : export UNPAYWALL_EMAIL='ton.email@exemple.fr'")
INPUT  = "BRIDGES_pdf_a_recuperer.xlsx"   # dans 03_fulltext/tracking/
OUTPUT = "BRIDGES_pdf_a_recuperer_unpaywall.xlsx"
DOI_COLUMN = "DOI"
# -----------------------

df = pd.read_excel(INPUT)

results = []
session = requests.Session()

for n, doi in enumerate(df[DOI_COLUMN].astype(str), start=1):
    doi = doi.strip()
    rec = {"is_oa": "", "oa_status": "", "oa_pdf_url": "", "oa_landing_url": ""}
    if doi and doi.lower() != "nan":
        url = f"https://api.unpaywall.org/v2/{doi}?email={EMAIL}"
        try:
            r = session.get(url, timeout=20)
            if r.status_code == 200:
                d = r.json()
                rec["is_oa"] = "Oui" if d.get("is_oa") else "Non"
                rec["oa_status"] = d.get("oa_status", "")
                loc = d.get("best_oa_location") or {}
                rec["oa_pdf_url"] = loc.get("url_for_pdf") or ""
                rec["oa_landing_url"] = loc.get("url") or ""
            elif r.status_code == 404:
                rec["is_oa"] = "DOI introuvable"
            else:
                rec["is_oa"] = f"Erreur {r.status_code}"
        except Exception as e:
            rec["is_oa"] = f"Erreur: {e}"
    results.append(rec)

    if n % 25 == 0:
        print(f"{n}/{len(df)} traités...")
    time.sleep(0.2)   # rester poli avec l'API (max ~100k/jour)

res = pd.DataFrame(results)
out = pd.concat([df.reset_index(drop=True), res], axis=1)
out.to_excel(OUTPUT, index=False)

# petit résumé
oa = (res["is_oa"] == "Oui").sum()
closed = (res["is_oa"] == "Non").sum()
print("\n=== Résumé ===")
print(f"Open access (PDF libre potentiel) : {oa}")
print(f"Sous paywall                      : {closed}")
print(f"Avec URL de PDF directe           : {(res['oa_pdf_url'] != '').sum()}")
print(f"\nFichier écrit : {OUTPUT}")
print("Les articles 'Oui' avec une oa_pdf_url peuvent être téléchargés librement.")
print("Les 'Non' nécessitent ton accès institutionnel IRD/Ifremer.")
