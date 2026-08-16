"""Weekly cat-diet optimiser / diagnostic  --  v2, energy-anchored.

Finds the weekly plan (5-6 insect days + 1-2 fish days) that comes closest to
the vet's nutrient profile, and reports exactly which nutrients are still
short or in excess, i.e. what actually has to be supplemented or reduced.

What changed vs v1
------------------
* ENERGY is the anchor.  The vet sheet is 354 kcal / 291.71 g of food.  We
  scale the *energy* down to the 210-240 g range and then require the diet to
  land inside a narrow kcal band.  v1 had no energy constraint at all, so the
  solver inflated every ingredient until 603 kcal/day.
* Nutrient targets are expressed per 1000 kcal (nutrient DENSITY).  This is
  how NRC/FEDIAF state requirements and it makes the plan invariant to the
  exact gram scaling.
* DRY MATTER, not served weight, is bounded.  Water is a computed filler that
  brings the meal to a chosen moisture (~74 %, like the vet sheet's 74.64 %).
  v1 forced 240 g of *served* weight and let the solver fill it with flour.
* Every soft nutrient now has BOTH a shortfall and an EXCESS slack, plus hard
  safety ceilings (ULs) for vitamins A, D, and the trace minerals.  v1 had
  only `>=` constraints, so overshooting was free.
* Vitamin E is a DYNAMIC target: base requirement + 0.6 mg alpha-TE per gram
  of dietary PUFA (NRC 2006 antioxidant coupling).  Enforced as a linear
  constraint, so a PUFA-heavy plan automatically demands more E.
* Supplement bounds are realistic: cod-liver oil is a vitamin source (<= 1.5
  g/day), not a fat source; yeast <= 5 g/day; eggs <= 7/week.
* Per-meal Ca:P is enforced by default (v1's fish day was Ca:P 0.110 : 1).

Units follow the nutrient tables: macros/fatty acids in g, everything else
(minerals, amino acids, vitamins, taurine) in mg; cholesterol is converted to
g because the target is expressed in g.

Requires: pulp (CBC bundled).
"""

from __future__ import annotations

import copy
from collections.abc import Callable
from dataclasses import dataclass

import pulp

from nutrients import *
from utils import (
    apply_cooking_degradation,
    combine_nutrition,
    energy_kcal,
    scale,
    scale_to_grams,
    summary,
)

# =============================================================================
# 1. CONFIGURATION
# =============================================================================
DAYS = 7

# ---- the vet sheet, verbatim -------------------------------------------------
REF_FOOD_G = 291.71  # "Peso tot. Alim. (g)"
REF_DRY_G = 73.98  # "Peso sost s.s. (g)"
REF_WATER_G = 217.74  # "Acqua totale (g)"
REF_KCAL = 354.00  # "KCalorie"
REF_MOISTURE = REF_WATER_G / REF_FOOD_G  # 0.7464

# ---- how far we scale it down ----------------------------------------------
# You asked for 210-240 g of finished food.  We hit that by scaling ENERGY,
# and let the served weight fall out of the moisture target.
TARGET_FOOD_G = 225.0  # midpoint of your 210-240 g request
SCALE = TARGET_FOOD_G / REF_FOOD_G  # ~0.771

KCAL_TARGET = REF_KCAL * SCALE  # ~273 kcal/day
KCAL_TOL = 0.07  # +/- 6 % band on daily energy  (hard)

DRY_TARGET = REF_DRY_G * SCALE  # ~57 g dry matter/day
DRY_TOL = 0.12  # +/- 12 % band on dry matter   (hard)

MOISTURE_MIN = 0.69  # finished meal must be 69-81 % water
MOISTURE_MAX = 0.81
SERVED_MIN = 205.0  # absolute guard rails on served grams
SERVED_MAX = 250.0

WATER_LOSS = 0.20  # water lost while cooking the insect meal
EGG_G = 50.0  # edible part of one average egg (no shell)

FISH_DAYS_OPTIONS = (1, 2, 3)
MIN_INSECT_DAYS = 4
MIN_INSECT_FLOUR_G = 15.0
MIN_FISH_G = 60.0

# The insect meal is a DOUGH: flour + egg + water.  Force enough water that it
# is actually a dough and not a powder.  Ratio is g water per g of flour.
DOUGH_WATER_PER_FLOUR_MIN = 1.6
DOUGH_WATER_PER_FLOUR_MAX = 4.5

COUNT_UNDIFFERENTIATED = True

CA_P_MIN, CA_P_MAX = 1.05, 1.25  # weekly average
CA_P_MEAL_MIN, CA_P_MEAL_MAX = 0.95, 1.60  # each meal type
PER_MEAL_CA_P = True  # v1 had this off -> fish day 0.11

# Vitamin E must rise with PUFA load: E >= E_base + VIT_E_PER_G_PUFA * PUFA
VIT_E_PER_G_PUFA = 0.6  # mg alpha-TE per g PUFA (NRC-style)
VIT_E_BASE_MG = 1.76 * SCALE

# =============================================================================
# 1b. INGREDIENT BOUNDS  (grams/day, raw as weighed)
# =============================================================================
BOUNDS = {
    # insect-day solids
    "bsfl": (0.0, 30.0),  # was 80 -> Mn/Zn/Fe bomb
    "mealworms": (0.0, 30.0),
    "water_insect": (0.0, 260.0),  # the dough water
    # fish-day solids
    "cod": (0.0, 140.0),
    "mussels": (0.0, 60.0),  # was 150 -> Mn/Zn/Fe/iodine bomb
    "cod_roe": (0.0, 25.0),
    "water_fish": (0.0, 200.0),
    # powders / oils, split per meal type where it matters
    "eggshells_i": (0.0, 3.0),  # eggshell on insect days
    "eggshells_f": (0.0, 3.0),  # eggshell on fish days  (Ca:P differs!)
    "yeast": (0.0, 5.0),  # was 12 -> B2 796 %
    "cod_liver_oil": (0.0, 1.5),  # was 8 -> vitamin D 1238 %
    "algal_oil": (0.0, 1.5),
    "taurine": (0.0, 0.6),
}
EGG_BOUNDS = {"eggs_insect_week": (0, 6), "eggs_fish_week": (0, 3)}
MAX_EGGS_WEEK = 7

