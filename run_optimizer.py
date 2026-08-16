"""Weekly cat-diet optimiser -- v3: FEDIAF-first, vet-second.

Hierarchy of authority
----------------------
1. FEDIAF 2025, Table III-4b (complete cat food, per 1000 kcal ME) is the LAW.
   Every minimum and every maximum is a constraint, elastic only so that an
   impossible plan produces a diagnosis instead of "Infeasible".
2. The vet sheet (Piano Nutrizionale per Sirio) is used for
     a. ENERGY          -> 354 kcal * 0.80 = 283.2 kcal/day
     b. the FATTY ACID profile (LA / ALA / ARA / EPA / DHA, SFA:MUFA:PUFA)
     c. a mild "do not wildly exceed this" cap on everything else.
   It is NOT used as a requirement, because per 1000 kcal it is below the
   FEDIAF minimum for iron, zinc, manganese, iodine, folate and vitamin E.

Solver: lexicographic goal programming.
  phase 1 : minimise weighted FEDIAF violation      (should reach 0)
  phase 2 : lock phase 1, minimise vet-PUFA deviation, energy deviation,
            supplement usage and gram cost.

Units inside the model follow the nutrients/ tables:
  macros + fatty acids .... g
  minerals, amino acids,
  vitamins, taurine ....... mg
FEDIAF units (g / mg / ug / IU) are converted at the table level, once.

Requires: pulp (CBC bundled).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

import pulp

from nutrients import *
from utils import apply_cooking_degradation, energy_kcal, scale_to_grams, summary

DEBUG = False

# =============================================================================
# 1. CAT, ENERGY, AND WHICH FEDIAF COLUMN APPLIES
# =============================================================================
DAYS = 7

VET_KCAL = 354.00  # "KCalorie" on the vet sheet
VET_FOOD_G = 291.71  # "Peso tot. Alim. (g)"
VET_DRY_G = 73.98  # "Peso sost s.s. (g)"
VET_WATER_G = 217.74  # "Acqua totale (g)"

VET_SCALE = 0.80  # you asked for -20 %
KCAL_TARGET = VET_KCAL * VET_SCALE  # 283.2 kcal/day

CAT_BW_KG = 4.22  # 45.20 g protein / 10.70 g per kg BW

DIET_FORM = "wet"  # "wet" | "dry"  -> taurine and selenium columns

# Which FEDIAF adult column to interpolate towards.
#   "conservative" -> 75 kcal/kg^0.67 (highest nutrient densities)  [default]
#   "auto"         -> derive from KCAL_TARGET and CAT_BW_KG
#   <float>        -> your own MER in kcal/kg BW^0.67
DENSITY_BASIS = "conservative"

# Extra safety factor on every FEDIAF MINIMUM.  Home-made ingredients have
# unknown true availability; 1.05-1.15 is a defensible margin.  Maxima are
# never multiplied by this.
MIN_SAFETY = 1.00


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


ACTUAL_MER = KCAL_TARGET / CAT_BW_KG**0.67
if DENSITY_BASIS == "conservative":
    MER = 75.0
elif DENSITY_BASIS == "auto":
    MER = _clamp(ACTUAL_MER, 75.0, 100.0)
else:
    MER = _clamp(float(DENSITY_BASIS), 75.0, 100.0)

# =============================================================================
# 2. PHYSICAL SHAPE OF THE MEAL
# =============================================================================
KCAL_TOL = 0.05  # hard band on the weekly-average energy
PER_MEAL_KCAL_SOFT = 0.15  # free band on each meal type
PER_MEAL_KCAL_HARD = 0.45  # absolute band on each meal type

DRY_TARGET = VET_DRY_G * VET_SCALE  # ~59 g DM/day
DRY_TOL = 0.20

MOISTURE_MIN, MOISTURE_MAX = 0.68, 0.82
SERVED_MIN, SERVED_MAX = 190.0, 265.0

WATER_LOSS = 0.20  # water boiled off from the insect dough
EGG_G = 50.0  # edible part of one average egg

FISH_DAYS_OPTIONS = (1, 2, 3)
MIN_INSECT_DAYS = 4
MIN_INSECT_FLOUR_G = 15.0
MIN_FISH_G = 60.0

DOUGH_WATER_PER_FLOUR_MIN = 1.6
DOUGH_WATER_PER_FLOUR_MAX = 4.5

COUNT_UNDIFFERENTIATED = True  # fold "C18:2" into linoleic etc.
ENFORCE_UNTRACKED = False  # treat "no data in any table" as 0 -> supplement
FEDIAF_SCOPE = "weekly"  # "weekly" | "meal"

# FEDIAF Ca/P for adult cats: minimum 1/1, nutritional maximum 2/1.
CA_P_MIN, CA_P_MAX = 1.0, 2.0
CA_P_SWEET = 1.2  # soft target inside that window
CA_P_MEAL_MIN, CA_P_MEAL_MAX = 0.9, 2.2

N6_N3_MIN, N6_N3_MAX = 2.5, 12.0  # vet plan sits at 5.5 : 1

VIT_E_PER_G_PUFA = 0.6  # mg alpha-TE per g dietary PUFA, ON TOP of FEDIAF

# =============================================================================
# 3. INGREDIENT BOUNDS (grams/day, raw as weighed)
# =============================================================================
USE_COD = False
USE_MUSSELS = True

BOUNDS = {
    "bsfl": (0.0, 30.0),
    "mealworms": (0.0, 30.0),
    "water_insect": (0.0, 260.0),
    "cod": (0.0, 140.0),
    "mussels": (0.0, 60.0),
    "cod_roe": (0.0, 25.0),
    "water_fish": (0.0, 220.0),
    "eggshells_i": (0.0, 3.0),
    "eggshells_f": (0.0, 3.0),
    "yeast": (0.0, 5.0),
    "cod_liver_oil": (0.0, 1.5),
    "algal_oil": (0.0, 1.5),
    "taurine": (0.0, 0.6),
}
if not USE_COD:
    BOUNDS["cod"] = (0.0, 0.0)
if not USE_MUSSELS:
    BOUNDS["mussels"] = (0.0, 0.0)

EGG_BOUNDS = {"eggs_insect_week": (0, 6), "eggs_fish_week": (0, 4)}
MAX_EGGS_WEEK = 7

# =============================================================================
# 4. UNIT CONVERSION
# =============================================================================
IU_A_MG = 0.0003  # 1 IU vitamin A   = 0.3  ug retinol
IU_D_MG = 0.000025  # 1 IU vitamin D   = 0.025 ug cholecalciferol
IU_E_MG = 0.67  # 1 IU vitamin E   = 0.67 mg RRR-alpha-tocopherol

_UNIT_IN_MG = {"g": 1000.0, "mg": 1.0, "ug": 1e-3,
               "IU_A": IU_A_MG, "IU_D": IU_D_MG, "IU_E": IU_E_MG}
_UNIT_LABEL = {"g": "g", "mg": "mg", "ug": "ug",
               "IU_A": "IU", "IU_D": "IU", "IU_E": "IU"}


def convert(value: float, from_unit: str, internal: str) -> float:
    mg = value * _UNIT_IN_MG[from_unit]
    return mg / 1000.0 if internal == "g" else mg


# =============================================================================
# 5. NUTRIENT ACCESSORS  (unchanged semantics from v2)
# =============================================================================
def _deep_sum(node) -> float:
    if isinstance(node, dict):
        return sum(_deep_sum(v) for v in node.values())
    return float(node)


def _section(profile: dict, name: str) -> dict:
    value = profile.get(name, {})
    return value if isinstance(value, dict) else {}


def macro(section: str) -> Callable[[dict], float]:
    return lambda p: _deep_sum(_section(p, section))


def mineral(name: str) -> Callable[[dict], float]:
    return lambda p: _section(p, "ashes").get(name, 0.0)


def amino(*names: str) -> Callable[[dict], float]:  # tables in g -> mg
    return lambda p: 1000.0 * sum(_section(p, "proteins").get(n, 0.0) for n in names)


def vitamin(*names: str) -> Callable[[dict], float]:
    return lambda p: sum(_section(p, "vitamins").get(n, 0.0) for n in names)


def vitamin_family(prefix: str) -> Callable[[dict], float]:
    return lambda p: sum(v for k, v in _section(p, "vitamins").items()
                         if k.startswith(prefix))


def fat_class(cls: str) -> Callable[[dict], float]:
    return lambda p: _deep_sum(_section(p, "fats").get(cls, {}))


def fatty_acid(*names: str, cls: str = "polyunsaturated") -> Callable[[dict], float]:
    return lambda p: sum(_section(p, "fats").get(cls, {}).get(n, 0.0) for n in names)


def other(name: str, factor: float = 1.0) -> Callable[[dict], float]:
    return lambda p: _section(p, "others").get(name, 0.0) * factor


LA_KEYS = ["linoleic_acid_C18_2_n6"]
ALA_KEYS = ["alpha_linolenic_acid_C18_3_n3"]
ARA_KEYS = ["arachidonic_acid_C20_4_n6"]
if COUNT_UNDIFFERENTIATED:
    LA_KEYS += ["octadecadienoic_acid_C18_2"]
    ALA_KEYS += ["octadecatrienoic_acid_C18_3"]
    ARA_KEYS += ["eicosatetraenoic_acid_C20_4"]
EPA_KEY = "eicosapentaenoic_acid_C20_5_n3"
DHA_KEY = "docosahexaenoic_acid_C22_6_n3"


# =============================================================================
# 6. THE SINGLE TABLE OF TRUTH
# =============================================================================
@dataclass(frozen=True)
class Nutrient:
    key: str
    label: str
    getter: Callable[[dict], float]
    group: str
    internal: str = "mg"            # unit the getter returns
    funit: str = "mg"               # unit FEDIAF uses
    fmin: tuple[float, float] | None = None   # (75 kcal col, 100 kcal col)
    fmax: float | None = None       # per 1000 kcal, FEDIAF units
    fmax_src: str = ""
    vet: float | None = None        # per day at the vet's 354 kcal, INTERNAL units
    w_short: float = 0.0            # weight of a shortfall vs the VET target
    w_over: float = 1.0             # weight of an excess above the soft cap
    over_factor: float = 2.0        # soft cap = over_factor * vet target
    dynamic: bool = False

    # -- derived -----------------------------------------------------------
    @property
    def f2i(self) -> float:
        """multiply a FEDIAF-unit value by this to get internal units"""
        return convert(1.0, self.funit, self.internal)

    @property
    def unit_label(self) -> str:
        return _UNIT_LABEL[self.funit]

    def fediaf_min(self) -> float | None:
        """FEDIAF units per 1000 kcal, interpolated to this cat's MER."""
        if self.fmin is None:
            return None
        m75, m100 = self.fmin
        return _clamp(m75 * 75.0 / MER, min(m75, m100), max(m75, m100)) * MIN_SAFETY

    def min_internal(self) -> float | None:
        v = self.fediaf_min()
        return None if v is None else v * self.f2i

    def max_internal(self) -> float | None:
        return None if self.fmax is None else self.fmax * self.f2i

    def vet_target(self) -> float | None:
        return None if self.vet is None else self.vet * VET_SCALE

