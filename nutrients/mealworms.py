"""Nutritional values of mealworms (Tenebrio molitor) averaged from:

Jankauskienė, Agnė, et al. "Nutritional composition and safety parameters of mealworms (Tenebrio molitor) reared on substrates derived from by-products." Applied Sciences 14.7 (2024): 2744.
Zhang, Guoqiang, et al. "Nutritional value and advances of mealworm (Tenebrio molitor) as a sustainable functional ingredient in bakery products: A key step toward sustainable diets." Future Foods 12 (2025): 100716.

Basis: 100 g dry matter of whole larvae. No source reports residual
moisture for the pooled material, so water is not given.

Units:
    proteins, fats, carbs, water : g / 100 g
    ashes, vitamins, others      : mg / 100 g

Methodology:
- Macro totals: the review's table was used as the literature-level source
  and the Appl. Sci. study as the second source, avoiding double-counting
  the Jankauskiene study that also appears in the review.
- Amino acids: the Appl. Sci. values are directly on dry matter; the
  review's arginine and tryptophan are per 100 g protein and were
  converted to dry matter using the averaged protein level. proteins.others
  is the unassigned remainder of total protein.
- Fatty acids: the directly measured larval profile from Appl. Sci. was
  combined with the review's oil profile and the composite profile was
  normalized to 100% of total fat. This is an approximation, because the
  review's fatty-acid measurements come from extracted mealworm oil rather
  than intact dry larvae. The reported subclass totals were dropped since
  the individual acids sum to them exactly.
- Oil-only micronutrients were approximated as
  concentration_in_whole_mealworm ~ concentration_in_oil x oil_fraction,
  treating the reported oil fraction as total extractable fat (the averaged
  fat content was used). This applies to the tocopherols, carotenoids,
  squalene and apigenin, which therefore remain inferred rather than
  directly measured whole-larva values.
- Vitamin E: only the four tocopherol homologues are kept. The review's
  "total tocopherols" figure (4.32018 mg/100 g) exceeds their sum
  (3.70690 mg/100 g); the 0.61 mg residual is not attributable to a named
  homologue and was dropped rather than kept alongside the parts.
- Fatty acid naming: C22:1 n-9 is erucic acid, C20:3 n-6 is
  dihomo-gamma-linolenic acid and C22:4 n-6 is adrenic acid. The reported
  C20:1, C17:1, C16:2 and C18:3 (unspecified family) have no resolvable
  omega assignment, so IUPAC-style names are kept for them.
- Carotenoids are reported as an unspeciated total and are largely
  non-provitamin A in insects, so they are listed under others.
- The phenolic compounds are kept as reported by the Appl. Sci. study.
"""

TABLE = {
    "proteins": {
        "alanine": 3.46750,
        "arginine": 3.08598,
        "aspartic_acid": 3.80250,
        "cystine": 0.332500,
        "glutamic_acid": 5.56750,
        "glycine": 2.59250,
        "histidine": 1.69750,
        "isoleucine": 1.94500,
        "leucine": 3.45000,
        "lysine": 2.72750,
        "methionine": 0.562500,
        "phenylalanine": 1.67500,
        "proline": 2.92000,
        "serine": 1.58750,
        "threonine": 1.36250,
        "tryptophan": 0.941096,
        "tyrosine": 3.53500,
        "valine": 2.80000,
        "others": 6.95584,
    },
    "fats": {
        "saturated": {
            "lauric_acid_C12_0": 0.377563,
            "tridecanoic_acid_C13_0": 0.00941400,
            "myristic_acid_C14_0": 0.485654,
            "pentadecanoic_acid_C15_0": 0.0192757,
            "palmitic_acid_C16_0": 4.99473,
            "margaric_acid_C17_0": 0.479883,
            "stearic_acid_C18_0": 1.05418,
            "arachidic_acid_C20_0": 0.168217,
        },
        "monounsaturated": {
            "myristoleic_acid_C14_1_n5": 0.0562589,
            "palmitoleic_acid_C16_1_n7": 0.523478,
            "heptadecenoic_acid_C17_1": 0.0181550,
            "oleic_acid_C18_1_n9": 10.2756,
            "eicosenoic_acid_C20_1": 0.219545,
            "erucic_acid_C22_1_n9": 0.354365,
        },
        "polyunsaturated": {
            "hexadecadienoic_acid_C16_2": 0.0285778,
            "linoleic_acid_C18_2_n6": 6.18827,
            "linoleic_acid_C18_2_n6_trans": 0.123725,
            "gamma_linolenic_acid_C18_3_n6": 0.166760,
            "octadecatrienoic_acid_C18_3": 0.154320,
            "eicosatrienoic_acid_C20_3_n3": 1.11285,
            "dihomo_gamma_linolenic_acid_C20_3_n6": 0.423624,
            "eicosapentaenoic_acid_C20_5_n3": 0.402106,
            "adrenic_acid_C22_4_n6": 0.546676,
            "docosahexaenoic_acid_C22_6_n3": 0.474727,
        },
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
        "others": 7.20250,
    },
    "vitamins": {
        "vitamin_e_alpha_tocopherol": 0.889828,
        "vitamin_e_beta_tocopherol": 0.243592,
        "vitamin_e_gamma_tocopherol": 2.44022,
        "vitamin_e_delta_tocopherol": 0.133259,
    },
    "others": {
        "total_carotenoids": 0.391181,
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