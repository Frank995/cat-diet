"""Nutritional values of cod roe from:

https://www.matvaretabellen.no/en/cod-roe-raw/

Food: Gadus morhua Linnaeus, 1758 — raw cod roe (food id 04.052).

Basis: 100 g raw roe, wet weight (source normalization factor 1.0).
Energy: 116 kcal / 100 g.

Units:
    proteins, fats, carbs, water : g / 100 g
    ashes, vitamins, others      : mg / 100 g

Notes:
- The source gives no amino-acid breakdown, so the whole protein fraction
  (23.2 g) sits in proteins.others.
- Fatty acids reported as zero (C12:0, C14:0, C18:2 n-6, C18:3 n-3, C20:3,
  C20:4 n-3, C22:5 n-3) are omitted. The 0.6 g in fats.others is the
  difference between the reported total fat (2.6 g) and the sum of the
  identified fatty acids (2.0 g).
- Vitamin A is reported identically as RAE, RE and retinol with zero
  beta-carotene, so it is kept only as vitamin_a_retinol.
- Vitamin E is the source's alpha-tocopherol-equivalent figure.
- Only preformed niacin is kept; the "niacin equivalents" figure (5.5 mg)
  is dropped because it includes tryptophan-derived niacin already counted
  in the protein fraction.
- The "salt (NaCl)" figure (300 mg) is dropped because it is derived from
  the sodium value and would double-count it.
- Carbohydrates, starch and all sugar fractions are reported as zero.
"""

TABLE = {
    "proteins": {
        "others": 23.2000,
    },
    "fats": {
        "saturated": {
            "palmitic_acid_C16_0": 0.400000,
            "stearic_acid_C18_0": 0.100000,
        },
        "monounsaturated": {
            "palmitoleic_acid_C16_1_n7": 0.100000,
            "oleic_acid_C18_1_n9": 0.300000,
        },
        "polyunsaturated": {
            "arachidonic_acid_C20_4_n6": 0.100000,
            "eicosapentaenoic_acid_C20_5_n3": 0.300000,
            "docosahexaenoic_acid_C22_6_n3": 0.700000,
        },
        "others": 0.600000,
    },
    "ashes": {
        "calcium": 8.00000,
        "copper": 0.120000,
        "iodine": 0.195000,
        "iron": 0.900000,
        "magnesium": 13.0000,
        "phosphorus": 403.000,
        "potassium": 272.000,
        "selenium": 0.105000,
        "sodium": 101.000,
        "zinc": 4.50000,
    },
    "carbs": {
        "fibers": {
            "others": 0.000000,
        },
        "others": 0.000000,
    },
    "vitamins": {
        "vitamin_a_retinol": 0.0280000,
        "vitamin_b1_thiamin": 0.770000,
        "vitamin_b2_riboflavin": 0.660000,
        "vitamin_b3_niacin": 1.20000,
        "vitamin_b6_pyridoxine": 0.260000,
        "vitamin_b9_folate": 0.0220000,
        "vitamin_b12_cobalamin": 0.0195000,
        "vitamin_c_ascorbic_acid": 19.0000,
        "vitamin_d3_cholecalciferol": 0.00520000,
        "vitamin_e_alpha_tocopherol": 10.3000,
    },
    "others": {
        "cholesterol": 323.000,
        "salt": 300.000
    },
    "water": 74.0000,
}