TOCOPHEROL_POTENCY = {  # alpha-tocopherol equivalents (common feed-science factors)
    "vitamin_e_alpha_tocopherol": 1.00,
    "vitamin_e_beta_tocopherol": 0.50,
    "vitamin_e_gamma_tocopherol": 0.10,
    "vitamin_e_delta_tocopherol": 0.03,
    "vitamin_e_alpha_tocotrienol": 0.30,
    "vitamin_e_beta_tocotrienol": 0.05,
    "vitamin_e_gamma_tocotrienol": 0.01,
    "vitamin_e_delta_tocotrienol": 0.01,
}

def vitamin_e_alpha_te(p: dict) -> float:
    vits = _section(p, "vitamins")
    return sum(v * TOCOPHEROL_POTENCY.get(k, 0.0)
               for k, v in vits.items() if k.startswith("vitamin_e"))


_TAURINE = (0.67, 0.50) if DIET_FORM == "wet" else (0.33, 0.25)
_SELENIUM = (87.50, 65.00) if DIET_FORM == "wet" else (70.00, 52.50)

# NOTE ON MAXIMA -------------------------------------------------------------
# FEDIAF III-4b only gives NUMERIC maxima for vitamin A (100 000 IU), vitamin D
# (7 500 IU) and sodium (3.75 g, footnote e).  Everything else marked "(L)" is
# an EU legal limit expressed on a DM basis in Table III-4a, which is not in
# the extract you gave me.  Until you paste III-4a in, the ceilings below come
# from NRC 2006 safe-upper-limits / prudent practice and are marked as such.
LEGAL_MAX_TODO = "NRC/prudent - replace with FEDIAF III-4a legal limit"

