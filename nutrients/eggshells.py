"""Nutritional values of chicken eggshells averaged from:

Ajala, E. O., et al. "Characterization and evaluation of chicken eggshell for use as a bio-resource." Arid Zone Journal of Engineering, Technology and Environment 14.1 (2018): 26-40.
Schaafsma, A., et al. "Mineral, amino acid, and hormonal composition of chicken eggshell powder and the evaluation of its use in human nutrition." Poultry science 79.12 (2000): 1833-1838.

Basis: 100 g demembranized chicken eggshell, dry matter (moisture-free).
Moisture as received was 0.95 g / 100 g (Paper 1) and was scaled out, so
water is 0 on this basis.
Energy: 81.88 kcal / 100 g (Paper 1 only).

Units:
    proteins, fats, carbs, water : g / 100 g
    ashes, others                : mg / 100 g

Methodology:
- Dry-matter scaling: all Paper-1 proximate values were multiplied by
  100/(100-0.95) = 1.00959. Paper 2 reports demembranized eggshell powder,
  assumed already essentially dry.
- Unit conversion: Paper 1 gives minerals in mg/L of acid digestate
  (sealed 100 mL microwave vessels, 1 g sample -> 100 mL), so x10 gives
  mg/100 g, then dry-matter scaled. Paper 2 gives mg (or ug/ng) per g of
  powder, so x100 gives mg/100 g. Paper 1's "cal/g" gross energy is
  kcal/kg, so /10 gives kcal/100 g.
- Averaging: Ca, Mg, Fe, Zn and Cu (both papers) were arithmetically
  averaged on the dry basis. Na and K (Paper 1) and P, Sr, B, Cr, F, Se,
  V, Pb, Al, Cd, Hg (Paper 2) were kept as reported. AAS/ICP measures
  total elemental content, so no compound apportionment was needed.
- ashes.others is total ash (45724.4 mg, Paper 1) minus the sum of the
  identified minerals; it represents the oxygen/carbon (carbonate, oxide)
  fraction bound to the metals plus unmeasured trace inorganics.
- Trace elements reported as "<" or "<=" upper bounds in Paper 2 (B, V,
  Pb, Al, Cd, Hg) are kept at their detection-limit values and should be
  read as upper-bound estimates.
- Protein: average of Paper 1 (1.41 g) and Paper 2 (1.8 g) = 1.61 g. Only
  glycine and arginine are quantified (Paper 2, converted from mg/100 g to
  g/100 g); the rest of the protein fraction is proteins.others.
- Carbohydrate (48.09 g) and crude fibre (4.42 g) are reported separately
  by Paper 1, so fibre is not subtracted from carbs.others.
- The Kjeldahl total nitrogen and ammonia nitrogen figures (Paper 2) are
  kept in others; they are the analytical basis of the protein estimate
  and must not be added to it.
"""

TABLE = {
    "proteins": {
        "glycine": 0.142200,
        "arginine": 0.194400,
        "others": 1.27340,
    },
    "fats": {
        "others": 0.370000,
    },
    "ashes": {
        "aluminum": 0.500000,
        "boron": 0.0530000,
        "cadmium": 0.00500000,
        "calcium": 31662.0,
        "chromium": 0.0120000,
        "copper": 0.703000,
        "fluorine": 0.375000,
        "iron": 8.19000,
        "lead": 0.0500000,
        "magnesium": 4515.80,
        "mercury": 0.0200000,
        "phosphorus": 99.0000,
        "potassium": 172.200,
        "selenium": 0.00235000,
        "sodium": 341.500,
        "strontium": 37.2000,
        "vanadium": 0.0500000,
        "zinc": 5.25000,
        "others": 8881.50,
    },
    "carbs": {
        "fibers": {
            "others": 4.42000,
        },
        "others": 48.0900,
    },
    "others": {},
    "water": 0.000000,
}