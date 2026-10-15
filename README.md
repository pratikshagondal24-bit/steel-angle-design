# Unequal Angle Member Checker

Guided Streamlit prototype for a T.Y. Civil Engineering FA-2 assignment. It asks the member type first, then axial force/material values, connection details (for tension), and the angle section last.

## Current scope

- **Tension:** calculates and reports yielding, angle rupture (including the shear-lag factor), and bolted block shear separately as `Satisfies` or `Not Satisfy`.
- **Compression:** the app accepts this selection and force, then validates the section name, but clearly reports that the compression buckling module is not yet implemented. It never shows tension checks as compression results.
- Supported lookup includes the equal-angle Table III and unequal-angle Table IV size/thickness combinations transcribed from the supplied SP 6 (Part 1):1964. Examples: ISA 90x60x6 has area 865 mm² per angle; ISA 55x55x10 has area 1002 mm² per angle. Enter `2 ISA 55x55x10` for a symmetric double angle, assumed to have one angle on each side of the gusset with equal force sharing.
- The connection model is one bolt line through one leg of each angle. The guided example defaults are 375 kN, M20 bolts with 22 mm holes, 50 mm pitch, 33 mm end distance, 5 bolts, and a 37.8 mm transverse block-path length. The heel-to-bolt-line gauge is not requested; the app infers it as connected-leg width minus the entered transverse path, so verify this geometric assumption against the actual connection drawing. Units are mm, mm², MPa (N/mm²), and kN.

`angle_sections.py` holds the lookup catalogue and normalization. `design.py` validates inputs and calculates the three tension checks. `app.py` provides the guided interface. `test_design.py` includes three direct-substitution reference cases and invalid-input checks.

## Run

1. Install Python 3.10 or newer.
2. Open a terminal in the project folder. (Optionally create and activate a virtual environment.)
3. Install dependencies: `python -m pip install -r requirements.txt`
4. Start the application: `python -m streamlit run app.py`
5. Run tests: `python -m unittest -v` (or `python -m pytest -q` after installing the listed development dependency).

## Engineering assumptions and limits

The code paths are based on IS 800:2007 Clause 6.2 (gross yielding), Clause 6.3.3 (single angle connected through one leg), and Clause 6.4.1 (bolted block shear), with default γm0 = 1.10 and γm1 = 1.25. Double-angle capacities are calculated as twice the one-angle capacity for a symmetric arrangement on opposite sides of the gusset. Inputs and calculations are displayed step by step. The interface uses a deterministic explanation; no language model produces or changes the engineering calculations.

The provided `is.800.2007.pdf` was zero bytes in the supplied folder and could not be checked. Verify clause wording, equations, geometry assumptions, amendments, partial factors, material properties, and current section availability against a licensed/current IS 800:2007 and relevant material/section standards. SP 6 (Part 1):1964 is a historical steel book, and not proof of current availability.

This is not professional design software. It does not design bolts/gussets or check bolt strength, bearing, tear-out, eccentricity, fatigue, slenderness limits, serviceability, load combinations, or other connection/member limit states. For compression, use a separate verified buckling design workflow.
