import streamlit as st
import pandas as pd
import urllib.parse
from openai import OpenAI
from datetime import datetime, timedelta
# =========================================================
# LOGIN
# =========================================================
def check_login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.title("🔐 Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            if (username == st.secrets["credentials"]["username"] and
                password == st.secrets["credentials"]["password"]):
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Username atau password salah.")
        st.stop()

check_login()

# =========================================================
# LOAD GOOGLE SHEET
# =========================================================
# ... sisa kode kamu di sini
# =========================================================
# LOAD GOOGLE SHEET
# =========================================================
SPREADSHEET_ID = "1TCjREKxsvnsGTpKpJ_hERzatSYZ5qM3ZN8CDIw2Yqjk"
SHEET_NAME = "All Content"

encoded_sheet = urllib.parse.quote(SHEET_NAME)
url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet={encoded_sheet}"

try:
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()

    for col in ["common_post_impressions", "common_post_reach", "common_likes_count", "common_comments_count", "common_shares_count", "profile_post_saved_total","common_interactions_count"]:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(",", "")
                .str.extract(r"(-?\d+)", expand=False) 
            )
            df[col] = pd.to_numeric(df[col], errors="coerce")

except Exception as e:
    st.error(f"Gagal load spreadsheet: {e}")
    st.stop()

# 4 MINGGU TERAKHIR
today = datetime.today()
eight_weeks_ago = today - timedelta(weeks=8)

df["Week_dt"] = pd.to_datetime(df["Week_code"], dayfirst=True, errors="coerce")
df = df[df["Week_dt"] >= eight_weeks_ago]
   

df["Periode"] = df["Date_Week"]
# =========================================================
# BUILD KPI TABLE PER PLATFORM
# =========================================================
def build_kpi_table(df_platform):
    grouped = df_platform.groupby("Date_Week", sort=False).agg(
        Total_Impression  = ("Impression", "sum"),
        Total_Interaction = ("Engagement", "sum"),
    ).reset_index().fillna(0) 

    grouped["ER"]          = (grouped["Total_Interaction"] / grouped["Total_Impression"] * 100).round(2).fillna(0)
    grouped["Achievement"] = (grouped["ER"] / 9 * 100).round(2).fillna(0)

    grouped = grouped.rename(columns={
        "Date_Week":         "Periode",
        "Total_Impression":  "Total Impression",
        "Total_Interaction": "Total Interaction",
    })

    grouped["ER"]          = grouped["ER"].apply(lambda x: f"{x:.2f}%")
    grouped["Achievement"] = grouped["Achievement"].apply(lambda x: f"{x:.2f}%")

    return grouped.set_index("Periode")
# =========================================================
# FILTER PER PLATFORM & DISPLAY
# =========================================================
platforms = {
    "📸 Instagram": "instagram",
    "👥 Facebook":  "facebook",
    "🎵 TikTok":    "tiktok",
    "▶️ YouTube":   "youtube",
}

for label, platform_name in platforms.items():
    df_p = df[df["Platform"].str.strip().str.lower() == platform_name]
    if df_p.empty:
        continue
    st.subheader(label)
    tbl = build_kpi_table(df_p)
    st.dataframe(tbl, use_container_width=True)