NUTRIENTS: list[Nutrient] = [
    # ------------------------------------------------- macros
    Nutrient("protein", "protein", macro("proteins"), "macros", "g", "g",
             fmin=(83.30, 62.50), vet=45.20, w_short=2.0, over_factor=2.0),
    Nutrient("fat", "fat", macro("fats"), "macros", "g", "g",
             fmin=(22.50, 22.50), vet=17.73, w_short=2.0, over_factor=1.6,
             w_over=3.0),
    Nutrient("carbs", "carbohydrate", macro("carbs"), "macros", "g", "g",
             vet=3.28, over_factor=3.0, w_over=2.0),

    # ------------------------------------------------- amino acids (mg)
    Nutrient("arginine", "arginine", amino("arginine"), "amino acids",
             fmin=(3.30, 2.50), funit="g", vet=2944.64, over_factor=4.0),
    Nutrient("histidine", "histidine", amino("histidine"), "amino acids",
             fmin=(0.87, 0.65), funit="g", vet=1297.03, over_factor=4.0),
    Nutrient("isoleucine", "isoleucine", amino("isoleucine"), "amino acids",
             fmin=(1.44, 1.08), funit="g", vet=2278.46, over_factor=4.0),
    Nutrient("leucine", "leucine", amino("leucine"), "amino acids",
             fmin=(3.40, 2.55), funit="g", vet=3794.13, over_factor=4.0),
    Nutrient("lysine", "lysine", amino("lysine"), "amino acids",
             fmin=(1.13, 0.85), funit="g", vet=4101.94, over_factor=4.0),
    Nutrient("methionine", "methionine", amino("methionine"), "amino acids",
             fmin=(0.57, 0.43), funit="g", vet=1300.21, over_factor=3.0),
    Nutrient("methionine_cystine", "methionine + cystine",
             amino("methionine", "cysteine"), "amino acids",
             fmin=(1.13, 0.85), funit="g", over_factor=4.0),
    Nutrient("cysteine", "cystine", amino("cysteine"), "amino acids",
             vet=541.57, over_factor=4.0),
    Nutrient("phenylalanine", "phenylalanine", amino("phenylalanine"),
             "amino acids", fmin=(1.33, 1.00), funit="g", vet=2002.09,
             over_factor=4.0),
    Nutrient("phenylalanine_tyrosine", "phenylalanine + tyrosine",
             amino("phenylalanine", "tyrosine"), "amino acids",
             fmin=(5.11, 3.83), funit="g", over_factor=4.0),
    Nutrient("tyrosine", "tyrosine", amino("tyrosine"), "amino acids",
             vet=1579.61, over_factor=4.0),
    Nutrient("threonine", "threonine", amino("threonine"), "amino acids",
             fmin=(1.73, 1.30), funit="g", vet=2208.56, over_factor=4.0),
    Nutrient("tryptophan", "tryptophan", amino("tryptophan"), "amino acids",
             fmin=(0.44, 0.33), funit="g", vet=492.73, over_factor=4.0),
    Nutrient("valine", "valine", amino("valine"), "amino acids",
             fmin=(1.70, 1.28), funit="g", vet=2511.67, over_factor=4.0),
    Nutrient("taurine", f"taurine ({DIET_FORM})", other("taurine"), "amino acids",
             fmin=_TAURINE, funit="g", vet=250.0, w_short=1.0, over_factor=6.0),

    # ------------------------------------------------- fats (g)
    Nutrient("linoleic_acid_C18_2_n6", "linoleic acid 18:2 n-6",
             fatty_acid(*LA_KEYS), "fats", "g", "g",
             fmin=(1.67, 1.25), vet=2.72, w_short=3.0, over_factor=2.0),
    Nutrient("alpha_linolenic_acid_C18_3_n3", "alpha-linolenic 18:3 n-3",
             fatty_acid(*ALA_KEYS), "fats", "g", "g",
             vet=0.10, w_short=3.0, over_factor=6.0),
    Nutrient("arachidonic_acid_C20_4_n6", "arachidonic acid 20:4 n-6",
             fatty_acid(*ARA_KEYS), "fats", "g", "mg",
             fmin=(20.00, 15.00), vet=0.30, w_short=4.0, over_factor=4.0),
    Nutrient("eicosapentaenoic_acid_C20_5_n3", "EPA 20:5 n-3",
             fatty_acid(EPA_KEY), "fats", "g", "g",
             vet=0.15, w_short=4.0, over_factor=4.0),
    Nutrient("docosahexaenoic_acid_C22_6_n3", "DHA 22:6 n-3",
             fatty_acid(DHA_KEY), "fats", "g", "g",
             vet=0.30, w_short=4.0, over_factor=4.0),
    Nutrient("epa_dha", "EPA + DHA", fatty_acid(EPA_KEY, DHA_KEY), "fats", "g", "g",
             fmax=2.80, fmax_src="NRC SUL"),
    Nutrient("saturated", "saturated FA", fat_class("saturated"), "fats", "g", "g",
             vet=6.90, w_short=1.0, over_factor=1.6, w_over=2.0),
    Nutrient("monounsaturated", "monounsaturated FA", fat_class("monounsaturated"),
             "fats", "g", "g", vet=4.23, w_short=1.0, over_factor=1.8, w_over=2.0),
    Nutrient("polyunsaturated", "polyunsaturated FA", fat_class("polyunsaturated"),
             "fats", "g", "g", vet=3.40, w_short=2.0, over_factor=1.6, w_over=2.0),
    Nutrient("cholesterol", "cholesterol", other("cholesterol", 1e-3), "fats",
             "g", "g", vet=197.84 / 1000.0, over_factor=2.5, w_over=2.0),

    # ------------------------------------------------- minerals (mg)
    Nutrient("calcium", "calcium", mineral("calcium"), "minerals",
             funit="g", fmin=(1.33, 1.00), fmax=4.00, fmax_src=LEGAL_MAX_TODO,
             vet=1359.50, over_factor=1.6, w_over=2.0),
    Nutrient("phosphorus", "phosphorus", mineral("phosphorus"), "minerals",
             funit="g", fmin=(0.85, 0.64), fmax=2.50,
             fmax_src="prudent (renal; cf. footnote f)",
             vet=1358.73, over_factor=1.6, w_over=3.0),
    Nutrient("potassium", "potassium", mineral("potassium"), "minerals",
             funit="g", fmin=(2.00, 1.50), fmax=4.00, fmax_src=LEGAL_MAX_TODO,
             vet=781.86, over_factor=2.0),
    Nutrient("sodium", "sodium", mineral("sodium"), "minerals",
             funit="g", fmin=(0.25, 0.19), fmax=3.75, fmax_src="FEDIAF footnote e",
             vet=213.03, over_factor=3.0, w_over=2.0),
    Nutrient("chloride", "chloride", mineral("chloride"), "minerals",
             funit="g", fmin=(0.39, 0.29), over_factor=3.0),
    Nutrient("magnesium", "magnesium", mineral("magnesium"), "minerals",
             funit="g", fmin=(0.13, 0.10), fmax=0.40, fmax_src=LEGAL_MAX_TODO,
             vet=59.48, over_factor=2.0, w_over=2.0),

    # ------------------------------------------------- trace elements (mg)
    Nutrient("copper", "copper", mineral("copper"), "trace elements",
             fmin=(1.67, 1.25), fmax=5.0, fmax_src=LEGAL_MAX_TODO,
             vet=0.93, over_factor=2.5, w_over=3.0),
    Nutrient("iodine", "iodine", mineral("iodine"), "trace elements",
             fmin=(0.43, 0.33), fmax=1.10, fmax_src=LEGAL_MAX_TODO,
             vet=0.10, over_factor=3.0, w_over=3.0),
    Nutrient("iron", "iron", mineral("iron"), "trace elements",
             fmin=(26.70, 20.00), fmax=60.0, fmax_src=LEGAL_MAX_TODO,
             vet=4.79, over_factor=3.0, w_over=3.0),
    Nutrient("manganese", "manganese", mineral("manganese"), "trace elements",
             fmin=(1.67, 1.25), fmax=10.0, fmax_src=LEGAL_MAX_TODO,
             vet=0.12, over_factor=6.0, w_over=3.0),
    Nutrient("selenium", f"selenium ({DIET_FORM})", mineral("selenium"),
             "trace elements", funit="ug", fmin=_SELENIUM, fmax=500.0,
             fmax_src=LEGAL_MAX_TODO, vet=32.69 / 1000.0, over_factor=3.0,
             w_over=3.0),
    Nutrient("zinc", "zinc", mineral("zinc"), "trace elements",
             fmin=(25.00, 18.80), fmax=50.0, fmax_src=LEGAL_MAX_TODO,
             vet=6.48, over_factor=3.0, w_over=2.0),

    # ------------------------------------------------- vitamins (mg)
    Nutrient("vitamin_a_retinol", "vitamin A", vitamin("vitamin_a_retinol"),
             "vitamins", funit="IU_A", fmin=(1110.0, 833.0), fmax=100000.0,
             fmax_src="FEDIAF (N)", vet=6501.38 * IU_A_MG, over_factor=6.0,
             w_over=3.0),
    Nutrient("vitamin_d3_cholecalciferol", "vitamin D",
             vitamin("vitamin_d3_cholecalciferol", "vitamin_d"), "vitamins",
             funit="IU_D", fmin=(83.30, 62.50), fmax=7500.0,
             fmax_src="FEDIAF (N)", vet=87.22 * IU_D_MG, over_factor=6.0,
             w_over=5.0),
    Nutrient("vitamin_e_tocopherols", "vitamin E", vitamin_e_alpha_te, "vitamins",
             funit="IU_E", fmin=(12.70, 9.50), fmax=1000.0, fmax_src="prudent",
             vet=1.76, over_factor=20.0, dynamic=True),
    Nutrient("vitamin_b1_thiamin", "vitamin B1", vitamin("vitamin_b1_thiamin"),
             "vitamins", fmin=(1.47, 1.10), vet=0.58, over_factor=10.0),
    Nutrient("vitamin_b2_riboflavin", "vitamin B2", vitamin("vitamin_b2_riboflavin"),
             "vitamins", fmin=(1.05, 0.80), vet=0.83, over_factor=10.0),
    Nutrient("vitamin_b3_niacin", "vitamin B3", vitamin("vitamin_b3_niacin"),
             "vitamins", fmin=(10.50, 8.00), fmax=200.0, fmax_src="NRC SUL",
             vet=12.71, over_factor=8.0),
    Nutrient("vitamin_b5_pantothenic_acid", "vitamin B5",
             vitamin("vitamin_b5_pantothenic_acid"), "vitamins",
             fmin=(1.92, 1.44), vet=3.45, over_factor=10.0),
    Nutrient("vitamin_b6_pyridoxine", "vitamin B6", vitamin("vitamin_b6_pyridoxine"),
             "vitamins", fmin=(0.83, 0.63), vet=0.79, over_factor=10.0),
    Nutrient("vitamin_b8_biotin", "vitamin B7 (biotin)", vitamin("vitamin_b8_biotin"),
             "vitamins", funit="ug", fmin=(20.00, 15.00), vet=7.67 / 1000.0,
             over_factor=15.0),
    Nutrient("vitamin_b9_folate", "vitamin B9 (folate)", vitamin("vitamin_b9_folate"),
             "vitamins", funit="ug", fmin=(253.0, 188.0), vet=44.16 / 1000.0,
             over_factor=15.0),
    Nutrient("vitamin_b12_cobalamin", "vitamin B12",
             vitamin("vitamin_b12_cobalamin"), "vitamins", funit="ug",
             fmin=(5.87, 4.40), vet=16.28 / 1000.0, over_factor=30.0),
    Nutrient("vitamin_j_choline", "vitamin J", vitamin("vitamin_j_choline"), "vitamins",
             fmin=(800.0, 600.0), over_factor=4.0),
    Nutrient("vitamin_c_ascorbic_acid", "vitamin C (not required)",
             vitamin("vitamin_c_ascorbic_acid"), "vitamins", vet=5.72,
             over_factor=20.0),
]

