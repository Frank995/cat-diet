"""Nutritional values of dried Spirulina (Arthrospira spp.) based on:

- nutritionvalue.org — "Seaweed, dried, spirulina"
  https://www.nutritionvalue.org/Seaweed%2C_dried%2C_spirulina_nutritional_value.html
  (normalized from the source's 112 g / 1 cup serving to 100 g)
- Marjanović et al. (2024) "Bioactive Compounds from Spirulina spp.—
  Nutritional Value, Extraction, and Application in Food Industry"
  Separations 11, 257. https://doi.org/10.3390/separations11090257
- Dillon, Phan Phuc & Dubacq (1995) "Nutritional Value of the Alga
  Spirulina", World Rev. Nutr. Diet. 77:32-46 (S. platensis / S. maxima
  composition tables)


Basis: 100 g dried spirulina powder.


Units:
    proteins, fats, carbs, water : g / 100 g
    ashes, vitamins, others      : mg / 100 g


Notes:
    - Ranges reported by sources (e.g., "60-70% protein") were converted to
      midpoints before averaging across sources; nutrients reported by a single
      source were used as-is.
    - Notable cross-source disagreements exist for phosphorus (118 vs.
      825 mg/100 g) and sodium (1047 vs. 34 mg/100 g)—likely reflecting added
      salt/seawater cultivation in commercial powder vs. freshwater Zarrouk-
      medium figures from Dillon.
    - Beta-carotene varied substantially (0.34, ~150-200, and ~250 mg/100 g) and
      was averaged to a rough midpoint (~130 mg/100 g); treat this value as
      low-confidence.
    - Cystine converted to cysteine (x 1.0084)
"""

TABLE = {
    "proteins": {
        "histidine": 1.15200,
        "isoleucine": 3.11500,
        "leucine": 5.02600,
        "lysine": 2.91900,
        "methionine": 1.18900,
        "phenylalanine": 2.97200,
        "threonine": 3.12100,
        "tryptophan": 0.76700,
        "valine": 3.98500,
        "alanine": 4.75800,
        "arginine": 4.26100,
        "aspartic_acid": 6.05300,
        "cysteine": 0.5384856,
        "glutamic_acid": 7.98500,
        "glycine": 3.13300,
        "proline": 2.44100,
        "serine": 2.93700,
        "tyrosine": 2.67800,
        "others": 3.47400,
    },
    "fats": {
        "saturated": {
            "myristic_acid_C14_0": 0.070500,
            "palmitic_acid_C16_0": 2.09400,
            "stearic_acid_C18_0": 0.072000,
            "others": 0.254000,
        },
        "monounsaturated": {
            "palmitoleic_acid_C16_1_n7": 0.423000,
            "octadecenoic_acid_C18_1": 0.312000,
            "others": 0.000000,
        },
        "polyunsaturated": {
            "octadecadienoic_acid_C18_2": 0.898000,
            "octadecatrienoic_acid_C18_3": 0.959000,
            "others": 0.000000,
        },
        "others": 1.11900,
    },
    "ashes": {
        "calcium": 118.500,
        "copper": 6.09800,
        "iron": 40.2500,
        "magnesium": 180.000,
        "manganese": 2.02500,
        "phosphorus": 471.500,
        "potassium": 1399.00,
        "selenium": 0.00720000,
        "sodium": 540.500,
        "zinc": 2.65000,
        "chloride": 420.000,
        "others": 4730.20,
    },
    "carbs": {
        "fibers": {
            "others": 2.53000,
        },
        "sugars": 3.10000,
        "others": 10.1000,
    },
    "vitamins": {
        "vitamin_a_beta_carotene": 128.000000,
        "vitamin_b1_thiamin": 3.08000,
        "vitamin_b2_riboflavin": 3.72500,
        "vitamin_b3_niacin": 11.4600,
        "vitamin_b5_pantothenic_acid": 2.10000,
        "vitamin_b6_pyridoxine": 0.369000,
        "vitamin_b9_folate": 0.0695000,
        "vitamin_b12_cobalamin": 0.101000,
        "vitamin_c_ascorbic_acid": 10.0900,
        "vitamin_e_alpha_tocopherol": 5.00000,
        "vitamin_j_choline": 65.9800,
        "vitamin_k1_phylloquinone": 0.0255400,
    },
    "others": {
        "phycocyanin": 17000.0,
        "chlorophyll_a": 1000.00,
    },
    "water": 6.39000,
}
