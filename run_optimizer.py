"""Weekly diet optimiser for one cat: insect-first, FEDIAF-2025 compliant.

Builds ONE weekly menu from the per-100 g tables in ``nutrients.py``:
a cooked BSFL+mealworm dough (>= 4 days/week), a few non-insect meals
(cod / mussels / cod roe / egg) and a fixed set of daily supplemental foods,
then solves it as a lexicographic goal program with PuLP/CBC.

Authority: FEDIAF Nutritional Guidelines, September 2025, Table III-4b
(adult cat, per 1000 kcal ME) for minima, Table III-4a for the EU legal
maxima (dry-matter basis), the vet sheet (Sirio, 25/02/2026) for the fatty
acid profile and as a "do not wildly exceed" echo.

Edit section 1 only. Everything else is documented in place.
"""

from __future__ import annotations

import warnings
from collections.abc import Callable, Mapping
from dataclasses import dataclass

import pulp

import nutrients as NT
from utils import (
    apply_cooking_degradation,
    energy_kcal,
    scale_to_grams,
    summary,
    validate_table,
)

# =============================================================================
# 1.  USER SETTINGS -- the only numbers you normally touch
# =============================================================================
CAT_BW_KG = 4.22  # ideal body weight (vet sheet: 45.20 g prot / 10.70 = 4.224)

# Energy per day, in FEDIAF-cat ME (see ENERGY MODEL below).
#   The vet sheet says 354 kcal, but it was computed with 4/9/4 on TOTAL carbs.
#   The same food scored with FEDIAF's cat equation (4 / 8.5 / 4 on NFE) is
#   337 kcal.  Your -20 % therefore becomes 337 * 0.80 = 270 kcal.
#   NOTE: 270 kcal = 103 kcal/kg BW^0.67.  FEDIAF Table VII-9 gives 100 for an
#   ACTIVE cat and only 52-75 for an indoor/neutered one (= 137-197 kcal/day
#   for Sirio).  If he is indoor + neutered, discuss a further cut with the vet;
#   the recipe stays complete because it is formulated on the dense 75-column.
KCAL_PER_DAY = 270.0

# Physical shape of one daily portion (as served: food + water + powders).
#   Vet sheet x 0.80: 291.71 -> 233.4 g served, 73.98 -> 59.2 g dry matter.
#   Together they fix the moisture at 1 - DM/served = 74.6 % (vet: 74.64 %).
SERVED_G_PER_DAY = 233.4
DRY_MATTER_G_PER_DAY = 59.2

# Sea food the cat actually accepts.  Flip to False and it disappears.
#   (cod liver oil is NOT here: it is a supplemental food, see SUPPLEMENTAL.)
SEAFOOD_ENABLED = {
    "cod": True,  # served RAW
    "mussels": True,  # served BOILED
    "cod_roe": True,  # served raw
}

# Lifestyle. Used ONLY to sanity-check KCAL_PER_DAY against FEDIAF Table VII-9
# ("average daily energy requirements of adult cats"). It changes no constraint.
#   "indoor_neutered" -> 52-75 kcal/kg BW^0.67
#   "active"          -> 100 kcal/kg BW^0.67 (indoor+outdoor, plays/runs)
CAT_LIFESTYLE = "active"

# =============================================================================
# 2.  ADVANCED -- structure of the week, tolerances, goal weights
#     Touch only if the solver says the plan is impossible.
# =============================================================================
DAYS = 7
MIN_INSECT_DAYS = 4  # "mostly insect based"
SEA_DAYS_CHOICES = tuple(range(DAYS - MIN_INSECT_DAYS + 1))  # 0..3

DIET_FORM = "wet"  # moisture > 60 % -> FEDIAF "wet"; taurine/selenium columns.
#   NOTE on taurine: FEDIAF's higher "canned" figure exists because heat
#   processing increases microbial taurine degradation in the gut (§7.3.2).
#   Our dough IS heat processed, so the wet/canned column is the honest choice.

# Which FEDIAF adult column to aim at (Table III-4b has two).
#   A cat that eats LESS energy per kg needs a DENSER food.
#   "conservative" -> always the 75 kcal/kg^0.67 column = densest = safest.
#   "auto"         -> the column matching this cat's real intake (clamped).
DENSITY_BASIS = "conservative"
MIN_SAFETY = 1.00  # extra margin on EVERY FEDIAF minimum (maxima never scaled)

# FEDIAF §3.2.1: "If the protein digestibility of >= 80 % cannot be guaranteed,
# it is recommended to increase the essential amino acid levels by a minimum of
# 10 %."  Insect meals carry chitin; 1.10 is the guideline's own number.
AA_DIGESTIBILITY_MARGIN = 1.10

# Tolerances (weekly average unless stated) ---------------------------------
KCAL_TOL = 0.04  # hard band around KCAL_PER_DAY
SERVED_TOL = 0.12  # hard band around SERVED_G_PER_DAY, per meal type
DRY_TOL = 0.15  # hard band around DRY_MATTER_G_PER_DAY
MOISTURE_SLACK = 0.06  # +/- around the moisture implied by your two numbers
PER_MEAL_KCAL_SOFT = 0.15
PER_MEAL_KCAL_HARD = 0.40

# Insect dough ---------------------------------------------------------------
DOUGH_WATER_LOSS = 0.20  # fraction of dough water boiled off
DOUGH_WATER_PER_FLOUR = (1.6, 4.5)  # g water per g flour, workable range
MIN_FLOUR_G_PER_DAY = 15.0

# Eggs are indivisible -------------------------------------------------------
EGG_G = 50.0  # edible part of one average egg.  NOTE: weigh yours.
MAX_EGGS_WEEK = 7
MAX_EGGS_PER_SEA_MEAL = 2
MIN_ANIMAL_G_PER_SEA_MEAL = 60.0  # cod + mussels + roe + egg on a sea day

# Ratios ---------------------------------------------------------------------
CA_P = (1.0, 2.0)  # FEDIAF III-4b: min 1/1, adult nutritional max 2/1
CA_P_SWEET = 1.25  # soft target inside that window
CA_P_MEAL = (0.95, 2.10)  # per-meal-type window: "do not swing too much"
N6_N3 = (2.5, 12.0)  # vet plan sits at 5.5 : 1

# Vitamin E.  FEDIAF §3.3.2 (Hendriks 2002): "add 5 to 10 IU vitamin E above
# minimum level per gram of fish oil added per kilogram of diet" == 5-10 IU per
# gram of fish oil.  The PUFA/MUFA rule below is the classic feed-science one
# (0.5-1 mg alpha-tocopherol per g PUFA -> ~1 IU/g); MUFA coefficient is mine.
VIT_E_IU_PER_G_MARINE_OIL = 7.5
VIT_E_IU_PER_G_PUFA = 1.0
VIT_E_IU_PER_G_MUFA = 0.15

# Prudent ceilings that FEDIAF does NOT provide for cats (see report legend).
CHOLESTEROL_MAX_MG_PER_1000KCAL = 850.0  # no FEDIAF/NRC limit exists at all
CALCIUM_MAX_G_PER_1000KCAL = 5.00  # cats: blank in III-4b (dogs: 6.25 N)
PHOSPHORUS_MAX_G_PER_1000KCAL = 4.00  # cats: blank; footnote f limits only
#   INORGANIC P (>=1.5 g Pi/1000 kcal affects kidney markers; 1 g shown safe).
#   This diet adds no inorganic phosphate, so footnote f is not triggered.
MAGNESIUM_MAX_G_PER_1000KCAL = 0.40  # cats: blank; struvite prudence

# Goal weights ---------------------------------------------------------------
W_FEDIAF_MIN, W_FEDIAF_MAX, W_LEGAL_MAX = 1.0, 1.5, 3.0
W_CA_P, W_VIT_E, W_ARG = 3.0, 2.0, 1.0
W_KCAL_DEV, W_MEAL_KCAL = 30.0, 6.0
W_CA_P_SWEET, W_VET, W_VET_FAT = 2.0, 1.0, 1.5
GRAM_COST = 0.02

SOLVER = pulp.PULP_CBC_CMD(msg=False)
DEBUG = False

# ---- derived (do not edit) --------------------------------------------------
VET_KCAL_SHEET = 354.0  # as printed by the vet's software (4/9/4, with fibre)
VET_KCAL_FEDIAF = 337.4  # same food re-scored with 4/8.5/4 on NFE
VET_SCALE = KCAL_PER_DAY / VET_KCAL_FEDIAF  # rescales every vet target
ACTUAL_MER = KCAL_PER_DAY / CAT_BW_KG**0.67


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


MER = 75.0 if DENSITY_BASIS == "conservative" else _clamp(ACTUAL_MER, 75.0, 100.0)

_IMPLIED_MOISTURE = 1.0 - DRY_MATTER_G_PER_DAY / SERVED_G_PER_DAY
MOISTURE = (
    max(0.60, _IMPLIED_MOISTURE - MOISTURE_SLACK),
    min(0.86, _IMPLIED_MOISTURE + MOISTURE_SLACK),
)
SERVED = (SERVED_G_PER_DAY * (1 - SERVED_TOL), SERVED_G_PER_DAY * (1 + SERVED_TOL))
DRY = (DRY_MATTER_G_PER_DAY * (1 - DRY_TOL), DRY_MATTER_G_PER_DAY * (1 + DRY_TOL))

