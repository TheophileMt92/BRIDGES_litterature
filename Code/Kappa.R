library(irr)
library(tidyverse)

# 1. Importer les fichiers remplis par chaque screener
tm <- readxl::read_excel(here::here("Kappa", "BRIDGES_sample_33_TM.xlsx"), sheet = 1)
ac <- readxl::read_excel(here::here("Kappa", "BRIDGES_sample_33_AC.xlsx"), sheet = 1)
sd <- readxl::read_excel(here::here("Kappa", "BRIDGES_sample_33_SD.xlsx"), sheet = 1)
sm <- readxl::read_excel(here::here("Kappa", "BRIDGES_sample_33_SM.xlsx"), sheet = 1)

# 2. Simplifier les decisions en binaire
binarize <- function(x) {
  if_else(x %in% c("Include", "Review/synthesis"), "Include", "Exclude")
}

ratings <- tibble(
  doi = tm$doi,
  TM = binarize(tm$decision),
  AC = binarize(ac$decision),
  SD = binarize(sd$decision),
  SM = binarize(sm$decision)
)

# 3. Fleiss' Kappa (accord global entre les 4 screeners)
ratings_matrix <- ratings |>
  select(-doi) |>
  apply(1, function(row) {
    c(Include = sum(row == "Include"), Exclude = sum(row == "Exclude"))
  }) |>
  t()

fleiss <- kappam.fleiss(ratings_matrix)
cat("Fleiss' Kappa (4 screeners):", round(fleiss$value, 3), "\n")
cat("p-value:", fleiss$p.value, "\n")

# 4. Cohen's Kappa pairwise
screeners <- c("TM", "AC", "SD", "SM")

pairwise <- expand.grid(s1 = screeners, s2 = screeners, stringsAsFactors = FALSE) |>
  filter(s1 < s2) |>
  rowwise() |>
  mutate(
    kappa = kappa2(cbind(ratings[[s1]], ratings[[s2]]))$value,
    agreement = mean(ratings[[s1]] == ratings[[s2]]) * 100
  )

print(pairwise)

# 5. "Indice Theophile": accord TM vs majorite des 3 autres
ratings <- ratings |>
  mutate(
    majority = if_else(
      (AC == "Include") + (SD == "Include") + (SM == "Include") >= 2,
      "Include", "Exclude"
    ),
    tm_agrees = TM == majority
  )

cat("\nAccord TM vs majorite:", round(mean(ratings$tm_agrees) * 100, 1), "%\n")

# 6. Detail des desaccords
disagreements <- ratings |>
  filter(!tm_agrees) |>
  left_join(tm |> select(doi, title, decision, notes), by = "doi")

print(disagreements)
