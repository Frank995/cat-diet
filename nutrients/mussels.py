"""Nutritional values of raw blue mussels from:

https://www.nutritionvalue.org (blue mussels)

Basis: 100 g raw blue mussel, wet weight, normalized from the source's
150 g serving (factor 0.666667).
Energy: 86.0000 kcal / 100 g.

Units:
    proteins, fats, carbs, water : g / 100 g
    ashes, vitamins, others      : mg / 100 g

Notes:
- The amino acids plus proteins.others reconcile exactly with the reported
  total protein (11.9 g). The sulphur amino acid is reported as cystine.
- Fatty acids reported as zero (C4:0-C12:0) are omitted. fats.others
  (0.713 g) is the unresolved remainder of total fat (2.24 g).
- C18:1, C18:2, C18:3, C18:4, C20:1, C20:4 and C22:1 are reported as
  positional-isomer sums without an omega family, so the IUPAC-style names
  are kept.
- ashes.others is total ash (1586.67 mg) minus the sum of the identified
  minerals.
- Vitamin A is entirely retinol (all carotenoids zero). Folate is reported
  identically as DFE and food folate with zero folic acid, so a single
  vitamin_b9_folate key is kept. Vitamin K is entirely K1; vitamin D and
  all tocotrienols are zero and are omitted.
- Total carbohydrate (3.69333 g) is entirely non-fiber (fiber reported 0).
"""

TABLE = {
    "proteins": {
        "alanine": 0.720000,
        "arginine": 0.868000,
        "aspartic_acid": 1.14800,
        "cystine": 0.156000,
        "glutamic_acid": 1.61800,
        "glycine": 0.744000,
        "histidine": 0.228000,
        "isoleucine": 0.518000,
        "leucine": 0.838000,
        "lysine": 0.888667,
        "methionine": 0.268000,
        "phenylalanine": 0.426000,
        "proline": 0.486000,
        "serine": 0.532667,
        "threonine": 0.512000,
        "tryptophan": 0.133333,
        "tyrosine": 0.381333,
        "valine": 0.520000,
        "others": 0.914000,
    },
    "fats": {
        "saturated": {
            "myristic_acid_C14_0": 0.0586667,
            "palmitic_acid_C16_0": 0.294000,
            "stearic_acid_C18_0": 0.068000,
        },
        "monounsaturated": {
            "palmitoleic_acid_C16_1_n7": 0.138000,
            "octadecenoic_acid_C18_1": 0.204667,
            "eicosenoic_acid_C20_1": 0.138000,
            "docosenoic_acid_C22_1": 0.026000,
        },
        "polyunsaturated": {
            "octadecadienoic_acid_C18_2": 0.018000,
            "octadecatrienoic_acid_C18_3": 0.020000,
            "octadecatetraenoic_acid_C18_4": 0.0353333,
            "eicosatetraenoic_acid_C20_4": 0.0700000,
            "eicosapentaenoic_acid_C20_5_n3": 0.188000,
            "docosapentaenoic_acid_C22_5_n3": 0.0220000,
            "docosahexaenoic_acid_C22_6_n3": 0.253333,
        },
        "others": 0.713000,
    },
    "ashes": {
        "calcium": 26.0000,
        "copper": 0.0933333,
        "iron": 3.94667,
        "magnesium": 34.0000,
        "manganese": 3.40000,
        "phosphorus": 197.000,
        "potassium": 320.000,
        "selenium": 0.0448000,
        "sodium": 286.000,
        "zinc": 1.60000,
        "others": 714.585,
    },
    "carbs": {
        "fibers": {
            "others": 0.000000,
        },
        "others": 3.69333,
    },
    "vitamins": {
        "vitamin_a_retinol": 0.0480000,
        "vitamin_b1_thiamin": 0.160000,
        "vitamin_b2_riboflavin": 0.210000,
        "vitamin_b3_niacin": 1.60000,
        "vitamin_b5_pantothenic_acid": 0.500000,
        "vitamin_b6": 0.0500000,
        "vitamin_b9_folate": 0.0420000,
        "vitamin_b12_cobalamin": 0.0120000,
        "vitamin_c_ascorbic_acid": 8.00000,
        "vitamin_e_alpha_tocopherol": 0.546667,
        "vitamin_e_gamma_tocopherol": 0.0200000,
        "vitamin_k1_phylloquinone": 0.0000666667,
    },
    "others": {
        "choline": 65.0000,
        "cholesterol": 28.0000,
    },
    "water": 80.5800,
}