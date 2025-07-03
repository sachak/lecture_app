# app.py
# =============================================================
# Ã‰valuation Lecture / Ã‰criture â€“ Module 1
# Infos gÃ©nÃ©rales + premier test vocabulaire + export CSV
# =============================================================

import streamlit as st
import pandas as pd
import uuid        # pour gÃ©nÃ©rer un identifiant unique si lâ€™utilisateur nâ€™en saisit pas

# -------------------------------------------------------------
#  FONCTION PRINCIPALE
# -------------------------------------------------------------
def main():
    st.set_page_config(
        page_title="Ã‰valuation Lecture/Ã‰criture â€“ Module 1",
        page_icon="ðŸ“",
        layout="centered"
    )

    st.title("ðŸ“ Ã‰valuation Lecture / Ã‰criture â€“ Module 1")
    st.write(
        "Bienvenue ! Remplissez dâ€™abord vos **informations gÃ©nÃ©rales**, "
        "puis rÃ©pondez au **Test 1**. "
        "Vous pourrez ensuite tÃ©lÃ©charger un **fichier CSV** contenant vos rÃ©ponses."
    )

    # ---------- 1. Informations gÃ©nÃ©rales ----------
    st.header("Informations gÃ©nÃ©rales")

    col1, col2 = st.columns([3, 1])
    with col1:
        participant_id = st.text_input(
            "Identifiant participant (facultatif : laissez vide pour quâ€™il soit gÃ©nÃ©rÃ©)"
        )

    # GÃ©nÃ©ration dâ€™un identifiant alÃ©atoire si champ vide
    if participant_id.strip() == "":
        participant_id = str(uuid.uuid4())

    with col2:
        st.markdown("Identifiant utilisÃ© :")
        st.code(participant_id, language="")

    age = st.number_input("Ã‚ge (en annÃ©es)", min_value=16, max_value=99, value=25, step=1)
    sexe = st.radio("Sexe", ["Femme", "Homme", "Autre"], horizontal=True)
    etude = st.selectbox(
        "Niveau dâ€™Ã©tude",
        [
            "CollÃ¨ge",
            "LycÃ©e",
            "BaccalaurÃ©at",
            "Bac +2",
            "Licence / Master",
            "Doctorat",
            "Autre",
        ],
    )

    st.markdown("---")

    # ---------- 2. Test 1 : Vocabulaire ----------
    st.header("Test 1 â€“ Vocabulaire (synonyme)")
    st.write("Choisissez le mot **le plus proche** du sens de : **impÃ©tueux**")

    options = ["Calme", "Fougueux", "Timide", "Lent"]
    reponse_vocab = st.radio("Votre rÃ©ponse :", options, index=None)

    st.markdown("---")

    # ---------- 3. Construction du CSV ----------
    data = {
        "participant_id": [participant_id],
        "age": [age],
        "sexe": [sexe],
        "etude": [etude],
        "test1_item": ["impÃ©tueux"],
        "test1_reponse": [reponse_vocab],
    }
    df = pd.DataFrame(data)
    csv_bytes = df.to_csv(index=False).encode("utf-8")

    # ---------- 4. TÃ©lÃ©chargement ----------
    st.header("TÃ©lÃ©chargement")

    st.download_button(
        label="ðŸ“¥ TÃ©lÃ©charger mes rÃ©ponses (CSV)",
        data=csv_bytes,
        file_name=f"{participant_id}_module1.csv",
        mime="text/csv",
        disabled=reponse_vocab is None,  # activation seulement aprÃ¨s rÃ©ponse
    )

    st.info(
        "AprÃ¨s tÃ©lÃ©chargement, vous pourrez fermer la page ou passer au module suivant."
    )


# -------------------------------------------------------------
#  POINT Dâ€™ENTRÃ‰E
# -------------------------------------------------------------
if __name__ == "__main__":
    main()
