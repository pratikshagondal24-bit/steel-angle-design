"""Transparent IS 800 tension checks for one unequal angle connected by one leg."""

from dataclasses import dataclass
from math import sqrt

from angle_sections import AngleSection


class InputError(ValueError):
    """Raised for missing or physically invalid design inputs."""


@dataclass(frozen=True)
class AngleTensionInput:
    section: AngleSection
    angle_count: int
    applied_load_kn: float
    fy_mpa: float
    fu_mpa: float
    bolt_count: int
    bolt_diameter_mm: float
    hole_diameter_mm: float
    pitch_mm: float
    end_distance_mm: float
    connected_leg: str
    gauge_from_heel_mm: float
    transverse_length_mm: float
    gamma_m0: float = 1.10
    gamma_m1: float = 1.25


@dataclass(frozen=True)
class Check:
    name: str
    strength_kn: float
    passes: bool
    formula: str
    calculation: str


@dataclass(frozen=True)
class AngleTensionResult:
    checks: tuple[Check, Check, Check]
    design_strength_kn: float
    governing_check: str
    utilization: float
    passes: bool
    beta: float
    areas: dict[str, float]


def _positive(name: str, value: float) -> None:
    if value is None or value <= 0:
        raise InputError(f"{name} must be greater than zero.")


