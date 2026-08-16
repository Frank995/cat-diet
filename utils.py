"""Utilities to scale, combine, cook and summarize the nutrient tables.

All tables share one shape and one set of units:

    proteins, fats, carbs, water : g / 100 g of food
    ashes, vitamins, others      : mg / 100 g of food

    TABLE = {
        "proteins": {<amino acid>: g, ..., "others": g},
        "fats": {
            "saturated":        {<fatty acid>: g, ..., "others": g},
            "monounsaturated":  {<fatty acid>: g, ..., "others": g},
            "polyunsaturated":  {<fatty acid>: g, ..., "others": g},
            "others": g,
        },
        "ashes":    {<mineral>: mg, ..., "others": mg},
        "carbs":    {"sugars": {<sugar>: g}, "fibers": {<fiber>: g}, "others": g},
        "vitamins": {<vitamin>: mg},
        "others":   {<compound>: mg},
        "water": g,
    }

Because every section reconciles with its own total through its "others"
residual, every aggregate (total protein, total fat, total ash, ...) is simply
the sum of the leaves of that section - no stored totals, no drift.
"""

from __future__ import annotations

import copy
import math
import re
import warnings
from collections.abc import Callable, Mapping
from typing import Any

__all__ = [
    "ATWATER_GENERAL",
    "ATWATER_MODIFIED",
    "RETENTION",
    "apply_cooking_degradation",
    "combine_nutrition",
    "energy_kcal",
    "round_table",
    "scale",
    "scale_to_grams",
    "smart_round",
    "sort_nested_dict",
    "summary",
    "validate_table",
]

Number = (int, float)

GRAM_SECTIONS = ("proteins", "fats", "carbs")
MILLIGRAM_SECTIONS = ("ashes", "vitamins", "others")
MG_PER_G = 1000.0

CANONICAL_ORDER: dict[tuple, list[str]] = {
    (): ["proteins", "fats", "ashes", "carbs", "vitamins", "others", "water"],
    ("fats",): ["saturated", "monounsaturated", "polyunsaturated"],
    ("carbs",): ["sugars", "fibers"],
}


# --------------------------------------------------------------------------- #
# generic helpers
# --------------------------------------------------------------------------- #
def smart_round(value: float, sig: int = 6) -> float:
    """Round to `sig` significant digits, so trace values survive.

    round(0.000117647, 4) == 0.0001 loses the vitamin K1 content entirely;
    smart_round(0.000117647) == 0.000117647.
    """
    if not isinstance(value, Number) or isinstance(value, bool):
        return value
    if value == 0 or not math.isfinite(value):
        return float(value)
    return float(f"{value:.{sig}g}")


def _map_leaves(
    node: Any, fn: Callable[[float, tuple], float], path: tuple = ()
) -> Any:
    """Recursively rebuild `node`, applying `fn(value, path)` to every number."""
    if isinstance(node, Mapping):
        return {k: _map_leaves(v, fn, path + (k,)) for k, v in node.items()}
    if isinstance(node, Number) and not isinstance(node, bool):
        return fn(float(node), path)
    raise TypeError(f"Unsupported value at {'.'.join(path) or '<root>'}: {node!r}")


def _sum_leaves(node: Any) -> float:
    if isinstance(node, Mapping):
        return sum(_sum_leaves(v) for v in node.values())
    return float(node)


def round_table(table: Mapping, sig: int = 6) -> dict:
    """Significant-digit rounding of every number in a table."""
    return _map_leaves(table, lambda v, _p: smart_round(v, sig))


def scale(table: Mapping, factor: float, sig: int | None = 6) -> dict:
    """Multiply every value by `factor` (e.g. 0.5 for half a portion)."""
    out = _map_leaves(table, lambda v, _p: v * factor)
    return round_table(out, sig) if sig else out


def scale_to_grams(table: Mapping, grams: float, sig: int | None = 6) -> dict:
    """Tables are per 100 g; return the absolute content of `grams` of food."""
    return scale(table, grams / 100.0, sig=sig)