SPEC_BY_KEY = {n.key: n for n in NUTRIENTS}


# =============================================================================
# 7. SUPPLEMENTS  (weightless single/multi-nutrient products, grams/day)
# =============================================================================
@dataclass(frozen=True)
class Supplement:
    slug: str
    name: str
    contents: dict[str, float]  # INTERNAL units of nutrient per gram of product
    max_g: float
    cost: float = 0.25          # relative cost of using the whole allowance


SUPPLEMENTS: list[Supplement] = [
    Supplement("salt", "table salt (NaCl)",
               {"sodium": 393.4, "chloride": 606.6}, 1.0, 0.20),
    Supplement("kcl", "potassium chloride",
               {"potassium": 524.5, "chloride": 475.5}, 3.0, 0.20),
    Supplement("zn", "zinc gluconate (14.3 % Zn)", {"zinc": 143.0}, 0.30, 0.25),
    Supplement("fe", "iron bisglycinate (20 % Fe)", {"iron": 200.0}, 0.15, 0.25),
    Supplement("cu", "copper gluconate (14 % Cu)", {"copper": 140.0}, 0.05, 0.35),
    Supplement("mn", "manganese gluconate (11.4 % Mn)",
               {"manganese": 114.0}, 0.05, 0.30),
    Supplement("i", "potassium iodide (76.5 % I)", {"iodine": 765.0}, 0.002, 0.35),
    Supplement("se", "sodium selenite (45.6 % Se)",
               {"selenium": 456.0}, 0.0004, 0.40),
    Supplement("mg", "magnesium bisglycinate (14 % Mg)",
               {"magnesium": 140.0}, 0.40, 0.35),
    Supplement("j", "choline bitartrate (41 % choline)",
               {"vitamin_j_choline": 410.0}, 1.50, 0.15),
    Supplement("vit_e", "vitamin E, d-alpha-tocopherol (pure)",
               {"vitamin_e_tocopherols": 1000.0}, 0.05, 0.20),
    Supplement("b1", "thiamine (pure)", {"vitamin_b1_thiamin": 1000.0}, 0.02, 0.15),
    Supplement("b2", "riboflavin (pure)",
               {"vitamin_b2_riboflavin": 1000.0}, 0.02, 0.15),
    Supplement("b3", "niacinamide (pure)", {"vitamin_b3_niacin": 1000.0}, 0.05, 0.15),
    Supplement("b5", "calcium pantothenate (pure)",
               {"vitamin_b5_pantothenic_acid": 1000.0}, 0.02, 0.15),
    Supplement("b6", "pyridoxine HCl (pure)",
               {"vitamin_b6_pyridoxine": 1000.0}, 0.02, 0.15),
    Supplement("b7", "biotin (pure)", {"vitamin_b8_biotin": 1000.0}, 0.002, 0.15),
    Supplement("b9", "folic acid (pure)", {"vitamin_b9_folate": 1000.0}, 0.005, 0.15),
    Supplement("b12", "cyanocobalamin (pure)",
               {"vitamin_b12_cobalamin": 1000.0}, 0.002, 0.15),
    Supplement("met", "DL-methionine",
               {"methionine": 1000.0, "methionine_cystine": 1000.0}, 1.0, 0.35),
    Supplement("vit_d", "vitamin D3 (pure, 40 000 IU/mg)",
               {"vitamin_d3_cholecalciferol": 1000.0}, 0.0001, 0.50),
]

for _s in SUPPLEMENTS:
    for _k in _s.contents:
        assert _k in SPEC_BY_KEY, f"unknown nutrient {_k} in supplement {_s.slug}"
        assert SPEC_BY_KEY[_k].internal == "mg", f"{_k} must be mg-based"

# =============================================================================
# 8. INGREDIENTS
# =============================================================================
WATER_TABLE = {"water": 100.0}
TAURINE_TABLE = {"others": {"taurine": 100_000.0}, "water": 0.0}


@dataclass(frozen=True)
class Ingredient:
    key: str
    label: str
    table: dict
    cooked: bool = False


