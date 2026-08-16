"""Nutritional values of the alga spirulina (Arthrospira / Spirulina platensis &
S. maxima) averaged from:

Dillon, J.C., Anh Phan Phuc, and J.P. Dubacq. "Nutritional value of the alga
    Spirulina." Plants in Human Nutrition. World Rev Nutr Diet 77 (1995): 32-46.
Marjanovic, B., et al. "Bioactive Compounds from Spirulina spp. - Nutritional
    Value, Extraction, and Application in Food Industry." Separations 11 (2024): 257.
USDA / nutritionvalue.org entry "Seaweed, dried, spirulina" (1 cup = 112 g),
    rescaled to 100 g.

Basis: 100 g dried spirulina powder as sold (water 6.39 g / 100 g). The three
sources were averaged component-by-component (ranges taken at their midpoint);
the four dry macro-fractions (protein, fat, carbohydrate, ash) were then scaled
by a single common factor (1.0205) so that protein + fat + carbs + ash + water
closes at exactly 100 g.

Units:
    proteins, fats, carbs, water : g / 100 g
    ashes, vitamins, others      : mg / 100 g

Notes:
- Macro-fraction inputs disagree widely: protein 57.5-71 %, fat 3.9-8.6 %,
  carbohydrate 8.5-23.9 %, ash 6.2-13 %. Carbohydrate is a "by difference"
  figure in all three sources and is the least reliable number in the table
  (Dillon ~8-13 %, Marjanovic 15-25 %, USDA 23.9 %); the averaged 15.4 g should
  be treated as an order-of-magnitude estimate only.
- Amino acids were handled as fractions of crude protein (Dillon Table 3, three
  columns, mg/g crude protein N x 6.25; plus the USDA profile), averaged, and
  re-multiplied by the final protein figure. Dillon's isoleucine 18 mg/g and
  tryptophan 3 mg/g columns are almost certainly analytical outliers and pull
  those two entries down. proteins.others (1.79 g) is the non-amino-acid
  nitrogen remainder; note that ~15 % of spirulina crude protein is
  non-protein nitrogen (nucleic acids, etc.), so the true residual is larger
  than what the amino-acid sums leave.
- Phycocyanin (14-20 % of dry weight) is a protein and is therefore already
  contained in the proteins block, not listed separately there.
- Fatty acids were averaged as % of total fatty acids (USDA profile; Dillon
  Table 5 for S. platensis: Sat 46, 16:1 10, 18:1 5, 18:2 12, 18:3w6 21;
  Marjanovic: 16:0 44.5, 18:2 14.9, 18:3w6 13.4) and then normalised so the
  sub-items sum exactly to total fat. This implicitly assigns the non-fatty-acid
  part of the lipids (glycerol + galactose/sulfoquinovose head groups of MGDG,
  DGDG, SQDG, PG - which make up most of spirulina lipid) proportionally to the
  fatty acids; individual acid values are therefore ~1.4x their true mass.
- Spirulina's 18:3 is gamma-linolenic acid (18:3 n-6), not alpha-linolenic acid;
  it is the single most distinctive nutrient here (~1 g / 100 g). No n-3 PUFA
  is present in S. platensis.
- Irreconcilable mineral conflicts, averaged anyway and flagged:
  phosphorus (Dillon 825 vs USDA 118 mg) and sodium (Dillon 34 vs USDA 1049 mg
  - the USDA sample clearly carries processing/harvest salt). Chloride and
  selenium/copper are single-source values.
- Mercury: Dillon cites ~9.5 ppm (= 0.95 mg/100 g) from Johnson & Shubert but
  also cites Slotton et al., who found only trace levels with a better method.
  The two are irreconcilable by more than an order of magnitude, so no mercury
  key is given.
- ashes.others (5.42 g) is total ash minus all quantified elements; it is large
  because ash includes the counter-ions (carbonate/bicarbonate, sulfate,
  silicate) of the highly alkaline growth medium, which no source quantifies.
- vitamin_b12: USDA reports 0 mcg (modern assays distinguish inactive
  pseudo-cobalamin); Dillon's Table 8 average (0.202 mg/100 g) is kept because
  it is the only quantitative source, but it is largely NOT bioavailable B12.
- beta_carotene: from Dillon only (0.15-0.20 % dry weight and 700-1700 ug/g,
  averaged to 163 mg/100 g). USDA lists 0.342 mg/100 g - a ~500x discrepancy,
  presumably a bleached/aged sample; the USDA value was discarded.
- carbs.fiber is "crude fiber" (Dillon 3 % and 1 %) averaged with USDA total
  dietary fiber - two different analytical definitions. carbs.others is
  dominated by the glycogen-like branched glucan of spirulina plus the ~1 %
  glucose polysaccharide, and absorbs all the by-difference error.
- "others" entries are informational overlaps with the blocks above (pigments,
  nucleic acids); they must NOT be added to the 100 g balance.
"""

