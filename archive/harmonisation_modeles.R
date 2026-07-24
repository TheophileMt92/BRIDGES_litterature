## =====================================================================
## BRIDGES - Harmonisation des noms de modèles (Fiche Articles)
## =====================================================================
## Transforme le champ Modele_utilise (très détaillé, une variante par
## article) en un Modele_canonique propre, pour les analyses et radars.
##
## Aucune dépendance à une API. À intégrer dans le workflow Quarto.
## La table de correspondance est explicite et modifiable : ajuste l'ordre
## et les motifs selon ta validation du fichier Excel de correspondance.
## =====================================================================

library(dplyr)
library(stringr)
library(readxl)
library(tidyr)

## --- 1. Fonction de canonisation -------------------------------------
## L'ORDRE compte : les familles dominantes / les plus spécifiques d'abord.
## Un article est rattaché au PREMIER motif qui correspond (modèle principal).
canoniser_modele <- function(x) {
  l <- str_to_lower(replace_na(as.character(x), ""))
  dplyr::case_when(
    l == "" | l == "nan"                                                   ~ "NA (à vérifier)",
    str_detect(l, "ecopath|ecosim|ecospace|ewe|ecotran|rpath|ecotroph")   ~ "Ecopath with Ecosim (EwE)",
    str_detect(l, "atlantis")                                             ~ "Atlantis",
    str_detect(l, "osmose")                                               ~ "OSMOSE",
    str_detect(l, "mizer|size-spectrum|size spectrum")                    ~ "Size-spectrum (mizer)",
    str_detect(l, "displace")                                             ~ "DISPLACE",
    str_detect(l, "corset|hireefsim|simreef")                             ~ "CORSET / dérivés récifaux",
    str_detect(l, "dbem|bioclimate envelope|bioclimatic envelope")        ~ "DBEM (Dynamic Bioclimate Envelope Model)",
    str_detect(l, "mefisto")                                              ~ "MEFISTO",
    str_detect(l, "flbeia")                                               ~ "FLBEIA",
    str_detect(l, "fishrent")                                             ~ "FishRent",
    str_detect(l, "bemtool")                                              ~ "BEMTOOL",
    str_detect(l, "isis-fish|isis fish")                                  ~ "ISIS-Fish",
    str_detect(l, "poseidon")                                             ~ "POSEIDON",
    str_detect(l, "strathe2e")                                            ~ "StrathE2E",
    str_detect(l, "gadget")                                               ~ "Gadget",
    str_detect(l, "sefes")                                                ~ "SEFES",
    str_detect(l, "sprat")                                                ~ "SPRAT",
    str_detect(l, "smart") & str_detect(l, "trawl")                       ~ "SMART",
    str_detect(l, "oceanparcels|lagrangian")                              ~ "Biophysique / Lagrangien",
    str_detect(l, "ergom|getm")                                           ~ "GETM-ERGOM (hydro-biogéochimique)",
    str_detect(l, "loop analysis|qualitative network|signed digraph|qnm|conceptual ecosystem") ~ "Modèle qualitatif (loop analysis / QNM)",
    str_detect(l, "system dynamics|stella|extendsim")                     ~ "System dynamics",
    str_detect(l, "random forest|machine learning")                       ~ "Machine learning (RF, etc.)",
    str_detect(l, "maxent|sdmtmb|species distribution|habitat model|habitat suitability") | l == "sdm" ~ "Species Distribution Model (SDM)",
    str_detect(l, "mice|intermediate complexity|minimally realistic")     ~ "MICE (complexité intermédiaire)",
    str_detect(l, "management strategy evaluation") | str_starts(l, "mse") ~ "MSE (Management Strategy Evaluation)",
    str_detect(l, "earth system model| esm|gcm|cmip|mitgcm|noresm|mpi-esm") ~ "Earth System / Climate model",
    str_detect(l, "bioécon|bioecon|bio-écon|biéconomique|gordon-schaefer|integrated assessment") | str_detect(l, "\\biam\\b") ~ "Modèle bioéconomique",
    str_detect(l, "food web|trophic|ecological network")                  ~ "Modèle trophique / réseau",
    str_detect(l, "population") & str_detect(l, "age|size|matrix|delay-difference|récolte|harvest") ~ "Dynamique de population (structurée)",
    str_detect(l, "surplus production|aspic|cmsy")                        ~ "Production excédentaire",
    str_detect(l, "bayesian")                                             ~ "Modèle bayésien",
    TRUE                                                                  ~ "AUTRE / à classer"
  )
}

## --- 2. Application à la Fiche Articles -------------------------------
## La Fiche Articles est en format "champs en lignes, articles en colonnes".
## On la transpose pour avoir une ligne par article.
chemin_extraction <- "extraction_articles_BRIDGES_REMPLIE.xlsx"

fa <- read_excel(chemin_extraction)
champs <- fa$Champ
cols_articles <- setdiff(names(fa), "Champ")
cols_articles <- cols_articles[!str_detect(cols_articles, "\\[confiance\\]$")]

# transpose -> une ligne par article
articles <- fa |>
  select(Champ, all_of(cols_articles)) |>
  pivot_longer(-Champ, names_to = "article", values_to = "valeur") |>
  pivot_wider(names_from = Champ, values_from = valeur)

# ajoute la colonne canonique
articles <- articles |>
  mutate(Modele_canonique = canoniser_modele(Modele_utilise))

## --- 3. Contrôle : table des effectifs -------------------------------
effectifs <- articles |>
  count(Modele_canonique, sort = TRUE)
print(effectifs, n = 100)

## --- 4. Export -------------------------------------------------------
write.csv(articles, "articles_harmonises.csv", row.names = FALSE, fileEncoding = "UTF-8")
write.csv(effectifs, "effectifs_modeles.csv", row.names = FALSE, fileEncoding = "UTF-8")

cat("\nFichiers écrits : articles_harmonises.csv et effectifs_modeles.csv\n")
cat("Seuil radar suggéré : modèles avec n >= 10 en individuel, le reste en familles.\n")
