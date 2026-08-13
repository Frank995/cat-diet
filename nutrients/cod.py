"""Nutritional values of wild cod averaged from:

Jensen, Ida-Johanne, et al. "Nutritional content and bioactive properties of wild and farmed cod (Gadus morhua L.) subjected to food preparation." Journal of Food Composition and Analysis 31.2 (2013): 212-216.
https://www.nutritionvalue.org (wild raw cod)

Basis: 100 g raw Atlantic cod, wet weight. The NutritionValue entry was
normalized from an 85 g serving to 100 g; the Jensen et al. values were
already reported per wet fillet mass.
Energy: 82.3529 kcal / 100 g.

Units:
    proteins, fats, carbs, water : g / 100 g
    ashes, vitamins, others      : mg / 100 g

Notes:
- The two sources report the sulphur amino acids differently (Jensen:
  cysteine; NutritionValue: cystine). Both are retained as reported, since
  together with the other amino acids and proteins.others they reconcile
  exactly with the averaged total protein (17.4809 g).
- Fatty acids reported as zero (C4:0-C12:0) are omitted. fats.others
  (0.371176 g) is the unresolved remainder of total fat (0.810294 g).
- C18:1, C18:2, C18:3, C18:4 and C20:4 are reported by the source as
  positional-isomer sums without an omega family, so the IUPAC-style names
  are kept.
- ashes.others is total ash (1232.35 mg) minus the sum of the identified
  minerals.
- Vitamin A is entirely retinol (all carotenoids zero). Folate is reported
  identically as DFE and food folate with zero folic acid, so a single
  vitamin_b9_folate key is kept. Vitamin D is entirely D3 and vitamin E
  entirely alpha-tocopherol; vitamin K is entirely K1.
- Carbohydrate and fiber (including chitin) are reported as zero.
"""

TABLE = {
    "proteins": {
        "alanine": 1.11574,
        "arginine": 1.11794,
        "aspartic_acid": 1.59926,
        "cysteine": 0.0950000,
        "cystine": 0.190588,
        "glutamic_acid": 2.79632,
        "glycine": 0.857647,
        "histidine": 0.434265,
        "isoleucine": 0.770588,
        "leucine": 1.47853,
        "lysine": 1.67265,
        "methionine": 0.561029,
        "phenylalanine": 0.717647,
        "proline": 0.627206,
        "serine": 0.787941,
        "threonine": 0.800588,
        "tryptophan": 0.198824,
        "tyrosine": 0.635588,
        "valine": 0.863235,
        "others": 0.160294,
    },
    "fats": {
        "saturated": {
            "myristic_acid_C14_0": 0.00970588,
            "palmitic_acid_C16_0": 0.0902941,
            "stearic_acid_C18_0": 0.0272059,
        },
        "monounsaturated": {
            "palmitoleic_acid_C16_1_n7": 0.0132353,
            "octadecenoic_acid_C18_1": 0.0530882,
            "eicosenoic_acid_C20_1": 0.0152941,
            "docosenoic_acid_C22_1": 0.00676471,
        },
        "polyunsaturated": {
            "octadecadienoic_acid_C18_2": 0.00985294,
            "octadecatrienoic_acid_C18_3": 0.00117647,
            "octadecatetraenoic_acid_C18_4": 0.00558824,
            "eicosatetraenoic_acid_C20_4": 0.0223529,
            "eicosapentaenoic_acid_C20_5_n3": 0.0592647,
            "docosapentaenoic_acid_C22_5_n3": 0.00779412,
            "docosahexaenoic_acid_C22_6_n3": 0.117500,
        },
        "others": 0.371176,
    },
    "ashes": {
        "calcium": 16.0000,
        "copper": 0.0235294,
        "iron": 0.376471,
        "magnesium": 32.0000,
        "manganese": 0.0152941,
        "phosphorus": 203.000,
        "potassium": 413.000,
        "selenium": 0.0331059,
        "sodium": 54.0000,
        "zinc": 0.447059,
        "others": 513.455,
    },
    "carbs": {
        "fibers": {
            "others": 0.000000,
        },
        "others": 0.000000,
    },
    "vitamins": {
        "vitamin_a_retinol": 0.0120000,
        "vitamin_b1_thiamin": 0.0764706,
        "vitamin_b2_riboflavin": 0.0647059,
        "vitamin_b3_niacin": 2.06353,
        "vitamin_b5_pantothenic_acid": 0.152941,
        "vitamin_b6_pyridoxine": 0.244706,
        "vitamin_b9_folate": 0.00700000,
        "vitamin_b12_cobalamin": 0.000905882,
        "vitamin_c_ascorbic_acid": 0.941176,
        "vitamin_d3_cholecalciferol": 0.000905882,
        "vitamin_e_alpha_tocopherol": 0.635294,
        "vitamin_k1_phylloquinone": 0.000117647,
    },
    "others": {
        "choline": 65.1765,
        "cholesterol": 43.0000,
        "taurine": 115.000,
        "beta_alanine": 95.0000,
        "1_methylhistidine": 115.000,
    },
    "water": 80.3368,
}