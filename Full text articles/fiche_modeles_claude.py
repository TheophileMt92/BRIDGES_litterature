#!/usr/bin/env python3
"""
BRIDGES - Remplissage assisté de la Fiche Modèles v8 (capacités théoriques)
============================================================================

Documente, pour chaque modèle distinct du corpus, ses caractéristiques
intrinsèques (niche fondamentale), en suivant EXACTEMENT la structure de la
Fiche Modèles v8 : identification, classification, accessibilité, capacités
(échelle Oui/Optionnel/Non), pertinence côtière, besoins en données,
évaluation BRIDGES.

Les champs Cap_* utilisent l'échelle Oui / Optionnel / Non (= 1 / 0.5 / 0)
pour permettre la superposition radar avec les Util_* de la Fiche Articles.

IMPORTANT — VALIDATION HUMAINE REQUISE. Pré-remplissage à valider, surtout
pour les modèles rares. Colonnes [confiance] basse/moyenne en priorité.

PRÉREQUIS
    pip3 install anthropic openpyxl pandas
    Clé dans ANTHROPIC_API_KEY.
UTILISATION
    python3 fiche_modeles_claude.py
"""

import os, re, json, time
import pandas as pd
from anthropic import Anthropic

EXTRACTION = "extraction_articles_BRIDGES_REMPLIE.xlsx"
OUTPUT     = "fiche_modeles_BRIDGES_REMPLIE.xlsx"
MODEL      = "claude-sonnet-4-6"
PAUSE      = 1.0
DOIS_REFERENCE = {}   # { "Nom modèle": "10.xxxx/..." } optionnel
client = Anthropic()

VOCAB = {
 "Approche_generale": ["Mécanistique","Statistique","Hybride"],
 "Implementation": ["Agent-based","Individual-based","Structurel (âge/taille)","Équations différentielles","Optimisation","Statistique bayésien","Machine learning","Autre"],
 "Deterministe_stochastique": ["Déterministe","Stochastique","Les deux"],
 "Regle_decision": ["Oui","Non"],
 "Telechargement_gratuit": ["Oui","Non","Freemium","Sur demande"],
 "Code_source": ["Ouvert","Partiellement ouvert","Fermé"],
 "Documentation": ["Complète","Partielle","Minimale","Absente"],
 "Tutoriels_exemples": ["Oui","Non"],
 "Expertise_requise": ["Faible (GUI)","Moyenne (scripting)","Élevée (programmation)"],
 "Langage_plateforme": ["R","Python","MATLAB","C/C++","Java","Standalone software","Web-based","Multiple"],
 "Maintenance_active": ["Oui","Non","Inconnue"],
 "Communaute_utilisateurs": ["Grande","Moyenne","Petite","Absente"],
 "Score_accessibilite": ["1","2","3","4","5"],
 "Cap_OON": ["Oui","Optionnel","Non"],
 "Domaine_spatial": ["Côtier","Récifal","Estuarien","Pélagique","Hauturier","Multi-domaine","Non applicable"],
 "Resolution_spatiale": ["< 1 km²","1-10 km²","10-100 km²","> 100 km²","Non spatial"],
 "Habitats_representes": ["Récif corallien","Mangrove","Herbier","Fond meuble","Rocheux","Pélagique","Aucun"],
 "Couplage_benthique_pelagique": ["Oui","Optionnel","Non"],
 "Resolution_verticale": ["Surface seule","Colonne intégrée","Résol. verticale explicite","Non applicable"],
 "Forcage_physique": ["Bathymétrie","Courants","Température","Salinité","Substrat","Marées","Aucun"],
 "Volume_donnees": ["Faible","Modéré","Élevé","Très élevé"],
 "Adaptabilite_data_poor": ["Élevée","Moyenne","Faible"],
 "Pertinence_BRIDGES": ["1","2","3","4","5"],
 "Applique_sites_BRIDGES": ["Non","La Réunion","Mayotte","Îles Éparses","Autre océan Indien","Autre Pacifique","À préciser"],
}

FIELDS = ["Nom_modele","Reference_principale","URL_officielle",
 "Approche_generale","Implementation_informatique","Deterministe_stochastique","Regle_decision",
 "Telechargement_gratuit","Code_source","Documentation","Tutoriels_exemples","Expertise_requise",
 "Langage_plateforme","Maintenance_active","Communaute_utilisateurs","Score_accessibilite",
 "Cap_physique","Cap_biologique","Cap_peche","Cap_economique","Cap_social",
 "Cap_spatial","Cap_temporel","Cap_scenarios","Cap_tradeoffs","Cap_incertitude","Cap_participation",
 "Domaine_spatial","Resolution_spatiale","Habitats_representes","Couplage_benthique_pelagique",
 "Resolution_verticale","Forcage_physique",
 "Donnees_obs_requises","Donnees_param_requises","Volume_donnees","Adaptabilite_data_poor","Strategies_data_poor",
 "Pertinence_BRIDGES","Applique_sites_BRIDGES","Forces","Limites","Notes"]

