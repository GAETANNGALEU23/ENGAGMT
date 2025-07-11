import streamlit as st
import streamlit.components.v1 as components
import json
import os
import pandas as pd
import io
import sys
import uuid
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
import shutil
import time

# Importer le pipeline
pipeline_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "PIPELINE_COMPLET"))
sys.path.append(pipeline_path)
from Pipeline import execute_pipeline

# Configuration page Streamlit
st.set_page_config(page_title="Afriland First Bank - Reporting", page_icon="🏦", layout="wide")

# Nettoyage des anciennes sessions
def clean_old_sessions(base_dir="tmp_sessions", max_age_minutes=60):
    now = time.time()
    if not os.path.exists(base_dir):
        return
    for folder in os.listdir(base_dir):
        folder_path = os.path.join(base_dir, folder)
        if os.path.isdir(folder_path):
            age_minutes = (now - os.path.getmtime(folder_path)) / 60
            if age_minutes > max_age_minutes:
                try:
                    shutil.rmtree(folder_path)
                except Exception as e:
                    print(f"Erreur suppression : {e}")

# Initialiser la session Streamlit
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pipeline_executed" not in st.session_state:
    st.session_state.pipeline_executed = False
if "last_output_path" not in st.session_state:
    st.session_state.last_output_path = None
if "summary_html_path" not in st.session_state:
    st.session_state.summary_html_path = None
if "last_user_input" not in st.session_state:
    st.session_state.last_user_input = None
if "query_count" not in st.session_state:
    st.session_state.query_count = 0
if "query_logs" not in st.session_state:
    st.session_state.query_logs = []
if "session_id" not in st.session_state:
    st.session_state.session_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"

# Créer le dossier de session
base_session_dir = "tmp_sessions"
session_dir = os.path.join(base_session_dir, st.session_state.session_id)
os.makedirs(session_dir, exist_ok=True)
clean_old_sessions(base_session_dir, 1440)

# Bandeau
st.markdown('<div style="background-color:#c8102e;padding:15px;border-radius:10px;color:white;text-align:center;"><h2>Afriland First Bank - IA Reporting</h2></div>', unsafe_allow_html=True)

# Affichage des messages
for message in st.session_state.messages:
    role_class = "user-message" if message["role"] == "user" else "bot-message"
    st.markdown(f'<div class="{role_class}">{message["content"]}</div>', unsafe_allow_html=True)

# Entrée utilisateur
user_input = st.text_input("Posez votre question ou décrivez le rapport souhaité :")
if st.button("Envoyer") and user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.query_count += 1
    query_id = f"{st.session_state.query_count:04d}"
    query_dir = os.path.join(session_dir, query_id)
    os.makedirs(query_dir, exist_ok=True)

    input_json_path = os.path.join(query_dir, "input_phrases.json")
    summary_html_path = os.path.join(query_dir, "summary_simple_table.html")
    visualisation_dir = os.path.join(query_dir, "visualisations")
    merged_output_path = os.path.join(query_dir, "merged_output.json")

    st.session_state.summary_html_path = summary_html_path
    st.session_state.visualisation_dir = visualisation_dir

    try:
        with open(input_json_path, "w", encoding="utf-8") as f:
            json.dump({"phrases": [user_input]}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Erreur création input : {e}")
        st.stop()

    with st.spinner("Analyse en cours..."):
        try:
            execute_pipeline(output_directory=query_dir)

            if os.path.exists(merged_output_path):
                with open(merged_output_path, "r", encoding="utf-8") as f:
                    result = json.load(f)
                bot_response = f"Analyse de votre requête : '{user_input}'. Rapport généré avec succès."
                st.session_state.pipeline_executed = True
                st.session_state.last_output_path = merged_output_path
                st.session_state.last_user_input = user_input
                st.session_state.query_logs.append({
                    "id": query_id,
                    "phrase": user_input,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "dir": query_dir
                })

                # ✅ Affichage immédiat du résultat
                st.success(bot_response)

                # 🖼️ Visualisations PNG
                if os.path.exists(visualisation_dir):
                    image_files = [f for f in os.listdir(visualisation_dir) if f.endswith(".png")]
                    for image_file in sorted(image_files):
                        st.image(os.path.join(visualisation_dir, image_file), caption=image_file, use_column_width=True)
                else:
                    st.warning("Aucune visualisation trouvée.")

                # 📊 Tableau HTML
                if os.path.exists(summary_html_path):
                    with open(summary_html_path, "r", encoding="utf-8") as f:
                        html_content = f.read()
                    try:
                        df = pd.read_html(io.StringIO(html_content.replace("'", '"')))[0]
                        st.markdown("### Aperçu du rapport généré :")
                        st.dataframe(df, use_container_width=True)
                    except Exception as e:
                        st.error(f"Erreur affichage tableau : {e}")
                else:
                    st.warning("Le fichier summary_simple_table.html est introuvable.")

            else:
                st.error("Le fichier de sortie n’a pas été généré.")

        except Exception as e:
            st.error(f"Erreur exécution pipeline : {e}")