# FEDIAF Table VII-9. The "active" band is +/-15 % around the tabulated 100.
LIFESTYLE_MER = {"indoor_neutered": (52.0, 75.0), "active": (85.0, 115.0)}

# =============================================================================
# 3.  UNITS AND THE ENERGY MODEL
# =============================================================================
# FEDIAF Table VII-14, conversion factors:
IU_A_MG = 0.0003  # 1 IU vitamin A = 0.3 ug retinol  (1 mg retinol = 3333 IU)
IU_D_MG = 0.000025  # 1 IU vitamin D = 0.025 ug cholecalciferol (1 ug = 40 IU)
# Vitamin E is handled directly in IU with FEDIAF's bio-equivalences:
TOCOPHEROL_IU_PER_MG = {
    "vitamin_e_alpha_tocopherol": 1.49,  # d-alpha-tocopherol (natural, in food)
    "vitamin_e_beta_tocopherol": 0.33,  # FEDIAF lists dl- forms only
    "vitamin_e_gamma_tocopherol": 0.01,
    "vitamin_e_delta_tocopherol": 0.25,
    # NOTE: FEDIAF's dl-delta (0.25) > dl-gamma (0.01) is odd - most sources put
    # gamma ~0.1 and delta ~0.03 of alpha.  I follow the guideline verbatim; if
    # your tables are gamma-rich this is the one number worth double-checking.
    "vitamin_e_alpha_tocotrienol": 0.0,  # not listed by FEDIAF -> not counted
}

_MG = {"g": 1000.0, "mg": 1.0, "ug": 1e-3}


def unit_factor(funit: str, internal: str) -> float:
    """Multiply a value in FEDIAF units by this to get model units."""
    if funit == internal:
        return 1.0
    if funit == "IU_A" and internal == "mg":
        return IU_A_MG
    if funit == "IU_D" and internal == "mg":
        return IU_D_MG
    if funit in _MG and internal in _MG:
        return _MG[funit] / _MG[internal]
    raise ValueError(f"no conversion {funit} -> {internal}")


_UNIT_LABEL = {
    "g": "g",
    "mg": "mg",
    "ug": "ug",
    "IU_A": "IU",
    "IU_D": "IU",
    "IU_E": "IU",
}

# ENERGY -- FEDIAF §7.2.2.2 b), "products of vegetable or animal origin in their
# natural state, fresh or preserved": for CATS
#       kcal ME = 4 x %crude protein + 8.5 x %crude fat + 4 x %NFE
# This is the correct model for a home-made diet (the modified Atwater 3.5/8.5/
# 3.5 is meant for processed pet food and reads ~10 % low here).
FEDIAF_CAT_ME = (4.0, 8.5, 4.0)


def nrc_me_kcal(prot_g, fat_g, nfe_g, fibre_g, dm_g, served_g) -> float:
    """FEDIAF §7.2.2.2 a) 4-step NRC estimate -- used only as a cross-check.

    It is nonlinear (digestibility depends on crude fibre), so the LP uses the
    linear equation above and we compare afterwards.  Insect chitin shows up
    here: every 1 % crude fibre in DM costs 0.88 points of energy digestibility.
    """
    if served_g <= 0 or dm_g <= 0:
        return 0.0
    cp, cf = 100 * prot_g / served_g, 100 * fat_g / served_g
    nfe, fib = 100 * nfe_g / served_g, 100 * fibre_g / served_g
    ge = 5.7 * cp + 9.4 * cf + 4.1 * (nfe + fib)
    dig = 87.9 - 0.88 * (100 * fibre_g / dm_g)
    return (ge * dig / 100 - 0.77 * cp) * served_g / 100


# =============================================================================
# 4.  ACCESSORS (all None-safe: profiles are cleaned before use)
# =============================================================================
def _deep_sum(node) -> float:
    if isinstance(node, Mapping):
        return sum(_deep_sum(v) for v in node.values())
    return 0.0 if node is None else float(node)


def _section(profile: Mapping, name: str) -> Mapping:
    v = profile.get(name, {})
    return v if isinstance(v, Mapping) else {}


def _get(d: Mapping, key: str) -> float:
    v = d.get(key, 0.0)
    return 0.0 if v is None else float(v)


def macro(section: str) -> Callable[[Mapping], float]:
    return lambda p: _deep_sum(_section(p, section))


def mineral(name: str) -> Callable[[Mapping], float]:
    return lambda p: _get(_section(p, "ashes"), name)


def amino(*names: str) -> Callable[[Mapping], float]:  # tables g -> model mg
    return lambda p: 1000.0 * sum(_get(_section(p, "proteins"), n) for n in names)


def vitamin(*names: str) -> Callable[[Mapping], float]:
    return lambda p: sum(_get(_section(p, "vitamins"), n) for n in names)


def fat_class(cls: str) -> Callable[[Mapping], float]:
    return lambda p: _deep_sum(_section(p, "fats").get(cls, {}))


def fatty_acid(*names, cls: str = "polyunsaturated") -> Callable[[Mapping], float]:
    return lambda p: sum(_get(_section(p, "fats").get(cls, {}), n) for n in names)


def other(name: str) -> Callable[[Mapping], float]:
    return lambda p: _get(_section(p, "others"), name)


def fibre(p: Mapping) -> float:
    return _deep_sum(_section(p, "carbs").get("fibers", {}))


def vitamin_e_iu(p: Mapping) -> float:
    """Total vitamin E activity in IU (FEDIAF Table VII-14 bio-equivalences)."""
    vits = _section(p, "vitamins")
    return sum(_get(vits, k) * f for k, f in TOCOPHEROL_IU_PER_MG.items())


# Vitamin A: FEDIAF Table VII-14 gives the beta-carotene conversion for DOGS
# only -- cats cannot cleave carotenoids.  Retinol is the only valid source.
VITAMIN_A_GETTER = vitamin("vitamin_a_retinol")

EPA_KEY, DHA_KEY = "timnodonic_acid", "cervonic_acid"


# =============================================================================
# 5.  THE SINGLE TABLE OF TRUTH  (FEDIAF 2025, adult cat)
#   fmin      = (75 kcal/kg^0.67 column, 100 kcal column) per 1000 kcal ME
#   fmax_kcal = nutritional maximum (N) or prudent cap, per 1000 kcal ME
#   fmax_dm   = EU legal maximum (L), per 100 g DM  <- the only basis FEDIAF
#               publishes for legal limits (§3.1.3); applies to the TOTAL when
#               the element is added as an additive (our premix does add them).
#   vet       = per day at the vet's sheet, in MODEL units (auto-rescaled)
# =============================================================================
@dataclass(frozen=True)
class Nutrient:
    key: str
    label: str
    getter: Callable[[Mapping], float]
    group: str
    internal: str = "mg"
    funit: str = "mg"
    fmin: tuple[float, float] | None = None
    fmax_kcal: float | None = None
    fmax_kcal_src: str = ""
    fmax_dm: float | None = None
    fmax_dm_src: str = ""
    aa_margin: bool = False  # apply the +10 % low-digestibility margin
    vet: float | None = None
    w_short: float = 0.0
    w_over: float = 1.0
    over_factor: float = 2.0

    @property
    def f2i(self) -> float:
        return unit_factor(self.funit, self.internal)

    @property
    def unit_label(self) -> str:
        return _UNIT_LABEL[self.funit]

    def fediaf_min(self) -> float | None:
        if self.fmin is None:
            return None
        m75, m100 = self.fmin
        v = _clamp(m75 * 75.0 / MER, min(m75, m100), max(m75, m100)) * MIN_SAFETY
        return v * AA_DIGESTIBILITY_MARGIN if self.aa_margin else v

    def min_internal(self) -> float | None:
        v = self.fediaf_min()
        return None if v is None else v * self.f2i

    def max_kcal_internal(self) -> float | None:
        return None if self.fmax_kcal is None else self.fmax_kcal * self.f2i

    def max_dm_internal(self) -> float | None:
        return None if self.fmax_dm is None else self.fmax_dm * self.f2i

    def vet_target(self) -> float | None:
        return None if self.vet in (None, 0) else self.vet * VET_SCALE


_TAURINE = (0.67, 0.50) if DIET_FORM == "wet" else (0.33, 0.25)
_SELENIUM = (87.50, 65.00) if DIET_FORM == "wet" else (70.00, 52.50)

L = "EU legal limit (L), FEDIAF III-4a"
N = "FEDIAF nutritional maximum (N)"
P = "prudent - FEDIAF gives no maximum for cats"