# =============================================================================
# 1c. SAFETY CEILINGS (hard) and soft excess tolerance
# =============================================================================
# Hard ULs on the weekly average, in the same units as the Spec targets.
# Derived from NRC 2006 safe upper limits, scaled to this diet's energy.
KCAL_K = KCAL_TARGET / 1000.0  # thousands of kcal per day

MAX_TARGETS: dict[str, float] = {
    "vitamin_a_retinol": KCAL_K * 25.0,  # mg/1000 kcal  (~100k IU)
    "vitamin_d3_cholecalciferol": KCAL_K * 0.0188,  # mg/1000 kcal  (~750 IU)
    "vitamin_e_tocopherols": KCAL_K * 300.0,
    "vitamin_b3_niacin": KCAL_K * 200.0,
    "zinc": KCAL_K * 60.0,
    "copper": KCAL_K * 6.0,
    "iron": KCAL_K * 60.0,
    "manganese": KCAL_K * 12.0,
    "iodine": KCAL_K * 1.4,
    "selenium": KCAL_K * 0.60,
    "calcium": KCAL_K * 6000.0,
    "phosphorus": KCAL_K * 4500.0,
    "magnesium": KCAL_K * 400.0,
    "sodium": KCAL_K * 1500.0,
}

# How far above target a nutrient may go before it costs anything (soft).
# You said: "a bit more of vitamins are fine, a bit less of minerals are fine".
DEFAULT_OVER_FACTOR = 2.0
OVER_FACTOR = {
    # vitamins: generous headroom
    "vitamin_b1_thiamin": 8.0,
    "vitamin_b2_riboflavin": 8.0,
    "vitamin_b5_pantothenic_acid": 8.0,
    "vitamin_b6": 8.0,
    "vitamin_b9_folate": 8.0,
    "vitamin_b12_cobalamin": 20.0,
    "vitamin_c_ascorbic_acid": 10.0,
    "vitamin_b3_niacin": 6.0,
    "vitamin_b8_biotin": 10.0,
    "vitamin_e_tocopherols": 10.0,
    "vitamin_a_retinol": 4.0,
    "vitamin_d3_cholecalciferol": 3.0,
    # amino acids: protein-rich diet, overshoot is harmless
    "tryptophan": 4.0,
    "threonine": 4.0,
    "isoleucine": 4.0,
    "leucine": 4.0,
    "lysine": 4.0,
    "methionine": 3.0,
    "cysteine": 4.0,
    "phenylalanine": 4.0,
    "tyrosine": 4.0,
    "valine": 4.0,
    "arginine": 4.0,
    "histidine": 4.0,
    "taurine": 6.0,
    # minerals: tight, these are the ones that ran away in v1
    "calcium": 1.35,
    "phosphorus": 1.35,
    "potassium": 2.0,
    "sodium": 2.5,
    "magnesium": 2.0,
    "iron": 2.5,
    "zinc": 2.5,
    "copper": 2.5,
    "manganese": 3.0,
    "iodine": 3.0,
    "selenium": 3.0,
    # fats: keep the profile honest
    "saturated": 1.6,
    "monounsaturated": 1.8,
    "polyunsaturated": 1.6,
    "linoleic_acid_C18_2_n6": 2.0,
    "alpha_linolenic_acid_C18_3_n3": 6.0,
    "arachidonic_acid_C20_4_n6": 4.0,
    "eicosapentaenoic_acid_C20_5_n3": 4.0,
    "docosahexaenoic_acid_C22_6_n3": 4.0,
    "cholesterol": 2.5,
    # macros
    "protein": 1.6,
    "fat": 1.5,
    "carbs": 2.0,
}

# Relative weight of each SHORTFALL in the objective.
DEFICIT_WEIGHTS = {
    "taurine": 6.0,
    "docosahexaenoic_acid_C22_6_n3": 4.0,
    "eicosapentaenoic_acid_C20_5_n3": 3.0,
    "arachidonic_acid_C20_4_n6": 4.0,
    "lysine": 2.0,
    "methionine": 2.0,
    "cysteine": 2.0,
    "vitamin_a_retinol": 2.0,
    "vitamin_e_tocopherols": 3.0,
    "calcium": 3.0,
    "phosphorus": 3.0,
    "protein": 4.0,
    "fat": 3.0,
}
# Relative weight of each EXCESS in the objective.
EXCESS_WEIGHTS = {
    "manganese": 4.0,
    "zinc": 3.0,
    "iron": 3.0,
    "copper": 3.0,
    "selenium": 3.0,
    "iodine": 3.0,
    "magnesium": 2.0,
    "sodium": 2.0,
    "vitamin_d3_cholecalciferol": 5.0,
    "vitamin_a_retinol": 3.0,
    "carbs": 3.0,
    "fat": 3.0,
    "saturated": 2.0,
    "monounsaturated": 2.0,
    "polyunsaturated": 2.0,
    "cholesterol": 2.0,
    "calcium": 2.0,
    "phosphorus": 2.0,
}
DEFAULT_EXCESS_WEIGHT = 1.0

KCAL_DEV_WEIGHT = 40.0  # penalty per relative unit of energy deviation
GRAM_COST = 0.02  # meaningful regulariser now (was 1e-4)

# =============================================================================
# 2. PSEUDO-INGREDIENTS (per 100 g, same table structure as nutrients/)
# =============================================================================
WATER_TABLE = {"water": 100.0}

TAURINE_TABLE = {"others": {"taurine": 100_000.0}, "water": 0.0}

