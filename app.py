"""Guided Streamlit app for a single unequal-angle tension-member check."""

import streamlit as st

from angle_sections import CATALOG, parse_angle
from design import AngleTensionInput, InputError, calculate_angle_tension, explain_angle_result


st.set_page_config(page_title="AI Steel Angle Design | IS 800", page_icon="🏗️", layout="wide")
st.title("🏗️ AI Application for Steel Angle Design")
st.caption("FA-2 · Design of Steel Structures · IS 800:2007 educational prototype")
st.warning("For student learning only. Check the applicable licensed IS 800:2007 and amendments, material standards, connection geometry, and every omitted design requirement before relying on a result.")

if "step" not in st.session_state:
    st.session_state.step = 0

if st.button("Start over", key="restart"):
    for key in ("step", "member_type", "force_kn", "fy", "fu", "connection", "section_text"):
        st.session_state.pop(key, None)
    st.session_state.step = 0
    st.rerun()

st.progress(min((st.session_state.step + 1) / 4, 1.0), text=f"Step {min(st.session_state.step + 1, 4)} of 4")

if st.session_state.step == 0:
    with st.form("member_type_form"):
        st.subheader("1. Which member do you want to check?")
        member_type = st.radio("Select member type", ["Tensile member", "Compressive member"], horizontal=True)
        submitted = st.form_submit_button("Continue")
    if submitted:
        st.session_state.member_type = member_type
        st.session_state.step = 1
        st.rerun()

elif st.session_state.step == 1:
    with st.form("force_form"):
        st.subheader("2. Enter the force")
        force = st.number_input("Factored axial force (kN)", min_value=0.01, value=375.0, step=5.0)
        fy = st.number_input("Yield stress fy (MPa = N/mm²)", min_value=1.0, value=250.0, step=5.0)
        fu = st.number_input("Ultimate tensile stress fu (MPa = N/mm²)", min_value=1.0, value=410.0, step=5.0)
        st.caption("Enter material strengths from the relevant material specification and thickness range. The app does not infer grade properties.")
        submitted = st.form_submit_button("Continue")
    if submitted:
        if fu < fy:
            st.error("fu must be at least fy. Verify the material values.")
        else:
            st.session_state.force_kn = force
            st.session_state.fy = fy
            st.session_state.fu = fu
            st.session_state.step = 2
            st.rerun()

elif st.session_state.step == 2:
    st.subheader("3. Connection and material details")
    if st.session_state.member_type == "Compressive member":
        st.info("The current prototype calculates the three requested tension checks (yielding, angle rupture, and block shear). Compression design requires additional buckling inputs and checks and is not implemented in this version. Continue to section selection to confirm the angle exists in the steel book.")
        if st.button("Continue to section selection"):
            st.session_state.step = 3
            st.rerun()
    else:
        with st.form("connection_form"):
            bolt_count = st.number_input("Number of bolts in one line along the load", min_value=2, max_value=20, value=5, step=1)
            bolt_diameter = st.number_input("Nominal bolt diameter (mm)", min_value=1.0, value=20.0, step=1.0)
            hole_diameter = st.number_input("Hole diameter d₀ (mm)", min_value=1.0, value=22.0, step=1.0)
            pitch = st.number_input("Bolt pitch along load direction (mm)", min_value=1.0, value=50.0, step=5.0)
            end_distance = st.number_input("End distance to first bolt centre (mm)", min_value=1.0, value=33.0, step=1.0)
            connected_leg = st.radio("Which angle leg is connected to the gusset?", ["Longer leg", "Shorter leg"], horizontal=True)
            transverse = st.number_input("Block path length from the end bolt line to leg toe, Lt (mm)", min_value=1.0, value=37.8, step=1.0)
            st.caption("Model defaults: 5 bolts in one line; one bolt line through one connected leg. The heel-to-bolt-line gauge is not requested; the calculation derives it from the selected connected-leg width and Lt. Confirm this geometry matches your connection drawing.")
            submitted = st.form_submit_button("Continue to section selection")
        if submitted:
            st.session_state.connection = {
                "bolt_count": int(bolt_count), "bolt_diameter_mm": bolt_diameter,
                "hole_diameter_mm": hole_diameter, "pitch_mm": pitch,
                "end_distance_mm": end_distance,
                "connected_leg": "longer" if connected_leg == "Longer leg" else "shorter",
                "transverse_length_mm": transverse,
            }
            st.session_state.step = 3
            st.rerun()

