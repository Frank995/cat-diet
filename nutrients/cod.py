"""
Nutritional values of wild Atlantic cod (Gadus morhua) based on:


- Jensen, I.-J., et al. "Nutritional content and bioactive properties of wild and
  farmed cod (Gadus morhua L.) subjected to food preparation."
  Journal of Food Composition and Analysis 31.2 (2013): 212-216.
- https://www.nutritionvalue.org/Fish%2C_raw%2C_Atlantic%2C_cod_nutritional_value.html

Basis: 100 g raw Atlantic cod, wet weight.

Units:
    proteins, fats, carbs, water : g / 100 g
    ashes, vitamins, others      : mg / 100 g

Notes:
    - NutritionValue reports cystine rather than cysteine. The cystine value
      was converted using 1 g cystine = 1.0084 g cysteine before averaging.
"""

TABLE = {
    "proteins": {
        "alanine": 1.038235294,
        "arginine": 1.097941176,
        "aspartic_acid": 1.531764706,
        "cysteine": 0.151094588,
        "glutamic_acid": 2.723823529,
        "glycine": 0.797647059,
        "histidine": 0.416764706,
        "isoleucine": 0.740588235,
        "leucine": 1.423529412,
        "lysine": 1.617647059,
        "methionine": 0.533529412,
        "phenylalanine": 0.672647059,
        "proline": 0.604705882,
        "serine": 0.742941176,
        "threonine": 0.760588235,
        "tryptophan": 0.198823529,
        "tyrosine": 0.610588235,
        "valine": 0.833235294,
        "others": 0.188235294,
    },
    "fats": {
        "saturated": {
            "myristic_acid": 0.009411765,
            "palmitic_acid": 0.090588235,
            "stearic_acid": 0.029411765,
            "others": 0.001176471,
        },
        "monounsaturated": {
            "palmitoleic_acid": 0.016470588,
            "oleic_acid": 0.061176471,
            "gadoleic_acid": 0.015294118,
            "cetoleic_acid": 0.003529412,
            "others": 0.000000000,
        },
        "polyunsaturated": {
            "linoleic_acid": 0.004705882,
            "alpha_linolenic_acid": 0.001176471,
            "stearidonic_acid": 0.001176471,
            "arachidonic_acid": 0.022352941,
            "timnodonic_acid": 0.063529412,
            "osbond_acid": 0.010588235,
            "cervonic_acid": 0.120000000,
            "others": 0.008235294,
        },
        "others": 0.215294118,
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
        "others": 513.457482,
    },
    "carbs": {
        "fibers": {
            "others": 0.000000,
        },
        "others": 0.000000,
    },
    "vitamins": {
        "vitamin_a_retinol": 0.0120000,
        "vitamin_b1": 0.0764706,
        "vitamin_b2": 0.0647059,
        "vitamin_b3": 2.06353,
        "vitamin_b5": 0.152941,
        "vitamin_b6": 0.244706,
        "vitamin_b9": 0.00700000,
        "vitamin_b12": 0.000905882,
        "vitamin_c": 0.941176,
        "vitamin_d3": 0.000905882,
        "vitamin_e_alpha_tocopherol": 0.635294,
        "vitamin_k1": 0.000117647,
    },
    "others": {
        "choline": 65.1765,
        "cholesterol": 43.0000,
        "taurine": 110.000,
        "beta_alanine": 30.000,
        "1_methylhistidine": 100.000,
    },
    "water": 81.061765,
}
