#!/usr/bin/env python3
"""
BRIDGES - Extraction assistée par Claude des données d'articles
================================================================

Lit les PDF du dossier PDF/, envoie le texte de chaque article à l'API Claude
avec un prompt structuré contraint par le vocabulaire contrôlé de la maquette
v17, et remplit une copie de la maquette (une colonne par article) avec, pour
chaque champ, un niveau de confiance pour cibler la validation humaine.

IMPORTANT — VALIDATION HUMAINE REQUISE
Cette extraction est une AIDE. Chaque champ doit être relu et validé par un
humain avant analyse. Les modèles peuvent produire des valeurs plausibles mais
fausses, surtout sur les champs interprétatifs. Ne jamais utiliser les sorties
brutes pour les analyses sans relecture.

PRÉREQUIS
---------
    pip3 install anthropic pymupdf openpyxl pandas
    La clé API doit être dans la variable d'environnement ANTHROPIC_API_KEY.

UTILISATION
-----------
    python3 extraction_claude.py          # traite LIMITE articles (test)
    Mettre LIMITE = 0 pour traiter tout le dossier PDF/.
"""

import os
import re
import json
import time
import glob
import pandas as pd
import fitz  # PyMuPDF
from anthropic import Anthropic

# --- PARAMÈTRES ---
PDF_DIR = "PDF"
TEMPLATE = "extraction_articles_BRIDGES_v17.xlsx"   # la maquette d'origine
OUTPUT   = "extraction_articles_BRIDGES_REMPLIE.xlsx"
MODEL    = "claude-sonnet-4-6"
LIMITE   = 0            # 5 pour tester ; 0 = tous les PDF
MAX_CHARS_PDF = 60000   # tronque les très longs articles (~15k tokens)
PAUSE = 1.0
# ------------------

client = Anthropic()   # lit ANTHROPIC_API_KEY depuis l'environnement

# Vocabulaire contrôlé (valeurs autorisées) — extrait de la maquette v17
VOCAB = {
 "Type_article": ["Empirique","Méthodologique","Review","Synthèse comparative","Méta-analyse"],
 "Milieu": ["Marine","Estuarine","Coastal","Brackish","Multiple"],
 "Bassin_oceanique": ["Atlantic","Pacific","Indian","Arctic","Southern","Mediterranean","Multiple","Global"],
 "Etendue_spatiale": ["Local (single site)","National (single country)","Regional (multiple countries)","Basin-scale","Global","Theoretical/Generic"],
 "Resolution_spatiale": ["Point","Fine (<1 km)","Medium (1-10 km)","Coarse (10-100 km)","Very coarse (>100 km)","Irregular/Polygon","Not spatially explicit"],
 "Resolution_temporelle": ["Daily","Weekly","Monthly","Seasonal","Annual","Decadal","Equilibrium/Static"],
 "Horizon_temporel": ["Historical only","Short-term (<5 years)","Medium-term (5-20 years)","Long-term (20-50 years)","Very long-term (>50 years)","Multiple horizons"],
 "Contexte_donnees": ["Data-rich","Data-moderate","Data-poor"],
 "Type_output": ["Aucun","Cartes de distribution","Cartes de priorité","Zonage spatial","Indicateurs biodiversité","Indicateurs économiques","Indicateurs sociaux","Séries temporelles","Courbes de compromis (Pareto)","Tableaux de bord","Probabilités/Incertitudes"],
 "Tradeoffs_type": ["Conservation vs Exploitation","Court terme vs Long terme","Économique vs Écologique","Usages multiples","Équité vs Efficacité","Local vs Global"],
 "Contexte_decisionnel": ["Marine Protected Areas (MPA)","Marine Spatial Planning (MSP)","Fisheries management","Ecosystem-based management","Conservation prioritization","Climate adaptation","Impact assessment","Restoration planning","Resource allocation","Coastal zone management","Theoretical/Methodological"],
 "Pertinence_BRIDGES": ["1","2","3","4","5"],
}

# Champs binaires Oui/Non (utilisation réelle — alimentent les radar plots 04.01)
UTIL_FIELDS = ["Util_physique","Util_biologique","Util_peche","Util_economique",
               "Util_social","Util_spatial","Util_temporel","Util_scenarios",
               "Util_tradeoffs","Util_incertitude"]

