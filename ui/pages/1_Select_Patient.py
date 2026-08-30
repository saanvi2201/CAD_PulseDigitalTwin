import streamlit as st
import pandas as pd

from ui_helpers import (
    setup_page,
    RAW_LIFESTYLE_CSV,
    RAW_CLINICAL_CSV,
    MANUAL_PATIENTS_CSV,
    set_selected_patient,
    COHORT_EXPLAINER,
)


# =============================================================================
# PAGE SETUP
# =============================================================================

setup_page("Select Patient", "🔎")

st.title("🔎 Select Patient")


tab_predefined, tab_manual = st.tabs(
    [
        "📊  Predefined Dataset Patient",
        "✍️  Manually Entered Patient",
    ]
)


# =============================================================================
# TAB 1 — PREDEFINED DATASET
# =============================================================================

with tab_predefined:

    st.markdown(
        "<div class='cad-card'>"
        "Patients are read directly from your raw dataset files. "
        "Selecting one here never modifies or copies it into the "
        "manual-patient store."
        "</div>",
        unsafe_allow_html=True,
    )

    # -------------------------------------------------------------------------
    # Choose dataset
    # -------------------------------------------------------------------------

    cohort_choice = st.radio(
        "Which dataset?",
        ["lifestyle", "clinical"],
        horizontal=True,
        key="predefined_cohort_choice",
        format_func=lambda c:
            "🏃 Lifestyle cohort"
            if c == "lifestyle"
            else "🏥 Clinical cohort",
    )

    st.markdown(
        f"<div class='cad-card' style='background:#141726'>"
        f"{COHORT_EXPLAINER[cohort_choice]}"
        f"</div>",
        unsafe_allow_html=True,
    )

    # -------------------------------------------------------------------------
    # Select correct raw dataset
    # -------------------------------------------------------------------------

    csv_path = (
        RAW_LIFESTYLE_CSV
        if cohort_choice == "lifestyle"
        else RAW_CLINICAL_CSV
    )

    try:

        df = pd.read_csv(csv_path)

    except FileNotFoundError:

        st.error(
            f"Could not find {csv_path}. "
            "Check the path in `ui_helpers.py`."
        )

        df = None


    # -------------------------------------------------------------------------
    # Display predefined patients
    # -------------------------------------------------------------------------

    if df is not None:

        st.write(
            f"**{len(df):,} patients available.**"
        )

        # =====================================================================
        # LIFESTYLE DATASET FILTERS
        # =====================================================================

        if cohort_choice == "lifestyle":

            c1, c2, c3 = st.columns(3)

            with c1:

                age_range = st.slider(
                    "Age filter",
                    int(df.age.min()),
                    int(df.age.max()),
                    (
                        int(df.age.min()),
                        int(df.age.max()),
                    ),
                )

            with c2:

                gender_filter = st.multiselect(
                    "Gender",
                    sorted(
                        df.gender.unique().tolist()
                    ),
                    default=sorted(
                        df.gender.unique().tolist()
                    ),
                )

            with c3:

                max_rows = st.number_input(
                    "Patients to browse",
                    10,
                    500,
                    50,
                    step=10,
                )

            filtered = df[
                (df.age.between(*age_range))
                & (df.gender.isin(gender_filter))
            ].head(max_rows)

        # =====================================================================
        # CLINICAL DATASET
        # =====================================================================

        else:

            max_rows = st.number_input(
                "Patients to browse",
                10,
                500,
                50,
                step=10,
                key="clin_rows",
            )

            filtered = df.head(max_rows)


        # =====================================================================
        # PREPARE TABLE FOR DISPLAY
        # =====================================================================

        # IMPORTANT:
        # The actual dataset row number is still preserved internally.
        # We simply call it "Patient ID" in the UI so the interface is
        # easier to understand.
        filtered_display = (
            filtered
            .reset_index()
            .rename(
                columns={
                    "index": "patient_id"
                }
            )
        )


        # ---------------------------------------------------------------------
        # Display age as whole years
        # ---------------------------------------------------------------------
        #
        # The underlying dataset still contains decimal age values such as:
        # 50.39178082
        #
        # We ONLY round the value shown in the UI.
        # The original value remains untouched in `df`.
        #

        if "age" in filtered_display.columns:

            filtered_display["age"] = (
                filtered_display["age"]
                .round()
                .astype(int)
            )


        st.dataframe(
            filtered_display,
            use_container_width=True,
            height=280,
        )


        # =====================================================================
        # SELECT PATIENT
        # =====================================================================

        c1, c2 = st.columns([2, 1])

        with c1:

            # Keep the backend variable as `row_index`.
            # nb10b_patient_loader.py expects the actual dataset row number.

            default_patient_id = (
                int(
                    filtered_display.iloc[0]["patient_id"]
                )
                if len(filtered_display)
                else 0
            )

            row_index = st.number_input(
                "Patient ID to load "
                "(pick from the table above)",
                min_value=0,
                max_value=len(df) - 1,
                value=default_patient_id,
            )

        with c2:

            st.write("")
            st.write("")

            load_clicked = st.button(
                "✅ Load this patient",
                type="primary",
                use_container_width=True,
            )


        # =====================================================================
        # LOAD SELECTED PATIENT
        # =====================================================================

        if load_clicked:

            try:

                if cohort_choice == "lifestyle":

                    from nb10b_patient_loader import (
                        load_real_lifestyle_patient
                    )

                    patient = load_real_lifestyle_patient(
                        csv_path,
                        int(row_index),
                    )

                else:

                    from nb10b_patient_loader import (
                        load_real_clinical_patient
                    )

                    patient = load_real_clinical_patient(
                        csv_path,
                        int(row_index),
                    )


                # -----------------------------------------------------------------
                # Store selected patient in Streamlit session state
                # -----------------------------------------------------------------

                set_selected_patient(
                    patient,
                    cohort=cohort_choice,
                    source="predefined",
                    label=(
                        f"{cohort_choice.capitalize()} dataset, "
                        f"Patient ID {row_index}"
                    ),
                )


                st.success(
                    f"Loaded Patient ID {row_index}."
                )


                if st.button(
                    "🗂️ Go to Patient Dashboard →",
                    type="primary",
                ):

                    st.switch_page(
                        "pages/2_Patient_Dashboard.py"
                    )


            except ValueError as e:

                st.error(str(e))

            except Exception as e:

                st.error(
                    f"Could not load this patient: {e}"
                )


