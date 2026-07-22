#!/usr/bin/env python3
"""
BRIDGES - Téléchargement des PDF en accès libre (version 2)
===========================================================

Améliorations par rapport à la v1 :
  - En plus de l'URL de PDF directe (oa_pdf_url), tente la page
    d'atterrissage OA (oa_landing_url) et y cherche un lien PDF.
  - Gère les cas fréquents (PMC, arXiv, biorxiv, repositories) en
    construisant l'URL du PDF quand c'est possible.
  - Réessais sur les erreurs réseau temporaires.
  - Pause plus longue et User-Agent navigateur pour réduire les blocages.
  - Toujours relançable : saute les PDF déjà présents.

PRÉREQUIS
---------
    pip install pandas requests openpyxl

UTILISATION
-----------
    python download_pdfs_v2.py

Lance-le dans le même dossier que BRIDGES_pdf_a_recuperer_unpaywall.xlsx.
Les PDF vont dans PDF/. Le suivi est écrit dans BRIDGES_telechargement_suivi_v2.xlsx.
"""

import pandas as pd
import requests
import os
import time
import re
from urllib.parse import urljoin

# --- À PERSONNALISER si besoin ---
INPUT  = "BRIDGES_pdf_a_recuperer_unpaywall.xlsx"
OUTDIR = "PDF"
SUIVI  = "BRIDGES_telechargement_suivi_v2.xlsx"
PDF_URL_COL    = "oa_pdf_url"
LANDING_URL_COL= "oa_landing_url"
FNAME_COL      = "Nom de fichier"
PAUSE = 1.0          # secondes entre articles
RETRIES = 2          # réessais sur erreur réseau
# ----------------------------------

os.makedirs(OUTDIR, exist_ok=True)
df = pd.read_excel(INPUT)

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/120.0 Safari/537.36"),
    "Accept": "application/pdf,text/html;q=0.9,*/*;q=0.8",
}
session = requests.Session()

def safe_name(name, idx):
    if not isinstance(name, str) or not name.strip():
        name = f"article_{idx:03d}.pdf"
    name = re.sub(r'[^\w\-.]', '_', name.strip())
    if not name.lower().endswith(".pdf"):
        name += ".pdf"
    return name

def looks_like_pdf(resp):
    ctype = resp.headers.get("Content-Type", "").lower()
    return ("pdf" in ctype) or resp.content[:5].startswith(b"%PDF")

def get(url):
    """GET avec réessais ; renvoie la réponse ou None."""
    for attempt in range(RETRIES + 1):
        try:
            return session.get(url, headers=HEADERS, timeout=45, allow_redirects=True)
        except Exception:
            if attempt < RETRIES:
                time.sleep(2)
            else:
                return None

def derive_pdf_url(url):
    """Construit une URL PDF probable pour quelques hébergeurs connus."""
    if not url:
        return None
    u = url.lower()
    # PubMed Central
    m = re.search(r'(pmc\d+)', u)
    if "ncbi.nlm.nih.gov/pmc" in u and m:
        return f"https://www.ncbi.nlm.nih.gov/pmc/articles/{m.group(1).upper()}/pdf/"
    # arXiv
    if "arxiv.org/abs/" in u:
        return url.replace("/abs/", "/pdf/")
    # bioRxiv / medRxiv
    if ("biorxiv.org" in u or "medrxiv.org" in u) and not u.endswith(".pdf"):
        return url.rstrip("/") + ".full.pdf"
    return None

def find_pdf_in_html(html, base_url):
    """Cherche un lien PDF dans une page HTML (méta citation_pdf_url ou liens .pdf)."""
    # balise standard utilisée par la plupart des éditeurs
    m = re.search(r'<meta[^>]+name=["\']citation_pdf_url["\'][^>]+content=["\']([^"\']+)["\']',
                  html, re.IGNORECASE)
    if m:
        return m.group(1)
    m = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']citation_pdf_url["\']',
                  html, re.IGNORECASE)
    if m:
        return m.group(1)
    # lien direct .pdf
    m = re.search(r'href=["\']([^"\']+\.pdf[^"\']*)["\']', html, re.IGNORECASE)
    if m:
        return urljoin(base_url, m.group(1))
    return None

def try_download(url, path):
    """Tente de télécharger un PDF depuis une URL (directe ou via page). Renvoie statut."""
    if not url or str(url).lower() == "nan":
        return None
    resp = get(url)
    if resp is None:
        return "Erreur réseau"
    if resp.status_code != 200:
        return f"HTTP {resp.status_code}"
    if looks_like_pdf(resp) and len(resp.content) > 1024:
        with open(path, "wb") as f:
            f.write(resp.content)
        return "Téléchargé"
    # sinon c'est probablement une page HTML : on y cherche un lien PDF
    ctype = resp.headers.get("Content-Type", "").lower()
    if "html" in ctype:
        pdf_link = find_pdf_in_html(resp.text, resp.url) or derive_pdf_url(resp.url)
        if pdf_link:
            r2 = get(pdf_link)
            if r2 is not None and r2.status_code == 200 and looks_like_pdf(r2) and len(r2.content) > 1024:
                with open(path, "wb") as f:
                    f.write(r2.content)
                return "Téléchargé (via page)"
    return "Pas un PDF accessible"

results = []
n_ok = n_skip = n_fail = n_nourl = 0

for i, row in df.iterrows():
    idx = i + 1
    fname = safe_name(row.get(FNAME_COL, ""), idx)
    path = os.path.join(OUTDIR, fname)

    if os.path.exists(path) and os.path.getsize(path) > 1024:
        results.append({"ID": idx, "Nom de fichier": fname, "Statut": "Déjà présent"})
        n_skip += 1
        continue

    pdf_url = str(row.get(PDF_URL_COL, "") or "").strip()
    landing = str(row.get(LANDING_URL_COL, "") or "").strip()

    candidates = [u for u in (pdf_url, landing) if u and u.lower() != "nan"]
    if not candidates:
        results.append({"ID": idx, "Nom de fichier": fname, "Statut": "Pas d'URL OA"})
        n_nourl += 1
        continue

    status = "Pas un PDF accessible"
    for u in candidates:
        st = try_download(u, path)
        if st and st.startswith("Téléchargé"):
            status = st
            break
        elif st:
            status = st
    if status.startswith("Téléchargé"):
        n_ok += 1
    else:
        n_fail += 1

    results.append({"ID": idx, "Nom de fichier": fname, "Statut": status})
    time.sleep(PAUSE)

    if idx % 25 == 0:
        print(f"{idx}/{len(df)} traités... (ok:{n_ok} sautés:{n_skip} échecs:{n_fail})")

suivi = pd.DataFrame(results)
suivi.to_excel(SUIVI, index=False)

print("\n=== Résumé ===")
print(f"Téléchargés (cette session) : {n_ok}")
print(f"Déjà présents               : {n_skip}")
print(f"Sans URL OA                 : {n_nourl}")
print(f"Échecs                      : {n_fail}")
total_pdf = len([f for f in os.listdir(OUTDIR) if f.lower().endswith('.pdf')])
print(f"\nTotal PDF dans {OUTDIR}/      : {total_pdf}")
print(f"Suivi détaillé              : {SUIVI}")
print("\nRelançable : il ne refait que ce qui manque.")
print("Le solde (échecs + sans URL) est à récupérer via ton accès IRD/Ifremer.")
