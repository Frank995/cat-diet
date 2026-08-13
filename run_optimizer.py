"""Weekly cat-diet optimiser / diagnostic.

Finds the weekly plan (5-6 insect days + 1-2 fish days) that comes closest to
the nutrient targets, and reports exactly which nutrients are still short, i.e.
what actually has to be supplemented.

Model
-----
* All nutrient constraints are on the **weekly average** intake per day, which
  is how the targets are expressed.
* Every daily meal is served at MEAL_G grams (water is the free filler).
* Only the insect meal is cooked, so only its ingredients get the thermal
  retention factors from `nutrients.apply_cooking_degradation`.
* Powders/oils (eggshell, yeast, taurine, cod-liver oil, algal oil) are added
  after cooking, as a constant daily dose, to whichever meal is served.
* Eggs are integer counts of an average egg (edible part).

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
MEAL_G = 240.0            # grams served per day (as eaten, water included)
SCALE = 240.0 / 290.0     # targets were built for 290 g, diet is 240 g
WATER_LOSS = 0.20         # water lost while cooking the insect meal
EGG_G = 50.0              # edible part of one average egg (whole egg, no shell)

FISH_DAYS_OPTIONS = (1, 2)      # "one or two days per week"
MIN_INSECT_DAYS = 5             # >= 5 insect days per week
MIN_INSECT_FLOUR_G = 20.0       # an insect meal must really contain insects
MIN_FISH_G = 100.0              # a fish meal must really contain fish

ENABLE_COD_ROE = True           # cod roe as an optional fish-day ingredient
IGNORE_EGGSHELL_CARBS = True    # the paper's "carbohydrate by difference" for
                                # eggshell is carbonate, not a nutrient
COUNT_UNDIFFERENTIATED = True   # USDA-style "18:2", "18:3", "20:4" without an
                                # omega family are counted as LA / ALA / ARA
CA_P_MIN, CA_P_MAX = 1.1, 1.2   # weekly-average Ca:P window
PER_MEAL_CA_P = False           # also enforce the window on each meal type

# grams/day bounds (raw, as weighed)
BOUNDS = {
    "bsfl": (0.0, 80.0),
    "mealworms": (0.0, 80.0),
    "water_insect": (0.0, MEAL_G),
    "cod": (0.0, 240.0),
    "mussels": (0.0, 150.0),
    "cod_roe": (0.0, 40.0 if ENABLE_COD_ROE else 0.0),
    "water_fish": (0.0, MEAL_G),
    "eggshells": (0.0, 8.0),
    "yeast": (0.0, 12.0),
    "cod_liver_oil": (0.0, 8.0),
    "algal_oil": (0.0, 8.0),
    "taurine": (0.0, 2.0),
}
EGG_BOUNDS = {"eggs_insect_week": (0, 14), "eggs_fish_week": (0, 7)}

# Optional hard safety ceilings on the weekly average, e.g.
# MAX_TARGETS = {"vitamin_a_retinol": 5 * ..., "vitamin_d3_cholecalciferol": ...}
MAX_TARGETS: dict[str, float] = {}

# Relative weight of each shortfall in the objective (default 1.0).
DEFICIT_WEIGHTS = {
    "taurine": 5.0,
    "docosahexaenoic_acid_C22_6_n3": 3.0,
    "eicosapentaenoic_acid_C20_5_n3": 3.0,
    "arachidonic_acid_C20_4_n6": 3.0,
    "lysine": 2.0,
    "methionine": 2.0,
    "cysteine": 2.0,
    "vitamin_a_retinol": 2.0,
    "calcium": 2.0,
    "phosphorus": 2.0,
}
GRAM_COST = 1e-4          # tiny regulariser: prefer the smaller solution

# =============================================================================
# 2. PSEUDO-INGREDIENTS (not in nutrients/, same table structure, per 100 g)
# =============================================================================
WATER_TABLE = {"water": 100.0}

TAURINE_TABLE = {  # pure taurine powder
    "others": {"taurine": 100_000.0},
    "water": 0.0,
}

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

EGGSHELL_TABLE = copy.deepcopy(EGGS_TABLE)
if IGNORE_EGGSHELL_CARBS:
    EGGSHELL_TABLE["carbs"] = {"fibers": {"others": 0.0}, "others": 0.0}

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


def amino(*names: str) -> Callable[[dict], float]:          # g -> mg
    return lambda p: 1000.0 * sum(_section(p, "proteins").get(n, 0.0) for n in names)


def vitamin(*names: str) -> Callable[[dict], float]:
    return lambda p: sum(_section(p, "vitamins").get(n, 0.0) for n in names)


def vitamin_family(prefix: str) -> Callable[[dict], float]:
    return lambda p: sum(v for k, v in _section(p, "vitamins").items() if k.startswith(prefix))


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
    hard: bool = False          # hard constraint, no shortfall allowed
    group: str = ""


NUTRIENTS: list[Spec] = [
    # ---------------- macros (hard) ----------------
    Spec("protein", "protein", "g", 45.20 * SCALE, macro("proteins"), hard=True, group="macros"),
    Spec("fat", "fat", "g", 17.23 * SCALE, macro("fats"), hard=True, group="macros"),
    Spec("carbs", "carbohydrate", "g", 3.28 * SCALE, macro("carbs"), hard=True, group="macros"),
    # ---------------- minerals (mg) ----------------
    Spec("calcium", "calcium", "mg", 1359.50 * SCALE, mineral("calcium"), group="minerals"),
    Spec("phosphorus", "phosphorus", "mg", 1358.73 * SCALE, mineral("phosphorus"), group="minerals"),
    Spec("potassium", "potassium", "mg", 781.86 * SCALE, mineral("potassium"), group="minerals"),
    Spec("sodium", "sodium", "mg", 213.03 * SCALE, mineral("sodium"), group="minerals"),
    Spec("magnesium", "magnesium", "mg", 59.48 * SCALE, mineral("magnesium"), group="minerals"),
    Spec("iron", "iron", "mg", 4.79 * SCALE, mineral("iron"), group="minerals"),
    Spec("zinc", "zinc", "mg", 6.48 * SCALE, mineral("zinc"), group="minerals"),
    Spec("copper", "copper", "mg", 0.93 * SCALE, mineral("copper"), group="minerals"),
    Spec("manganese", "manganese", "mg", 0.12 * SCALE, mineral("manganese"), group="minerals"),
    Spec("iodine", "iodine", "mg", 0.10 * SCALE, mineral("iodine"), group="minerals"),
    Spec("selenium", "selenium", "mg", 32.69 / 1000.0 * SCALE, mineral("selenium"), group="minerals"),
    # ---------------- vitamins (mg) ----------------
    Spec("vitamin_a_retinol", "vitamin A (retinol)", "mg", 6501.38 * 0.3 / 1000.0 * SCALE,
         vitamin("vitamin_a_retinol"), group="vitamins"),
    Spec("vitamin_b1_thiamin", "vitamin B1", "mg", 0.58 * SCALE,
         vitamin("vitamin_b1_thiamin"), group="vitamins"),
    Spec("vitamin_b2_riboflavin", "vitamin B2", "mg", 0.83 * SCALE,
         vitamin("vitamin_b2_riboflavin"), group="vitamins"),
    Spec("vitamin_b3_niacin", "vitamin B3", "mg", 12.71 * SCALE,
         vitamin("vitamin_b3_niacin"), group="vitamins"),
    Spec("vitamin_b5_pantothenic_acid", "vitamin B5", "mg", 3.45 * SCALE,
         vitamin("vitamin_b5_pantothenic_acid"), group="vitamins"),
    Spec("vitamin_b6", "vitamin B6", "mg", 0.79 * SCALE,
         vitamin("vitamin_b6"), group="vitamins"),
    Spec("vitamin_b8_biotin", "vitamin B8 (biotin)", "mg", 7.67 / 1000.0 * SCALE,
         vitamin("vitamin_b8_biotin"), group="vitamins"),
    Spec("vitamin_b9_folate", "vitamin B9 (folate)", "mg", 44.16 / 1000.0 * SCALE,
         vitamin("vitamin_b9_folate"), group="vitamins"),
    Spec("vitamin_b12_cobalamin", "vitamin B12", "mg", 16.28 / 1000.0 * SCALE,
         vitamin("vitamin_b12_cobalamin"), group="vitamins"),
    Spec("vitamin_c_ascorbic_acid", "vitamin C", "mg", 5.72 * SCALE,
         vitamin("vitamin_c_ascorbic_acid"), group="vitamins"),
    Spec("vitamin_d3_cholecalciferol", "vitamin D3", "mg", 87.22 * 0.025 / 1000.0 * SCALE,
         vitamin("vitamin_d3_cholecalciferol", "vitamin_d"), group="vitamins"),
    Spec("vitamin_e_tocopherols", "vitamin E", "mg", 1.76 * SCALE,
         vitamin_family("vitamin_e"), group="vitamins"),
    # ---------------- amino acids (mg) ----------------
    Spec("tryptophan", "tryptophan", "mg", 492.73 * SCALE, amino("tryptophan"), group="amino acids"),
    Spec("threonine", "threonine", "mg", 2208.56 * SCALE, amino("threonine"), group="amino acids"),
    Spec("isoleucine", "isoleucine", "mg", 2278.46 * SCALE, amino("isoleucine"), group="amino acids"),
    Spec("leucine", "leucine", "mg", 3794.13 * SCALE, amino("leucine"), group="amino acids"),
    Spec("lysine", "lysine", "mg", 4101.94 * SCALE, amino("lysine"), group="amino acids"),
    Spec("methionine", "methionine", "mg", 1300.21 * SCALE, amino("methionine"), group="amino acids"),
    Spec("cysteine", "cysteine + cystine", "mg", 541.57 * SCALE,
         amino("cysteine", "cystine"), group="amino acids"),
    Spec("phenylalanine", "phenylalanine", "mg", 2002.09 * SCALE, amino("phenylalanine"), group="amino acids"),
    Spec("tyrosine", "tyrosine", "mg", 1579.61 * SCALE, amino("tyrosine"), group="amino acids"),
    Spec("valine", "valine", "mg", 2511.67 * SCALE, amino("valine"), group="amino acids"),
    Spec("arginine", "arginine", "mg", 2944.64 * SCALE, amino("arginine"), group="amino acids"),
    Spec("histidine", "histidine", "mg", 1297.03 * SCALE, amino("histidine"), group="amino acids"),
    Spec("taurine", "taurine", "mg", 250.0, other("taurine"), group="amino acids"),
    # ---------------- fats (g) ----------------
    Spec("saturated", "saturated FA", "g", 6.90 * SCALE, fat_class("saturated"), group="fats"),
    Spec("monounsaturated", "monounsaturated FA", "g", 4.23 * SCALE,
         fat_class("monounsaturated"), group="fats"),
    Spec("polyunsaturated", "polyunsaturated FA", "g", 3.40 * SCALE,
         fat_class("polyunsaturated"), group="fats"),
    Spec("linoleic_acid_C18_2_n6", "linoleic acid 18:2 n-6", "g", 2.72 * SCALE,
         fatty_acid(*LA_KEYS), group="fats"),
    Spec("alpha_linolenic_acid_C18_3_n3", "alpha-linolenic acid 18:3 n-3", "g", 0.10 * SCALE,
         fatty_acid(*ALA_KEYS), group="fats"),
    Spec("arachidonic_acid_C20_4_n6", "arachidonic acid 20:4 n-6", "g", 0.30 * SCALE,
         fatty_acid(*ARA_KEYS), group="fats"),
    Spec("eicosapentaenoic_acid_C20_5_n3", "EPA 20:5 n-3", "g", 0.15,
         fatty_acid("eicosapentaenoic_acid_C20_5_n3"), group="fats"),
    Spec("docosahexaenoic_acid_C22_6_n3", "DHA 22:6 n-3", "g", 0.30,
         fatty_acid("docosahexaenoic_acid_C22_6_n3"), group="fats"),
    Spec("cholesterol", "cholesterol", "g", 197.84 / 1000.0 * SCALE,
         other("cholesterol", 1e-3), group="fats"),
]

SPEC_BY_KEY = {s.key: s for s in NUTRIENTS}
SOFT = [s for s in NUTRIENTS if not s.hard]

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
    "mealworms": Ingredient("mealworms", "mealworm flour", MEALWORMS_TABLE, cooked=True),
    "eggs_cooked": Ingredient("eggs_cooked", "whole egg (cooked)", EGGS_TABLE, cooked=True),
    "water_insect": Ingredient("water_insect", "water (cooked off)", WATER_TABLE, cooked=True),
    # fish meal (raw)
    "cod": Ingredient("cod", "wild cod", COD_TABLE),
    "mussels": Ingredient("mussels", "blue mussels", MUSSELS_TABLE),
    "cod_roe": Ingredient("cod_roe", "cod roe", COD_ROE_TABLE),
    "eggs_raw": Ingredient("eggs_raw", "whole egg (raw)", EGGS_TABLE),
    "water_fish": Ingredient("water_fish", "water", WATER_TABLE),
    # powders / oils, added to any meal after cooking
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
WEIGHT = {k: summary(p, sig=12)["weight"] for k, p in PROFILE.items()}   # g served per g raw
COEFF = {k: {s.key: s.getter(p) for s in NUTRIENTS} for k, p in PROFILE.items()}


# =============================================================================
# 5. THE OPTIMISATION MODEL
# =============================================================================
def solve(fish_days: int, liver_oil_everyday: bool) -> dict | None:
    """Solve one scenario (number of fish days x liver-oil placement)."""
    C = fish_days
    S = DAYS - C
    if S < MIN_INSECT_DAYS:
        return None

    prob = pulp.LpProblem(f"cat_diet_C{C}_lo{'daily' if liver_oil_everyday else 'fish'}",
                          pulp.LpMinimize)

    def var(name):
        low, high = BOUNDS[name]
        return pulp.LpVariable(name, lowBound=low, upBound=high)

    x = {name: var(name) for name in BOUNDS}
    eggs_i = pulp.LpVariable("eggs_insect_week", *EGG_BOUNDS["eggs_insect_week"], cat="Integer")
    eggs_f = pulp.LpVariable("eggs_fish_week", *EGG_BOUNDS["eggs_fish_week"], cat="Integer")

    # ---- weekly grams of each ingredient (linear expressions) ----------------
    lo_days = DAYS if liver_oil_everyday else C
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
        (DAYS * x["eggshells"], "eggshells"),
        (DAYS * x["yeast"], "yeast"),
        (lo_days * x["cod_liver_oil"], "cod_liver_oil"),
        (DAYS * x["algal_oil"], "algal_oil"),
        (DAYS * x["taurine"], "taurine"),
    ]

    def avg(nutrient_key):
        """Weekly-average daily supply of a nutrient."""
        return pulp.lpSum(grams * COEFF[ing][nutrient_key] for grams, ing in weekly) / DAYS

    # ---- served weight of each meal type ------------------------------------
    supp_common = (WEIGHT["eggshells"] * x["eggshells"]
                   + WEIGHT["yeast"] * x["yeast"]
                   + WEIGHT["algal_oil"] * x["algal_oil"]
                   + WEIGHT["taurine"] * x["taurine"])
    lo_weight = WEIGHT["cod_liver_oil"] * x["cod_liver_oil"]

    insect_weight = (WEIGHT["bsfl"] * x["bsfl"]
                     + WEIGHT["mealworms"] * x["mealworms"]
                     + WEIGHT["eggs_cooked"] * (EGG_G / S) * eggs_i
                     + WEIGHT["water_insect"] * x["water_insect"]
                     + supp_common
                     + (lo_weight if liver_oil_everyday else 0))
    fish_weight = (WEIGHT["cod"] * x["cod"]
                   + WEIGHT["mussels"] * x["mussels"]
                   + WEIGHT["cod_roe"] * x["cod_roe"]
                   + WEIGHT["eggs_raw"] * (EGG_G / C) * eggs_f
                   + WEIGHT["water_fish"] * x["water_fish"]
                   + supp_common + lo_weight)

    prob += insect_weight == MEAL_G, "insect_meal_weight"
    prob += fish_weight == MEAL_G, "fish_meal_weight"
    prob += x["bsfl"] + x["mealworms"] >= MIN_INSECT_FLOUR_G, "min_insect_flour"
    prob += x["cod"] + x["mussels"] + x["cod_roe"] >= MIN_FISH_G, "min_fish"

    # ---- hard macro constraints ---------------------------------------------
    for spec in NUTRIENTS:
        if spec.hard:
            prob += avg(spec.key) >= spec.target, f"hard_{spec.key}"

    # ---- Ca:P window (weekly average, optionally per meal type) -------------
    prob += avg("calcium") - CA_P_MAX * avg("phosphorus") <= 0, "ca_p_upper"
    prob += avg("calcium") - CA_P_MIN * avg("phosphorus") >= 0, "ca_p_lower"

    if PER_MEAL_CA_P:
        def meal_avg(meal_ings, nutrient_key):
            return pulp.lpSum(expr * COEFF[ing][nutrient_key] for expr, ing in meal_ings)

        insect_ings = [(x["bsfl"], "bsfl"), (x["mealworms"], "mealworms"),
                       ((EGG_G / S) * eggs_i, "eggs_cooked"),
                       (x["eggshells"], "eggshells"), (x["yeast"], "yeast")]
        fish_ings = [(x["cod"], "cod"), (x["mussels"], "mussels"), (x["cod_roe"], "cod_roe"),
                     ((EGG_G / C) * eggs_f, "eggs_raw"),
                     (x["eggshells"], "eggshells"), (x["yeast"], "yeast")]
        for tag, ings in (("insect", insect_ings), ("fish", fish_ings)):
            prob += meal_avg(ings, "calcium") - CA_P_MAX * meal_avg(ings, "phosphorus") <= 0, f"{tag}_ca_p_up"
            prob += meal_avg(ings, "calcium") - CA_P_MIN * meal_avg(ings, "phosphorus") >= 0, f"{tag}_ca_p_lo"

    # ---- soft constraints with shortfall slacks -----------------------------
    deficit = {s.key: pulp.LpVariable(f"deficit_{s.key}", lowBound=0) for s in SOFT}
    for spec in SOFT:
        prob += avg(spec.key) + deficit[spec.key] >= spec.target, f"soft_{spec.key}"

    for key, ceiling in MAX_TARGETS.items():
        prob += avg(key) <= ceiling, f"max_{key}"

    # ---- objective: relative shortfall, lightly regularised ------------------
    prob.setObjective(
        pulp.lpSum(DEFICIT_WEIGHTS.get(s.key, 1.0) * deficit[s.key] / s.target for s in SOFT)
        + GRAM_COST * pulp.lpSum(x[k] for k in
                                 ("bsfl", "mealworms", "cod", "mussels", "cod_roe",
                                  "eggshells", "yeast", "cod_liver_oil", "algal_oil", "taurine"))
    )

    prob.solve(pulp.PULP_CBC_CMD(msg=False))
    if pulp.LpStatus[prob.status] != "Optimal":
        return {"status": pulp.LpStatus[prob.status], "fish_days": C,
                "liver_oil_everyday": liver_oil_everyday}

    solution = {k: float(v.value()) for k, v in x.items()}
    solution["eggs_insect_week"] = round(eggs_i.value())
    solution["eggs_fish_week"] = round(eggs_f.value())
    return {
        "status": "Optimal",
        "objective": float(pulp.value(prob.objective)),
        "fish_days": C,
        "insect_days": S,
        "liver_oil_everyday": liver_oil_everyday,
        "solution": solution,
        "deficits": {k: float(v.value()) for k, v in deficit.items()},
    }


# =============================================================================
# 6. REBUILD THE ACTUAL MEALS (cross-check of the LP through the real pipeline)
# =============================================================================
def build_meals(result: dict) -> tuple[dict, dict, dict]:
    sol = result["solution"]
    S, C = result["insect_days"], result["fish_days"]
    egg_ins_day = sol["eggs_insect_week"] * EGG_G / S
    egg_fish_day = sol["eggs_fish_week"] * EGG_G / C

    supplements = [
        scale_to_grams(EGGSHELL_TABLE, sol["eggshells"]),
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
    insect_meal = combine_nutrition(insect_cooked, *supplements,
                                    *( [liver_oil] if result["liver_oil_everyday"] else [] ))

    fish_meal = combine_nutrition(
        scale_to_grams(COD_TABLE, sol["cod"]),
        scale_to_grams(MUSSELS_TABLE, sol["mussels"]),
        scale_to_grams(COD_ROE_TABLE, sol["cod_roe"]),
        scale_to_grams(EGGS_TABLE, egg_fish_day),
        scale_to_grams(WATER_TABLE, sol["water_fish"]),
        liver_oil, *supplements,
    )

    daily_average = scale(combine_nutrition(scale(insect_meal, S), scale(fish_meal, C)), 1.0 / DAYS)
    return insect_meal, fish_meal, daily_average


# =============================================================================
# 7. REPORT
# =============================================================================
def report(result: dict) -> None:
    sol = result["solution"]
    S, C = result["insect_days"], result["fish_days"]
    insect_meal, fish_meal, daily = build_meals(result)

    print("=" * 74)
    print(f"WEEKLY PLAN : {S} insect days + {C} fish day(s)"
          f"   |   cod-liver oil {'every day' if result['liver_oil_everyday'] else 'on fish days only'}")
    print("=" * 74)

    print(f"\nINSECT MEAL - {S} days/week (raw grams, cooked together)")
    print(f"  BSFL flour           : {sol['bsfl']:7.1f} g")
    print(f"  Mealworm flour       : {sol['mealworms']:7.1f} g")
    print(f"  Whole egg            : {sol['eggs_insect_week'] * EGG_G / S:7.1f} g"
          f"   ({sol['eggs_insect_week']} eggs/week in the batch)")
    print(f"  Water                : {sol['water_insect']:7.1f} g")
    print(f"  -> served weight     : {summary(insect_meal)['weight']:7.1f} g"
          f"   ({energy_kcal(insect_meal):.0f} kcal)")

    print(f"\nFISH MEAL - {C} day(s)/week (raw grams)")
    print(f"  Wild cod             : {sol['cod']:7.1f} g")
    print(f"  Blue mussels         : {sol['mussels']:7.1f} g")
    print(f"  Cod roe              : {sol['cod_roe']:7.1f} g")
    print(f"  Whole egg            : {sol['eggs_fish_week'] * EGG_G / C:7.1f} g"
          f"   ({sol['eggs_fish_week']} eggs/week)")
    print(f"  Water                : {sol['water_fish']:7.1f} g")
    print(f"  -> served weight     : {summary(fish_meal)['weight']:7.1f} g"
          f"   ({energy_kcal(fish_meal):.0f} kcal)")

    print("\nDAILY POWDERS / OILS (stirred into whichever meal is served)")
    print(f"  Eggshell powder      : {sol['eggshells']:7.2f} g")
    print(f"  Nutritional yeast    : {sol['yeast']:7.2f} g")
    print(f"  Cod liver oil        : {sol['cod_liver_oil']:7.2f} g"
          f"   ({'daily' if result['liver_oil_everyday'] else 'fish days only'})")
    print(f"  Algal EPA/DHA oil    : {sol['algal_oil']:7.2f} g")
    print(f"  Taurine powder       : {sol['taurine']:7.3f} g")

    weekly_shopping = {
        "BSFL flour": S * sol["bsfl"], "Mealworm flour": S * sol["mealworms"],
        "Eggs (n)": sol["eggs_insect_week"] + sol["eggs_fish_week"],
        "Wild cod": C * sol["cod"], "Blue mussels": C * sol["mussels"],
        "Cod roe": C * sol["cod_roe"], "Eggshell powder": DAYS * sol["eggshells"],
        "Nutritional yeast": DAYS * sol["yeast"],
        "Cod liver oil": (DAYS if result["liver_oil_everyday"] else C) * sol["cod_liver_oil"],
        "Algal oil": DAYS * sol["algal_oil"], "Taurine": DAYS * sol["taurine"],
    }
    print("\nWEEKLY SHOPPING LIST")
    for name, amount in weekly_shopping.items():
        if amount > 1e-6:
            unit = "" if name.endswith("(n)") else " g"
            print(f"  {name:<22}: {amount:8.1f}{unit}")

    # ---- nutrient balance, computed from the rebuilt weekly-average diet -----
    print("\n" + "-" * 74)
    print("NUTRIENT BALANCE (weekly average per day)")
    print("-" * 74)
    print(f"{'nutrient':<26}{'target':>11}{'supplied':>12}{'%':>8}  unit")
    shortfalls, excesses = [], []
    group = None
    for spec in NUTRIENTS:
        if spec.group != group:
            group = spec.group
            print(f"  [{group}]")
        supplied = spec.getter(daily)
        pct = 100.0 * supplied / spec.target if spec.target else float("inf")
        flag = "" if pct >= 99.5 else "  <-- SHORT"
        print(f"{spec.label:<26}{spec.target:>11.4g}{supplied:>12.4g}{pct:>7.0f}%  {spec.unit}{flag}")
        if pct < 99.5:
            shortfalls.append((spec, spec.target - supplied, pct))
        elif pct > 500:
            excesses.append((spec, pct))

    ca, ph = SPEC_BY_KEY["calcium"].getter(daily), SPEC_BY_KEY["phosphorus"].getter(daily)
    print(f"\nCa:P (weekly average)   : {ca / ph:.3f} : 1   (window {CA_P_MIN}-{CA_P_MAX})")
    for label, meal in (("insect meal", insect_meal), ("fish meal", fish_meal)):
        c, p = SPEC_BY_KEY["calcium"].getter(meal), SPEC_BY_KEY["phosphorus"].getter(meal)
        print(f"Ca:P ({label:<12})  : {c / p:.3f} : 1")
    s = summary(daily)
    print(f"\nAverage day: {s['weight']:.0f} g served, {energy_kcal(daily):.0f} kcal "
          f"(modified Atwater) | protein {s['proteins']:.1f} g, fat {s['fats']:.1f} g, "
          f"carbs {s['carbs']:.1f} g, ash {s['ashes']:.2f} g, water {s['water']:.0f} g")

    print("\n" + "-" * 74)
    print("STILL TO SUPPLEMENT (daily shortfall after the whole plan)")
    print("-" * 74)
    if not shortfalls:
        print("  Nothing - every target is met by the food itself.")
    for spec, gap, pct in sorted(shortfalls, key=lambda t: t[2]):
        print(f"  {spec.label:<26}: +{gap:9.4g} {spec.unit:<3} ({pct:.0f}% of target covered)")

    if excesses:
        print("\nWELL ABOVE TARGET (check tolerable upper limits):")
        for spec, pct in sorted(excesses, key=lambda t: -t[1]):
            print(f"  {spec.label:<26}: {pct:.0f}% of target")


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
                print(f"[C={fish_days}, liver oil "
                      f"{'daily' if liver_oil_everyday else 'fish days'}] -> {res['status']}")
                continue
            results.append(res)

    if not results:
        print("No feasible plan. Loosen the hard macro targets, the Ca:P window, "
              "the 240 g meal weight or the ingredient bounds.")
        return

    best = min(results, key=lambda r: r["objective"])
    print("Scenarios explored (lower objective = smaller relative shortfalls):")
    for r in sorted(results, key=lambda r: r["objective"]):
        mark = " <- chosen" if r is best else ""
        print(f"  {r['insect_days']} insect + {r['fish_days']} fish days, liver oil "
              f"{'daily':<11}" if r["liver_oil_everyday"] else
              f"  {r['insect_days']} insect + {r['fish_days']} fish days, liver oil "
              f"{'fish days':<11}", end="")
        print(f": objective {r['objective']:.4f}{mark}")
    print()
    report(best)


if __name__ == "__main__":
    main()