INGREDIENTS = {
    "bsfl": Ingredient("bsfl", "BSFL flour", BSFL_TABLE, cooked=True),
    "mealworms": Ingredient("mealworms", "mealworm flour", MEALWORMS_TABLE, cooked=True),
    "eggs_cooked": Ingredient("eggs_cooked", "whole egg (cooked)", EGGS_TABLE, cooked=True),
    "water_insect": Ingredient("water_insect", "water (dough)", WATER_TABLE, cooked=True),
    "cod": Ingredient("cod", "wild cod", COD_TABLE),
    "mussels": Ingredient("mussels", "blue mussels", MUSSELS_TABLE),
    "cod_roe": Ingredient("cod_roe", "cod roe", COD_ROE_TABLE),
    "eggs_raw": Ingredient("eggs_raw", "whole egg (raw)", EGGS_TABLE),
    "water_fish": Ingredient("water_fish", "water", WATER_TABLE),
    "eggshells": Ingredient("eggshells", "eggshell powder", EGGSHELLS_TABLE),
    "yeast": Ingredient("yeast", "nutritional yeast", YEAST_TABLE),
    "cod_liver_oil": Ingredient("cod_liver_oil", "cod liver oil", COD_LIVER_OIL_TABLE),
    "algal_oil": Ingredient("algal_oil", "algal EPA/DHA oil", ALGAL_OIL_TABLE),
    "taurine": Ingredient("taurine", "taurine powder", TAURINE_TABLE),
}


def per_gram_profile(ing: Ingredient) -> dict:
    profile = scale_to_grams(ing.table, 1.0, sig=None)
    if ing.cooked:
        profile = apply_cooking_degradation(profile, water_loss_rate=WATER_LOSS, sig=12)
    return profile


PROFILE = {k: per_gram_profile(v) for k, v in INGREDIENTS.items()}
COEFF = {k: {n.key: n.getter(p) for n in NUTRIENTS} for k, p in PROFILE.items()}
KCAL_PG = {k: energy_kcal(p) for k, p in PROFILE.items()}
WEIGHT_PG = {k: summary(p, sig=12)["weight"] for k, p in PROFILE.items()}
WATER_PG = {k: summary(p, sig=12)["water"] for k, p in PROFILE.items()}
DRY_PG = {k: WEIGHT_PG[k] - WATER_PG[k] for k in PROFILE}
ASH_PG = {k: _deep_sum(_section(p, "ashes")) / 1000.0 for k, p in PROFILE.items()}

# nutrients for which not a single ingredient table has data
UNTRACKED = {
    n.key for n in NUTRIENTS
    if all(abs(COEFF[i][n.key]) < 1e-15 for i in PROFILE)
    and not any(n.key in s.contents for s in SUPPLEMENTS)
}
DATA_MISSING = {
    n.key for n in NUTRIENTS
    if all(abs(COEFF[i][n.key]) < 1e-15 for i in PROFILE)
}


# =============================================================================
# 9. A PLAN: the same expressions for the LP and for the report
# =============================================================================
def _total(items: Iterable):
    return sum(items, 0)


class Plan:
    """Quantities may be LpVariables or plain floats."""

    def __init__(self, x, eggs_i, eggs_f, sup, S, C, liver_oil_everyday):
        self.S, self.C = S, C
        self.sup = sup
        self.lo_daily = liver_oil_everyday

        common = [
            (x["yeast"], "yeast"),
            (x["algal_oil"], "algal_oil"),
            (x["taurine"], "taurine"),
        ]
        self.insect_items = [
            (x["bsfl"], "bsfl"),
            (x["mealworms"], "mealworms"),
            (EGG_G * eggs_i / S, "eggs_cooked"),
            (x["water_insect"], "water_insect"),
            (x["eggshells_i"], "eggshells"),
            *common,
        ]
        if liver_oil_everyday:
            self.insect_items.append((x["cod_liver_oil"], "cod_liver_oil"))
        self.fish_items = [
            (x["cod"], "cod"),
            (x["mussels"], "mussels"),
            (x["cod_roe"], "cod_roe"),
            (EGG_G * eggs_f / C, "eggs_raw"),
            (x["water_fish"], "water_fish"),
            (x["eggshells_f"], "eggshells"),
            (x["cod_liver_oil"], "cod_liver_oil"),
            *common,
        ]

    # ---- supplements -----------------------------------------------------
    def supp(self, key: str):
        return _total(self.sup[s.slug] * s.contents[key]
                      for s in SUPPLEMENTS if key in s.contents)

    def supp_grams(self):
        return _total(self.sup[s.slug] for s in SUPPLEMENTS)

    # ---- per meal type ---------------------------------------------------
    def meal_nutrient(self, items, key):
        return _total(q * COEFF[i][key] for q, i in items) + self.supp(key)

    def meal_scalar(self, items, table, add_supp_mass=False):
        v = _total(q * table[i] for q, i in items)
        return v + self.supp_grams() if add_supp_mass else v

    def meal_kcal(self, items):
        return self.meal_scalar(items, KCAL_PG)

    # ---- weekly average per day -----------------------------------------
    def nutrient(self, key):
        return (self.S * self.meal_nutrient(self.insect_items, key)
                + self.C * self.meal_nutrient(self.fish_items, key)) / DAYS

    def scalar(self, table, add_supp_mass=False):
        return (self.S * self.meal_scalar(self.insect_items, table, add_supp_mass)
                + self.C * self.meal_scalar(self.fish_items, table, add_supp_mass)) / DAYS

    def kcal(self):
        return self.scalar(KCAL_PG)


# =============================================================================
# 10. MODEL
# =============================================================================
GRAM_COST = 0.02
KCAL_DEV_WEIGHT = 30.0
PER_MEAL_KCAL_WEIGHT = 6.0
CA_P_WEIGHT = 2.0
FEDIAF_MIN_WEIGHT = 1.0
FEDIAF_MAX_WEIGHT = 1.5
VET_ECHO = 1.0        # global multiplier on "do not exceed the vet profile"
VET_PUFA_WEIGHT = 1.0  # global multiplier on vet fatty-acid fidelity