# --------------------------------------------------------------------------- #
# combining
# --------------------------------------------------------------------------- #
def combine_nutrition(*tables: Mapping, sig: int | None = 6) -> dict:
    """Sum any number of nutrient profiles, key by key. Missing keys count as 0.

    The inputs must already be expressed on the same basis: scale each food
    with `scale_to_grams` first, otherwise you are adding percentages.

    Note: a section missing from one table (e.g. `water` for the dry-matter
    insect tables) is simply taken from the tables that do have it.
    """
    if not tables:
        return {}

    def merge(a: Any, b: Any, path: tuple = ()) -> Any:
        if a is None:
            return copy.deepcopy(b)
        if b is None:
            return copy.deepcopy(a)
        if isinstance(a, Mapping) and isinstance(b, Mapping):
            return {
                key: merge(a.get(key), b.get(key), path + (key,))
                for key in list(a) + [k for k in b if k not in a]  # stable order
            }
        if isinstance(a, Number) and isinstance(b, Number):
            return float(a) + float(b)
        raise TypeError(
            f"Cannot merge '{'.'.join(path) or '<root>'}': "
            f"incompatible types {type(a).__name__} and {type(b).__name__}."
        )

    combined = copy.deepcopy(dict(tables[0]))
    for other in tables[1:]:
        combined = merge(combined, other)
    return round_table(combined, sig) if sig else combined


# --------------------------------------------------------------------------- #
# summaries
# --------------------------------------------------------------------------- #
def summary(table: Mapping, sig: int = 6) -> dict:
    """Proximate summary in grams, recomputed from the leaves (unit-aware)."""
    proteins = _sum_leaves(table.get("proteins", {}))
    fats = _sum_leaves(table.get("fats", {}))
    carbs_all = _sum_leaves(table.get("carbs", {}))
    fibers = _sum_leaves(table.get("carbs", {}).get("fibers", {}))
    sugars = _sum_leaves(table.get("carbs", {}).get("sugars", {}))
    ashes = _sum_leaves(table.get("ashes", {})) / MG_PER_G
    water = float(table.get("water", 0.0))

    out = {
        "proteins": proteins,
        "fats": fats,
        "carbs": carbs_all,
        "sugars": sugars,
        "fibers": fibers,
        "nfe": carbs_all - fibers,  # nitrogen-free extract
        "ashes": ashes,
        "water": water,
        "weight": proteins + fats + carbs_all + ashes + water,
        "dry_matter": proteins + fats + carbs_all + ashes,
    }
    return {k: smart_round(v, sig) for k, v in out.items()}


ATWATER_GENERAL = (4.0, 9.0, 4.0)  # human food, protein / fat / carbohydrate
ATWATER_MODIFIED = (3.5, 8.5, 3.5)  # AAFCO modified Atwater, pet food


def energy_kcal(
    table: Mapping, factors=ATWATER_MODIFIED, include_fiber: bool = False
) -> float:
    """Metabolisable energy estimate. Fiber is excluded by default (NFE basis)."""
    s = summary(table, sig=12)
    carbs = s["carbs"] if include_fiber else s["nfe"]
    kp, kf, kc = factors
    return smart_round(kp * s["proteins"] + kf * s["fats"] + kc * carbs, 6)


# --------------------------------------------------------------------------- #
# cooking degradation
# --------------------------------------------------------------------------- #
#: retention factors, named after the *loss* tier they represent
RETENTION = {
    "minimal": 0.960,  # ~4 % loss  (3-5 %)
    "low": 0.910,  # ~9 % loss  (8-10 %)
    "moderate": 0.825,  # ~17.5 % loss (15-20 %)
    "high": 0.650,  # ~35 % loss (30-40 %)
}

# Amino acids: Maillard/oxidation-sensitive ones lose a bit more than the rest.
PROTEIN_TIERS = {
    "lysine": "low",
    "cysteine": "low",
    "methionine": "low",
    "tryptophan": "low",
}

