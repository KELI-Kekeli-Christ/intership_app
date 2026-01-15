import io
import requests
import time
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import streamlit as st
from datetime import date, timedelta

st.set_page_config(page_title="Internship Finder", layout="wide")
st.title("Internship Finder")

# --- Barre latérale ou Haut de page pour la config ---
api_url = st.text_input("API URL", value="http://127.0.0.1:5000/find-internships")

st.markdown("### Critères de recherche")

# Utilisation de 5 colonnes pour inclure les nouveaux filtres
col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    domain = st.text_input("Domaine / Poste", value="Data Science")
with col2:
    # NOUVEAU CHAMP
    keywords = st.text_input("Mots-clés (ex: Python, Finance)", value="")
with col3:
    after_date = st.date_input("Après le", value=date.today()-timedelta(days=7))

col4, col5 = st.columns(2)
with col4:
    city = st.text_input("Ville (Optionnel)", value="")
with col5:
    company = st.text_input("Entreprise (Optionnel)", value="")

if st.button("Chercher"):
    params = {
        "domain": domain,
        "keywords": keywords,  # <--- Ajout ici
        "after": after_date.isoformat(),
        "city": city,
        "company": company
    }


    def do_request(url, params):
        try:
            r = requests.get(url, params=params, timeout=90)  # Timeout augmenté car IA travaille
            r.raise_for_status()
            return (True, r.json())
        except Exception as e:
            return (False, str(e))


    progress_bar = st.progress(0)
    status_text = st.empty()

    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(do_request, api_url, params)

    pct = 0
    status_text.info("Recherche et analyse IA en cours (cela peut prendre quelques secondes)...")

    # Animation de la barre de progression
    while not future.done():
        time.sleep(0.5)
        if pct < 90:
            pct += 5
        progress_bar.progress(pct)

    success, payload = future.result()
    progress_bar.progress(100)

    if not success:
        status_text.error(f"Erreur lors de l'appel API: {payload}")
    else:
        data = payload
        summary = data.get("search_summary", "")
        # Note: L'API renvoie maintenant des objets structurés dans raw_links
        raw_links = data.get("raw_links", [])

        status_text.success("Résultats reçus et structurés")

        st.subheader("Résumé de l'IA")
        st.info(summary)

        if raw_links:
            # Création du DataFrame
            df = pd.DataFrame(raw_links)

            # --- 1. Renommage et sélection des colonnes ---
            # L'API tente de renvoyer les clés exactes, mais on sécurise avec .get ou reindex
            wanted_cols = ['Title', 'Durée', 'Entreprise', 'Ville', 'Snippet', 'Link']

            # On s'assure que toutes les colonnes existent (si l'API a raté un champ)
            for col in wanted_cols:
                if col not in df.columns:
                    df[col] = "N/A"

            # --- 2. Ordonnancement strict ---
            df = df[wanted_cols]

            st.subheader("Offres trouvées")

            # Configuration de l'affichage interactif (Liens cliquables)
            st.data_editor(
                df,
                column_config={
                    "Link": st.column_config.LinkColumn("Lien de l'offre"),
                },
                hide_index=True,
                use_container_width=True
            )

            # Préparer le fichier Excel
            towrite = io.BytesIO()
            with pd.ExcelWriter(towrite, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name="Offres", index=False)
                pd.DataFrame({"summary": [summary]}).to_excel(writer, sheet_name="Résumé", index=False)
            towrite.seek(0)

            st.download_button(
                label="Télécharger les résultats en Excel",
                data=towrite.read(),
                file_name=f"stages_{domain}_{date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("Aucune offre trouvée pour ces paramètres.")