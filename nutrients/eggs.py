"""Nutritional values of organic eggs averaged from:

Filipiak-Florkiewicz, Agnieszka, et al. "The quality of eggs (organic and nutraceutical vs. conventional) and their technological properties." Poultry Science 96.7 (2017): 2480-2490.
Çakmak, Meltem, Fikret Karatas, and Dursun Özer. "Investigation of amino acids content of different poultry eggs types." MW Journal of Science 1.2 (2024): 10-20.
Medina-Cruz, María F., et al. "Nutritional aspects, production and viability in the market of organic chicken eggs." Food Chemistry Advances 4 (2024): 100595.
Caffa, Irene, et al. "Nutritional aspects of eggs for a healthy and sustainable consumption: a narrative review." Food Science & Nutrition 13.9 (2025): e70285.
https://www.nutritionvalue.org (egg yolk and egg white)

Basis: 100 g whole egg (yolk + white recombined), wet weight.

Units:
    proteins, fats, carbs, water : g / 100 g
    ashes, vitamins, others      : mg / 100 g
"""

TABLE = {
    "proteins": {
        "alanine": 0.651726,
        "arginine": 0.571495,
        "asparagine": 0.407333,
        "aspartic_acid": 1.31356,
        "cysteine": 0.316411,
        "glutamic_acid": 1.72276,
        "glutamine": 0.349000,
        "glycine": 0.437913,
        "histidine": 0.255911,
        "isoleucine": 0.662486,
        "leucine": 1.10688,
        "lysine": 0.791628,
        "methionine": 0.439078,
        "phenylalanine": 0.670008,
        "proline": 0.427798,
        "serine": 0.688578,
        "threonine": 0.416534,
        "tryptophan": 0.225826,
        "tyrosine": 0.411270,
        "valine": 0.765207,
        "others": 1.43530,
    },
    "fats": {
        "saturated": {
            "caprylic_acid_C8_0": 0.00392157,
            "capric_acid_C10_0": 0.000980392,
            "lauric_acid_C12_0": 0.00167039,
            "myristic_acid_C14_0": 0.0350435,
            "pentadecanoic_acid_C15_0": 0.00581039,
            "palmitic_acid_C16_0": 2.35798,
            "margaric_acid_C17_0": 0.0168318,
            "stearic_acid_C18_0": 0.641001,
            "arachidic_acid_C20_0": 0.00452098,
            "behenic_acid_C22_0": 0.0117647,
            "lignoceric_acid_C24_0": 0.00392157,
            "others": 0.000000,
        },
        "monounsaturated": {
            "myristoleic_acid_C14_1_n5": 0.00736000,
            "palmitoleic_acid_C16_1_n7": 0.321041,
            "hexadecenoic_acid_C16_1_n9": 0.0866300,
            "heptadecenoic_acid_C17_1": 0.0119600,
            "oleic_acid_C18_1_n9": 3.74419,
            "vaccenic_acid_C18_1_n7": 0.303535,
            "eicosenoic_acid_C20_1": 0.0204629,
            "erucic_acid_C22_1_n9": 0.00392157,
            "others": 0.000000,
        },
        "polyunsaturated": {
            "linoleic_acid_C18_2_n6": 1.23586,
            "conjugated_linoleic_acid_C18_2": 0.00542837,
            "gamma_linolenic_acid_C18_3_n6": 0.00788670,
            "alpha_linolenic_acid_C18_3_n3": 0.0504098,
            "eicosadienoic_acid_C20_2": 0.0101200,
            "dihomo_gamma_linolenic_acid_C20_3_n6": 0.00736000,
            "arachidonic_acid_C20_4_n6": 0.0956145,
            "eicosapentaenoic_acid_C20_5_n3": 0.00167039,
            "adrenic_acid_C22_4_n6": 0.00920000,
            "docosapentaenoic_acid_C22_5_n3": 0.00759000,
            "docosahexaenoic_acid_C22_6_n3": 0.0313937,
            "others": 0.000000,
        },
        "others": 0.102328,
    },
    "ashes": {
        "calcium": 14.5492,
        "copper": 0.0147025,
        "iron": 0.483892,
        "magnesium": 2.99750,
        "manganese": 0.0124320,
        "phosphorus": 140.000,
        "potassium": 46.6025,
        "selenium": 0.0320000,
        "sodium": 42.7317,
        "zinc": 0.294977,
        "others": 1050.50,
    },
    "carbs": {
        "sugars": 0.5811055,
        "fibers": {
            "others": 0.000000,
        },
        "others": 0.864127,
    },
    "vitamins": {
        "vitamin_a_retinol": 0.123667,
        "vitamin_a_alpha_carotene": 0.0126667,
        "vitamin_a_beta_carotene": 0.0293333,
        "vitamin_a_beta_cryptoxanthin": 0.0110000,
        "vitamin_b1_thiamin": 0.0608437,
        "vitamin_b2_riboflavin": 0.469400,
        "vitamin_b3_niacin": 0.0785502,
        "vitamin_b5_pantothenic_acid": 1.12335,
        "vitamin_b6_pyridoxine": 0.119727,
        "vitamin_b9_folate": 0.0513333,
        "vitamin_b12_cobalamin": 0.000707665,
        "vitamin_d3_cholecalciferol": 0.00180392,
        "vitamin_e_alpha_tocopherol": 0.862745,
        "vitamin_e_beta_tocopherol": 0.0196078,
        "vitamin_e_gamma_tocopherol": 0.450980,
        "vitamin_e_delta_tocopherol": 0.0196078,
        "vitamin_e_alpha_tocotrienol": 0.0196078,
        "vitamin_j_choline": 274.141,
        "vitamin_k1_phylloquinone": 0.000196078,
    },
    "others": {
        "cholesterol": 361.667,
        "betaine": 0.594177,
        "lutein_zeaxanthin": 0.364667,
    },
    "water": 74.0538,
}