def calculate_angle_tension(data: AngleTensionInput) -> AngleTensionResult:
    """Calculate yielding, angle net rupture and bolted block shear.

    The connection model is a single bolt line in one leg of a single angle.
    The student supplies transverse block-path length from the critical bolt
    line to the leg toe. Formula and geometric assumptions must be checked
    against the licensed applicable IS 800:2007 and its amendments.
    """
    for name, value in (
        ("factored tensile force", data.applied_load_kn), ("fy", data.fy_mpa),
        ("fu", data.fu_mpa), ("bolt diameter", data.bolt_diameter_mm),
        ("hole diameter", data.hole_diameter_mm), ("pitch", data.pitch_mm),
        ("end distance", data.end_distance_mm), ("bolt gauge from heel", data.gauge_from_heel_mm),
        ("transverse block-path length", data.transverse_length_mm),
        ("gamma_m0", data.gamma_m0), ("gamma_m1", data.gamma_m1),
    ):
        _positive(name, value)
    if not isinstance(data.bolt_count, int) or data.bolt_count < 2:
        raise InputError("Use at least 2 bolts in one line so the connection length Lc is defined.")
    if data.hole_diameter_mm < data.bolt_diameter_mm:
        raise InputError("Hole diameter must be at least the nominal bolt diameter.")
    if data.fu_mpa < data.fy_mpa:
        raise InputError("fu should be at least fy; verify the material specification.")
    if data.connected_leg not in {"longer", "shorter"}:
        raise InputError("Select whether the longer or shorter angle leg is connected.")

    sec = data.section
    if data.angle_count not in {1, 2}:
        raise InputError("This prototype supports one angle or a symmetric double-angle pair.")
    t = sec.thickness_mm
    connected = sec.long_leg_mm if data.connected_leg == "longer" else sec.short_leg_mm
    outstanding = sec.short_leg_mm if data.connected_leg == "longer" else sec.long_leg_mm
    if data.hole_diameter_mm >= connected:
        raise InputError("Hole diameter leaves no net width in the connected leg.")
    if data.transverse_length_mm <= data.hole_diameter_mm / 2:
        raise InputError("Transverse block-path length must exceed half the hole diameter.")
    if data.gauge_from_heel_mm >= connected:
        raise InputError("Bolt gauge from heel must be less than the connected leg width.")

    # IS 800:2007 Cl. 6.2: gross-section yielding.
    gross_area = data.angle_count * sec.gross_area_mm2
    t_y = gross_area * data.fy_mpa / data.gamma_m0 / 1000
    ycheck = Check("Yielding", t_y, data.applied_load_kn <= t_y,
                   r"T_{dg}=A_g f_y/\gamma_{m0}",
                   f"Ag,total={data.angle_count}×{sec.gross_area_mm2:.0f}={gross_area:.0f} mm²; Tdg=Ag,total×fy/γm0/1000={t_y:.2f} kN")

    # Single angle through one leg, Cl. 6.3.3. Lc is bolt-line length between
    # the outermost bolt centres. The beta limits are applied as specified.
    lc = (data.bolt_count - 1) * data.pitch_mm
    # bs is the outstanding leg width plus the connected-leg portion to the
    # bolt line, less one thickness. This applies for either connected leg;
    # the connected leg choice only changes which leg is outstanding.
    bs = outstanding + data.gauge_from_heel_mm - t
    beta_raw = 1.4 - 0.076 * (outstanding / t) * (data.fy_mpa / data.fu_mpa) * (bs / lc)
    beta_cap = data.fu_mpa * data.gamma_m0 / (data.fy_mpa * data.gamma_m1)
    beta = min(beta_cap, max(0.7, beta_raw))
    anc = (connected - data.hole_diameter_mm) * t
    ago = (outstanding - t / 2) * t
    t_n_single = (0.9 * anc * data.fu_mpa / data.gamma_m1 + beta * ago * data.fy_mpa / data.gamma_m0) / 1000
    t_n = data.angle_count * t_n_single
    ncheck = Check("Rupture", t_n, data.applied_load_kn <= t_n,
                   r"T_{dn}=0.9A_{nc}f_u/\gamma_{m1}+\beta A_{go}f_y/\gamma_{m0}",
                   f"Per angle: Anc=({connected:g}−{data.hole_diameter_mm:g})×{t:g}={anc:.1f} mm²; Ago=({outstanding:g}−{t:g}/2)×{t:g}={ago:.1f} mm²; Lc={lc:g} mm; bs={bs:.1f} mm; β raw={beta_raw:.3f}, applied β={beta:.3f}. Total for {data.angle_count} angle(s): Tdn={data.angle_count}×{t_n_single:.2f}={t_n:.2f} kN")

    # Bolted block-shear model for one bolt line. Lv includes half a hole at
    # each end; the net shear deduction uses the full hole diameter per bolt.
    lv = data.end_distance_mm + (data.bolt_count - 1) * data.pitch_mm + data.hole_diameter_mm / 2
    avg = lv * t
    avn = (lv - data.bolt_count * data.hole_diameter_mm) * t
    atg = data.transverse_length_mm * t
    atn = (data.transverse_length_mm - data.hole_diameter_mm / 2) * t
    if avn <= 0:
        raise InputError("Bolt holes deduct all of the longitudinal net shear length; revise pitch/count/edge distance.")
    if atn <= 0:
        raise InputError("Bolt hole deduction leaves no net transverse tension area.")
    tb1 = (avg * data.fy_mpa / (sqrt(3) * data.gamma_m0) + 0.9 * atn * data.fu_mpa / data.gamma_m1) / 1000
    tb2 = (0.9 * avn * data.fu_mpa / (sqrt(3) * data.gamma_m1) + atg * data.fy_mpa / data.gamma_m0) / 1000
    t_b = data.angle_count * min(tb1, tb2)
    bcheck = Check("Block shear", t_b, data.applied_load_kn <= t_b,
                   r"T_{db}=\min\left[\frac{A_{vg}f_y}{\sqrt{3}\gamma_{m0}}+\frac{0.9A_{tn}f_u}{\gamma_{m1}},\;\frac{0.9A_{vn}f_u}{\sqrt{3}\gamma_{m1}}+\frac{A_{tg}f_y}{\gamma_{m0}}\right]",
                   f"Per angle: Lv={lv:.1f} mm; Avg={avg:.1f}, Avn={avn:.1f}, Atg={atg:.1f}, Atn={atn:.1f} mm²; combination 1={tb1:.2f} kN; combination 2={tb2:.2f} kN. Total for {data.angle_count} angle(s): Tdb={data.angle_count}×{min(tb1, tb2):.2f}={t_b:.2f} kN")

    checks = (ycheck, ncheck, bcheck)
    governing = min(checks, key=lambda check: check.strength_kn)
    td = governing.strength_kn
    return AngleTensionResult(checks, td, governing.name, data.applied_load_kn / td,
                              all(check.passes for check in checks), beta,
                              {"Ag": gross_area, "Anc": anc * data.angle_count, "Ago": ago * data.angle_count,
                               "Avg": avg, "Avn": avn, "Atg": atg, "Atn": atn,
                               "Lc": lc, "bs": bs, "Lv": lv})


def explain_angle_result(result: AngleTensionResult, force_kn: float) -> str:
    if result.passes:
        return (f"The angle passes the three included tension checks. The smallest calculated resistance is "
                f"{result.design_strength_kn:.2f} kN ({result.governing_check}); the applied factored force "
                f"{force_kn:.2f} kN uses {result.utilization * 100:.1f}% of it.")
    failed = ", ".join(check.name.lower() for check in result.checks if not check.passes)
    return (f"The angle does not pass: the applied factored force is greater than the calculated resistance for "
            f"{failed}. The lowest design strength is {result.design_strength_kn:.2f} kN, governed by {result.governing_check}.")