# Liste complète des champs demandés à Claude (priorité visualisations 04.01-04.06)
def build_prompt(text):
    vocab_str = "\n".join(f"- {k} : {' | '.join(v)}" for k, v in VOCAB.items())
    util_str = ", ".join(UTIL_FIELDS)
    return f"""Tu es assistant d'extraction pour une scoping review (projet BRIDGES) sur les
modèles socio-écologiques marins. Extrais les informations du texte d'article ci-dessous.

RÈGLES STRICTES :
- Réponds UNIQUEMENT par un objet JSON valide, sans texte avant ni après, sans balises Markdown.
- Pour les champs à vocabulaire contrôlé, utilise EXACTEMENT une des valeurs autorisées.
- Si une information n'est pas présente dans le texte, mets la valeur "NA" (n'invente jamais).
- Pour chaque champ, ajoute un niveau de confiance dans un objet séparé "confiance"
  avec les valeurs "haute", "moyenne" ou "basse".
- Pour les champs multi-valeurs, sépare par " ; ".

VOCABULAIRE CONTRÔLÉ (valeurs autorisées) :
{vocab_str}

CHAMPS BINAIRES (réponds "Oui" ou "Non") — utilisation RÉELLE du modèle dans l'article :
{util_str}

STRUCTURE JSON ATTENDUE :
{{
  "valeurs": {{
    "Type_article": "...",
    "Modele_utilise": "nom du modèle, ex: Ecopath with Ecosim (EwE), Atlantis, SDM, modèle bioéconomique...",
    "Milieu": "...",
    "Bassin_oceanique": "...",
    "Etendue_spatiale": "...",
    "Resolution_spatiale": "...",
    "Resolution_temporelle": "...",
    "Horizon_temporel": "...",
    "Util_physique": "Oui/Non", "Util_biologique": "Oui/Non", "Util_peche": "Oui/Non",
    "Util_economique": "Oui/Non", "Util_social": "Oui/Non", "Util_spatial": "Oui/Non",
    "Util_temporel": "Oui/Non", "Util_scenarios": "Oui/Non", "Util_tradeoffs": "Oui/Non",
    "Util_incertitude": "Oui/Non",
    "Type_output": "...",
    "Tradeoffs_analyses": "Oui/Non",
    "Tradeoffs_type": "...",
    "Contexte_decisionnel": "...",
    "Contexte_donnees": "...",
    "Compartiments_modelises": "liste des compartiments parmi Physique/Biologique/Pêche/Économique/Social",
    "Pertinence_BRIDGES": "1-5 (5=très pertinent pour une scoping review sur modèles de gestion socio-écologique marine)",
    "Forces": "1-2 phrases",
    "Limites": "1-2 phrases"
  }},
  "confiance": {{ "Type_article": "haute/moyenne/basse", ... pour chaque champ ... }}
}}

TEXTE DE L'ARTICLE :
{text}
"""

def extract_pdf_text(path):
    doc = fitz.open(path)
    parts = []
    for page in doc:
        parts.append(page.get_text())
    doc.close()
    txt = "\n".join(parts)
    txt = re.sub(r'\n{3,}', '\n\n', txt)
    return txt[:MAX_CHARS_PDF]

def call_claude(text):
    msg = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": build_prompt(text)}],
    )
    raw = "".join(b.text for b in msg.content if b.type == "text").strip()
    raw = re.sub(r'^```(json)?|```$', '', raw, flags=re.MULTILINE).strip()
    return json.loads(raw)

# --- traitement des PDF ---
pdfs = sorted(glob.glob(os.path.join(PDF_DIR, "*.pdf")))
if LIMITE and LIMITE > 0:
    pdfs = pdfs[:LIMITE]
print(f"{len(pdfs)} PDF à traiter (modèle {MODEL}).")

extractions = []   # liste de (nom_fichier, valeurs_dict, confiance_dict)
for i, path in enumerate(pdfs, start=1):
    name = os.path.basename(path)
    try:
        text = extract_pdf_text(path)
        if len(text) < 500:
            print(f"  [{i}/{len(pdfs)}] {name} : texte illisible (PDF scanné ?) — ignoré")
            extractions.append((name, {"_erreur": "texte illisible"}, {}))
            continue
        result = call_claude(text)
        extractions.append((name, result.get("valeurs", {}), result.get("confiance", {})))
        print(f"  [{i}/{len(pdfs)}] {name} : OK")
    except Exception as e:
        print(f"  [{i}/{len(pdfs)}] {name} : ERREUR {type(e).__name__}: {str(e)[:80]}")
        extractions.append((name, {"_erreur": str(e)[:120]}, {}))
    time.sleep(PAUSE)

# --- écriture : une colonne par article, champ + confiance ---
rows = []
all_fields = []
for _, vals, _ in extractions:
    for k in vals:
        if k not in all_fields and not k.startswith("_"):
            all_fields.append(k)

data = {"Champ": all_fields}
for name, vals, conf in extractions:
    col_val = [vals.get(f, "") for f in all_fields]
    data[name] = col_val
    data[name + " [confiance]"] = [conf.get(f, "") for f in all_fields]

out = pd.DataFrame(data)
out.to_excel(OUTPUT, index=False)

ok = sum(1 for _, v, _ in extractions if "_erreur" not in v)
print(f"\n=== Résumé ===")
print(f"Articles extraits avec succès : {ok}/{len(extractions)}")
print(f"Fichier écrit : {OUTPUT}")
print("\nRAPPEL : relire et valider chaque champ avant analyse.")
print("Les colonnes [confiance] = basse/moyenne sont à vérifier en priorité.")
if LIMITE and LIMITE > 0:
    print(f"\nTest sur {LIMITE} articles. Mets LIMITE = 0 dans le script pour tout traiter.")