def build(fish_days: int, liver_oil_everyday: bool):
    C, S = fish_days, DAYS - fish_days
    prob = pulp.LpProblem(f"cat_diet_C{C}", pulp.LpMinimize)

    x = {k: pulp.LpVariable(k, lowBound=lo, upBound=hi) for k, (lo, hi) in BOUNDS.items()}
    eggs_i = pulp.LpVariable("eggs_insect_week", *EGG_BOUNDS["eggs_insect_week"],
                             cat="Integer")
    eggs_f = pulp.LpVariable("eggs_fish_week", *EGG_BOUNDS["eggs_fish_week"],
                             cat="Integer")
    prob += eggs_i + eggs_f <= MAX_EGGS_WEEK, "max_eggs_week"
    sup = {s.slug: pulp.LpVariable(f"sup_{s.slug}", 0, s.max_g) for s in SUPPLEMENTS}

    P = Plan(x, eggs_i, eggs_f, sup, S, C, liver_oil_everyday)

    # ---------------- energy -------------------------------------------------
    kcal = P.kcal()
    prob += kcal >= KCAL_TARGET * (1 - KCAL_TOL), "kcal_lo"
    prob += kcal <= KCAL_TARGET * (1 + KCAL_TOL), "kcal_hi"
    kcal_dev = pulp.LpVariable("kcal_dev", lowBound=0)
    prob += kcal_dev >= kcal - KCAL_TARGET
    prob += kcal_dev >= KCAL_TARGET - kcal

    meal_dev = []
    for tag, items in (("insect", P.insect_items), ("fish", P.fish_items)):
        mk = P.meal_kcal(items)
        prob += mk >= KCAL_TARGET * (1 - PER_MEAL_KCAL_HARD), f"{tag}_kcal_lo"
        prob += mk <= KCAL_TARGET * (1 + PER_MEAL_KCAL_HARD), f"{tag}_kcal_hi"
        d = pulp.LpVariable(f"{tag}_kcal_dev", lowBound=0)
        prob += d >= mk - KCAL_TARGET * (1 + PER_MEAL_KCAL_SOFT)
        prob += d >= KCAL_TARGET * (1 - PER_MEAL_KCAL_SOFT) - mk
        meal_dev.append(d)

    # ---------------- physical shape ----------------------------------------
    dry = P.scalar(DRY_PG, add_supp_mass=True)
    prob += dry >= DRY_TARGET * (1 - DRY_TOL), "dry_lo"
    prob += dry <= DRY_TARGET * (1 + DRY_TOL), "dry_hi"

    for tag, items in (("insect", P.insect_items), ("fish", P.fish_items)):
        w = P.meal_scalar(items, WEIGHT_PG, add_supp_mass=True)
        wat = P.meal_scalar(items, WATER_PG)
        prob += w >= SERVED_MIN, f"{tag}_served_lo"
        prob += w <= SERVED_MAX, f"{tag}_served_hi"
        prob += wat >= MOISTURE_MIN * w, f"{tag}_moist_lo"
        prob += wat <= MOISTURE_MAX * w, f"{tag}_moist_hi"

    flour = x["bsfl"] + x["mealworms"]
    prob += x["water_insect"] >= DOUGH_WATER_PER_FLOUR_MIN * flour, "dough_lo"
    prob += x["water_insect"] <= DOUGH_WATER_PER_FLOUR_MAX * flour, "dough_hi"
    prob += flour >= MIN_INSECT_FLOUR_G, "min_flour"
    prob += x["cod"] + x["mussels"] + x["cod_roe"] >= MIN_FISH_G, "min_fish"

    # ---------------- FEDIAF, elastic ---------------------------------------
    scopes = [("week", P.nutrient, kcal)]
    if FEDIAF_SCOPE == "meal":
        scopes = [
            ("insect", lambda k: P.meal_nutrient(P.insect_items, k), P.meal_kcal(P.insect_items)),
            ("fish", lambda k: P.meal_nutrient(P.fish_items, k), P.meal_kcal(P.fish_items)),
        ]

    fediaf_short, fediaf_over = {}, {}
    violation_terms = []
    for scope, getter, kcal_expr in scopes:
        for n in NUTRIENTS:
            lo = n.min_internal()
            if lo is not None and (n.key not in DATA_MISSING or ENFORCE_UNTRACKED):
                s = pulp.LpVariable(f"short_{scope}_{n.key}", lowBound=0)
                prob += getter(n.key) + s >= lo * kcal_expr / 1000.0, f"min_{scope}_{n.key}"
                ref = lo * KCAL_TARGET / 1000.0
                violation_terms.append(FEDIAF_MIN_WEIGHT * s / ref)
                if scope in ("week", "insect"):
                    fediaf_short[n.key] = s
            hi = n.max_internal()
            if hi is not None:
                e = pulp.LpVariable(f"over_{scope}_{n.key}", lowBound=0)
                prob += getter(n.key) - e <= hi * kcal_expr / 1000.0, f"max_{scope}_{n.key}"
                ref = hi * KCAL_TARGET / 1000.0
                violation_terms.append(FEDIAF_MAX_WEIGHT * e / ref)
                if scope in ("week", "insect"):
                    fediaf_over[n.key] = e

    # Ca:P -- FEDIAF 1/1 .. 2/1 for adults
    ca, ph = P.nutrient("calcium"), P.nutrient("phosphorus")
    cap_short = pulp.LpVariable("short_ca_p_ratio", lowBound=0)
    cap_over = pulp.LpVariable("over_ca_p_ratio", lowBound=0)
    prob += ca + cap_short * ph_ref(ph) >= CA_P_MIN * ph, "ca_p_lo"
    prob += ca - cap_over * ph_ref(ph) <= CA_P_MAX * ph, "ca_p_hi"
    violation_terms += [FEDIAF_MIN_WEIGHT * cap_short, FEDIAF_MAX_WEIGHT * cap_over]

    for tag, items in (("insect", P.insect_items), ("fish", P.fish_items)):
        c = P.meal_nutrient(items, "calcium")
        p = P.meal_nutrient(items, "phosphorus")
        prob += c - CA_P_MEAL_MAX * p <= 0, f"{tag}_ca_p_hi"
        prob += c - CA_P_MEAL_MIN * p >= 0, f"{tag}_ca_p_lo"

    ca_dev = pulp.LpVariable("ca_p_sweet_dev", lowBound=0)
    prob += ca_dev >= ca - CA_P_SWEET * ph
    prob += ca_dev >= CA_P_SWEET * ph - ca

    # vitamin E scales with the PUFA load (FEDIAF minimum is only the floor)
    pufa = P.nutrient("polyunsaturated")
    vit_e = P.nutrient("vitamin_e_tocopherols")
    e_floor = SPEC_BY_KEY["vitamin_e_tocopherols"].min_internal() * KCAL_TARGET / 1000.0
    e_short = pulp.LpVariable("short_vitamin_e_pufa", lowBound=0)
    prob += vit_e + e_short >= e_floor + VIT_E_PER_G_PUFA * pufa, "vitE_pufa"
    violation_terms.append(2.0 * e_short / e_floor)

    # n-6 : n-3
    n6 = P.nutrient("linoleic_acid_C18_2_n6") + P.nutrient("arachidonic_acid_C20_4_n6")
    n3 = (P.nutrient("alpha_linolenic_acid_C18_3_n3")
          + P.nutrient("eicosapentaenoic_acid_C20_5_n3")
          + P.nutrient("docosahexaenoic_acid_C22_6_n3"))
    prob += n6 - N6_N3_MAX * n3 <= 0, "n6n3_hi"
    prob += n6 - N6_N3_MIN * n3 >= 0, "n6n3_lo"

    fediaf_violation = _total(violation_terms)

    # ---------------- vet layer (soft, phase 2) ------------------------------
    vet_terms = []
    vet_short, vet_over = {}, {}
    for n in NUTRIENTS:
        tgt = n.vet_target()
        if tgt is None or tgt <= 0:
            continue
        val = P.nutrient(n.key)
        if n.w_short > 0:
            d = pulp.LpVariable(f"vet_short_{n.key}", lowBound=0)
            prob += val + d >= tgt, f"vet_lo_{n.key}"
            vet_short[n.key] = d
            w = VET_PUFA_WEIGHT if n.group == "fats" else 1.0
            vet_terms.append(w * n.w_short * d / tgt)
        lo = n.min_internal()
        floor = 0.0 if lo is None else 1.05 * lo * KCAL_TARGET / 1000.0
        cap = max(n.over_factor * tgt, floor)
        e = pulp.LpVariable(f"vet_over_{n.key}", lowBound=0)
        prob += val - e <= cap, f"vet_hi_{n.key}"
        vet_over[n.key] = e
        vet_terms.append(VET_ECHO * n.w_over * e / tgt)

    supp_cost = _total(s.cost * sup[s.slug] / s.max_g for s in SUPPLEMENTS)
    gram_cost = GRAM_COST * _total(
        x[k] for k in ("bsfl", "mealworms", "cod", "mussels", "cod_roe",
                       "eggshells_i", "eggshells_f", "yeast", "cod_liver_oil",
                       "algal_oil", "taurine"))

    phase2 = (_total(vet_terms)
              + KCAL_DEV_WEIGHT * kcal_dev / KCAL_TARGET
              + PER_MEAL_KCAL_WEIGHT * _total(meal_dev) / KCAL_TARGET
              + CA_P_WEIGHT * ca_dev / max(1e-9, CA_P_SWEET * KCAL_TARGET / 1000.0 * 1000.0)
              + supp_cost
              + gram_cost)

    return {
        "prob": prob, "plan": P, "x": x, "sup": sup,
        "eggs_i": eggs_i, "eggs_f": eggs_f, "S": S, "C": C,
        "lo_daily": liver_oil_everyday,
        "fediaf_violation": fediaf_violation, "phase2": phase2,
        "fediaf_short": fediaf_short, "fediaf_over": fediaf_over,
        "vet_short": vet_short, "vet_over": vet_over,
    }