NUTRIENTS: list[Nutrient] = [
    # ------------------------------------------------------------- macros
    Nutrient(
        "protein",
        "protein",
        macro("proteins"),
        "macros",
        "g",
        "g",
        fmin=(83.30, 62.50),
        vet=45.20,
        w_short=2.0,
        over_factor=2.0,
    ),
    Nutrient(
        "fat",
        "fat",
        macro("fats"),
        "macros",
        "g",
        "g",
        fmin=(22.50, 22.50),
        vet=17.73,
        w_short=2.0,
        over_factor=1.6,
        w_over=3.0,
    ),
    # FEDIAF: fat minimum is NOT energy-corrected (§3.3.2 "Total Fat").
    Nutrient(
        "carbs",
        "carbohydrate",
        macro("carbs"),
        "macros",
        "g",
        "g",
        vet=3.28,
        over_factor=3.0,
        w_over=2.0,
    ),
    Nutrient(
        "fibre",
        "crude/total fibre",
        fibre,
        "macros",
        "g",
        "g",
        vet=1.81,
        over_factor=2.5,
        w_over=1.0,
    ),
    # ---------------------------------------------------------- amino acids
    # aa_margin=True -> +10 % (FEDIAF §3.2.1, digestibility < 80 %)
    Nutrient(
        "arginine",
        "arginine",
        amino("arginine"),
        "amino acids",
        fmin=(3.30, 2.50),
        funit="g",
        aa_margin=True,
        vet=2944.64,
        over_factor=4.0,
    ),
    Nutrient(
        "histidine",
        "histidine",
        amino("histidine"),
        "amino acids",
        fmin=(0.87, 0.65),
        funit="g",
        aa_margin=True,
        vet=1297.03,
        over_factor=4.0,
    ),
    Nutrient(
        "isoleucine",
        "isoleucine",
        amino("isoleucine"),
        "amino acids",
        fmin=(1.44, 1.08),
        funit="g",
        aa_margin=True,
        vet=2278.46,
        over_factor=4.0,
    ),
    Nutrient(
        "leucine",
        "leucine",
        amino("leucine"),
        "amino acids",
        fmin=(3.40, 2.55),
        funit="g",
        aa_margin=True,
        vet=3794.13,
        over_factor=4.0,
    ),
    Nutrient(
        "lysine",
        "lysine",
        amino("lysine"),
        "amino acids",
        fmin=(1.13, 0.85),
        funit="g",
        aa_margin=True,
        vet=4101.94,
        over_factor=4.0,
    ),
    Nutrient(
        "methionine",
        "methionine",
        amino("methionine"),
        "amino acids",
        fmin=(0.57, 0.43),
        funit="g",
        aa_margin=True,
        vet=1300.21,
        over_factor=3.0,
    ),
    # NOTE: the 3.25 g/1000 kcal methionine (N) and 4.25 tryptophan (N) and
    # 8.75 arginine (N) in III-4b are labelled "Growth" -> not applied here.
    Nutrient(
        "methionine_cystine",
        "methionine + cystine",
        amino("methionine", "cysteine"),
        "amino acids",
        fmin=(1.13, 0.85),
        funit="g",
        aa_margin=True,
        over_factor=4.0,
    ),
    Nutrient(
        "cysteine",
        "cystine",
        amino("cysteine"),
        "amino acids",
        vet=541.57,
        over_factor=4.0,
    ),
    Nutrient(
        "phenylalanine",
        "phenylalanine",
        amino("phenylalanine"),
        "amino acids",
        fmin=(1.33, 1.00),
        funit="g",
        aa_margin=True,
        vet=2002.09,
        over_factor=4.0,
    ),
    # 5.11/3.83 is the melanin (black coat) level FEDIAF adopts; §3.3.2 adds
    # "to maximise black hair colour, tyrosine >= phenylalanine".
    Nutrient(
        "phenylalanine_tyrosine",
        "phenylalanine + tyrosine",
        amino("phenylalanine", "tyrosine"),
        "amino acids",
        fmin=(5.11, 3.83),
        funit="g",
        aa_margin=True,
        over_factor=4.0,
    ),
    Nutrient(
        "tyrosine",
        "tyrosine",
        amino("tyrosine"),
        "amino acids",
        vet=1579.61,
        over_factor=4.0,
    ),
    Nutrient(
        "threonine",
        "threonine",
        amino("threonine"),
        "amino acids",
        fmin=(1.73, 1.30),
        funit="g",
        aa_margin=True,
        vet=2208.56,
        over_factor=4.0,
    ),
    Nutrient(
        "tryptophan",
        "tryptophan",
        amino("tryptophan"),
        "amino acids",
        fmin=(0.44, 0.33),
        funit="g",
        aa_margin=True,
        vet=492.73,
        over_factor=4.0,
    ),
    Nutrient(
        "valine",
        "valine",
        amino("valine"),
        "amino acids",
        fmin=(1.70, 1.28),
        funit="g",
        aa_margin=True,
        vet=2511.67,
        over_factor=4.0,
    ),
    Nutrient(
        "taurine",
        f"taurine ({DIET_FORM})",
        other("taurine"),
        "amino acids",
        fmin=_TAURINE,
        funit="g",
        vet=250.0,
        w_short=1.0,
        over_factor=6.0,
    ),
    # ---------------------------------------------------------------- fats
    Nutrient(
        "linoleic_acid",
        "linoleic acid",
        fatty_acid("linoleic_acid"),
        "fats",
        "g",
        "g",
        fmin=(1.67, 1.25),
        vet=2.72,
        w_short=3.0,
        over_factor=2.0,
    ),
    Nutrient(
        "alpha_linolenic_acid",
        "alpha-linolenic",
        fatty_acid("alpha_linolenic_acid"),
        "fats",
        "g",
        "g",
        vet=0.10,
        w_short=3.0,
        over_factor=6.0,
    ),  # no adult min in FEDIAF
    Nutrient(
        "arachidonic_acid",
        "arachidonic acid",
        fatty_acid("arachidonic_acid"),
        "fats",
        "g",
        "mg",
        fmin=(20.00, 15.00),
        vet=0.30,
        w_short=4.0,
        over_factor=4.0,
    ),
    Nutrient(
        "timnodonic_acid",
        "EPA",
        fatty_acid(EPA_KEY),
        "fats",
        "g",
        "g",
        vet=0.15,
        w_short=4.0,
        over_factor=4.0,
    ),
    Nutrient(
        "cervonic_acid",
        "DHA",
        fatty_acid(DHA_KEY),
        "fats",
        "g",
        "g",
        vet=0.30,
        w_short=4.0,
        over_factor=4.0,
    ),
    Nutrient(
        "epa_dha",
        "EPA + DHA",
        fatty_acid(EPA_KEY, DHA_KEY),
        "fats",
        "g",
        "g",
        fmax_kcal=2.80,
        fmax_kcal_src="NRC 2006 SUL (not FEDIAF)",
    ),
    Nutrient(
        "saturated",
        "saturated FA",
        fat_class("saturated"),
        "fats",
        "g",
        "g",
        vet=6.90,
        w_short=1.0,
        over_factor=1.6,
        w_over=2.0,
    ),
    Nutrient(
        "monounsaturated",
        "monounsaturated FA",
        fat_class("monounsaturated"),
        "fats",
        "g",
        "g",
        vet=4.23,
        w_short=1.0,
        over_factor=1.8,
        w_over=2.0,
    ),
    Nutrient(
        "polyunsaturated",
        "polyunsaturated FA",
        fat_class("polyunsaturated"),
        "fats",
        "g",
        "g",
        vet=3.40,
        w_short=2.0,
        over_factor=1.6,
        w_over=2.0,
    ),
    Nutrient(
        "cholesterol",
        "cholesterol",
        other("cholesterol"),
        "fats",
        "mg",
        "mg",
        fmax_kcal=CHOLESTEROL_MAX_MG_PER_1000KCAL,
        fmax_kcal_src="prudent - no cholesterol limit exists for cats",
        vet=197.84,
        over_factor=2.0,
        w_over=2.0,
    ),
    # ------------------------------------------------------------ minerals
    Nutrient(
        "calcium",
        "calcium",
        mineral("calcium"),
        "minerals",
        funit="g",
        fmin=(1.33, 1.00),
        fmax_kcal=CALCIUM_MAX_G_PER_1000KCAL,
        fmax_kcal_src=P,
        vet=1359.50,
        over_factor=1.6,
        w_over=2.0,
    ),
    Nutrient(
        "phosphorus",
        "phosphorus",
        mineral("phosphorus"),
        "minerals",
        funit="g",
        fmin=(0.85, 0.64),
        fmax_kcal=PHOSPHORUS_MAX_G_PER_1000KCAL,
        fmax_kcal_src=P + " (footnote f limits INORGANIC P only)",
        vet=1358.73,
        over_factor=1.6,
        w_over=3.0,
    ),
    Nutrient(
        "potassium",
        "potassium",
        mineral("potassium"),
        "minerals",
        funit="g",
        fmin=(2.00, 1.50),
        vet=781.86,
        over_factor=2.0,
    ),
    Nutrient(
        "sodium",
        "sodium",
        mineral("sodium"),
        "minerals",
        funit="g",
        fmin=(0.25, 0.19),
        fmax_kcal=3.75,
        fmax_kcal_src="FEDIAF footnote e (shown safe for healthy cats)",
        vet=213.03,
        over_factor=3.0,
        w_over=2.0,
    ),
    Nutrient(
        "chloride",
        "chloride",
        mineral("chloride"),
        "minerals",
        funit="g",
        fmin=(0.39, 0.29),
        over_factor=3.0,
    ),
    Nutrient(
        "magnesium",
        "magnesium",
        mineral("magnesium"),
        "minerals",
        funit="g",
        fmin=(0.13, 0.10),
        fmax_kcal=MAGNESIUM_MAX_G_PER_1000KCAL,
        fmax_kcal_src=P,
        vet=59.48,
        over_factor=2.0,
        w_over=2.0,
    ),
    # ------------------------------------------------------- trace elements
    # NOTE: copper oxide and iron oxide/carbonate must NOT be counted towards
    # the minimum (FEDIAF §3.3.2) -> the premix uses gluconate/bisglycinate.
    Nutrient(
        "copper",
        "copper",
        mineral("copper"),
        "trace elements",
        fmin=(1.67, 1.25),
        fmax_dm=2.80,
        fmax_dm_src=L,
        vet=0.93,
        over_factor=2.5,
        w_over=3.0,
    ),
    Nutrient(
        "iodine",
        "iodine",
        mineral("iodine"),
        "trace elements",
        fmin=(0.43, 0.33),
        fmax_dm=1.10,
        fmax_dm_src=L,
        vet=0.10,
        over_factor=3.0,
        w_over=3.0,
    ),
    Nutrient(
        "iron",
        "iron",
        mineral("iron"),
        "trace elements",
        fmin=(26.70, 20.00),
        fmax_dm=68.18,
        fmax_dm_src=L,
        vet=4.79,
        over_factor=3.0,
        w_over=3.0,
    ),
    Nutrient(
        "manganese",
        "manganese",
        mineral("manganese"),
        "trace elements",
        fmin=(1.67, 1.25),
        fmax_dm=17.00,
        fmax_dm_src=L,
        vet=0.12,
        over_factor=6.0,
        w_over=3.0,
    ),
    Nutrient(
        "selenium",
        f"selenium ({DIET_FORM})",
        mineral("selenium"),
        "trace elements",
        funit="ug",
        fmin=_SELENIUM,
        fmax_dm=56.80,
        fmax_dm_src=L + "; ORGANIC Se supplementation max 22.73 ug/100g DM",
        vet=32.69 / 1000.0,
        over_factor=3.0,
        w_over=3.0,
    ),
    Nutrient(
        "zinc",
        "zinc",
        mineral("zinc"),
        "trace elements",
        fmin=(25.00, 18.80),
        fmax_dm=22.70,
        fmax_dm_src=L,
        vet=6.48,
        over_factor=3.0,
        w_over=2.0,
    ),
    # ------------------------------------------------------------- vitamins
    Nutrient(
        "vitamin_a_retinol",
        "vitamin A (retinol)",
        VITAMIN_A_GETTER,
        "vitamins",
        funit="IU_A",
        fmin=(1110.0, 833.0),
        fmax_kcal=100000.0,
        fmax_kcal_src=N + " adult & growth",
        vet=6501.38 * IU_A_MG,
        over_factor=6.0,
        w_over=3.0,
    ),
    Nutrient(
        "vitamin_d3",
        "vitamin D3",
        vitamin("vitamin_d3"),
        "vitamins",
        funit="IU_D",
        fmin=(83.30, 62.50),
        fmax_kcal=7500.0,
        fmax_kcal_src=N,
        fmax_dm=227.0,
        fmax_dm_src=L + " - applies ONLY if D3 is added as an additive",
        vet=87.22 * IU_D_MG,
        over_factor=6.0,
        w_over=5.0,
    ),
    Nutrient(
        "vitamin_e",
        "vitamin E",
        vitamin_e_iu,
        "vitamins",
        internal="IU_E",
        funit="IU_E",
        fmin=(12.70, 9.50),
        vet=1.76 * 1.49,
        over_factor=20.0,
    ),  # vet's 1.76 mg -> IU (d-alpha)
    Nutrient(
        "vitamin_k1",
        "vitamin K1 (fish diets)",
        vitamin("vitamin_k1"),
        "vitamins",
        funit="ug",
        fmin=(25.0, 25.0),
        over_factor=20.0,
    ),
    # NOTE vitamin K: FEDIAF has no number, but §3.3.2 warns that canned cat
    # food high in FISH may prolong coagulation times and suggests supplementing.
    # 25 ug/1000 kcal = AAFCO's 0.1 mg/kg DM for diets with >25 % fish.
    Nutrient(
        "vitamin_b1",
        "vitamin B1",
        vitamin("vitamin_b1"),
        "vitamins",
        fmin=(1.47, 1.10),
        vet=0.58,
        over_factor=10.0,
    ),
    Nutrient(
        "vitamin_b2",
        "vitamin B2",
        vitamin("vitamin_b2"),
        "vitamins",
        fmin=(1.05, 0.80),
        vet=0.83,
        over_factor=10.0,
    ),
    Nutrient(
        "vitamin_b3",
        "vitamin B3",
        vitamin("vitamin_b3"),
        "vitamins",
        fmin=(10.50, 8.00),
        vet=12.71,
        over_factor=8.0,
    ),
    Nutrient(
        "vitamin_b5",
        "vitamin B5",
        vitamin("vitamin_b5"),
        "vitamins",
        fmin=(1.92, 1.44),
        vet=3.45,
        over_factor=10.0,
    ),
    # FEDIAF §3.3.2: "Requirements of vitamin B6 increase with increasing
    # protein content of the food" -> keep B6 comfortably above the minimum.
    Nutrient(
        "vitamin_b6",
        "vitamin B6",
        vitamin("vitamin_b6"),
        "vitamins",
        fmin=(0.83, 0.63),
        vet=0.79,
        over_factor=10.0,
    ),
    Nutrient(
        "vitamin_b8",
        "vitamin B8 (biotin)",
        vitamin("vitamin_b8"),
        "vitamins",
        funit="ug",
        fmin=(20.00, 15.00),
        vet=7.67 / 1000.0,
        over_factor=15.0,
    ),
    Nutrient(
        "vitamin_b9",
        "vitamin B9 (folate)",
        vitamin("vitamin_b9"),
        "vitamins",
        funit="ug",
        fmin=(253.0, 188.0),
        vet=44.16 / 1000.0,
        over_factor=15.0,
    ),
    Nutrient(
        "vitamin_b12",
        "vitamin B12",
        vitamin("vitamin_b12"),
        "vitamins",
        funit="ug",
        fmin=(5.87, 4.40),
        vet=16.28 / 1000.0,
        over_factor=30.0,
    ),
    Nutrient(
        "vitamin_c",
        "vitamin C (not required)",
        vitamin("vitamin_c"),
        "vitamins",
        vet=5.72,
        over_factor=20.0,
    ),
    # --------------------------------------------------------------- others
    Nutrient(
        "choline",
        "choline",
        other("choline"),
        "others",
        fmin=(800.0, 600.0),
        over_factor=4.0,
    ),
]
SPEC = {n.key: n for n in NUTRIENTS}

