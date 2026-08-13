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
        "alanine": 2.64686,
        "arginine": 3.67615,
        "aspartic_acid": 4.15070,
        "cysteine": 0.455111,
        "glutamic_acid": 4.34636,
        "glycine": 2.20499,
        "histidine": 1.42453,
        "isoleucine": 2.35458,
        "leucine": 3.68456,
        "lysine": 3.64566,
        "methionine": 0.934236,
        "phenylalanine": 2.26207,
        "proline": 1.87119,
        "serine": 2.60154,
        "threonine": 2.62600,
        "tryptophan": 0.641654,
        "tyrosine": 2.43377,
        "valine": 2.70381,
        "others": 1.71122,
    },
    "fats": {
        "saturated": {
            "palmitic_acid_C16_0": 0.208800,
            "stearic_acid_C18_0": 0.0580000,
            "others": 0.0580000,
        },
        "monounsaturated": {
            "palmitoleic_acid_C16_1_n7": 0.371200,
            "oleic_acid_C18_1_n9": 0.336400,
            "others": 0.0116000,
        },
        "polyunsaturated": {
            "linoleic_acid_C18_2_n6": 0.104400,
            "alpha_linolenic_acid_C18_3_n3": 0.00464000,
            "others": 0.00696000,
        },
    },
    "ashes": {
        "arsenic": 0.0280000,
        "cadmium": 0.0890000,
        "calcium": 195.000,
        "mercury": 0.00400000,
        "phosphorus": 1155.00,
        "others": 4344.88,
    },
    "carbs": {
        "fibers": {
            "beta_glucan": 10.3800,
            "mannan": 7.81000,
            "others": 2.02000,
        },
        "others": 20.3600,
    },
    "vitamins": {},
    "others": {},
    "water": 6.20000,
}