"""Nutritional values of black soldier fly larvae (Hermetia illucens) averaged from:

- Lu, Shengyong, et al. "Nutritional composition of black soldier fly larvae (Hermetia
  illucens L.) and its potential uses as alternative protein sources in animal diets:
  A review." Insects 13.9 (2022): 831.
- Zulkifli, Nor Fatin Najihah Mohamad, et al. "Nutritional value of black soldier fly
  (Hermetia illucens) larvae processed by different methods." PLoS ONE 17.2 (2022):
  e0263924.

Basis: 100 g dried BSFL meal (spray-dried + 2x oven-dried samples, n=3, averaged),
dry-matter proximate basis. Residual moisture (5.21 g/100g) is reported separately
and is not summed into the other categories.

Units:
    proteins, fats, carbs, water : g / 100 g
    ashes, vitamins, others      : mg / 100 g

Notes:
    - Fatty acids were rescaled from "% of total fat" to g/100g using each sample's
      own lipid content before averaging.
"""

TABLE = {
    "proteins": {
        "alanine": 3.06333,
        "arginine": 2.20000,
        "aspartic_acid": 4.31333,
        "cysteine": 0.143333,
        "glutamic_acid": 5.42333,
        "glycine": 0.196667,
        "histidine": 2.51667,
        "hydroxyproline": 0.0300000,
        "isoleucine": 2.14667,
        "leucine": 3.26667,
        "lysine": 2.97000,
        "methionine": 0.870000,
        "phenylalanine": 1.81333,
        "proline": 2.65667,
        "serine": 1.83000,
        "threonine": 1.73667,
        "tryptophan": 0.623333,
        "tyrosine": 2.46667,
        "valine": 2.76667,
        "others": 3.98000,
    },
    "fats": {
        "saturated": {
            "capric_acid": 0.136813,
            "lauric_acid": 9.73405,
            "myristic_acid": 2.71780,
            "palmitic_acid": 7.16744,
            "stearic_acid": 1.13241,
            "heneicosanoic_acid_C21_0": 0.0777087,
            "behenic_acid": 0.0332453,
            "others": 0.000000,
        },
        "monounsaturated": {
            "palmitoleic_acid": 0.728945,
            "oleic_acid": 3.99473,
            "gondoic_acid": 0.0588187,
            "others": 0.000000,
        },
        "polyunsaturated": {
            "linoleic_acid": 3.31156,
            "alpha_linolenic_acid": 0.280013,
            "eicosadienoic_acid_C20_2_n6": 1.40730,
            "dihomo_gamma_linolenic_acid": 0.0485893,
            "timnodonic_acid": 0.125000,
            "cervonic_acid": 0.010000,
            "others": 0.000000,
        },
        "others": 0.000000,
    },
    "ashes": {
        "calcium": 2023.23,
        "copper": 1.97233,
        "iron": 43.4490,
        "magnesium": 314.424,
        "manganese": 14.5853,
        "phosphorus": 763.333,
        "potassium": 1241.98,
        "sodium": 416.592,
        "zinc": 83.2353,
        "others": 3003.85833,
    },
    "carbs": {
        "fibers": {
            "chitin": 6.17000,
            "others": 2.78000,
        },
        "others": 7.30667,
    },
    "vitamins": {
        "vitamin_b1": 1.32667,
        "vitamin_b2": 9.91333,
        "vitamin_c": 0.260000,
    },
    "others": {},
    "water": 5.21000,
}
