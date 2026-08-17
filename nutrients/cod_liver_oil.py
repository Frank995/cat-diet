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
            "myristic_acid_C14_0": 3.57778,
            "palmitic_acid_C16_0": 10.6222,
            "stearic_acid_C18_0": 2.80000,
            "others": 5.60000,
        },
        "monounsaturated": {
            "palmitoleic_acid_C16_1_n7": 8.31111,
            "octadecenoic_acid_C18_1": 20.6444,
            "eicosenoic_acid_C20_1": 10.4222,
            "docosenoic_acid_C22_1": 7.33333,
            "others": 0.000000,
        },
        "polyunsaturated": {
            "octadecadienoic_acid_C18_2": 0.933333,
            "octadecatrienoic_acid_C18_3": 0.933333,
            "octadecatetraenoic_acid_C18_4": 0.933333,
            "eicosatetraenoic_acid_C20_4": 0.933333,
            "eicosapentaenoic_acid_C20_5_n3": 6.88889,
            "docosapentaenoic_acid_C22_5_n3": 0.933333,
            "docosahexaenoic_acid_C22_6_n3": 10.9778,
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
        "vitamin_d3_cholecalciferol": 0.250000,
    },
    "others": {
        "cholesterol": 570.000,
    },
    "water": 0.000000,
}