# =============================================================================
# 6.  FOODS
#   prep: "raw" (as weighed) | "cooked" (utils.RETENTION factors applied)
#   mass_from_table: False for mineral powders whose table lists only ELEMENTS
#   lo/hi: grams PER SERVING of the meal type the food belongs to
# =============================================================================
WATER_TABLE = {"water": 100.0}


@dataclass(frozen=True)
class Food:
    key: str
    label: str
    table: object
    prep: str = "raw"
    water_loss: float = 0.0
    fat_loss: float = 0.0
    mass_from_table: bool = True
    marine_oil: bool = False  # triggers the vitamin E / fish-oil rule
    lo: float = 0.0
    hi: float = 0.0

    def resolve(self):
        return (
            self.table
            if isinstance(self.table, Mapping)
            else getattr(NT, str(self.table), None)
        )


FOOD_SPECS = [
    # ---- weekly insect dough (cooked together) --------------------------
    Food("bsfl", "BSFL flour", "BSFL_TABLE", "cooked", DOUGH_WATER_LOSS, hi=35.0),
    Food(
        "mealworms",
        "mealworm flour",
        "MEALWORMS_TABLE",
        "cooked",
        DOUGH_WATER_LOSS,
        hi=35.0,
    ),
    Food(
        "water_dough",
        "water (dough)",
        WATER_TABLE,
        "cooked",
        DOUGH_WATER_LOSS,
        hi=400.0,
    ),
    # Eggs are ALWAYS cooked: raw white = avidin (a biotin antagonist, which is
    # exactly why FEDIAF lists biotin) + Salmonella.  Boiled in shell -> no
    # water loss, only heat-labile vitamins.
    Food(
        "egg",
        "whole egg, boiled",
        "EGGS_TABLE",
        "cooked",
        0.0,
        hi=EGG_G * MAX_EGGS_WEEK,
    ),
    # ---- non-insect meal -------------------------------------------------
    Food("cod", "wild cod (raw)", "COD_TABLE", "raw", hi=150.0),
    Food("cod_roe", "cod roe (raw)", "COD_ROE_TABLE", "raw", hi=30.0),
    # MUSSELS_TABLE is the RAW meat -> cooking degradation + 30 % water loss.
    # NOTE: 0.30 is my estimate for steamed/boiled mussel meat; adjust if you
    # weigh the meat before and after cooking.
    Food("mussels", "blue mussels (boiled)", "MUSSELS_TABLE", "cooked", 0.30, hi=90.0),
    Food("water_raw", "water", WATER_TABLE, "raw", hi=300.0),
    # ---- supplemental foods, every day, dose may differ per meal type ----
    Food(
        "eggshells",
        "eggshell powder",
        "EGGSHELLS_TABLE",
        "raw",
        mass_from_table=False,
        hi=3.0,
    ),
    Food("yeast", "nutritional yeast", "YEAST_TABLE", "raw", hi=6.0),
    Food("spirulina", "spirulina powder", "SPIRULINA_TABLE", "raw", hi=2.0),
    Food(
        "cod_liver_oil",
        "cod liver oil",
        "COD_LIVER_OIL_TABLE",
        "raw",
        marine_oil=True,
        hi=1.0,
    ),
    Food(
        "algal_oil",
        "algal EPA/DHA oil",
        "ALGAL_OIL_TABLE",
        "raw",
        marine_oil=True,
        hi=1.5,
    ),
    Food("sunflower_oil", "sunflower oil", "SUNFLOWER_OIL_TABLE", "raw", hi=4.0),
]

