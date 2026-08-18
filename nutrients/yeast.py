"""Nutritional values of nutritional yeast (Saccharomyces cerevisiae) averaged from:

- Cao, Xin, et al. "Evaluation of the nutritional quality of yeast protein in
  comparison to animal and plant proteins using growing rats and INFOGEST model."
  Food Chemistry 463 (2025): 141178.
- Jach, Monika E., and Anna Serefko. "Nutritional yeast biomass: characterization
  and application." Diet, microbiome and health. Academic Press, 2018. 237-270.
- Patterson, Rob, et al. "Yeast derivatives as a source of bioactive components in
  animal nutrition: a brief review." Frontiers in Veterinary Science 9 (2023): 1067383.
- https://www.amazon.it/dp/B09NL5FHBQ

Basis: 100 g yeast biomass as sold (water 6.2 g/100g, i.e. 93.8 g dry matter/100g).
Literature values were converted to this basis before averaging (Patterson's "% as-is"
figures rebased via each source's stated DM%; Jach's "dried biomass" figures rebased
from 100% DM). Absolute totals were then reconciled against the "Energy Feelings
Nutritional Yeast" product label, a fortified commercial product (added iron and
B-vitamins), since literature alone does not support such fortification-level doses.

Units:
    proteins, fats, carbs, water : g / 100 g
    ashes, vitamins, others      : mg / 100 g

Notes:
    - Amino acid ratios (mg AA/g protein) were averaged from Jach and Cao (the latter's
      purified yeast protein isolate used for AA ratios only, not proximate composition);
      Patterson's whole-biomass amino acid data was excluded due to internal Min>Mean
      inconsistencies in the source table.
    - Fatty acid sub-ratios follow Jach's S. cerevisiae profile, rescaled so saturated/
      monounsaturated/polyunsaturated sum to the label's total fat.
    - Iron and all vitamin levels reflect product fortification and are sourced from the
      label, not the literature, which reports no comparable natural concentrations.
"""

TABLE = {
    "proteins": {
        "alanine": 2.855,
        "arginine": 3.965,
        "aspartic_acid": 4.477,
        "cysteine": 0.313,
        "glutamic_acid": 4.688,
        "glycine": 2.378,
        "histidine": 1.536,
        "isoleucine": 2.451,
        "leucine": 3.821,
        "lysine": 3.295,
        "methionine": 0.912,
        "phenylalanine": 2.361,
        "proline": 2.018,
        "serine": 2.806,
        "threonine": 2.424,
        "tryptophan": 0.588,
        "tyrosine": 2.625,
        "valine": 2.799,
        "others": 0.688,
    },
    "fats": {
        "saturated": {
            "palmitic_acid": 0.643,
            "stearic_acid": 0.179,
            "others": 0.179,
        },
        "monounsaturated": {
            "palmitoleic_acid": 1.778,
            "oleic_acid": 1.611,
            "others": 0.056,
        },
        "polyunsaturated": {
            "linoleic_acid": 0.500,
            "alpha_linolenic_acid": 0.022,
            "others": 0.033,
        },
        "others": 0.0,
    },
    "ashes": {
        "iron": 120.0,
        "arsenic": 0.026,
        "cadmium": 0.083,
        "calcium": 189.9,
        "mercury": 0.004,
        "phosphorus": 1115.1,
        "sodium": 70.74,
        "others": 3971.46,
    },
    "carbs": {
        "fibers": {
            "beta_glucan": 10.272,
            "mannan": 7.729,
            "others": 1.999,
        },
        "sugars": 1.0,
        "others": 18.0,
    },
    "vitamins": {
        "vitamin_b1": 41.0,
        "vitamin_b2": 18.0,
        "vitamin_b3": 420.0,
        "vitamin_b5": 140.0,
        "vitamin_b6": 34.0,
        "vitamin_b8": 0.196,
        "vitamin_b9": 4.1,
        "vitamin_b12": 0.044,
    },
    "others": {},
    "water": 6.2,
}
