"""Nutritional values of high-oleic sunflower oil from:

https://www.nutritionvalue.org/Oil%2C_high_oleic_%2870%25_and_over%29%2C_sunflower_nutritional_value.html

Source serving: 14 g (1.0 tbsp) high-oleic sunflower oil.
Basis: 100 g oil, scaled from the source's 14 g serving (factor 7.142857).

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
            "tetradecanoic_acid_C14_0": 0.0571429,
            "pentadecanoic_acid_C15_0": 0.800000,
            "hexadecanoic_acid_C16_0": 3.67857,
            "octadecanoic_acid_C18_0": 4.32143,
            "docosanoic_acid_C22_0": 1.000000,
            "others": 0.000000,
        },
        "monounsaturated": {
            "hexadecenoic_acid_C16_1": 0.0928571,
            "octadecenoic_acid_C18_1": 82.6286,
            "eicosenoic_acid_C20_1": 0.964286,
            "others": 0.000000,
        },
        "polyunsaturated": {
            "octadecadienoic_acid_C18_2": 3.60714,
            "octadecatrienoic_acid_C18_3": 0.192857,
            "others": 0.000000,
        },
        "others": 0.000000,
    },
    "ashes": {
        "others": 0.000000,
    },
    "carbs": {
        "fibers": {
            "others": 0.000000,
        },
        "others": 0.000000,
    },
    "vitamins": {
        "vitamin_e_alpha_tocopherol": 41.0714,
        "vitamin_k1_phylloquinone": 0.00571429,
    },
    "others": {},
    "water": 0.000000,
}
