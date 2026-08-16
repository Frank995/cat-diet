"""Nutritional values of algal oil from:

https://www.norsan.it (Foten ALga Delicata)

Basis: 100 g oil, calculated from label data.
Energy: Not explicitly reported on label (typically ~900 kcal / 100 g for oils).

Units:
    proteins, fats, carbs, water : g / 100 g
    ashes, vitamins, others      : mg / 100 g

Notes:
- The label gives percentages which are interpreted as g / 100 g.
- Total components sum to 100.8 g (Fats 99.5 + Proteins 0.5 + Ashes 0.5
  + Fibers 0.3) due to Weende analysis overlapping.
- Omega-3 total is 42.35 g, but EPA (11.5), DHA (23.1), and DPA (2.3) sum to 36.9 g.
  The remaining 5.45 g of unspecified Omega-3s, plus the 57.15 g of other unspecified fats
  (from the olive and sunflower oils base), are grouped together into fats.others (total 62.6 g).
- Ashes ("Ceneri grezze") are 0.5 g / 100 g, which converts to 500 mg / 100 g to match
  the requested unit.
- Vitamins were reported per 1000 ml. Using an estimated oil density of 0.92 g/ml (1000 ml = 920 g),
  the values were converted to a 100 g basis:
    - Vitamin D3: 20,000 IU / 920 g = 2173.9 IU / 100 g.
      Converted to mg: 2173.9 IU * 0.000025 mg/IU = ~0.0543 mg / 100 g.
    - Vitamin E (RRR d-alpha-tocopherol): 894 IU / 920 g = 97.17 IU / 100 g.
      Converted to mg: 97.17 IU * 0.67 mg/IU = ~65.106 mg / 100 g.
"""

TABLE = {
    "proteins": {
        "others": 0.500000,
    },
    "fats": {
        "polyunsaturated": {
            "eicosapentaenoic_acid_C20_5_n3": 11.5000,
            "docosapentaenoic_acid_C22_5_n3": 2.3000,
            "docosahexaenoic_acid_C22_6_n3": 23.1000,
        },
        "others": 62.6000,
    },
    "ashes": {
        "others": 500.000,
    },
    "carbs": {
        "fibers": {
            "others": 0.300000,
        },
        "others": 0.000000,
    },
    "vitamins": {
        "vitamin_d3_cholecalciferol": 0.054348,
        "vitamin_e_alpha_tocopherol": 65.1065,
    },
    "others": {},
    "water": 0.000000,
}
