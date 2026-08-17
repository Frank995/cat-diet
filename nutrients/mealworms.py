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
    - NutritionValue values were converted from an 85 g serving to 100 g before
      averaging with Jensen et al.
    - NutritionValue reports cystine rather than cysteine. The cystine value
      was converted using 1 g cystine = 1.0084 g cysteine before averaging.
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
            "lauric_acid_C12_0": 0.665932,
            "palmitic_acid_C16_0": 4.997220,
            "margaric_acid_C17_0": 1.098725,
            "stearic_acid_C18_0": 1.130385,
            "arachidic_acid_C20_0": 0.360182,
            "behenic_acid_C22_0": 0.360182,
            "others": 0.000000,
        },
        "monounsaturated": {
            "myristoleic_acid_C14_1_n5": 0.048557,
            "palmitoleic_acid_C16_1_n7": 0.585667,
            "oleic_acid_C18_1_n9": 10.681434,
            "eicosenoic_acid_C20_1": 0.430480,
            "erucic_acid_C22_1_n9": 0.446014,
            "others": 0.000000,
        },
        "polyunsaturated": {
            "linoleic_acid_C18_2_n6_trans": 0.105994,
            "linoleic_acid_C18_2_n6": 5.333136,
            "alpha_linolenic_acid_C18_3_n3": 0.018209,
            "gamma_linolenic_acid_C18_3_n6": 0.195493,
            "eicosatrienoic_acid_C20_3_n3": 1.442747,
            "dihomo_gamma_linolenic_acid_C20_3_n6": 0.511174,
            "adrenic_acid_C22_4_n6": 0.672208,
            "eicosapentaenoic_acid_C20_5_n3": 0.504542,
            "docosahexaenoic_acid_C22_6_n3": 0.546902,
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
        "2_5_dihydroxybenzoic_acid": 0.150000,
        "ellagic_acid": 0.260000,
        "caffeic_acid": 0.0600000,
        "ferulic_acid": 0.540000,
        "p_coumaric_acid": 0.0600000,
        "sinapic_acid": 0.150000,
        "quercetin_3_o_glucoside": 0.400000,
        "rutin": 0.400000,
    },
}
