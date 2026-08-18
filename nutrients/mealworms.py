"""Nutritional values of mealworms (Tenebrio molitor) averaged from:

- Jankauskienė, Agnė, et al. "Nutritional composition and safety parameters
  of mealworms (Tenebrio molitor) reared on substrates derived from by-products."
  Applied Sciences 14.7 (2024): 2744.
- Zhang, Guoqiang, et al. "Nutritional value and advances of mealworm (Tenebrio molitor)
  as a sustainable functional ingredient in bakery products: A key step toward sustainable diets."
  Future Foods 12 (2025): 100716.

Basis: 100 g dry matter of whole larvae. No source reports residual
moisture for the pooled material, so water is not given.

Units:
    proteins, fats, carbs, water : g / 100 g
    ashes, vitamins, others      : mg / 100 g
"""

TABLE = {
    "proteins": {
        "alanine": 3.467500,
        "aspartic_acid": 3.802500,
        "cysteine": 0.335293,
        "glutamic_acid": 5.567500,
        "glycine": 2.592500,
        "histidine": 1.697500,
        "isoleucine": 1.945000,
        "leucine": 3.450000,
        "lysine": 2.727500,
        "methionine": 0.562500,
        "phenylalanine": 1.675000,
        "proline": 2.920000,
        "serine": 1.587500,
        "threonine": 1.362500,
        "tyrosine": 3.535000,
        "valine": 2.800000,
        "others": 12.562500,
    },
    "fats": {
        "saturated": {
            "lauric_acid": 0.665932,
            "palmitic_acid": 4.997220,
            "margaric_acid": 1.098725,
            "stearic_acid": 1.130385,
            "arachidic_acid": 0.360182,
            "behenic_acid": 0.360182,
            "others": 0.000000,
        },
        "monounsaturated": {
            "myristoleic_acid": 0.048557,
            "palmitoleic_acid": 0.585667,
            "oleic_acid": 10.681434,
            "gondoic_acid": 0.430480,
            "erucic_acid": 0.446014,
            "others": 0.000000,
        },
        "polyunsaturated": {
            "linoleic_acid_trans": 0.105994,
            "linoleic_acid": 5.333136,
            "alpha_linolenic_acid": 0.018209,
            "gamma_linolenic_acid": 0.195493,
            "dihomo_alpha_linolenic_acid": 1.442747,
            "dihomo_gamma_linolenic_acid": 0.511174,
            "adrenic_acid": 0.672208,
            "timnodonic_acid": 0.504542,
            "cervonic_acid": 0.546902,
            "others": 0.000000,
        },
        "others": 0.000000,
    },
    "ashes": {
        "calcium": 118.637,
        "copper": 6.05750,
        "iron": 10.8480,
        "magnesium": 248.472,
        "manganese": 3.72200,
        "phosphorus": 587.550,
        "potassium": 1000.36,
        "selenium": 0.163025,
        "sodium": 197.757,
        "zinc": 21.1850,
        "others": 1901.92,
    },
    "carbs": {
        "fibers": {
            "others": 9.03500,
        },
        "others": 0.000000,
    },
    "vitamins": {
        "vitamin_e_alpha_tocopherol": 0.889828,
        "vitamin_e_beta_tocopherol": 0.243592,
        "vitamin_e_gamma_tocopherol": 2.44022,
        "vitamin_e_delta_tocopherol": 0.133259,
    },
    "others": {
        "squalene": 0.604682,
        "apigenin": 0.269384,
        "gallic_acid": 4.63000,
        "vanillic_acid": 1.36000,
        "protocatechuic_aldehyde": 23.1900,
        "gentisic_acid": 0.150000,
        "ellagic_acid": 0.260000,
        "caffeic_acid": 0.0600000,
        "ferulic_acid": 0.540000,
        "p_coumaric_acid": 0.0600000,
        "sinapic_acid": 0.150000,
        "quercetin_3_o_glucoside": 0.400000,
        "rutin": 0.400000,
    },
    "water": 0.000000
}
