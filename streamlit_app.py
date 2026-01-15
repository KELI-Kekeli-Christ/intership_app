import io
import requests
import time
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import streamlit as st
from datetime import date , timedelta

st.set_page_config(page_title="Internship Finder", layout="wide")
st.title("Internship Finder — Streamlit UI")

api_url = st.text_input("API URL", value="http://127.0.0.1:5000/find-internships")
col1, col2 = st.columns(2)
with col1:
    domain = st.text_input("Domaine", value="Data Science")
with col2:
    after_date = st.date_input("Après le", value=date.today()-timedelta(days=7))
if st.button("Chercher"):
    params = {"domain": domain, "after": after_date.isoformat()}

    def do_request(url, params):
        try:
            r = requests.get(url, params=params, timeout=60)
            r.raise_for_status()
            return (True, r.json())
        except Exception as e:
            return (False, str(e))

    progress_bar = st.progress(0)
    status_text = st.empty()

    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(do_request, api_url, params)

    pct = 0
    status_text.info("Lancement de la recherche...")
    while not future.done():
        time.sleep(0.2)
        pct = min(95, pct + 5)
        progress_bar.progress(pct)

    success, payload = future.result()
    progress_bar.progress(100)

    if not success:
        status_text.error(f"Erreur lors de l'appel API: {payload}")
    else:
        data = payload
        summary = data.get("search_summary", "")
        raw_links = data.get("raw_links", [])

        status_text.success("Résultats reçus")
        st.subheader("Résumé")
        st.write(summary)

        if raw_links:
            df = pd.DataFrame(raw_links)
            st.subheader("Offres trouvées")
            st.dataframe(df)

            # Préparer le fichier Excel
            towrite = io.BytesIO()
            with pd.ExcelWriter(towrite, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name="raw_links", index=False)
                # summary sheet
                pd.DataFrame({"summary": [summary]}).to_excel(writer, sheet_name="summary", index=False)
            towrite.seek(0)

            st.download_button(
                label="Télécharger les résultats en Excel",
                data=towrite.read(),
                file_name="internships.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("Aucune offre trouvée pour ces paramètres.")