# PLACEHOLDER - replace with your actual algal-oil label (per 100 g of oil).
ALGAL_OIL_TABLE = {
    "fats": {
        "saturated": {"myristic_acid_C14_0": 5.0, "palmitic_acid_C16_0": 25.0},
        "monounsaturated": {"oleic_acid_C18_1_n9": 8.0},
        "polyunsaturated": {
            "eicosapentaenoic_acid_C20_5_n3": 10.0,
            "docosapentaenoic_acid_C22_5_n3": 5.0,
            "docosahexaenoic_acid_C22_6_n3": 40.0,
        },
        "others": 7.0,
    },
    "water": 0.0,
}

EGGSHELL_TABLE = copy.deepcopy(EGGSHELLS_TABLE)


# =============================================================================
# 3. NUTRIENT ACCESSORS
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


def amino(*names: str) -> Callable[[dict], float]:  # g -> mg
    return lambda p: 1000.0 * sum(_section(p, "proteins").get(n, 0.0) for n in names)


def vitamin(*names: str) -> Callable[[dict], float]:
    return lambda p: sum(_section(p, "vitamins").get(n, 0.0) for n in names)


def vitamin_family(prefix: str) -> Callable[[dict], float]:
    return lambda p: sum(
        v for k, v in _section(p, "vitamins").items() if k.startswith(prefix)
    )


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


@dataclass(frozen=True)
class Spec:
    key: str
    label: str
    unit: str
    target: float
    getter: Callable[[dict], float]
    hard_min: bool = False  # no shortfall allowed
    group: str = ""
    dynamic: bool = False  # target computed from the solution (vit E)


# Everything below is the vet sheet * SCALE, i.e. the same profile at ~225 g.
NUTRIENTS: list[Spec] = [
    # ---------------- macros ----------------
    Spec("protein", "protein", "g", 45.20 * SCALE, macro("proteins"), group="macros"),
    Spec("fat", "fat", "g", 17.73 * SCALE, macro("fats"), group="macros"),
    Spec("carbs", "carbohydrate", "g", 3.28 * SCALE, macro("carbs"), group="macros"),
    # ---------------- minerals (mg) ----------------
    Spec(
        "calcium",
        "calcium",
        "mg",
        1359.50 * SCALE,
        mineral("calcium"),
        group="minerals",
    ),
    Spec(
        "phosphorus",
        "phosphorus",
        "mg",
        1358.73 * SCALE,
        mineral("phosphorus"),
        group="minerals",
    ),
    Spec(
        "potassium",
        "potassium",
        "mg",
        781.86 * SCALE,
        mineral("potassium"),
        group="minerals",
    ),
    Spec("sodium", "sodium", "mg", 213.03 * SCALE, mineral("sodium"), group="minerals"),
    Spec(
        "magnesium",
        "magnesium",
        "mg",
        59.48 * SCALE,
        mineral("magnesium"),
        group="minerals",
    ),
    Spec("iron", "iron", "mg", 4.79 * SCALE, mineral("iron"), group="minerals"),
    Spec("zinc", "zinc", "mg", 6.48 * SCALE, mineral("zinc"), group="minerals"),
    Spec("copper", "copper", "mg", 0.93 * SCALE, mineral("copper"), group="minerals"),
    Spec(
        "manganese",
        "manganese",
        "mg",
        0.12 * SCALE,
        mineral("manganese"),
        group="minerals",
    ),
    Spec("iodine", "iodine", "mg", 0.10 * SCALE, mineral("iodine"), group="minerals"),
    Spec(
        "selenium",
        "selenium",
        "mg",
        32.69 / 1000.0 * SCALE,
        mineral("selenium"),
        group="minerals",
    ),
    # ---------------- vitamins (mg) ----------------
    Spec(
        "vitamin_a_retinol",
        "vitamin A (retinol)",
        "mg",
        6501.38 * 0.3 / 1000.0 * SCALE,
        vitamin("vitamin_a_retinol"),
        group="vitamins",
    ),
    Spec(
        "vitamin_b1_thiamin",
        "vitamin B1",
        "mg",
        0.58 * SCALE,
        vitamin("vitamin_b1_thiamin"),
        group="vitamins",
    ),
    Spec(
        "vitamin_b2_riboflavin",
        "vitamin B2",
        "mg",
        0.83 * SCALE,
        vitamin("vitamin_b2_riboflavin"),
        group="vitamins",
    ),
    Spec(
        "vitamin_b3_niacin",
        "vitamin B3",
        "mg",
        12.71 * SCALE,
        vitamin("vitamin_b3_niacin"),
        group="vitamins",
    ),
    Spec(
        "vitamin_b5_pantothenic_acid",
        "vitamin B5",
        "mg",
        3.45 * SCALE,
        vitamin("vitamin_b5_pantothenic_acid"),
        group="vitamins",
    ),
    Spec(
        "vitamin_b6",
        "vitamin B6",
        "mg",
        0.79 * SCALE,
        vitamin("vitamin_b6"),
        group="vitamins",
    ),
    Spec(
        "vitamin_b8_biotin",
        "vitamin B8 (biotin)",
        "mg",
        7.67 / 1000.0 * SCALE,
        vitamin("vitamin_b8_biotin"),
        group="vitamins",
    ),
    Spec(
        "vitamin_b9_folate",
        "vitamin B9 (folate)",
        "mg",
        44.16 / 1000.0 * SCALE,
        vitamin("vitamin_b9_folate"),
        group="vitamins",
    ),
    Spec(
        "vitamin_b12_cobalamin",
        "vitamin B12",
        "mg",
        16.28 / 1000.0 * SCALE,
        vitamin("vitamin_b12_cobalamin"),
        group="vitamins",
    ),
    Spec(
        "vitamin_c_ascorbic_acid",
        "vitamin C",
        "mg",
        5.72 * SCALE,
        vitamin("vitamin_c_ascorbic_acid"),
        group="vitamins",
    ),
    Spec(
        "vitamin_d3_cholecalciferol",
        "vitamin D3",
        "mg",
        87.22 * 0.025 / 1000.0 * SCALE,
        vitamin("vitamin_d3_cholecalciferol", "vitamin_d"),
        group="vitamins",
    ),
    # NOTE: dynamic target, recomputed from the PUFA content of the solution.
    Spec(
        "vitamin_e_tocopherols",
        "vitamin E",
        "mg",
        VIT_E_BASE_MG,
        vitamin_family("vitamin_e"),
        group="vitamins",
        dynamic=True,
    ),
    # ---------------- amino acids (mg) ----------------
    Spec(
        "tryptophan",
        "tryptophan",
        "mg",
        492.73 * SCALE,
        amino("tryptophan"),
        group="amino acids",
    ),
    Spec(
        "threonine",
        "threonine",
        "mg",
        2208.56 * SCALE,
        amino("threonine"),
        group="amino acids",
    ),
    Spec(
        "isoleucine",
        "isoleucine",
        "mg",
        2278.46 * SCALE,
        amino("isoleucine"),
        group="amino acids",
    ),
    Spec(
        "leucine",
        "leucine",
        "mg",
        3794.13 * SCALE,
        amino("leucine"),
        group="amino acids",
    ),
    Spec(
        "lysine", "lysine", "mg", 4101.94 * SCALE, amino("lysine"), group="amino acids"
    ),
    Spec(
        "methionine",
        "methionine",
        "mg",
        1300.21 * SCALE,
        amino("methionine"),
        group="amino acids",
    ),
    Spec(
        "cysteine",
        "cysteine + cystine",
        "mg",
        541.57 * SCALE,
        amino("cysteine", "cystine"),
        group="amino acids",
    ),
    Spec(
        "phenylalanine",
        "phenylalanine",
        "mg",
        2002.09 * SCALE,
        amino("phenylalanine"),
        group="amino acids",
    ),
    Spec(
        "tyrosine",
        "tyrosine",
        "mg",
        1579.61 * SCALE,
        amino("tyrosine"),
        group="amino acids",
    ),
    Spec(
        "valine", "valine", "mg", 2511.67 * SCALE, amino("valine"), group="amino acids"
    ),
    Spec(
        "arginine",
        "arginine",
        "mg",
        2944.64 * SCALE,
        amino("arginine"),
        group="amino acids",
    ),
    Spec(
        "histidine",
        "histidine",
        "mg",
        1297.03 * SCALE,
        amino("histidine"),
        group="amino acids",
    ),
    Spec(
        "taurine", "taurine", "mg", 250.0 * SCALE, other("taurine"), group="amino acids"
    ),
    # ---------------- fats (g) ----------------
    Spec(
        "saturated",
        "saturated FA",
        "g",
        6.90 * SCALE,
        fat_class("saturated"),
        group="fats",
    ),
    Spec(
        "monounsaturated",
        "monounsaturated FA",
        "g",
        4.23 * SCALE,
        fat_class("monounsaturated"),
        group="fats",
    ),
    Spec(
        "polyunsaturated",
        "polyunsaturated FA",
        "g",
        3.40 * SCALE,
        fat_class("polyunsaturated"),
        group="fats",
    ),
    Spec(
        "linoleic_acid_C18_2_n6",
        "linoleic acid 18:2 n-6",
        "g",
        2.72 * SCALE,
        fatty_acid(*LA_KEYS),
        group="fats",
    ),
    Spec(
        "alpha_linolenic_acid_C18_3_n3",
        "alpha-linolenic acid 18:3 n-3",
        "g",
        0.10 * SCALE,
        fatty_acid(*ALA_KEYS),
        group="fats",
    ),
    Spec(
        "arachidonic_acid_C20_4_n6",
        "arachidonic acid 20:4 n-6",
        "g",
        0.30 * SCALE,
        fatty_acid(*ARA_KEYS),
        group="fats",
    ),
    Spec(
        "eicosapentaenoic_acid_C20_5_n3",
        "EPA 20:5 n-3",
        "g",
        0.15 * SCALE,
        fatty_acid("eicosapentaenoic_acid_C20_5_n3"),
        group="fats",
    ),
    Spec(
        "docosahexaenoic_acid_C22_6_n3",
        "DHA 22:6 n-3",
        "g",
        0.30 * SCALE,
        fatty_acid("docosahexaenoic_acid_C22_6_n3"),
        group="fats",
    ),
    Spec(
        "cholesterol",
        "cholesterol",
        "g",
        197.84 / 1000.0 * SCALE,
        other("cholesterol", 1e-3),
        group="fats",
    ),
]

