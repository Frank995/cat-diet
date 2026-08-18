"""Nutritional values of algal oil from:

- https://www.norsan.it/product/foten-alga-delicata/

Basis: 100 g oil, calculated from label data.

Units:
    proteins, fats, carbs, water : g / 100 g
    ashes, vitamins, others      : mg / 100 g

Notes:
    - Total on the label was 100,8 g. Values were scaled proportionally.
    - Added vitamins were computed on a 1000 ml base. Conversion was set
      to 1000 ml = 920 g.
"""

TABLE = {
    "proteins": {
        "others": 0.496032,
    },
    "fats": {
        "saturated": {
            "others": 0.000000,
        },
        "monounsaturated": {
            "others": 0.000000,
        },
        "polyunsaturated": {
            "timnodonic_acid": 11.4087,
            "osbond_acid": 2.28175,
            "cervonic_acid": 22.9167,
            "others": 5.40665,
        },
        "others": 56.6965,
    },
    "ashes": {
        "others": 49.6032,
    },
    "carbs": {
        "fibers": {
            "others": 0.297619,
        },
        "others": 0.000000,
    },
    "vitamins": {
        "vitamin_d3": 0.054348,
        "vitamin_e_alpha_tocopherol": 65.1065,
    },
    "others": {},
    "water": 0.000000,
}