# Exact vitamin keys (as used in the tables).
VITAMIN_TIERS = {
    "vitamin_a_retinol": "moderate",
    "vitamin_a_rae": "moderate",
    "vitamin_a_alpha_carotene": "low",
    "vitamin_a_beta_carotene": "low",
    "vitamin_a_beta_cryptoxanthin": "low",
    "vitamin_b1_thiamin": "moderate",
    "vitamin_b2_riboflavin": "low",
    "vitamin_b3_niacin": "low",
    "vitamin_b5_pantothenic_acid": "low",
    "vitamin_b6_pyridoxine": "moderate",
    "vitamin_b9_folate": "high",
    "vitamin_b12_cobalamin": "moderate",
    "vitamin_c_ascorbic_acid": "high",
    "vitamin_d3_cholecalciferol": "low",
    "vitamin_e_alpha_tocopherol": "moderate",
    "vitamin_e_beta_tocopherol": "moderate",
    "vitamin_e_gamma_tocopherol": "moderate",
    "vitamin_e_delta_tocopherol": "moderate",
    "vitamin_e_alpha_tocotrienol": "moderate",
    "vitamin_j_choline": "low",
    "vitamin_k1_phylloquinone": "minimal",
}

OTHERS_TIERS = {
    # small heat-stable nitrogenous compounds
    "taurine": "low",
    "beta_alanine": "low",
    "1_methylhistidine": "low",
    "betaine": "low",
    "total_nitrogen": "minimal",
    "ammonia_nitrogen": "low",
    # lipids / lipid-soluble
    "cholesterol": "minimal",
    "squalene": "moderate",
    "total_carotenoids": "moderate",
    "lutein_zeaxanthin": "moderate",
    # phenolics and flavonoids
    "apigenin": "moderate",
    "caffeic_acid": "moderate",
    "ellagic_acid": "moderate",
    "ferulic_acid": "moderate",
    "gallic_acid": "moderate",
    "p_coumaric_acid": "moderate",
    "protocatechuic_aldehyde": "moderate",
    "quercetin_3_o_glucoside": "moderate",
    "rutin": "moderate",
    "sinapic_acid": "moderate",
    "vanillic_acid": "moderate",
    "2_5_dihydroxybenzoic_acid": "moderate",
}

#: matches the standardized fatty-acid suffix, e.g. "..._C22_6_n3"
_FATTY_ACID_RE = re.compile(r"_C(\d+)_(\d+)(?:_n(\d+))?")


def _double_bonds(key: str) -> int | None:
    match = _FATTY_ACID_RE.search(key)
    return int(match.group(2)) if match else None


def apply_cooking_degradation(
    table: Mapping,
    water_loss_rate: float = 0.20,
    fat_loss_rate: float = 0.0,
    renormalize: bool = False,
    strict: bool = False,
    sig: int = 6,
) -> dict:
    """Apply thermal-degradation retention factors to a nutrient table.

    Args:
        table: a nutrient table (per 100 g raw food).
        water_loss_rate: fraction of the water evaporated/expressed while cooking.
        fat_loss_rate: fraction of the fat dripping off (0 for closed cooking).
        renormalize: if True, rescale the result to 100 g of *cooked* food;
            if False (default) the result stays on a "per 100 g of raw input"
            basis, i.e. absolute amounts, which is what you want before
            combining several cooked ingredients.
        strict: raise instead of warning when a key has no explicit tier.
        sig: significant digits kept in the output.

    Unlike the previous version, this walks the whole structure, so no section
    can be silently skipped, and every fallback is reported.
    """
    unknown: list[str] = []

    def _tier_lookup(key: str, exact: Mapping[str, str], default="moderate") -> str:
        if key in exact:
            return exact[key]
        unknown.append(key)
        return default

    # ---- per-section resolvers, receiving the path *inside* the section ----
    def proteins_r(path: tuple) -> float:
        return RETENTION[PROTEIN_TIERS.get(path[-1], "minimal")]

    def fats_r(path: tuple) -> float:
        subclass = path[0]
        key = path[-1]
        keep = 1.0 - fat_loss_rate
        if subclass == "polyunsaturated":
            n = _double_bonds(key)
            tier = "moderate" if (n is not None and n >= 4) else "low"
        elif subclass in ("saturated", "monounsaturated"):
            tier = "minimal"
        else:  # fats["others"] and any future subclass
            tier = "minimal"
        return RETENTION[tier] * keep

    def ashes_r(_path: tuple) -> float:
        # minerals do not degrade; losses are leaching, folded into MINIMAL
        return RETENTION["minimal"]

    def carbs_r(_path: tuple) -> float:
        return RETENTION["minimal"]

    def vitamins_r(path: tuple) -> float:
        return RETENTION[_tier_lookup(path[-1], VITAMIN_TIERS)]

    def others_r(path: tuple) -> float:
        return RETENTION[_tier_lookup(path[-1], OTHERS_TIERS)]

    resolvers = {
        "proteins": proteins_r,
        "fats": fats_r,
        "ashes": ashes_r,
        "carbs": carbs_r,
        "vitamins": vitamins_r,
        "others": others_r,
    }

    cooked: dict[str, Any] = {}
    for section, value in table.items():
        if section == "water":
            cooked["water"] = float(value) * (1.0 - water_loss_rate)
        elif section in resolvers:
            resolver = resolvers[section]
            cooked[section] = _map_leaves(value, lambda v, p, r=resolver: v * r(p))
        else:
            cooked[section] = copy.deepcopy(value)

    if unknown:
        message = "no explicit retention tier for: " + ", ".join(sorted(set(unknown)))
        if strict:
            raise KeyError(message)
        warnings.warn(message, RuntimeWarning, stacklevel=2)

    if renormalize:
        weight = summary(cooked, sig=12)["weight"]
        if weight > 0:
            cooked = scale(cooked, 100.0 / weight, sig=None)

    return round_table(cooked, sig)


