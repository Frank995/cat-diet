"""Nutritional values of nutritional yeast (Saccharomyces cerevisiae) averaged from:

Cao, Xin, et al. "Evaluation of the nutritional quality of yeast protein in comparison to animal and plant proteins using growing rats and INFOGEST model." Food Chemistry 463 (2025): 141178.
Jach, Monika E., and Anna Serefko. "Nutritional yeast biomass: characterization and application." Diet, microbiome and health. Academic Press, 2018. 237-270.
Patterson, Rob, et al. "Yeast derivatives as a source of bioactive components in animal nutrition: a brief review." Frontiers in Veterinary Science 9 (2023): 1067383.

Basis: 100 g yeast biomass as sold (water 6.2 g / 100 g). The averaged
literature values were then scaled to match the actual "Energy Feelings
Nutritional Yeast" macronutrient table.

Units:
    proteins, fats, carbs, water : g / 100 g
    ashes, vitamins, others      : mg / 100 g

Notes:
- Total carbohydrate is a "by difference" figure in both source papers,
  not a direct analytical measurement, and the two estimates disagree
  substantially (37.6 vs 43.5 g / 100 g), propagating all upstream error in
  protein/fat/ash/moisture. The averaged value should be treated as a rough
  estimate.
- No paper reports total dietary fiber directly for S. cerevisiae. Non-starch
  polysaccharide (mannan + beta-glucan + a small unresolved residue) from
  Doc 3 was used as the fiber proxy - again a single-source number. Chitin is
  mentioned only qualitatively as a cell-wall component in Doc 3 and is never
  quantified, so it has no key of its own and is implicitly folded into
  carbs.fibers.others.
- Total fat: Doc 2 (0.7%) and Doc 3 (1.62%) differ by more than 2x, likely
  reflecting different extraction solvents/protocols; they were simply
  averaged. The fatty-acid sub-profile (C16:0, C16:1, C18:0, C18:1, C18:2 n-6,
  C18:3 n-3 and the SFA/MUFA/PUFA residuals in each "others") comes from a
  single source (Doc 2, Table 9.5), so it carries more uncertainty than the
  aggregate fat number.
- proteins.others is the non-amino-acid nitrogen remainder of the protein
  fraction.
- No source quantifies vitamins for this material, so the vitamins table is
  empty even though nutritional yeast is normally a B-vitamin source
  (commercial products are usually fortified).
- ashes.others is the residual of total ash after phosphorus, calcium and the
  reported heavy-metal traces.
"""

TABLE = {
    "proteins": {
        "alanine": 2.911,
        "arginine": 4.043,
        "aspartic_acid": 4.565,
        "cysteine": 0.500,
        "glutamic_acid": 4.780,
        "glycine": 2.425,
        "histidine": 1.567,
        "isoleucine": 2.589,
        "leucine": 4.052,
        "lysine": 4.009,
        "methionine": 1.027,
        "phenylalanine": 2.488,
        "proline": 2.058,
        "serine": 2.861,
        "threonine": 2.888,
        "tryptophan": 0.706,
        "tyrosine": 2.676,
        "valine": 2.973,
        "others": 1.882,
    },
    "fats": {
        "saturated": {
            "palmitic_acid_C16_0": 0.643,
            "stearic_acid_C18_0": 0.179,
            "others": 0.179,
        },
        "monounsaturated": {
            "palmitoleic_acid_C16_1_n7": 1.333,
            "oleic_acid_C18_1_n9": 1.208,
            "others": 0.042,
        },
        "polyunsaturated": {
            "linoleic_acid_C18_2_n6": 0.375,
            "alpha_linolenic_acid_C18_3_n3": 0.017,
            "others": 0.025,
        },
    },
    "ashes": {
        "zinc": 120.0,

        "arsenic": 0.028,
        "cadmium": 0.089,
        "calcium": 195.0,
        "mercury": 0.004,
        "phosphorus": 1155.0,
        "others": 4344.88,
    },
    "carbs": {
        "fibers": {
            "beta_glucan": 11.30,
            "mannan": 8.50,
            "others": 2.20,
        },
        "sugars": 12.0,
        "others": 3.0, 
    },
    "vitamins": {
        "vitamin_b1_thiamine": 45.0,
        "vitamin_b6_pyridoxine": 34.0,
        "vitamin_b9_folic_acid": 4.4,
        "vitamin_b12_cobalamin": 0.044,
    },
    "others": {},
    "water": 6.2,
}