def ph_ref(_ph):
    """Scale for the Ca:P elastic slacks -- keeps them dimensionless-ish."""
    return 1.0


def solve(fish_days: int, liver_oil_everyday: bool) -> dict | None:
    if DAYS - fish_days < MIN_INSECT_DAYS:
        return None
    m = build(fish_days, liver_oil_everyday)
    prob = m["prob"]

    # ---- phase 1: FEDIAF compliance above all else ----
    prob.setObjective(m["fediaf_violation"])
    prob.solve(pulp.PULP_CBC_CMD(msg=False))
    if pulp.LpStatus[prob.status] != "Optimal":
        return {"status": pulp.LpStatus[prob.status], "fish_days": fish_days,
                "liver_oil_everyday": liver_oil_everyday}
    v1 = float(pulp.value(m["fediaf_violation"]))

    # ---- phase 2: the vet's fatty acids, energy fidelity, least supplements ----
    prob += m["fediaf_violation"] <= v1 + 1e-6, "lex_phase1_lock"
    prob.setObjective(m["phase2"])
    prob.solve(pulp.PULP_CBC_CMD(msg=False))
    if pulp.LpStatus[prob.status] != "Optimal":
        return {"status": "Phase2 " + pulp.LpStatus[prob.status],
                "fish_days": fish_days, "liver_oil_everyday": liver_oil_everyday}

    if DEBUG:
        for name, c in prob.constraints.items():
            if abs(c.value()) < 1e-7:
                print(f"  binding: {name}")

    sol = {k: float(v.value()) for k, v in m["x"].items()}
    sol["eggs_insect_week"] = int(round(m["eggs_i"].value()))
    sol["eggs_fish_week"] = int(round(m["eggs_f"].value()))
    sup = {k: float(v.value()) for k, v in m["sup"].items()}
    return {
        "status": "Optimal",
        "fediaf_violation": v1,
        "objective": float(pulp.value(m["phase2"])),
        "fish_days": fish_days, "insect_days": DAYS - fish_days,
        "liver_oil_everyday": liver_oil_everyday,
        "solution": sol, "supplements": sup,
    }


# =============================================================================
# 11. REPORT
# =============================================================================
def rebuild(result: dict) -> Plan:
    sol, sup = result["solution"], result["supplements"]
    return Plan(sol, sol["eggs_insect_week"], sol["eggs_fish_week"], sup,
                result["insect_days"], result["fish_days"],
                result["liver_oil_everyday"])