SPEC_BY_KEY = {s.key: s for s in NUTRIENTS}
SOFT = [s for s in NUTRIENTS if not s.hard_min]


# =============================================================================
# 4. PER-GRAM INGREDIENT PROFILES
# =============================================================================
@dataclass(frozen=True)
class Ingredient:
    key: str
    label: str
    table: dict
    cooked: bool = False


INGREDIENTS = {
    # insect meal (cooked)
    "bsfl": Ingredient("bsfl", "BSFL flour", BSFL_TABLE, cooked=True),
    "mealworms": Ingredient(
        "mealworms", "mealworm flour", MEALWORMS_TABLE, cooked=True
    ),
    "eggs_cooked": Ingredient(
        "eggs_cooked", "whole egg (cooked)", EGGS_TABLE, cooked=True
    ),
    "water_insect": Ingredient(
        "water_insect", "water (partly cooked off)", WATER_TABLE, cooked=True
    ),
    # fish meal (raw)
    "cod": Ingredient("cod", "wild cod", COD_TABLE),
    "mussels": Ingredient("mussels", "blue mussels", MUSSELS_TABLE),
    "cod_roe": Ingredient("cod_roe", "cod roe", COD_ROE_TABLE),
    "eggs_raw": Ingredient("eggs_raw", "whole egg (raw)", EGGS_TABLE),
    "water_fish": Ingredient("water_fish", "water", WATER_TABLE),
    # powders / oils, added after cooking
    "eggshells": Ingredient("eggshells", "eggshell powder", EGGSHELL_TABLE),
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
WEIGHT = {k: summary(p, sig=12)["weight"] for k, p in PROFILE.items()}
COEFF = {k: {s.key: s.getter(p) for s in NUTRIENTS} for k, p in PROFILE.items()}

# per-gram kcal and per-gram dry matter / water, needed for the new constraints
KCAL_PG = {k: energy_kcal(p) for k, p in PROFILE.items()}
WATER_PG = {k: summary(p, sig=12)["water"] for k, p in PROFILE.items()}
DRY_PG = {k: WEIGHT[k] - WATER_PG[k] for k in PROFILE}

# per-gram PUFA, for the dynamic vitamin-E constraint
PUFA_PG = {k: COEFF[k]["polyunsaturated"] for k in PROFILE}
VITE_PG = {k: COEFF[k]["vitamin_e_tocopherols"] for k in PROFILE}


# =============================================================================
# 5. THE OPTIMISATION MODEL
# =============================================================================
def solve(fish_days: int, liver_oil_everyday: bool) -> dict | None:
    C = fish_days
    S = DAYS - C
    if S < MIN_INSECT_DAYS:
        return None

    prob = pulp.LpProblem(
        f"cat_diet_C{C}_lo{'daily' if liver_oil_everyday else 'fish'}", pulp.LpMinimize
    )

    def var(name):
        low, high = BOUNDS[name]
        return pulp.LpVariable(name, lowBound=low, upBound=high)

    x = {name: var(name) for name in BOUNDS}
    eggs_i = pulp.LpVariable(
        "eggs_insect_week", *EGG_BOUNDS["eggs_insect_week"], cat="Integer"
    )
    eggs_f = pulp.LpVariable(
        "eggs_fish_week", *EGG_BOUNDS["eggs_fish_week"], cat="Integer"
    )
    prob += eggs_i + eggs_f <= MAX_EGGS_WEEK, "max_eggs_week"

    lo_days = DAYS if liver_oil_everyday else C

    # ---- weekly grams of each ingredient ------------------------------------
    weekly = [
        (S * x["bsfl"], "bsfl"),
        (S * x["mealworms"], "mealworms"),
        (S * x["water_insect"], "water_insect"),
        (EGG_G * eggs_i, "eggs_cooked"),
        (C * x["cod"], "cod"),
        (C * x["mussels"], "mussels"),
        (C * x["cod_roe"], "cod_roe"),
        (C * x["water_fish"], "water_fish"),
        (EGG_G * eggs_f, "eggs_raw"),
        (S * x["eggshells_i"], "eggshells"),
        (C * x["eggshells_f"], "eggshells"),
        (DAYS * x["yeast"], "yeast"),
        (lo_days * x["cod_liver_oil"], "cod_liver_oil"),
        (DAYS * x["algal_oil"], "algal_oil"),
        (DAYS * x["taurine"], "taurine"),
    ]

    def avg(key):
        """Weekly-average daily supply of `key`."""
        return pulp.lpSum(g * COEFF[i][key] for g, i in weekly) / DAYS

    def avg_of(table):
        return pulp.lpSum(g * table[i] for g, i in weekly) / DAYS

    # ---- ENERGY: the anchor that v1 was missing -----------------------------
    kcal_avg = avg_of(KCAL_PG)
    prob += kcal_avg >= KCAL_TARGET * (1 - KCAL_TOL), "kcal_lo"
    prob += kcal_avg <= KCAL_TARGET * (1 + KCAL_TOL), "kcal_hi"

    kcal_dev = pulp.LpVariable("kcal_dev", lowBound=0)
    prob += kcal_dev >= kcal_avg - KCAL_TARGET, "kcal_dev_pos"
    prob += kcal_dev >= KCAL_TARGET - kcal_avg, "kcal_dev_neg"

    # ---- DRY MATTER band (replaces v1's served-weight equality) -------------
    dry_avg = avg_of(DRY_PG)
    prob += dry_avg >= DRY_TARGET * (1 - DRY_TOL), "dry_lo"
    prob += dry_avg <= DRY_TARGET * (1 + DRY_TOL), "dry_hi"

    # ---- served weight and moisture, per meal type --------------------------
    supp_common = (
        WEIGHT["yeast"] * x["yeast"]
        + WEIGHT["algal_oil"] * x["algal_oil"]
        + WEIGHT["taurine"] * x["taurine"]
    )
    lo_w = WEIGHT["cod_liver_oil"] * x["cod_liver_oil"]

    insect_w = (
        WEIGHT["bsfl"] * x["bsfl"]
        + WEIGHT["mealworms"] * x["mealworms"]
        + WEIGHT["eggs_cooked"] * (EGG_G / S) * eggs_i
        + WEIGHT["water_insect"] * x["water_insect"]
        + WEIGHT["eggshells"] * x["eggshells_i"]
        + supp_common
        + (lo_w if liver_oil_everyday else 0)
    )
    fish_w = (
        WEIGHT["cod"] * x["cod"]
        + WEIGHT["mussels"] * x["mussels"]
        + WEIGHT["cod_roe"] * x["cod_roe"]
        + WEIGHT["eggs_raw"] * (EGG_G / C) * eggs_f
        + WEIGHT["water_fish"] * x["water_fish"]
        + WEIGHT["eggshells"] * x["eggshells_f"]
        + supp_common
        + lo_w
    )

    insect_water = (
        WATER_PG["bsfl"] * x["bsfl"]
        + WATER_PG["mealworms"] * x["mealworms"]
        + WATER_PG["eggs_cooked"] * (EGG_G / S) * eggs_i
        + WATER_PG["water_insect"] * x["water_insect"]
    )
    fish_water = (
        WATER_PG["cod"] * x["cod"]
        + WATER_PG["mussels"] * x["mussels"]
        + WATER_PG["cod_roe"] * x["cod_roe"]
        + WATER_PG["eggs_raw"] * (EGG_G / C) * eggs_f
        + WATER_PG["water_fish"] * x["water_fish"]
    )

    for tag, w, wat in (
        ("insect", insect_w, insect_water),
        ("fish", fish_w, fish_water),
    ):
        prob += w >= SERVED_MIN, f"{tag}_served_lo"
        prob += w <= SERVED_MAX, f"{tag}_served_hi"
        prob += wat >= MOISTURE_MIN * w, f"{tag}_moist_lo"
        prob += wat <= MOISTURE_MAX * w, f"{tag}_moist_hi"

    # ---- the dough really needs water (v1 produced a dry powder) -----------
    flour = x["bsfl"] + x["mealworms"]
    prob += x["water_insect"] >= DOUGH_WATER_PER_FLOUR_MIN * flour, "dough_water_lo"
    prob += x["water_insect"] <= DOUGH_WATER_PER_FLOUR_MAX * flour, "dough_water_hi"

    prob += flour >= MIN_INSECT_FLOUR_G, "min_insect_flour"
    prob += x["cod"] + x["mussels"] + x["cod_roe"] >= MIN_FISH_G, "min_fish"

    # ---- Ca:P -------------------------------------------------------------
    prob += avg("calcium") - CA_P_MAX * avg("phosphorus") <= 0, "ca_p_upper"
    prob += avg("calcium") - CA_P_MIN * avg("phosphorus") >= 0, "ca_p_lower"

    if PER_MEAL_CA_P:
        insect_ings = [
            (x["bsfl"], "bsfl"),
            (x["mealworms"], "mealworms"),
            ((EGG_G / S) * eggs_i, "eggs_cooked"),
            (x["eggshells_i"], "eggshells"),
            (x["yeast"], "yeast"),
        ]
        fish_ings = [
            (x["cod"], "cod"),
            (x["mussels"], "mussels"),
            (x["cod_roe"], "cod_roe"),
            ((EGG_G / C) * eggs_f, "eggs_raw"),
            (x["eggshells_f"], "eggshells"),
            (x["yeast"], "yeast"),
        ]
        for tag, ings in (("insect", insect_ings), ("fish", fish_ings)):
            ca = pulp.lpSum(e * COEFF[i]["calcium"] for e, i in ings)
            ph = pulp.lpSum(e * COEFF[i]["phosphorus"] for e, i in ings)
            prob += ca - CA_P_MEAL_MAX * ph <= 0, f"{tag}_ca_p_up"
            prob += ca - CA_P_MEAL_MIN * ph >= 0, f"{tag}_ca_p_lo"

    # ---- VITAMIN E coupled to PUFA (the thing you asked to monitor) --------
    pufa_avg = avg_of(PUFA_PG)
    vite_avg = avg_of(VITE_PG)
    vite_need = VIT_E_BASE_MG + VIT_E_PER_G_PUFA * pufa_avg
    vite_def = pulp.LpVariable("deficit_vitamin_e_dynamic", lowBound=0)
    prob += vite_avg + vite_def >= vite_need, "vitE_vs_pufa"

    # ---- soft two-sided constraints ---------------------------------------
    deficit, excess = {}, {}
    for s in SOFT:
        d = pulp.LpVariable(f"deficit_{s.key}", lowBound=0)
        e = pulp.LpVariable(f"excess_{s.key}", lowBound=0)
        deficit[s.key], excess[s.key] = d, e
        cap = OVER_FACTOR.get(s.key, DEFAULT_OVER_FACTOR) * s.target
        prob += avg(s.key) + d >= s.target, f"soft_lo_{s.key}"
        prob += avg(s.key) - e <= cap, f"soft_hi_{s.key}"

    # ---- hard safety ceilings ----------------------------------------------
    for key, ceiling in MAX_TARGETS.items():
        prob += avg(key) <= ceiling, f"max_{key}"

    # ---- objective ---------------------------------------------------------
    prob.setObjective(
        pulp.lpSum(
            DEFICIT_WEIGHTS.get(s.key, 1.0) * deficit[s.key] / s.target for s in SOFT
        )
        + pulp.lpSum(
            EXCESS_WEIGHTS.get(s.key, DEFAULT_EXCESS_WEIGHT) * excess[s.key] / s.target
            for s in SOFT
        )
        + DEFICIT_WEIGHTS.get("vitamin_e_tocopherols", 3.0) * vite_def / VIT_E_BASE_MG
        + KCAL_DEV_WEIGHT * kcal_dev / KCAL_TARGET
        + GRAM_COST
        * pulp.lpSum(
            x[k]
            for k in (
                "bsfl",
                "mealworms",
                "cod",
                "mussels",
                "cod_roe",
                "eggshells_i",
                "eggshells_f",
                "yeast",
                "cod_liver_oil",
                "algal_oil",
                "taurine",
            )
        )
    )

    prob.solve(pulp.PULP_CBC_CMD(msg=False))
    if pulp.LpStatus[prob.status] != "Optimal":
        return {
            "status": pulp.LpStatus[prob.status],
            "fish_days": C,
            "liver_oil_everyday": liver_oil_everyday,
        }

    sol = {k: float(v.value()) for k, v in x.items()}
    sol["eggs_insect_week"] = round(eggs_i.value())
    sol["eggs_fish_week"] = round(eggs_f.value())
    return {
        "status": "Optimal",
        "objective": float(pulp.value(prob.objective)),
        "fish_days": C,
        "insect_days": S,
        "liver_oil_everyday": liver_oil_everyday,
        "solution": sol,
        "deficits": {k: float(v.value()) for k, v in deficit.items()},
        "excesses": {k: float(v.value()) for k, v in excess.items()},
        "kcal_avg": float(pulp.value(kcal_avg)),
    }


# =============================================================================
# 6. REBUILD THE ACTUAL MEALS
# =============================================================================
def build_meals(result: dict) -> tuple[dict, dict, dict]:
    sol = result["solution"]
    S, C = result["insect_days"], result["fish_days"]
    egg_ins_day = sol["eggs_insect_week"] * EGG_G / S
    egg_fish_day = sol["eggs_fish_week"] * EGG_G / C

    supp_common = [
        scale_to_grams(YEAST_TABLE, sol["yeast"]),
        scale_to_grams(ALGAL_OIL_TABLE, sol["algal_oil"]),
        scale_to_grams(TAURINE_TABLE, sol["taurine"]),
    ]
    liver_oil = scale_to_grams(COD_LIVER_OIL_TABLE, sol["cod_liver_oil"])

    insect_cooked = apply_cooking_degradation(
        combine_nutrition(
            scale_to_grams(BSFL_TABLE, sol["bsfl"]),
            scale_to_grams(MEALWORMS_TABLE, sol["mealworms"]),
            scale_to_grams(EGGS_TABLE, egg_ins_day),
            scale_to_grams(WATER_TABLE, sol["water_insect"]),
        ),
        water_loss_rate=WATER_LOSS,
    )
    insect_meal = combine_nutrition(
        insect_cooked,
        scale_to_grams(EGGSHELL_TABLE, sol["eggshells_i"]),
        *supp_common,
        *([liver_oil] if result["liver_oil_everyday"] else []),
    )

    fish_meal = combine_nutrition(
        scale_to_grams(COD_TABLE, sol["cod"]),
        scale_to_grams(MUSSELS_TABLE, sol["mussels"]),
        scale_to_grams(COD_ROE_TABLE, sol["cod_roe"]),
        scale_to_grams(EGGS_TABLE, egg_fish_day),
        scale_to_grams(WATER_TABLE, sol["water_fish"]),
        scale_to_grams(EGGSHELL_TABLE, sol["eggshells_f"]),
        liver_oil,
        *supp_common,
    )

    daily = scale(
        combine_nutrition(scale(insect_meal, S), scale(fish_meal, C)), 1.0 / DAYS
    )
    return insect_meal, fish_meal, daily


# =============================================================================
# 7. REPORT
# =============================================================================
def effective_target(spec: Spec, daily: dict) -> float:
    """Vitamin E's requirement depends on the PUFA actually delivered."""
    if spec.key == "vitamin_e_tocopherols":
        pufa = SPEC_BY_KEY["polyunsaturated"].getter(daily)
        return max(VIT_E_BASE_MG, VIT_E_BASE_MG + VIT_E_PER_G_PUFA * pufa)
    return spec.target


def report(result: dict) -> None:
    sol = result["solution"]
    S, C = result["insect_days"], result["fish_days"]
    insect_meal, fish_meal, daily = build_meals(result)

    print("=" * 78)
    print(
        f"WEEKLY PLAN : {S} insect days + {C} fish day(s)"
        f"   |   cod-liver oil {'every day' if result['liver_oil_everyday'] else 'fish days only'}"
    )
    print(
        f"Energy anchor: {KCAL_TARGET:.0f} kcal/day target "
        f"(vet sheet {REF_KCAL:.0f} kcal at {REF_FOOD_G:.0f} g, scaled x{SCALE:.3f})"
    )
    print("=" * 78)

    si, sf = summary(insect_meal), summary(fish_meal)
    print(f"\nINSECT DOUGH - {S} days/week (raw grams, cooked together)")
    print(f"  BSFL flour           : {sol['bsfl']:7.1f} g")
    print(f"  Mealworm flour       : {sol['mealworms']:7.1f} g")
    print(
        f"  Whole egg            : {sol['eggs_insect_week'] * EGG_G / S:7.1f} g"
        f"   ({sol['eggs_insect_week']} eggs/week in the batch)"
    )
    print(
        f"  Water (into dough)   : {sol['water_insect']:7.1f} g"
        f"   ({WATER_LOSS:.0%} boils off)"
    )
    print(f"  Eggshell powder      : {sol['eggshells_i']:7.2f} g")
    print(
        f"  -> served            : {si['weight']:7.1f} g, {energy_kcal(insect_meal):6.0f} kcal, "
        f"{100 * si['water'] / si['weight']:4.1f} % water, "
        f"{si['weight'] - si['water']:5.1f} g DM"
    )

    print(f"\nFISH MEAL - {C} day(s)/week (raw grams)")
    print(f"  Wild cod             : {sol['cod']:7.1f} g")
    print(f"  Blue mussels         : {sol['mussels']:7.1f} g")
    print(f"  Cod roe              : {sol['cod_roe']:7.1f} g")
    print(
        f"  Whole egg            : {sol['eggs_fish_week'] * EGG_G / C:7.1f} g"
        f"   ({sol['eggs_fish_week']} eggs/week)"
    )
    print(f"  Water                : {sol['water_fish']:7.1f} g")
    print(f"  Eggshell powder      : {sol['eggshells_f']:7.2f} g")
    print(
        f"  -> served            : {sf['weight']:7.1f} g, {energy_kcal(fish_meal):6.0f} kcal, "
        f"{100 * sf['water'] / sf['weight']:4.1f} % water, "
        f"{sf['weight'] - sf['water']:5.1f} g DM"
    )

    print("\nDAILY POWDERS / OILS (both meal types)")
    print(f"  Nutritional yeast    : {sol['yeast']:7.2f} g")
    print(
        f"  Cod liver oil        : {sol['cod_liver_oil']:7.2f} g"
        f"   ({'daily' if result['liver_oil_everyday'] else 'fish days only'})"
    )
    print(f"  Algal EPA/DHA oil    : {sol['algal_oil']:7.2f} g")
    print(f"  Taurine powder       : {sol['taurine']:7.3f} g")

    shopping = {
        "BSFL flour": S * sol["bsfl"],
        "Mealworm flour": S * sol["mealworms"],
        "Eggs (n)": sol["eggs_insect_week"] + sol["eggs_fish_week"],
        "Wild cod": C * sol["cod"],
        "Blue mussels": C * sol["mussels"],
        "Cod roe": C * sol["cod_roe"],
        "Eggshell powder": S * sol["eggshells_i"] + C * sol["eggshells_f"],
        "Nutritional yeast": DAYS * sol["yeast"],
        "Cod liver oil": (DAYS if result["liver_oil_everyday"] else C)
        * sol["cod_liver_oil"],
        "Algal oil": DAYS * sol["algal_oil"],
        "Taurine": DAYS * sol["taurine"],
    }
    print("\nWEEKLY SHOPPING LIST")
    for name, amount in shopping.items():
        if amount > 1e-6:
            unit = "" if name.endswith("(n)") else " g"
            print(f"  {name:<22}: {amount:8.1f}{unit}")

    print("\n" + "-" * 78)
    print("NUTRIENT BALANCE (weekly average per day)")
    print("-" * 78)
    print(f"{'nutrient':<26}{'target':>11}{'supplied':>12}{'%':>8}{'cap':>10}  unit")
    shortfalls, overs = [], []
    group = None
    for spec in NUTRIENTS:
        if spec.group != group:
            group = spec.group
            print(f"  [{group}]")
        tgt = effective_target(spec, daily)
        supplied = spec.getter(daily)
        cap = OVER_FACTOR.get(spec.key, DEFAULT_OVER_FACTOR) * tgt
        pct = 100.0 * supplied / tgt if tgt else float("inf")
        flag = ""
        if pct < 90.0:
            flag = "  <-- SHORT"
            shortfalls.append((spec, tgt - supplied, pct))
        elif supplied > cap:
            flag = "  <-- OVER CAP"
            overs.append((spec, pct, cap, supplied))
        star = " *" if spec.dynamic else ""
        print(
            f"{spec.label + star:<26}{tgt:>11.4g}{supplied:>12.4g}{pct:>7.0f}%{cap:>10.4g}  {spec.unit}{flag}"
        )

    print(
        "  * vitamin E target = base + "
        f"{VIT_E_PER_G_PUFA} mg per g PUFA  (PUFA = "
        f"{SPEC_BY_KEY['polyunsaturated'].getter(daily):.2f} g)"
    )

    ca, ph = SPEC_BY_KEY["calcium"].getter(daily), SPEC_BY_KEY["phosphorus"].getter(
        daily
    )
    print(
        f"\nCa:P (weekly average)   : {ca / ph:.3f} : 1   (window {CA_P_MIN}-{CA_P_MAX})"
    )
    for label, meal in (("insect meal", insect_meal), ("fish meal", fish_meal)):
        c, p = SPEC_BY_KEY["calcium"].getter(meal), SPEC_BY_KEY["phosphorus"].getter(
            meal
        )
        print(
            f"Ca:P ({label:<12})  : {c / p:.3f} : 1   "
            f"(window {CA_P_MEAL_MIN}-{CA_P_MEAL_MAX})"
        )

    s = summary(daily)
    kcal = energy_kcal(daily)
    dm = s["weight"] - s["water"]
    print(
        f"\nAverage day: {s['weight']:.0f} g served ({100 * s['water'] / s['weight']:.1f} % water), "
        f"{dm:.1f} g dry matter, {kcal:.0f} kcal "
        f"({100 * kcal / KCAL_TARGET:.0f} % of the {KCAL_TARGET:.0f} kcal target)"
    )
    print(
        f"            protein {s['proteins']:.1f} g, fat {s['fats']:.1f} g, "
        f"carbs {s['carbs']:.1f} g, ash {s['ashes']:.2f} g"
    )
    print(
        f"            dry-matter basis: protein {100 * s['proteins'] / dm:.1f} %, "
        f"fat {100 * s['fats'] / dm:.1f} %, carbs {100 * s['carbs'] / dm:.1f} %"
        f"   (vet: 61.1 / 23.98 / 1.99 %)"
    )

    print("\n" + "-" * 78)
    print("STILL TO SUPPLEMENT (daily shortfall, < 90 % of target)")
    print("-" * 78)
    if not shortfalls:
        print("  Nothing - every target is met by the food itself.")
    for spec, gap, pct in sorted(shortfalls, key=lambda t: t[2]):
        print(f"  {spec.label:<26}: +{gap:9.4g} {spec.unit:<3} ({pct:.0f}% covered)")

    print("\n" + "-" * 78)
    print("ABOVE THE SOFT CAP (reduce, or verify the tolerable upper limit)")
    print("-" * 78)
    if not overs:
        print("  Nothing - no nutrient exceeds its soft cap.")
    for spec, pct, cap, supplied in sorted(overs, key=lambda t: -t[1]):
        print(
            f"  {spec.label:<26}: {supplied:9.4g} {spec.unit:<3} "
            f"= {pct:.0f}% of target (cap {cap:.4g})"
        )


# =============================================================================
# 8. MAIN
# =============================================================================
def main() -> None:
    results = []
    for fish_days in FISH_DAYS_OPTIONS:
        for liver_oil_everyday in (True, False):
            res = solve(fish_days, liver_oil_everyday)
            if res is None:
                continue
            if res["status"] != "Optimal":
                print(
                    f"[C={fish_days}, liver oil "
                    f"{'daily' if liver_oil_everyday else 'fish days'}] -> {res['status']}"
                )
                continue
            results.append(res)

    if not results:
        print(
            "No feasible plan. Relax KCAL_TOL / DRY_TOL, the moisture window, "
            "the Ca:P windows, or the ingredient bounds."
        )
        return

    best = min(results, key=lambda r: r["objective"])
    print("Scenarios explored (lower objective = smaller relative deviations):")
    for r in sorted(results, key=lambda r: r["objective"]):
        lo = "daily" if r["liver_oil_everyday"] else "fish days"
        mark = " <- chosen" if r is best else ""
        print(
            f"  {r['insect_days']} insect + {r['fish_days']} fish days, "
            f"liver oil {lo:<10}: objective {r['objective']:7.4f}, "
            f"{r['kcal_avg']:.0f} kcal{mark}"
        )
    print()
    report(best)


if __name__ == "__main__":
    main()
