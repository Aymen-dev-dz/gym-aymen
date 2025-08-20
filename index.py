# gym_manager_pro.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import plotly.express as px
import uuid, os

# ================= CONFIG =================
st.set_page_config(page_title="🏋️ Gym Manager Pro", page_icon="💪", layout="wide")
st.title("🏋️ Gestion des Abonnements — Salle de Sport")

DATA_PATH = "abonnements.csv"
DEFAULT_SUBS = {
    "Mensuel (30j)": 30,
    "Trimestriel (90j)": 90,
    "Semestriel (180j)": 180,
    "Annuel (365j)": 365,
    "Personnalisé…": None,
}

# ================= UTILS =================
def gen_id(): return str(uuid.uuid4())

@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    if os.path.exists(path):
        df = pd.read_csv(path, parse_dates=["Debut", "Expiration"])
    else:
        df = pd.DataFrame(columns=[
            "ID","Nom","Telephone","Abonnement","DureeJours","Montant","Debut","Expiration","Remarques"
        ])
    return df

def save_data(df: pd.DataFrame, path: str):
    df.to_csv(path, index=False)
    st.cache_data.clear()

def status_for(exp_date: date, warn_days: int = 7):
    today = date.today()
    if exp_date < today:
        return "❌ Expiré"
    elif exp_date <= today + timedelta(days=warn_days):
        return "⏳ Bientôt"
    return "✅ Actif"

def df_with_status(df, warn_days: int):
    df2 = df.copy()
    if df2.empty: return df2
    today = date.today()
    df2["Statut"] = df2["Expiration"].dt.date.apply(lambda d: status_for(d, warn_days))
    df2["JoursRestants"] = (df2["Expiration"].dt.date - today).apply(lambda x: x.days)
    return df2

# ================= LOAD =================
df = load_data(DATA_PATH)

# ================= SIDEBAR =================
st.sidebar.header("➕ Ajouter un abonnement")
abo_choice = st.sidebar.selectbox("Type d'abonnement", list(DEFAULT_SUBS.keys()))
duree = DEFAULT_SUBS[abo_choice] if DEFAULT_SUBS[abo_choice] else st.sidebar.number_input("Durée personnalisée (jours)", min_value=1, value=30)

nom = st.sidebar.text_input("Nom complet")
tel = st.sidebar.text_input("Téléphone", "")
montant = st.sidebar.number_input("Montant payé (DA)", min_value=0.0, step=500.0)
debut = st.sidebar.date_input("Date de début", date.today())
rem = st.sidebar.text_area("Remarques", "")

if st.sidebar.button("✅ Enregistrer"):
    if not nom.strip():
        st.sidebar.error("⚠️ Le nom est obligatoire")
    else:
        new_row = pd.DataFrame([{
            "ID": gen_id(),
            "Nom": nom.strip(),
            "Telephone": tel.strip(),
            "Abonnement": abo_choice,
            "DureeJours": int(duree),
            "Montant": float(montant),
            "Debut": pd.to_datetime(debut),
            "Expiration": pd.to_datetime(debut) + timedelta(days=int(duree)),
            "Remarques": rem.strip()
        }])
        df = pd.concat([df, new_row], ignore_index=True)
        save_data(df, DATA_PATH)
        st.sidebar.success("🎉 Abonnement ajouté avec succès")

warn_days = st.sidebar.slider("⚠️ Alerte avant expiration (jours)", 1, 30, 7)
st.sidebar.download_button("⬇️ Export CSV", df.to_csv(index=False).encode(), "abonnements.csv", "text/csv")

# ================= NOTIFS =================
st.subheader("🔔 Notifications")
alerts = []
df_status = df_with_status(df, warn_days)
for _, r in df_status.iterrows():
    if "Expiré" in r["Statut"]:
        alerts.append((r["Nom"], f"Expiré le {r['Expiration'].date()}", "❌"))
    elif "Bientôt" in r["Statut"]:
        alerts.append((r["Nom"], f"Expire dans {r['JoursRestants']} jours ({r['Expiration'].date()})", "⏳"))

if alerts:
    for nom, msg, icon in alerts:
        st.error(f"{icon} **{nom}** — {msg}")
else:
    st.success("✅ Aucun abonnement expiré ou proche d’expiration.")

# ================= TABLEAU =================
st.subheader("📋 Liste des abonnements")
if df_status.empty:
    st.info("Aucun enregistrement pour le moment.")
else:
    st.dataframe(df_status.sort_values("Expiration"), use_container_width=True)

# ================= STATS =================
st.markdown("---")
st.subheader("📊 Statistiques")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total abonnements", len(df_status))
col2.metric("Actifs", (df_status["Statut"]=="✅ Actif").sum())
col3.metric("Bientôt expirés", (df_status["Statut"]=="⏳ Bientôt").sum())
col4.metric("Expirés", (df_status["Statut"]=="❌ Expiré").sum())

if not df_status.empty:
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(px.pie(df_status, names="Statut", title="Répartition par statut"), use_container_width=True)
    with c2:
        df_status["Mois"] = df_status["Debut"].dt.to_period("M").dt.to_timestamp()
        st.plotly_chart(px.bar(df_status.groupby("Mois")["Montant"].sum().reset_index(), x="Mois", y="Montant", title="Revenus par mois"), use_container_width=True)