elif st.session_state.step == 3:
    with st.form("section_form"):
        st.subheader("4. Enter your angle section")
        section_text = st.text_input("Enter designation (examples: ISA 90x60x6 or 2 ISA 55x55x10)", placeholder="Enter your angle")
        st.caption(f"Catalogue lookup contains {len(CATALOG)} equal and unequal angle size/thickness combinations from SP 6 (Part 1):1964, Tables III and IV. Prefix with '2' for a symmetric double-angle pair, one angle on each side of the gusset.")
        submitted = st.form_submit_button("Check this section", type="primary")
    if submitted:
        parsed = parse_angle(section_text)
        if parsed is None:
            st.error("please select correct section")
        elif st.session_state.member_type == "Compressive member":
            section, angle_count = parsed
            designation = f"{angle_count}×{section.designation}" if angle_count == 2 else section.designation
            st.info(f"{designation} is listed in the steel-book catalogue. Compression buckling checks are not part of this tension-only prototype.")
        else:
            section, angle_count = parsed
            try:
                connected_leg_width = section.long_leg_mm if st.session_state.connection["connected_leg"] == "longer" else section.short_leg_mm
                # The UI omits gauge as requested. Infer it only under the
                # displayed straight-leg geometry assumption: width = gauge + Lt.
                derived_gauge = connected_leg_width - st.session_state.connection["transverse_length_mm"]
                data = AngleTensionInput(
                    section=section, angle_count=angle_count,
                    applied_load_kn=st.session_state.force_kn,
                    fy_mpa=st.session_state.fy, fu_mpa=st.session_state.fu,
                    gauge_from_heel_mm=derived_gauge,
                    **st.session_state.connection,
                )
                result = calculate_angle_tension(data)
            except InputError as exc:
                st.error(str(exc))
            else:
                designation = f"{angle_count}×{section.designation}" if angle_count == 2 else section.designation
                st.subheader(f"Results for {designation}")
                st.write(f"Steel-book gross area per angle = **{section.gross_area_mm2:.0f} mm²** · total Ag = **{result.areas['Ag']:.0f} mm²** · applied factored tensile force = **{data.applied_load_kn:.2f} kN**")
                st.markdown("### Three required checks")
                for check in result.checks:
                    status = "Satisfies" if check.passes else "Not Satisfy"
                    st.markdown(f"**{check.name} = {status}**  ·  Design strength = **{check.strength_kn:.2f} kN**")
                st.markdown(f"**Overall design strength Td = {result.design_strength_kn:.2f} kN** (governed by {result.governing_check})")
                st.metric("Utilization Tu / Td", f"{result.utilization:.3f}")
                if result.passes:
                    st.success("PASS — the selected angle satisfies yielding, rupture, and block shear for the inputs shown.")
                else:
                    st.error("FAIL — one or more of the three checks is Not Satisfy.")

                with st.expander("Step-by-step calculations and formulas", expanded=True):
                    for check in result.checks:
                        st.markdown(f"**{check.name}**")
                        st.latex(check.formula)
                        st.write(check.calculation)
                    st.write(f"Calculated β = {result.beta:.3f}; it is limited to the code bounds used in the angle rupture expression.")
                st.subheader("Educational explanation")
                st.info(explain_angle_result(result, data.applied_load_kn))
                st.caption("For a double angle, the model assumes a symmetric pair with one angle on each side of the gusset and equal force sharing. This prototype does not check bolt strength, bearing, tear-out, gusset plate, eccentricity, fatigue, serviceability, load combinations, or other member/connection requirements. The area catalogue comes from the supplied historical steel book; verify current section availability and dimensions.")

if st.session_state.step > 0 and st.button("Previous step"):
    st.session_state.step -= 1
    st.rerun()
