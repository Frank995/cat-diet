"""Nutritional values of chicken eggshells based on:

- Schaafsma, A., et al. "Mineral, amino acid, and hormonal composition
  of chicken eggshell powder and the evaluation of its use in human nutrition."
  Poultry science 79.12 (2000): 1833-1838.

Basis: 100 g demembranized chicken eggshell, dry matter.

Units:
    proteins, fats, carbs, water : g / 100 g
    ashes, others                : mg / 100 g

Notes:
    - Trace elements reported below detection limits in the source
      (Al, B, Cd, Hg, V, Pb) have been omitted to avoid misrepresenting
      threshold limits as exact nutritional content.
"""

TABLE = {
    "proteins": {
        "glycine": 0.142200,
        "arginine": 0.194400,
        "others": 1.46340,
    },
    "fats": {
        "saturated": {
            "others": 0.000000,
        },
        "monounsaturated": {
            "others": 0.000000,
        },
        "polyunsaturated": {
            "others": 0.000000,
        },
        "others": 0.000000,
    },
    "ashes": {
        "calcium": 40100.0,
        "magnesium": 450.000,
        "phosphorus": 99.0000,
        "strontium": 37.2000,
        "iron": 2.24000,
        "zinc": 0.513000,
        "copper": 0.770000,
        "fluorine": 0.375000,
        "chromium": 0.012000,
        "selenium": 0.002350,
        "others": 57800.0,
    },
    "carbs": {
        "fibers": {
            "others": 0.000000,
        },
        "others": 0.000000,
    },
    "others": {},
    "water": 0.000000,
}
