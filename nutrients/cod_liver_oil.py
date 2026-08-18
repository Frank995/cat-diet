"""Nutritional values of cod liver oil from:

- https://www.nutritionvalue.org/Fish_oil%2C_cod_liver_nutritional_value.html

Basis: 100 g oil, normalized from the source's 4.5 g serving.

Units:
    proteins, fats, carbs, water : g / 100 g
    ashes, vitamins, others      : mg / 100 g
"""

TABLE = {
    "proteins": {
        "others": 0.000000,
    },
    "fats": {
        "saturated": {
            "myristic_acid": 3.57778,
            "palmitic_acid": 10.6222,
            "stearic_acid": 2.80000,
            "others": 5.60000,
        },
        "monounsaturated": {
            "palmitoleic_acid": 8.31111,
            "oleic_acid": 20.6444,
            "gadoleic_acid": 10.4222,
            "cetoleic_acid": 7.33333,
            "others": 0.000000,
        },
        "polyunsaturated": {
            "linoleic_acid": 0.933333,
            "alpha_linolenic_acid": 0.933333,
            "stearidonic_acid": 0.933333,
            "arachidonic_acid": 0.933333,
            "timnodonic_acid": 6.88889,
            "osbond_acid": 0.933333,
            "cervonic_acid": 10.9778,
            "others": 0.000000,
        },
        "others": 8.15556,
    },
    "ashes": {
        "others": 0.00000,
    },
    "carbs": {
        "fibers": {
            "others": 0.000000,
        },
        "others": 0.000000,
    },
    "vitamins": {
        "vitamin_a_retinol": 30.0000,
        "vitamin_d3": 0.250000,
    },
    "others": {
        "cholesterol": 570.000,
    },
    "water": 0.000000,
}