# --------------------------------------------------------------------------- #
# ordering / validation
# --------------------------------------------------------------------------- #
def sort_nested_dict(
    d: Any,
    order: Mapping[tuple, list] | None = CANONICAL_ORDER,
    current_path: tuple = (),
) -> Any:
    """Recursively order keys: custom order first, then alphabetical.

    `others` is always pushed to the end of its level, since it is a residual.
    """
    if not isinstance(d, Mapping):
        return d

    processed = {
        k: sort_nested_dict(v, order, current_path + (k,)) for k, v in d.items()
    }

    custom = [k for k in (order or {}).get(current_path, []) if k in processed]
    rest = sorted(k for k in processed if k not in custom)
    keys = custom + rest
    if "others" in keys:  # residual always last
        keys = [k for k in keys if k != "others"] + ["others"]
    return {k: processed[k] for k in keys}


def validate_table(table: Mapping, name: str = "<table>") -> list[str]:
    """Cheap structural sanity check; returns a list of human-readable problems."""
    problems: list[str] = []
    allowed_top = set(GRAM_SECTIONS) | set(MILLIGRAM_SECTIONS) | {"water"}
    stale = re.compile(r"(total|_g_per_100g|_mg_per_100g|^nfe$|^difference$|_mg$)")

    for key in table:
        if key not in allowed_top:
            problems.append(f"{name}: unexpected top-level section '{key}'")

    if "fats" in table:
        for key in table["fats"]:
            if key not in ("saturated", "monounsaturated", "polyunsaturated", "others"):
                problems.append(f"{name}: unexpected fats subclass '{key}'")

    def walk(node: Any, path: tuple) -> None:
        if isinstance(node, Mapping):
            for k, v in node.items():
                if stale.search(k):
                    problems.append(
                        f"{name}: leftover total/unit key '{'.'.join(path + (k,))}'"
                    )
                walk(v, path + (k,))
        elif isinstance(node, Number) and not isinstance(node, bool):
            if node < 0:
                problems.append(f"{name}: negative value at '{'.'.join(path)}'")
        else:
            problems.append(f"{name}: non-numeric leaf at '{'.'.join(path)}': {node!r}")

    walk(table, ())

    if "water" in table:
        s = summary(table, sig=12)
        if s["weight"] > 105 or s["weight"] < 90:
            problems.append(
                f"{name}: sections sum to {s['weight']:.2f} g / 100 g "
                "(expected ~100 for a wet-basis table)"
            )
    return problems
