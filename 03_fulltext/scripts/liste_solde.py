#!/usr/bin/env python3
"""
BRIDGES - Liste des articles restant à récupérer
=================================================

Compare la liste complète des 816 articles avec les PDF déjà présents
dans le dossier PDF/, et produit une liste propre des articles encore
manquants, prête à envoyer à la bibliothèque IRD/Ifremer ou à traiter
via VPN.

Sortie : BRIDGES_a_recuperer_manuellement.xlsx
  - Onglet "A récupérer" : articles sans PDF (DOI, titre, lien, statut OA)
  - Onglet "DOI seuls"   : la liste des DOI (pratique pour la bibliothèque)

UTILISATION
-----------
    python liste_solde.py
"""

import pandas as pd
import os
import re

INPUT  = "BRIDGES_pdf_a_recuperer_unpaywall.xlsx"
PDFDIR = "PDF"
OUTPUT = "BRIDGES_a_recuperer_manuellement.xlsx"
FNAME_COL = "Nom de fichier"

df = pd.read_excel(INPUT)
present = set(os.listdir(PDFDIR)) if os.path.isdir(PDFDIR) else set()

def safe_name(name, idx):
    if not isinstance(name, str) or not name.strip():
        name = f"article_{idx:03d}.pdf"
    name = re.sub(r'[^\w\-.]', '_', name.strip())
    if not name.lower().endswith(".pdf"):
        name += ".pdf"
    return name

rows = []
for i, row in df.iterrows():
    idx = i + 1
    fname = safe_name(row.get(FNAME_COL, ""), idx)
    if fname in present and os.path.getsize(os.path.join(PDFDIR, fname)) > 1024:
        continue  # déjà récupéré
    doi = str(row.get("DOI", "")).strip()
    rows.append({
        "ID": idx,
        "Titre": row.get("Title", ""),
        "Auteurs": row.get("Authors", ""),
        "Année": row.get("Year", ""),
        "Journal": row.get("Journal", ""),
        "DOI": doi,
        "Lien DOI": f"https://doi.org/{doi}" if doi and doi.lower() != "nan" else "",
        "Open access (Unpaywall)": row.get("is_oa", ""),
        "Page OA": row.get("oa_landing_url", ""),
    })

solde = pd.DataFrame(rows)

with pd.ExcelWriter(OUTPUT, engine="openpyxl") as xl:
    solde.to_excel(xl, sheet_name="A récupérer", index=False)
    solde[["DOI"]].dropna().to_excel(xl, sheet_name="DOI seuls", index=False)

print(f"Articles déjà récupérés : {len(df) - len(solde)}")
print(f"Articles à récupérer    : {len(solde)}")
print(f"  dont marqués OA        : {(solde['Open access (Unpaywall)'] == 'Oui').sum()}")
print(f"  dont sous paywall      : {(solde['Open access (Unpaywall)'] == 'Non').sum()}")
print(f"\nFichier écrit : {OUTPUT}")
