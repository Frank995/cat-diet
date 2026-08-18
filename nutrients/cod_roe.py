"""Nutritional values of cod roe from:

- https://www.matvaretabellen.no/en/cod-roe-raw/

Basis: 100 g raw roe, wet weight.

Units:
    proteins, fats, carbs, water : g / 100 g
    ashes, vitamins, others      : mg / 100 g
"""

TABLE = {
    "proteins": {
        "others": 23.2000,
    },
    "fats": {
        "saturated": {
            "palmitic_acid": 0.400000,
            "stearic_acid": 0.100000,
            "others": 0.000000,
        },
        "monounsaturated": {
            "palmitoleic_acid": 0.100000,
            "oleic_acid": 0.300000,
            "others": 0.100000,
        },
        "polyunsaturated": {
            "arachidonic_acid": 0.100000,
            "timnodonic_acid": 0.300000,
            "cervonic_acid": 0.700000,
            "others": 0.000000,
        },
        "others": 0.500000,
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
        "others": 0.000000,
    },
    "carbs": {
        "fibers": {
            "others": 0.000000,
        },
        "others": 0.000000,
    },
    "vitamins": {
        "vitamin_a_retinol": 0.0280000,
        "vitamin_b1": 0.770000,
        "vitamin_b2": 0.660000,
        "vitamin_b3": 1.20000,
        "vitamin_b6": 0.260000,
        "vitamin_b9": 0.0220000,
        "vitamin_b12": 0.0195000,
        "vitamin_c": 19.0000,
        "vitamin_d3": 0.00520000,
        "vitamin_e_alpha_tocopherol": 10.3000,
    },
    "others": {
        "cholesterol": 323.000,
    },
    "water": 74.0000,
}