def report(result: dict) -> None:
    P = rebuild(result)
    sol, sup = result["solution"], result["supplements"]
    S, C = result["insect_days"], result["fish_days"]
    kcal = P.kcal()
    k1000 = kcal / 1000.0

    print("=" * 84)
    print(f"WEEKLY PLAN : {S} insect days + {C} fish day(s)   |   cod-liver oil "
          f"{'every day' if result['liver_oil_everyday'] else 'fish days only'}")
    print(f"Energy      : {kcal:.0f} kcal/day  (vet {VET_KCAL:.0f} kcal x {VET_SCALE:.2f}"
          f" = {KCAL_TARGET:.0f} kcal target)")
    print(f"FEDIAF basis: adult cat, {DIET_FORM} diet, MER {MER:.0f} kcal/kg BW^0.67 "
          f"({DENSITY_BASIS}); this cat actually eats {ACTUAL_MER:.0f} at {CAT_BW_KG} kg")
    print(f"FEDIAF scope: {FEDIAF_SCOPE}   |   safety factor on minima "
          f"x{MIN_SAFETY:.2f}   |   violation score {result['fediaf_violation']:.4f}")
    print("=" * 84)

    # ---------------- recipes ------------------------------------------------
    def meal_block(title, items, days, rows):
        w = P.meal_scalar(items, WEIGHT_PG, add_supp_mass=True)
        wat = P.meal_scalar(items, WATER_PG)
        print(f"\n{title} - {days} day(s)/week")
        for label, grams in rows:
            if grams > 1e-6:
                print(f"  {label:<24}: {grams:7.1f} g")
        print(f"  -> served{'':<15}: {w:7.1f} g, {P.meal_kcal(items):5.0f} kcal, "
              f"{100 * wat / w:4.1f} % water, {w - wat:5.1f} g DM")

    meal_block("INSECT DOUGH (cooked together)", P.insect_items, S, [
        ("BSFL flour", sol["bsfl"]),
        ("mealworm flour", sol["mealworms"]),
        (f"whole egg ({sol['eggs_insect_week']}/wk)", sol["eggs_insect_week"] * EGG_G / S),
        (f"water (-{WATER_LOSS:.0%} cooking)", sol["water_insect"]),
        ("eggshell powder", sol["eggshells_i"]),
    ])
    meal_block("FISH MEAL (raw)", P.fish_items, C, [
        ("wild cod", sol["cod"]),
        ("blue mussels", sol["mussels"]),
        ("cod roe", sol["cod_roe"]),
        (f"whole egg ({sol['eggs_fish_week']}/wk)", sol["eggs_fish_week"] * EGG_G / C),
        ("water", sol["water_fish"]),
        ("eggshell powder", sol["eggshells_f"]),
    ])

    print("\nEVERY DAY, both meal types")
    for label, g in (("nutritional yeast", sol["yeast"]),
                     ("cod liver oil", sol["cod_liver_oil"]),
                     ("algal EPA/DHA oil", sol["algal_oil"]),
                     ("taurine powder", sol["taurine"])):
        if g > 1e-6:
            print(f"  {label:<24}: {g:7.2f} g")

    used = [(s, sup[s.slug]) for s in SUPPLEMENTS if sup[s.slug] > 1e-9]
    print("\nSUPPLEMENTS THE FOOD CANNOT COVER (per day)")
    if not used:
        print("  none - the ingredients alone meet every FEDIAF minimum.")
    for s, g in used:
        elems = ", ".join(
            f"{g * mgpg:.3g} mg {SPEC_BY_KEY[k].label}" for k, mgpg in s.contents.items()
            if not k.endswith("_cystine"))
        print(f"  {s.name:<38}: {g * 1000:8.2f} mg product   -> {elems}")

    # ---------------- FEDIAF compliance --------------------------------------
    print("\n" + "-" * 84)
    print("FEDIAF COMPLIANCE  (per 1000 kcal ME, weekly average)")
    print("-" * 84)
    print(f"{'nutrient':<26}{'min':>10}{'actual':>12}{'max':>11}  unit   status")
    group, short_list, over_list = None, [], []
    for n in NUTRIENTS:
        lo, hi = n.fediaf_min(), n.fmax
        if lo is None and hi is None:
            continue
        if n.group != group:
            group, = (n.group,)
            print(f"  [{group}]")
        actual = P.nutrient(n.key) / n.f2i / k1000
        if n.key in DATA_MISSING:
            status = "NO DATA"
        elif lo is not None and actual < lo * 0.995:
            status = f"SHORT ({100 * actual / lo:.0f} %)"
            short_list.append((n, lo, actual))
        elif hi is not None and actual > hi * 1.005:
            status = f"OVER  ({100 * actual / hi:.0f} % of max)"
            over_list.append((n, hi, actual))
        else:
            status = "ok"
        print(f"{n.label:<26}{'-' if lo is None else f'{lo:.4g}':>10}"
              f"{actual:>12.4g}{'-' if hi is None else f'{hi:.4g}':>11}"
              f"  {n.unit_label:<5}  {status}")

    ca, ph = P.nutrient("calcium"), P.nutrient("phosphorus")
    print(f"\nCa:P weekly            : {ca / ph:.2f} : 1   "
          f"(FEDIAF adult {CA_P_MIN:.0f}/1 .. {CA_P_MAX:.0f}/1)")
    for tag, items in (("insect meal", P.insect_items), ("fish meal", P.fish_items)):
        c = P.meal_nutrient(items, "calcium")
        p = P.meal_nutrient(items, "phosphorus")
        print(f"Ca:P {tag:<18}: {c / p:.2f} : 1")

    # ---------------- vet layer ---------------------------------------------
    print("\n" + "-" * 84)
    print(f"VET FATTY-ACID PROFILE  (targets = vet sheet x {VET_SCALE:.2f}, per day)")
    print("-" * 84)
    print(f"{'nutrient':<26}{'vet target':>12}{'actual':>12}{'%':>8}  unit")
    for n in NUTRIENTS:
        if n.group not in ("fats", "macros") or n.vet_target() is None:
            continue
        tgt = n.vet_target()
        act = P.nutrient(n.key)
        print(f"{n.label:<26}{tgt:>12.4g}{act:>12.4g}{100 * act / tgt:>7.0f}%  {n.internal}")
    n6 = P.nutrient("linoleic_acid_C18_2_n6") + P.nutrient("arachidonic_acid_C20_4_n6")
    n3 = (P.nutrient("alpha_linolenic_acid_C18_3_n3")
          + P.nutrient("eicosapentaenoic_acid_C20_5_n3")
          + P.nutrient("docosahexaenoic_acid_C22_6_n3"))
    print(f"{'n-6 : n-3 ratio':<26}{'5.5':>12}{n6 / n3:>12.2f}"
          f"{'':>8}  (window {N6_N3_MIN}-{N6_N3_MAX})")
    e_min = SPEC_BY_KEY["vitamin_e_tocopherols"].min_internal() * k1000
    e_need = e_min + VIT_E_PER_G_PUFA * P.nutrient("polyunsaturated")
    print(f"{'vitamin E vs PUFA load':<26}{e_need:>12.2f}"
          f"{P.nutrient('vitamin_e_tocopherols'):>12.2f}{'':>8}  mg alpha-TE")

    # ---------------- physical summary --------------------------------------
    w = P.scalar(WEIGHT_PG, add_supp_mass=True)
    wat = P.scalar(WATER_PG)
    dm = w - wat
    prot, fat, carb = (P.nutrient("protein"), P.nutrient("fat"), P.nutrient("carbs"))
    ash = P.scalar(ASH_PG)
    print("\n" + "-" * 84)
    print(f"Average day: {w:.0f} g served ({100 * wat / w:.1f} % water), "
          f"{dm:.1f} g DM, {kcal:.0f} kcal")
    print(f"  on DM basis: protein {100 * prot / dm:.1f} %, fat {100 * fat / dm:.1f} %, "
          f"carbs {100 * carb / dm:.1f} %, ash {100 * ash / dm:.1f} %"
          f"   (vet: 61.1 / 24.0 / 2.0 %)")

    # ---------------- blind spots -------------------------------------------
    blind = sorted(k for k in DATA_MISSING if SPEC_BY_KEY[k].fmin is not None)
    if blind:
        print("\n" + "-" * 84)
        print("BLIND SPOTS - FEDIAF requires these, no ingredient table has data")
        print("-" * 84)
        for k in blind:
            n = SPEC_BY_KEY[k]
            need = n.fediaf_min() * k1000
            covered = P.nutrient(k) / n.f2i
            print(f"  {n.label:<26}: need {need:.4g} {n.unit_label}/day, "
                  f"supplements give {covered:.4g} "
                  f"{'(supplementable)' if any(k in s.contents for s in SUPPLEMENTS) else '<-- ADD A SOURCE'}")
        print("  (set ENFORCE_UNTRACKED = True to force the solver to dose them blind)")

    if short_list or over_list:
        print("\n" + "-" * 84)
        print("FEDIAF NOT MET - fix ingredient bounds or add a source")
        print("-" * 84)
        for n, lo, act in short_list:
            print(f"  SHORT {n.label:<24}: {act:.4g} vs min {lo:.4g} {n.unit_label}/1000 kcal")
        for n, hi, act in over_list:
            print(f"  OVER  {n.label:<24}: {act:.4g} vs max {hi:.4g} {n.unit_label}/1000 kcal"
                  f"   [{n.fmax_src}]")


# =============================================================================
# 12. MAIN
# =============================================================================
def main() -> None:
    results = []
    for fish_days in FISH_DAYS_OPTIONS:
        for lo_daily in (True, False):
            res = solve(fish_days, lo_daily)
            if res is None:
                continue
            if res["status"] != "Optimal":
                print(f"[{DAYS - fish_days}+{fish_days}, liver oil "
                      f"{'daily' if lo_daily else 'fish days'}] -> {res['status']}")
                continue
            results.append(res)

    if not results:
        print("No feasible plan. Relax KCAL_TOL / DRY_TOL / moisture / bounds.")
        return

    # FEDIAF first, then the vet objective
    best = min(results, key=lambda r: (round(r["fediaf_violation"], 6), r["objective"]))
    print("Scenarios (FEDIAF violation first, then vet/PUFA objective):")
    for r in sorted(results, key=lambda r: (round(r["fediaf_violation"], 6), r["objective"])):
        lo = "daily" if r["liver_oil_everyday"] else "fish days"
        mark = "  <- chosen" if r is best else ""
        print(f"  {r['insect_days']}+{r['fish_days']} days, liver oil {lo:<10}: "
              f"FEDIAF {r['fediaf_violation']:8.5f}, vet {r['objective']:8.4f}{mark}")
    print()
    report(best)


if __name__ == "__main__":
    main()