TABLE = {
    "proteins": {
        "alanine": 5.07880,
        "arginine": 4.49847,
        "aspartic_acid": 6.43763,
        "cysteine": 0.521048,
        "glutamic_acid": 8.12940,
        "glycine": 3.28301,
        "histidine": 1.23027,
        "isoleucine": 3.20187,
        "leucine": 5.27839,
        "lysine": 2.99142,
        "methionine": 1.25939,
        "phenylalanine": 3.19360,
        "proline": 2.57395,
        "serine": 3.03182,
        "threonine": 3.32681,
        "tryptophan": 0.719928,
        "tyrosine": 2.83719,
        "valine": 4.38590,
        "others": 1.79280,
    },
    "fats": {
        "saturated": {
            "myristic_acid_C14_0": 0.0835514,
            "palmitic_acid_C16_0": 2.68720,
            "stearic_acid_C18_0": 0.0855408,
        },
        "monounsaturated": {
            "palmitoleic_acid_C16_1_n7": 0.483604,
            "oleic_acid_C18_1_n9": 0.344003,
        },
        "polyunsaturated": {
            "linoleic_acid_C18_2_n6": 1.00544,
            "gamma_linolenic_acid_C18_3_n6": 0.996177,
            "alpha_linolenic_acid_C18_3_n3": 0.0,
        },
        "others": 0.155504,
    },
    "ashes": {
        "potassium": 1399.00,
        "phosphorus": 471.500,
        "sodium": 541.000,
        "chloride": 420.000,
        "magnesium": 180.000,
        "calcium": 118.500,
        "iron": 40.2500,
        "copper": 6.09821,
        "zinc": 2.65000,
        "manganese": 2.02500,
        "selenium": 0.00719643,
        "others": 5424.52,
    },
    "carbs": {
        "fibers": {
            "crude_fiber": 2.53274,
            "others": 0.0,
        },
        "sugars": 3.09821,
        "others": 9.75790,
    },
    "vitamins": {
        "vitamin_a_beta_carotene": 163.333,
        "vitamin_b1_thiamine": 3.08018,
        "vitamin_b2_riboflavin": 3.72482,
        "vitamin_b3_niacin": 11.4598,
        "vitamin_b5_pantothenic_acid": 2.10393,
        "vitamin_b6_pyridoxine": 0.369143,
        "vitamin_b9_folate": 0.0695000,
        "vitamin_b12_cobalamin": 0.202000,
        "vitamin_c_ascorbic_acid": 10.0893,
        "vitamin_e_alpha_tocopherol": 5.00000,
        "vitamin_j_choline": 65.9821,
        "vitamin_k1_phylloquinone": 0.0255357,
    },
    "others": {
        "phycocyanin": 17000.0,
        "chlorophyll_a": 1000.0,
        "xanthophylls": 150.0,
    },
    "water": 6.39286,
}