DOUGH_FLOUR_KEYS = ("bsfl", "mealworms")
SEA_FOOD_KEYS = ("cod", "mussels", "cod_roe")
SUPPLEMENTAL_KEYS = (
    "eggshells",
    "yeast",
    "spirulina",
    "cod_liver_oil",
    "algal_oil",
    "sunflower_oil",
)


# =============================================================================
# 7.  PURIFIED PREMIX (one daily dose; mass counted in the DM)
#     contents = MODEL units of nutrient per gram of product.
#     Potencies from FEDIAF Table VII-14 where applicable.
# =============================================================================
@dataclass(frozen=True)
class Premix:
    slug: str
    name: str
    contents: dict[str, float]
    max_g: float
    cost: float = 0.25


PREMIX: list[Premix] = [
    Premix(
        "salt", "table salt (NaCl)", {"sodium": 393.4, "chloride": 606.6}, 1.0, 0.20
    ),
    Premix("taurine", "taurine (pure)", {"taurine": 1000.0}, 0.60, 0.10),
    # 1 mg dl-alpha-tocopheryl acetate = 1 IU exactly (Table VII-14).
    Premix(
        "vit_e",
        "vitamin E, dl-alpha-tocopheryl acetate",
        {"vitamin_e": 1000.0},
        0.05,
        0.20,
    ),
]
for _p in PREMIX:
    for _k in _p.contents:
        assert _k in SPEC, f"unknown nutrient {_k} in premix {_p.slug}"
        assert SPEC[_k].internal in ("mg", "IU_E"), f"{_k}: unsupported unit"


# =============================================================================
# 8.  PER-GRAM COEFFICIENTS
# =============================================================================
def _clean(node):
    """None ('not measured') -> 0.0, so the LP never sees a None."""
    if isinstance(node, Mapping):
        return {k: _clean(v) for k, v in node.items()}
    return 0.0 if node is None else float(node)


PROFILE, COEFF, KCAL_PG = {}, {}, {}
WEIGHT_PG, WATER_PG, DRY_PG, ASH_PG, FIBRE_PG, NFE_PG = {}, {}, {}, {}, {}, {}
MISSING_TABLES: list[Food] = []
TABLE_PROBLEMS: list[str] = []
MISSING_TIERS: set[str] = set()

for _f in FOOD_SPECS:
    _tbl = _f.resolve()
    if _tbl is None:
        MISSING_TABLES.append(_f)
        continue
    TABLE_PROBLEMS += validate_table(_tbl, _f.key)
    _p = _clean(scale_to_grams(_tbl, 1.0, sig=None))  # per 1 g as weighed
    if _f.prep == "cooked":
        with warnings.catch_warnings(record=True) as _caught:
            warnings.simplefilter("always")
            _p = apply_cooking_degradation(
                _p, water_loss_rate=_f.water_loss, fat_loss_rate=_f.fat_loss, sig=12
            )
        MISSING_TIERS.update(str(w.message) for w in _caught)
    _s = summary(_p, sig=12)
    PROFILE[_f.key] = _p
    WEIGHT_PG[_f.key] = _s["weight"] if _f.mass_from_table else 1.0
    WATER_PG[_f.key] = _s["water"]
    DRY_PG[_f.key] = max(0.0, WEIGHT_PG[_f.key] - _s["water"])
    ASH_PG[_f.key] = _s["ashes"]
    FIBRE_PG[_f.key] = _s["fibers"]
    NFE_PG[_f.key] = _s["nfe"]
    KCAL_PG[_f.key] = energy_kcal(_p, factors=FEDIAF_CAT_ME, include_fiber=False)
    COEFF[_f.key] = {n.key: n.getter(_p) for n in NUTRIENTS}

FOODS = {f.key: f for f in FOOD_SPECS if f.key in PROFILE}
FLOURS = tuple(k for k in DOUGH_FLOUR_KEYS if k in FOODS)
SEAFOODS = tuple(k for k in SEA_FOOD_KEYS if k in FOODS and SEAFOOD_ENABLED.get(k))
SUPPLEMENTAL = tuple(k for k in SUPPLEMENTAL_KEYS if k in FOODS)
MARINE_OILS = tuple(k for k in SUPPLEMENTAL if FOODS[k].marine_oil)

DATA_MISSING = {
    n.key for n in NUTRIENTS if all(abs(COEFF[i][n.key]) < 1e-15 for i in COEFF)
}


# =============================================================================
# 9.  MODEL OBJECTS
# =============================================================================
def V(expr) -> float:
    v = pulp.value(expr)
    return 0.0 if v is None else float(v)


class Meal:
    """One meal TYPE.  Every day of that type is identical."""

    def __init__(self, key, label, days, items, premix):
        self.key, self.label, self.days = key, label, days
        self.items = list(items)  # [(grams_expr, food_key)]
        self.premix = premix

    def _f(self, table):
        return pulp.lpSum([q * table[k] for q, k in self.items])

    def premix_g(self):
        return pulp.lpSum([self.premix[p.slug] for p in PREMIX])

    def nutrient(self, key):
        return pulp.lpSum([q * COEFF[k][key] for q, k in self.items]) + pulp.lpSum(
            [self.premix[p.slug] * p.contents[key] for p in PREMIX if key in p.contents]
        )

    # premix powders: pure dry matter, ~0 kcal
    def kcal(self):
        return self._f(KCAL_PG)

    def weight(self):
        return self._f(WEIGHT_PG) + self.premix_g()

    def water(self):
        return self._f(WATER_PG)

    def dry(self):
        return self._f(DRY_PG) + self.premix_g()

    def ash(self):
        return self._f(ASH_PG)

    def fibre(self):
        return self._f(FIBRE_PG)

    def nfe(self):
        return self._f(NFE_PG)

    def marine_oil_g(self):
        return pulp.lpSum([q for q, k in self.items if k in MARINE_OILS])


class Week:
    """Weekly average per day -- the basis on which FEDIAF is checked."""

    def __init__(self, meals):
        self.meals = [m for m in meals if m is not None and m.days > 0]

    def per_day(self, fn):
        return pulp.lpSum([m.days * fn(m) for m in self.meals]) / DAYS

    def nutrient(self, key):
        return self.per_day(lambda m: m.nutrient(key))

    def kcal(self):
        return self.per_day(Meal.kcal)

    def weight(self):
        return self.per_day(Meal.weight)

    def water(self):
        return self.per_day(Meal.water)

    def dry(self):
        return self.per_day(Meal.dry)

    def ash(self):
        return self.per_day(Meal.ash)

    def fibre(self):
        return self.per_day(Meal.fibre)

    def nfe(self):
        return self.per_day(Meal.nfe)

    def marine_oil_g(self):
        return self.per_day(Meal.marine_oil_g)


