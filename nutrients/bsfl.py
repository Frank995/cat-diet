"""Nutritional values of black soldier fly larvae (Hermetia illucens) averaged from:

Lu, Shengyong, et al. "Nutritional composition of black soldier fly larvae (Hermetia illucens L.) and its potential uses as alternative protein sources in animal diets: A review." Insects 13.9 (2022): 831.
Zulkifli, Nor Fatin Najihah Mohamad, et al. "Nutritional value of black soldier fly (Hermetia illucens) larvae processed by different methods." PloS one 17.2 (2022): e0263924.

Basis: 100 g dry matter of whole larvae (residual moisture 5.21 g / 100 g).

Units:
    proteins, fats, carbs, water : g / 100 g
    ashes, vitamins, others      : mg / 100 g

Methodology:
- Protein: the review's full-fat macro protein was averaged with the PLOS
  dry-matter protein value, giving 41.735 g / 100 g DM. The PLOS amino
  acids (% DM) were averaged across SPR/OVN1/OVN2 and sum to 40.41 g;
  tryptophan was taken from the review, which reports it explicitly on a
  dry-matter basis. proteins.others is the remaining unassigned protein so
  that the amino-acid section reconciles exactly with total protein.
- Fat: the review's full-fat lipid was averaged with the PLOS lipid values,
  giving 33.0742 g / 100 g DM. The PLOS table reports each fatty acid as %
  of total fat, so each sample was converted using its own measured lipid
  content before averaging. fats.others (2.20639 g) is therefore the
  genuinely unassigned/non-analysed fraction needed to reach total fat.
  Stearidonic acid was not detected and is omitted.
- Ash: total ash is 7910.83 mg / 100 g DM. The PLOS mineral table is in
  mg/kg, so it was divided by 10 to get mg / 100 g; ashes.others is the
  residual 3008.02 mg.
- Carbohydrate is the compositional residual after protein, fat and ash:
  17.2800 g / 100 g DM. The review gives crude fibre 95.4 g/kg and chitin
  61.7 g/kg DM, hence 6.17 g chitin + 3.075 g other fibre, leaving 8.035 g
  non-fibre carbohydrate.
- Vitamins are reported directly by PLOS in mg / 100 g. Vitamin A /
  beta-carotene was not detected in any of the three samples and is
  omitted; B1 and B2 were detected in two samples, vitamin C in all three.
- Nucleotides are reported by PLOS as % of protein and were converted to
  mg / 100 g DM using that paper's average protein concentration.
- Fatty acid naming: C10:0 is capric acid and C20:3 n-6 is
  dihomo-gamma-linolenic acid; C20:1 is reported without an omega family.
"""

TABLE = {
    "proteins": {
        "alanine": 3.06333,
        "arginine": 2.20000,
        "aspartic_acid": 4.31333,
        "cysteine": 0.143333,
        "glutamic_acid": 5.42333,
        "glycine": 0.196667,
        "histidine": 2.51667,
        "hydroxyproline": 0.0300000,
        "isoleucine": 2.14667,
        "leucine": 3.26667,
        "lysine": 2.97000,
        "methionine": 0.870000,
        "phenylalanine": 1.81333,
        "proline": 2.65667,
        "serine": 1.83000,
        "threonine": 1.73667,
        "tryptophan": 0.623333,
        "tyrosine": 2.46667,
        "valine": 2.76667,
        "others": 1.29833,
    },
    "fats": {
        "saturated": {
            "capric_acid_C10_0": 0.136813,
            "lauric_acid_C12_0": 9.73405,
            "myristic_acid_C14_0": 2.71780,
            "palmitic_acid_C16_0": 7.16744,
            "stearic_acid_C18_0": 1.13241,
            "heneicosanoic_acid_C21_0": 0.0777087,
            "behenic_acid_C22_0": 0.0332453,
        },
        "monounsaturated": {
            "palmitoleic_acid_C16_1_n7": 0.728945,
            "oleic_acid_C18_1_n9": 3.99473,
            "eicosenoic_acid_C20_1": 0.0588187,
        },
        "polyunsaturated": {
            "linoleic_acid_C18_2_n6": 3.31156,
            "alpha_linolenic_acid_C18_3_n3": 0.280013,
            "eicosadienoic_acid_C20_2_n6": 1.40730,
            "dihomo_gamma_linolenic_acid_C20_3_n6": 0.0485893,
            "eicosapentaenoic_acid_C20_5_n3": 0.0255733,
            "docosahexaenoic_acid_C22_6_n3": 0.0127867,
        },
        "others": 2.20639,
    },
    "ashes": {
        "calcium": 2023.23,
        "copper": 1.97233,
        "iron": 43.4490,
        "magnesium": 314.424,
        "manganese": 14.5853,
        "phosphorus": 763.333,
        "potassium": 1241.98,
        "sodium": 416.592,
        "zinc": 83.2353,
        "others": 3008.02,
    },
    "carbs": {
        "fibers": {
            "chitin": 6.17000,
            "others": 3.07500,
        },
        "others": 8.03500,
    },
    "vitamins": {
        "vitamin_b1_thiamin": 1.32667,
        "vitamin_b2_riboflavin": 9.91333,
        "vitamin_c_ascorbic_acid": 0.260000,
    },
    "others": {},
    "water": 5.21000,
}
