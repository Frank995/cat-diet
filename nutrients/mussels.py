"""Nutritional values of raw blue mussels from:

https://www.nutritionvalue.org/Mollusks%2C_raw%2C_blue%2C_mussel_nutritional_value.html

Basis: 100 g raw blue mussel, wet weight, normalized from the source's
150 g serving (factor 0.666667).

Units:
    proteins, fats, carbs, water : g / 100 g
    ashes, vitamins, others      : mg / 100 g
"""

TABLE = {
    "proteins": {
        "alanine": 0.720000,
        "arginine": 0.868000,
        "aspartic_acid": 1.14800,
        "cysteine": 0.156000,
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
            "myristic_acid": 0.0586667,
            "palmitic_acid": 0.294000,
            "stearic_acid": 0.068000,
            "others": 0.004000,
        },
        "monounsaturated": {
            "palmitoleic_acid": 0.138000,
            "oleic_acid": 0.204667,
            "eicosenoic_acid_C20_1": 0.138000,
            "cetoleic_acid": 0.026000,
            "others": 0.000000,
        },
        "polyunsaturated": {
            "linoleic_acid": 0.018000,
            "alpha_linolenic_acid": 0.020000,
            "stearidonic_acid": 0.0353333,
            "arachidonic_acid": 0.0700000,
            "timnodonic_acid": 0.188000,
            "osbond_acid": 0.0220000,
            "cervonic_acid": 0.253333,
            "others": 0.000000,
        },
        "others": 0.702667,
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
        "vitamin_b1": 0.160000,
        "vitamin_b2": 0.210000,
        "vitamin_b3": 1.60000,
        "vitamin_b5": 0.500000,
        "vitamin_b6": 0.0500000,
        "vitamin_b9": 0.0420000,
        "vitamin_b12": 0.0120000,
        "vitamin_c": 8.00000,
        "vitamin_e_alpha_tocopherol": 0.546667,
        "vitamin_e_gamma_tocopherol": 0.0200000,
        "vitamin_k1": 0.0000666667,
    },
    "others": {
        "choline": 65.0000,
        "cholesterol": 28.0000,
    },
    "water": 80.5800,
}