# =============================================================================
# 10.  BUILD
# =============================================================================
def build(sea_days: int) -> dict:
    ins_days = DAYS - sea_days
    prob = pulp.LpProblem(f"cat_week_{ins_days}i{sea_days}s", pulp.LpMinimize)

    # ---- variables ---------------------------------------------------------
    # The dough is made ONCE for the whole week -> batch variables; each insect
    # day eats batch/ins_days.  Whole eggs are naturally integral at batch level.
    flour = {
        k: pulp.LpVariable(f"batch_{k}_g", 0, FOODS[k].hi * ins_days) for k in FLOURS
    }
    dough_water = pulp.LpVariable(
        "batch_water_g", 0, FOODS["water_dough"].hi * ins_days
    )
    dough_eggs = pulp.LpVariable("batch_eggs_n", 0, MAX_EGGS_WEEK, cat="Integer")

    sea = {k: pulp.LpVariable(f"sea_{k}_g", 0, FOODS[k].hi) for k in SEAFOODS}
    sea_water = pulp.LpVariable("sea_water_g", 0, FOODS["water_raw"].hi)
    # whole eggs PER non-insect meal (you cannot serve half a boiled egg twice)
    sea_eggs = pulp.LpVariable("sea_eggs_n", 0, MAX_EGGS_PER_SEA_MEAL, cat="Integer")

    sup = {
        (m, k): pulp.LpVariable(f"sup_{m}_{k}_g", 0, FOODS[k].hi)
        for m in ("ins", "sea")
        for k in SUPPLEMENTAL
    }
    pm = {p.slug: pulp.LpVariable(f"pm_{p.slug}_g", 0, p.max_g) for p in PREMIX}

    # ---- meals -------------------------------------------------------------
    ins_items = [(flour[k] / ins_days, k) for k in FLOURS]
    ins_items += [
        (dough_water / ins_days, "water_dough"),
        (EGG_G * dough_eggs / ins_days, "egg"),
    ]
    ins_items += [(sup[("ins", k)], k) for k in SUPPLEMENTAL]
    insect = Meal("insect", "INSECT DOUGH (gnocchi)", ins_days, ins_items, pm)

    sea_meal = None
    if sea_days:
        sea_items = [(sea[k], k) for k in SEAFOODS]
        sea_items += [(EGG_G * sea_eggs, "egg"), (sea_water, "water_raw")]
        sea_items += [(sup[("sea", k)], k) for k in SUPPLEMENTAL]
        sea_meal = Meal("sea", "NON-INSECT MEAL", sea_days, sea_items, pm)
    week = Week([insect, sea_meal])

    phase1, phase2 = [], []

    # ---- energy: weekly average is the law, single days may swing ----------
    kcal = week.kcal()
    prob += (kcal >= KCAL_PER_DAY * (1 - KCAL_TOL), "kcal_lo")
    prob += (kcal <= KCAL_PER_DAY * (1 + KCAL_TOL), "kcal_hi")
    kdev = pulp.LpVariable("kcal_dev", lowBound=0)
    prob += kdev >= kcal - KCAL_PER_DAY
    prob += kdev >= KCAL_PER_DAY - kcal
    phase2.append(W_KCAL_DEV * kdev / KCAL_PER_DAY)

    for m in week.meals:
        mk = m.kcal()
        prob += (mk >= KCAL_PER_DAY * (1 - PER_MEAL_KCAL_HARD), f"{m.key}_kcal_lo")
        prob += (mk <= KCAL_PER_DAY * (1 + PER_MEAL_KCAL_HARD), f"{m.key}_kcal_hi")
        d = pulp.LpVariable(f"{m.key}_kcal_dev", lowBound=0)
        prob += d >= mk - KCAL_PER_DAY * (1 + PER_MEAL_KCAL_SOFT)
        prob += d >= KCAL_PER_DAY * (1 - PER_MEAL_KCAL_SOFT) - mk
        phase2.append(W_MEAL_KCAL * d / KCAL_PER_DAY)

    # ---- physical shape ----------------------------------------------------
    week_dm = week.dry()
    prob += (week_dm >= DRY[0], "dry_lo")
    prob += (week_dm <= DRY[1], "dry_hi")
    for m in week.meals:
        w, wat = m.weight(), m.water()
        prob += (w >= SERVED[0], f"{m.key}_served_lo")
        prob += (w <= SERVED[1], f"{m.key}_served_hi")
        prob += (wat >= MOISTURE[0] * w, f"{m.key}_moist_lo")
        prob += (wat <= MOISTURE[1] * w, f"{m.key}_moist_hi")

    # ---- dough workability + "mostly insect" -------------------------------
    total_flour = pulp.lpSum(list(flour.values()))
    prob += (dough_water >= DOUGH_WATER_PER_FLOUR[0] * total_flour, "dough_lo")
    prob += (dough_water <= DOUGH_WATER_PER_FLOUR[1] * total_flour, "dough_hi")
    prob += (total_flour >= MIN_FLOUR_G_PER_DAY * ins_days, "min_flour")
    if sea_days:
        prob += (
            pulp.lpSum(list(sea.values())) + EGG_G * sea_eggs
            >= MIN_ANIMAL_G_PER_SEA_MEAL,
            "min_sea_animal",
        )
    prob += (dough_eggs + sea_days * sea_eggs <= MAX_EGGS_WEEK, "max_eggs_week")

    # ---- FEDIAF minima and maxima, elastic, WEEKLY AVERAGE -----------------
    short, over_kcal, over_dm = {}, {}, {}
    for n in NUTRIENTS:
        val = week.nutrient(n.key)
        lo = n.min_internal()
        if lo is not None and n.key not in DATA_MISSING:
            s = pulp.LpVariable(f"short_{n.key}", lowBound=0)
            prob += (val + s >= lo * kcal / 1000.0, f"min_{n.key}")
            short[n.key] = s
            phase1.append(W_FEDIAF_MIN * s / (lo * KCAL_PER_DAY / 1000.0))
        hi = n.max_kcal_internal()  # per 1000 kcal (N / prudent / NRC)
        if hi is not None:
            e = pulp.LpVariable(f"over_{n.key}", lowBound=0)
            prob += (val - e <= hi * kcal / 1000.0, f"max_{n.key}")
            over_kcal[n.key] = e
            phase1.append(W_FEDIAF_MAX * e / (hi * KCAL_PER_DAY / 1000.0))
        hi_dm = n.max_dm_internal()  # per 100 g DM (EU legal limits)
        if hi_dm is not None:
            e = pulp.LpVariable(f"overdm_{n.key}", lowBound=0)
            prob += (val - e <= hi_dm * week_dm / 100.0, f"maxdm_{n.key}")
            over_dm[n.key] = e
            phase1.append(W_LEGAL_MAX * e / (hi_dm * DRY_MATTER_G_PER_DAY / 100.0))

    # ---- arginine scales with protein --------------------------------------
    # FEDIAF §3.3.2 / Table VII-13: +0.02 g arginine per g crude protein above
    # the tabulated protein level (cats).  Linear -> straight into the LP.
    arg, prot = week.nutrient("arginine"), week.nutrient("protein")
    arg_base = SPEC["arginine"].min_internal() * kcal / 1000.0  # mg/day
    prot_base = SPEC["protein"].min_internal() * kcal / 1000.0  # g/day
    arg_slope = 20.0 * AA_DIGESTIBILITY_MARGIN  # mg arginine per g extra CP
    arg_s = pulp.LpVariable("short_arginine_protein", lowBound=0)
    prob += (
        arg + arg_s >= arg_base + arg_slope * (prot - prot_base),
        "arginine_protein_rule",
    )
    phase1.append(
        W_ARG * arg_s / (SPEC["arginine"].min_internal() * KCAL_PER_DAY / 1000.0)
    )

    # ---- Ca:P -- weekly average is what matters, meals must not swing ------
    P_REF = SPEC["phosphorus"].min_internal() * KCAL_PER_DAY / 1000.0
    ca, ph = week.nutrient("calcium"), week.nutrient("phosphorus")
    cap_lo = pulp.LpVariable("ca_p_short", lowBound=0)
    cap_hi = pulp.LpVariable("ca_p_over", lowBound=0)
    prob += (ca + cap_lo >= CA_P[0] * ph, "ca_p_lo")
    prob += (ca - cap_hi <= CA_P[1] * ph, "ca_p_hi")
    phase1 += [W_CA_P * cap_lo / P_REF, W_CA_P * cap_hi / P_REF]
    for m in week.meals:
        c, p = m.nutrient("calcium"), m.nutrient("phosphorus")
        s_lo = pulp.LpVariable(f"{m.key}_ca_p_short", lowBound=0)
        s_hi = pulp.LpVariable(f"{m.key}_ca_p_over", lowBound=0)
        prob += (c + s_lo >= CA_P_MEAL[0] * p, f"{m.key}_ca_p_lo")
        prob += (c - s_hi <= CA_P_MEAL[1] * p, f"{m.key}_ca_p_hi")
        phase1 += [0.5 * W_CA_P * s_lo / P_REF, 0.5 * W_CA_P * s_hi / P_REF]
    cap_dev = pulp.LpVariable("ca_p_sweet_dev", lowBound=0)
    prob += cap_dev >= ca - CA_P_SWEET * ph
    prob += cap_dev >= CA_P_SWEET * ph - ca
    phase2.append(W_CA_P_SWEET * cap_dev / (CA_P_SWEET * P_REF))

    # ---- vitamin E must follow the fat load (two independent rules) --------
    e_floor = SPEC["vitamin_e"].min_internal() * kcal / 1000.0  # IU/day
    vit_e = week.nutrient("vitamin_e")
    e_oil = pulp.LpVariable("short_vit_e_oil", lowBound=0)
    prob += (
        vit_e + e_oil >= e_floor + VIT_E_IU_PER_G_MARINE_OIL * week.marine_oil_g(),
        "vitE_fishoil",
    )
    e_unsat = pulp.LpVariable("short_vit_e_unsat", lowBound=0)
    prob += (
        vit_e + e_unsat
        >= e_floor
        + VIT_E_IU_PER_G_PUFA * week.nutrient("polyunsaturated")
        + VIT_E_IU_PER_G_MUFA * week.nutrient("monounsaturated"),
        "vitE_unsat",
    )
    ref_e = SPEC["vitamin_e"].min_internal() * KCAL_PER_DAY / 1000.0
    phase1 += [W_VIT_E * e_oil / ref_e, W_VIT_E * e_unsat / ref_e]

    # ---- n-6 : n-3 ---------------------------------------------------------
    n6 = week.nutrient("linoleic_acid") + week.nutrient("arachidonic_acid")
    n3 = (
        week.nutrient("alpha_linolenic_acid")
        + week.nutrient("timnodonic_acid")
        + week.nutrient("cervonic_acid")
    )
    prob += (n6 - N6_N3[1] * n3 <= 0, "n6n3_hi")
    prob += (n6 - N6_N3[0] * n3 >= 0, "n6n3_lo")

    # ---- vet layer: soft, phase 2 only -------------------------------------
    for n in NUTRIENTS:
        tgt = n.vet_target()
        if tgt is None:
            continue
        val = week.nutrient(n.key)
        w = W_VET_FAT if n.group == "fats" else W_VET
        if n.w_short > 0:
            d = pulp.LpVariable(f"vet_short_{n.key}", lowBound=0)
            prob += (val + d >= tgt, f"vet_lo_{n.key}")
            phase2.append(w * n.w_short * d / tgt)
        lo = n.min_internal()
        floor = 0.0 if lo is None else 1.05 * lo * KCAL_PER_DAY / 1000.0
        cap = max(n.over_factor * tgt, floor)
        e = pulp.LpVariable(f"vet_over_{n.key}", lowBound=0)
        prob += (val - e <= cap, f"vet_hi_{n.key}")
        phase2.append(W_VET * n.w_over * e / tgt)

    # ---- costs: fewest powders, smallest expensive portions ----------------
    phase2.append(pulp.lpSum([p.cost * pm[p.slug] / p.max_g for p in PREMIX]))
    phase2.append(
        GRAM_COST
        * (
            pulp.lpSum(list(flour.values())) / DAYS
            + pulp.lpSum(list(sea.values())) * sea_days / DAYS
            + pulp.lpSum([sup[k] for k in sup])
        )
    )

    return {
        "prob": prob,
        "week": week,
        "insect": insect,
        "sea": sea_meal,
        "flour": flour,
        "dough_water": dough_water,
        "dough_eggs": dough_eggs,
        "sea_g": sea,
        "sea_water": sea_water,
        "sea_eggs": sea_eggs,
        "sup": sup,
        "pm": pm,
        "ins_days": ins_days,
        "sea_days": sea_days,
        "phase1": pulp.lpSum(phase1),
        "phase2": pulp.lpSum(phase2),
        "arg_req": arg_base + arg_slope * (prot - prot_base),
    }