def build_prompt(model_name, doi=None):
    v = "\n".join(f"- {k} : {' | '.join(val)}" for k, val in VOCAB.items())
    doi_line = f"\nDOI de référence fourni : {doi}\n" if doi else ""
    return f"""Tu documentes les CARACTÉRISTIQUES INTRINSÈQUES (niche fondamentale) d'un modèle,
pour une scoping review sur les modèles socio-écologiques marins (projet BRIDGES).

MODÈLE : {model_name}{doi_line}

Décris ce que ce modèle EST et PEUT faire en général, indépendamment de tout
article d'application. Une seule fiche par modèle.

RÈGLES STRICTES :
- Réponds UNIQUEMENT par un objet JSON valide (aucun texte, aucun Markdown).
- Respecte EXACTEMENT les valeurs autorisées du vocabulaire ci-dessous.
- Les 11 champs Cap_* utilisent l'échelle "Oui" / "Optionnel" / "Non".
  Oui = le modèle représente nativement cette dimension ; Optionnel = possible via extension/configuration ; Non = pas conçu pour.
- Champs multi-valeurs : séparer par " ; ".
- Si information inconnue : "NA" (n'invente jamais, surtout DOI et URL).
- Ajoute un objet "confiance" (haute/moyenne/basse) par champ. Si tu ne connais pas
  bien ce modèle, mets confiance "basse" et reste prudent.

VOCABULAIRE CONTRÔLÉ :
{v}

CHAMPS Cap_ (échelle Oui/Optionnel/Non) :
  Compartiments : Cap_physique, Cap_biologique, Cap_peche, Cap_economique, Cap_social
  Dimensions : Cap_spatial, Cap_temporel, Cap_scenarios, Cap_tradeoffs, Cap_incertitude, Cap_participation

STRUCTURE JSON ATTENDUE (remplis TOUS ces champs dans "valeurs") :
{json.dumps(FIELDS, ensure_ascii=False)}

Format : {{ "valeurs": {{ champ: valeur, ... }}, "confiance": {{ champ: "haute/moyenne/basse", ... }} }}
"""

def call_claude(model_name, doi=None):
    msg = client.messages.create(model=MODEL, max_tokens=2500,
        messages=[{"role":"user","content":build_prompt(model_name, doi)}])
    raw = "".join(b.text for b in msg.content if b.type=="text").strip()
    raw = re.sub(r'^```(json)?|```$','',raw,flags=re.MULTILINE).strip()
    return json.loads(raw)

df = pd.read_excel(EXTRACTION)
row = df[df["Champ"]=="Modele_utilise"]
raw_models = []
if not row.empty:
    for col in df.columns:
        if col=="Champ" or col.endswith("[confiance]"): continue
        val = row.iloc[0][col]
        if isinstance(val,str) and val.strip() and val.strip().upper()!="NA":
            raw_models.append(val.strip())

def normalize(m):
    low=m.lower()
    if "ecopath" in low or "ewe" in low or "ecosim" in low: return "Ecopath with Ecosim (EwE)"
    if "atlantis" in low: return "Atlantis"
    if "osmose" in low: return "OSMOSE"
    if "bioécon" in low or "bioecon" in low or "bio-écon" in low: return "Modèle bioéconomique"
    if "species distribution" in low or low.strip()=="sdm" or "niche model" in low: return "Species Distribution Model (SDM)"
    return m.strip()

models = sorted(set(normalize(m) for m in raw_models))
print(f"{len(models)} modèles distincts (après regroupement). Coût estimé < 1 $.")
for m in models: print("  -", m)

extractions=[]
for i,m in enumerate(models, start=1):
    doi = DOIS_REFERENCE.get(m)
    try:
        res = call_claude(m, doi)
        extractions.append((m, res.get("valeurs",{}), res.get("confiance",{})))
        print(f"  [{i}/{len(models)}] {m} : OK")
    except Exception as e:
        print(f"  [{i}/{len(models)}] {m} : ERREUR {type(e).__name__}: {str(e)[:70]}")
        extractions.append((m, {"_erreur":str(e)[:120]}, {}))
    time.sleep(PAUSE)

data={"Champ":FIELDS}
for name,vals,conf in extractions:
    data[name]=[vals.get(f,"") for f in FIELDS]
    data[name+" [confiance]"]=[conf.get(f,"") for f in FIELDS]
pd.DataFrame(data).to_excel(OUTPUT, index=False)

ok=sum(1 for _,v,_ in extractions if "_erreur" not in v)
print(f"\n=== Résumé ===\nModèles documentés : {ok}/{len(extractions)}\nFichier : {OUTPUT}")
print("RAPPEL : valider chaque fiche ; vérifier surtout DOI/URL et les confiances basses.")