# =============================================================================
# TAB 2 — MANUAL ENTRY
# =============================================================================

with tab_manual:

    st.markdown(
        f"<div class='cad-card'>"
        f"Manually entered patients are saved to their own file "
        f"(<code>{MANUAL_PATIENTS_CSV}</code>) — completely separate "
        f"from the predefined dataset. They're never merged."
        f"</div>",
        unsafe_allow_html=True,
    )


    sub_new, sub_saved = st.tabs(
        [
            "➕  Enter new patient",
            "📁  Load a previously saved patient",
        ]
    )


    # =========================================================================
    # NEW MANUAL PATIENT
    # =========================================================================

    with sub_new:

        manual_cohort = st.radio(
            "Cohort",
            ["lifestyle", "clinical"],
            horizontal=True,
            key="manual_cohort",
            format_func=lambda c:
                "🏃 Lifestyle"
                if c == "lifestyle"
                else "🏥 Clinical",
        )


        st.markdown(
            f"<div class='cad-card' style='background:#141726'>"
            f"{COHORT_EXPLAINER[manual_cohort]}"
            f"</div>",
            unsafe_allow_html=True,
        )


        # ---------------------------------------------------------------------
        # Manual patient form
        # ---------------------------------------------------------------------

        with st.form("manual_patient_form"):

            age = st.number_input(
                "Age",
                1.0,
                120.0,
                50.0,
            )


            # =================================================================
            # LIFESTYLE MANUAL PATIENT
            # =================================================================

            if manual_cohort == "lifestyle":

                col1, col2 = st.columns(2)

                with col1:

                    gender_or_sex = st.selectbox(
                        "Gender",
                        ["m", "f"],
                    )

                    systolic_bp = st.number_input(
                        "Systolic BP",
                        70.0,
                        250.0,
                        120.0,
                    )

                    diastolic_bp = st.number_input(
                        "Diastolic BP",
                        40.0,
                        150.0,
                        80.0,
                    )

                    height_cm = st.number_input(
                        "Height (cm)",
                        100.0,
                        220.0,
                        170.0,
                    )

                    weight_kg = st.number_input(
                        "Weight (kg)",
                        30.0,
                        200.0,
                        70.0,
                    )


                with col2:

                    cholesterol_level = st.selectbox(
                        "Cholesterol level",
                        [1, 2, 3],
                    )

                    glucose_level = st.selectbox(
                        "Glucose level",
                        [1, 2, 3],
                    )

                    smoking = st.selectbox(
                        "Smoking",
                        [0, 1],
                        format_func=lambda x:
                            "Yes" if x else "No",
                    )

                    alcohol = st.selectbox(
                        "Alcohol",
                        [0, 1],
                        format_func=lambda x:
                            "Yes" if x else "No",
                    )

                    physical_activity = st.selectbox(
                        "Physically active",
                        [0, 1],
                        format_func=lambda x:
                            "Yes" if x else "No",
                    )


                extra = dict(
                    diastolic_bp=diastolic_bp,
                    height_cm=height_cm,
                    weight_kg=weight_kg,
                    cholesterol_level=cholesterol_level,
                    glucose_level=glucose_level,
                    smoking=smoking,
                    alcohol=alcohol,
                    physical_activity=physical_activity,
                )


            # =================================================================
            # CLINICAL MANUAL PATIENT
            # =================================================================

            else:

                col1, col2 = st.columns(2)

                with col1:

                    gender_or_sex = st.selectbox(
                        "Sex",
                        [1, 0],
                        format_func=lambda x:
                            "Male" if x == 1 else "Female",
                    )

                    systolic_bp = st.number_input(
                        "Resting BP",
                        70.0,
                        250.0,
                        130.0,
                    )

                    cholesterol_mgdl = st.number_input(
                        "Cholesterol (mg/dl)",
                        0.0,
                        700.0,
                        200.0,
                    )

                    chest_pain_type = st.selectbox(
                        "Chest pain type",
                        [0, 1, 2, 3],
                    )

                    fasting_blood_sugar = st.selectbox(
                        "Fasting blood sugar > 120",
                        [0, 1],
                        format_func=lambda x:
                            "Yes" if x else "No",
                    )


                with col2:

                    resting_ecg = st.selectbox(
                        "Resting ECG",
                        [0, 1, 2],
                    )

                    max_heart_rate = st.number_input(
                        "Max heart rate",
                        60.0,
                        220.0,
                        150.0,
                    )

                    exercise_angina = st.selectbox(
                        "Exercise angina",
                        [0, 1],
                        format_func=lambda x:
                            "Yes" if x else "No",
                    )

                    oldpeak = st.number_input(
                        "Oldpeak",
                        -3.0,
                        7.0,
                        1.0,
                        step=0.1,
                    )

                    st_slope = st.selectbox(
                        "ST slope",
                        [0, 1, 2],
                    )


                extra = dict(
                    cholesterol_mgdl=cholesterol_mgdl,
                    chest_pain_type=chest_pain_type,
                    fasting_blood_sugar=fasting_blood_sugar,
                    resting_ecg=resting_ecg,
                    max_heart_rate=max_heart_rate,
                    exercise_angina=exercise_angina,
                    oldpeak=oldpeak,
                    st_slope=st_slope,
                )


            submitted = st.form_submit_button(
                "💾 Build & save this patient",
                type="primary",
            )


        # =====================================================================
        # SAVE MANUAL PATIENT
        # =====================================================================

        if submitted:

            from nb10b_patient_loader import (
                build_manual_patient,
                save_manual_patient,
            )

            try:

                patient = build_manual_patient(
                    cohort=manual_cohort,
                    age=age,
                    gender_or_sex=gender_or_sex,
                    systolic_bp=systolic_bp,
                    **extra,
                )


                patient_id = save_manual_patient(
                    patient,
                    csv_path=MANUAL_PATIENTS_CSV,
                )


                set_selected_patient(
                    patient,
                    cohort=manual_cohort,
                    source="manual",
                    label=f"Manual patient {patient_id}",
                )


                st.success(
                    f"Saved as `{patient_id}` and selected."
                )


                if st.button(
                    "🗂️ Go to Patient Dashboard →",
                    type="primary",
                    key="go_dash_manual",
                ):

                    st.switch_page(
                        "pages/2_Patient_Dashboard.py"
                    )


            except ValueError as e:

                st.error(
                    f"Validation failed: {e}"
                )

            except Exception as e:

                st.error(
                    f"Could not build this patient: {e}"
                )


    # =========================================================================
    # PREVIOUSLY SAVED MANUAL PATIENTS
    # =========================================================================

    with sub_saved:

        from nb10b_patient_loader import (
            list_manual_patients,
            load_manual_patient,
        )


        listing = list_manual_patients(
            csv_path=MANUAL_PATIENTS_CSV
        )


        if listing.empty:

            st.info(
                "No manually entered patients saved yet."
            )

        else:

            st.dataframe(
                listing,
                use_container_width=True,
            )


            pid = st.selectbox(
                "Select a saved patient ID",
                listing["patient_id"].tolist(),
            )


            if st.button(
                "✅ Load selected saved patient",
                type="primary",
            ):

                try:

                    patient = load_manual_patient(
                        pid,
                        csv_path=MANUAL_PATIENTS_CSV,
                    )


                    cohort = (
                        "lifestyle"
                        if "height_cm" in patient
                        else "clinical"
                    )


                    set_selected_patient(
                        patient,
                        cohort=cohort,
                        source="manual",
                        label=f"Manual patient {pid}",
                    )


                    st.success(
                        f"Loaded {pid}."
                    )


                    if st.button(
                        "🗂️ Go to Patient Dashboard →",
                        type="primary",
                        key="go_dash_saved",
                    ):

                        st.switch_page(
                            "pages/2_Patient_Dashboard.py"
                        )


                except Exception as e:

                    st.error(
                        f"Could not load this patient: {e}"
                    )