# =============================================================================
# 11.  SOLVE (lexicographic: FEDIAF first, vet second)
# =============================================================================
def solve(sea_days: int) -> dict:
    m = build(sea_days)
    prob = m["prob"]

    prob.setObjective(m["phase1"])
    prob.solve(SOLVER)
    if pulp.LpStatus[prob.status] != "Optimal":
        return {"status": pulp.LpStatus[prob.status], "model": m}
    v1 = V(m["phase1"])

    # relative tolerance: an absolute 1e-6 can make a MIP infeasible for CBC
    prob += (m["phase1"] <= v1 + 1e-6 + 1e-4 * abs(v1), "lock_phase1")
    prob.setObjective(m["phase2"])
    prob.solve(SOLVER)
    if pulp.LpStatus[prob.status] != "Optimal":
        return {"status": "phase2 " + pulp.LpStatus[prob.status], "model": m}

    if DEBUG:
        for name, c in prob.constraints.items():
            if abs(c.value()) < 1e-7:
                print("  binding:", name)
    return {"status": "Optimal", "fediaf": v1, "vet": V(m["phase2"]), "model": m}


# =============================================================================
# 12.  REPORT
# =============================================================================
def _meal_line(mm: Meal) -> None:
    w, wat = V(mm.weight()), V(mm.water())
    print(
        f"  -> served{'':<17}: {w:7.1f} g, {V(mm.kcal()):5.0f} kcal, "
        f"{100 * wat / max(w, 1e-9):4.1f} % water, {w - wat:5.1f} g DM"
    )


def report(res: dict) -> None:
    m = res["model"]
    week, insect, sea = m["week"], m["insect"], m["sea"]
    S, C = m["ins_days"], m["sea_days"]
    kcal, dm = V(week.kcal()), V(week.dry())
    k1000, dm100 = kcal / 1000.0, dm / 100.0

    print("=" * 88)
    print(f"WEEKLY PLAN : {S} insect day(s) + {C} non-insect day(s)")
    print(
        f"Energy      : {kcal:.0f} kcal/day (FEDIAF cat equation 4/8.5/4 on NFE)"
        f"   target {KCAL_PER_DAY:.0f}"
    )
    print(
        f"FEDIAF basis: adult cat, {DIET_FORM} diet, {MER:.0f} kcal/kg BW^0.67 "
        f"column ({DENSITY_BASIS}); this plan feeds {ACTUAL_MER:.0f}"
    )
    print(
        f"Margins     : minima x{MIN_SAFETY:.2f}, essential AA x"
        f"{AA_DIGESTIBILITY_MARGIN:.2f} (digestibility <80 %)   |   "
        f"violation {res['fediaf']:.5f}"
    )
    print("=" * 88)

    # ---- recipe ------------------------------------------------------------
    print(f"\nWEEKLY INSECT DOUGH  (one batch, cook once, portion into {S} meals)")
    for k in FLOURS:
        g = V(m["flour"][k])
        if g > 1e-6:
            print(f"  {FOODS[k].label:<26}: {g:7.1f} g")
    print(
        f"  {'water':<26}: {V(m['dough_water']):7.1f} g "
        f"(-{DOUGH_WATER_LOSS:.0%} while cooking)"
    )
    print(
        f"  {'whole eggs (boiled)':<26}: {V(m['dough_eggs']):7.0f} egg(s)"
        f"  = {V(m['dough_eggs']) * EGG_G:.0f} g"
    )
    print(f"  -> one insect meal = 1/{S} of the batch")
    _meal_line(insect)

    if sea is not None:
        print(f"\nNON-INSECT MEAL  (x{C} per week, identical each time)")
        for k in SEAFOODS:
            g = V(m["sea_g"][k])
            if g > 1e-6:
                print(f"  {FOODS[k].label:<26}: {g:7.1f} g")
        if V(m["sea_eggs"]) > 0:
            print(f"  {'whole eggs (boiled)':<26}: {V(m['sea_eggs']):7.0f} egg(s)")
        if V(m["sea_water"]) > 1e-6:
            print(f"  {'water':<26}: {V(m['sea_water']):7.1f} g")
        _meal_line(sea)

    print("\nSUPPLEMENTAL FOODS  (per meal - part of the diet, not extras)")
    print(f"  {'':<26}{'insect meal':>13}{'non-insect':>13}")
    for k in SUPPLEMENTAL:
        gi = V(m["sup"][("ins", k)])
        gs = V(m["sup"][("sea", k)]) if sea is not None else 0.0
        if gi > 1e-6 or gs > 1e-6:
            print(f"  {FOODS[k].label:<26}{gi:>13.2f}{gs:>13.2f}   g")

    used = [(p, V(m["pm"][p.slug])) for p in PREMIX if V(m["pm"][p.slug]) > 1e-9]
    print("\nPURIFIED PREMIX, EVERY DAY (what food alone cannot deliver)")
    if not used:
        print("  none - the ingredients alone meet every FEDIAF minimum.")
    for p, g in used:
        elems = ", ".join(
            f"{g * c:.3g} {SPEC[k].internal.replace('IU_E','IU')} " f"{SPEC[k].label}"
            for k, c in p.contents.items()
            if k != "methionine_cystine"
        )
        print(f"  {p.name:<38}: {g * 1000:8.2f} mg -> {elems}")

    # ---- FEDIAF compliance -------------------------------------------------
    print("\n" + "-" * 88)
    print(
        "FEDIAF COMPLIANCE - WEEKLY AVERAGE   (minima and (N) maxima per 1000 "
        "kcal ME)"
    )
    print("-" * 88)
    print(f"{'nutrient':<28}{'min':>10}{'actual':>12}{'max':>11}  unit   status")
    group, shorts, overs = None, [], []
    for n in NUTRIENTS:
        lo, hi = n.fediaf_min(), n.fmax_kcal
        if lo is None and hi is None:
            continue
        if n.group != group:
            group = n.group
            print(f"  [{group}]")
        act = V(week.nutrient(n.key)) / n.f2i / k1000
        if n.key in DATA_MISSING:
            st = "NO DATA"
        elif lo is not None and act < lo * 0.995:
            st = f"SHORT ({100 * act / lo:.0f} %)"
            shorts.append((n, lo, act, "min", n.unit_label + "/1000 kcal"))
        elif hi is not None and act > hi * 1.005:
            st = f"OVER ({100 * act / hi:.0f} % of max)"
            overs.append((n, hi, act, n.fmax_kcal_src, n.unit_label + "/1000 kcal"))
        else:
            st = "ok"
        print(
            f"{n.label:<28}{'-' if lo is None else f'{lo:.4g}':>10}{act:>12.4g}"
            f"{'-' if hi is None else f'{hi:.4g}':>11}  {n.unit_label:<5}  {st}"
        )

    print("\nEU LEGAL MAXIMA (L) - dry-matter basis, the only basis FEDIAF gives")
    print(f"{'nutrient':<28}{'actual':>12}{'legal max':>12}  unit/100 g DM  status")
    for n in NUTRIENTS:
        if n.fmax_dm is None:
            continue
        act = V(week.nutrient(n.key)) / n.f2i / dm100
        st = "ok" if act <= n.fmax_dm * 1.005 else f"OVER ({100*act/n.fmax_dm:.0f} %)"
        if st != "ok":
            overs.append((n, n.fmax_dm, act, n.fmax_dm_src, n.unit_label + "/100 g DM"))
        print(f"{n.label:<28}{act:>12.4g}{n.fmax_dm:>12.4g}  {n.unit_label:<13}{st}")

    # ---- ratios and dynamic requirements -----------------------------------
    ph = V(week.nutrient("phosphorus"))
    print(
        f"\nCa:P weekly average    : "
        f"{V(week.nutrient('calcium')) / max(ph, 1e-9):.2f} : 1"
        f"   (FEDIAF adult {CA_P[0]:.0f}/1 .. {CA_P[1]:.0f}/1 (N), "
        f"target {CA_P_SWEET})"
    )
    for mm in week.meals:
        p = V(mm.nutrient("phosphorus"))
        print(
            f"Ca:P {mm.key + ' meal':<18}: "
            f"{V(mm.nutrient('calcium')) / max(p, 1e-9):.2f} : 1"
        )
    print(
        f"Arginine (protein-adj.): need {V(m['arg_req']):.0f} mg/day, "
        f"have {V(week.nutrient('arginine')):.0f} mg   "
        f"(+0.02 g/g CP above {SPEC['protein'].min_internal() * k1000:.1f} g)"
    )

    # ---- fatty acids / vet fidelity ---------------------------------------
    print("\n" + "-" * 88)
    print(f"FAT PROFILE vs VET SHEET (vet x {VET_SCALE:.2f}, per day)")
    print("-" * 88)
    print(f"{'nutrient':<28}{'target':>12}{'actual':>12}{'%':>8}  unit")
    for n in NUTRIENTS:
        if n.group not in ("fats", "macros") or n.vet_target() is None:
            continue
        t, a = n.vet_target(), V(week.nutrient(n.key))
        print(f"{n.label:<28}{t:>12.4g}{a:>12.4g}{100 * a / t:>7.0f}%  {n.internal}")
    n6 = V(week.nutrient("linoleic_acid")) + V(week.nutrient("arachidonic_acid"))
    n3 = sum(
        V(week.nutrient(k))
        for k in ("alpha_linolenic_acid", "timnodonic_acid", "cervonic_acid")
    )
    print(
        f"{'n-6 : n-3':<28}{'5.5':>12}{n6 / max(n3, 1e-9):>12.2f}"
        f"{'':>8}  (window {N6_N3[0]}-{N6_N3[1]})"
    )
    e_floor = SPEC["vitamin_e"].min_internal() * k1000
    need_oil = e_floor + VIT_E_IU_PER_G_MARINE_OIL * V(week.marine_oil_g())
    need_pufa = (
        e_floor
        + VIT_E_IU_PER_G_PUFA * V(week.nutrient("polyunsaturated"))
        + VIT_E_IU_PER_G_MUFA * V(week.nutrient("monounsaturated"))
    )
    print(
        f"{'vitamin E (fish-oil rule)':<28}{need_oil:>12.2f}"
        f"{V(week.nutrient('vitamin_e')):>12.2f}{'':>8}  IU"
    )
    print(
        f"{'vitamin E (PUFA+MUFA rule)':<28}{need_pufa:>12.2f}"
        f"{V(week.nutrient('vitamin_e')):>12.2f}{'':>8}  IU"
    )

    # ---- physical summary + energy cross-check -----------------------------
    w, wat = V(week.weight()), V(week.water())
    prot, fat = V(week.nutrient("protein")), V(week.nutrient("fat"))
    carb, ash = V(week.nutrient("carbs")), V(week.ash())
    fib, nfe = V(week.fibre()), V(week.nfe())
    nrc = nrc_me_kcal(prot, fat, nfe, fib, dm, w)
    print("\n" + "-" * 88)
    print(
        f"Average day: {w:.0f} g served ({100 * wat / w:.1f} % water), "
        f"{dm:.1f} g DM, {kcal:.0f} kcal, {kcal / dm:.2f} kcal/g DM"
    )
    print(
        f"  DM basis : protein {100*prot/dm:.1f} %, fat {100*fat/dm:.1f} %, "
        f"carbs {100*carb/dm:.1f} % (fibre {100*fib/dm:.1f} %), "
        f"ash {100*ash/dm:.1f} %   (vet: 61.1 / 24.0 / 2.0 % NFE)"
    )
    print(
        f"  energy cross-check: NRC 4-step (fibre-corrected) = {nrc:.0f} kcal "
        f"vs {kcal:.0f} kcal linear  ({100 * (nrc - kcal) / kcal:+.1f} %)"
    )
    if abs(nrc - kcal) / kcal > 0.05:
        print(
            "  NOTE: >5 % gap - chitin/fibre is depressing digestibility. "
            "Weigh the cat weekly and adjust KCAL_PER_DAY."
        )

    # ---- blind spots / failures -------------------------------------------
    blind = sorted(k for k in DATA_MISSING if SPEC[k].fmin is not None)
    if blind:
        print("\n" + "-" * 88)
        print("BLIND SPOTS - FEDIAF requires these, no ingredient table has a value")
        print("-" * 88)
        for k in blind:
            n = SPEC[k]
            src = (
                "premix covers it"
                if any(k in p.contents for p in PREMIX)
                else "<-- ADD A SOURCE OR FILL THE TABLE"
            )
            print(
                f"  {n.label:<28}: need {n.fediaf_min() * k1000:.4g} "
                f"{n.unit_label}/day, have {V(week.nutrient(k)) / n.f2i:.4g}   {src}"
            )

    if shorts or overs:
        print("\n" + "-" * 88)
        print("NOT MET - relax a bound, add an ingredient, or fix a table")
        print("-" * 88)
        for n, lim, a, _s, u in shorts:
            print(f"  SHORT {n.label:<26}: {a:.4g} vs min {lim:.4g} {u}")
        for n, lim, a, src, u in overs:
            print(f"  OVER  {n.label:<26}: {a:.4g} vs max {lim:.4g} {u}  [{src}]")


# =============================================================================
# 13.  MAIN
# =============================================================================
def _startup_notes() -> None:
    for f in MISSING_TABLES:
        print(f"NOTE: nutrients.{f.table} not found -> '{f.key}' disabled.")
    if TABLE_PROBLEMS:
        print("NOTE: table sanity check:")
        for p in TABLE_PROBLEMS:
            print("   -", p)
    if MISSING_TIERS:
        print("NOTE: cooking used the default retention tier for:")
        for t in sorted(MISSING_TIERS):
            print("   -", t)
    print(
        f"Shape : {SERVED_G_PER_DAY:.0f} g served, {DRY_MATTER_G_PER_DAY:.1f} g "
        f"DM -> {100 * _IMPLIED_MOISTURE:.1f} % water "
        f"(allowed {100 * MOISTURE[0]:.0f}-{100 * MOISTURE[1]:.0f} %), "
        f"{KCAL_PER_DAY / DRY_MATTER_G_PER_DAY:.2f} kcal/g DM"
    )
    bw067 = CAT_BW_KG**0.67
    lo_mer, hi_mer = LIFESTYLE_MER[CAT_LIFESTYLE]
    print(
        f"Energy: {KCAL_PER_DAY:.0f} kcal/day = {ACTUAL_MER:.0f} kcal/kg "
        f"BW^0.67 = {KCAL_PER_DAY / CAT_BW_KG:.0f} kcal/kg BW"
    )
    print(
        f"   FEDIAF VII-9 '{CAT_LIFESTYLE}': {lo_mer:.0f}-{hi_mer:.0f} "
        f"kcal/kg^0.67 = {lo_mer * bw067:.0f}-{hi_mer * bw067:.0f} kcal/day"
        f"  -> {'OK' if lo_mer <= ACTUAL_MER <= hi_mer else 'OUT OF BAND'}"
    )
    if not lo_mer <= ACTUAL_MER <= hi_mer:
        print(
            "   !! adjust KCAL_PER_DAY or CAT_LIFESTYLE, then re-weigh the cat "
            "weekly for 4 weeks and correct for real weight change."
        )
    if not FLOURS:
        raise SystemExit("No insect flour table available - nothing to optimise.")


def main() -> None:
    _startup_notes()
    results = []
    for sea_days in SEA_DAYS_CHOICES:
        if sea_days and not SEAFOODS and "egg" not in FOODS:
            continue
        r = solve(sea_days)
        r["sea_days"] = sea_days
        if r["status"] != "Optimal":
            print(f"[{DAYS - sea_days}+{sea_days}] -> {r['status']}")
            continue
        results.append(r)

    if not results:
        print(
            "No feasible plan. Loosen KCAL_TOL / DRY_TOL / SERVED_TOL, raise a "
            "food's 'hi' bound, or re-check SERVED vs DRY_MATTER consistency."
        )
        return

    def order(r):
        return (round(r["fediaf"], 6), r["vet"])

    best = min(results, key=order)
    print("\nScenarios (FEDIAF violation first, then vet fidelity):")
    for r in sorted(results, key=order):
        mark = "  <- chosen" if r is best else ""
        print(
            f"  {DAYS - r['sea_days']} insect + {r['sea_days']} sea : "
            f"FEDIAF {r['fediaf']:9.5f}, vet {r['vet']:8.4f}{mark}"
        )
    print()
    report(best)


if __name__ == "__main__":
    main()
