import streamlit as st
import pandas as pd
import urllib.parse
from datetime import datetime, timedelta
from auth import check_login

# =========================================================
# LOGIN
# =========================================================
check_login()

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

    for col in [
        "common_post_impressions",
        "common_post_reach",
        "common_likes_count",
        "common_comments_count",
        "common_shares_count",
        "profile_post_saved_total",
        "common_interactions_count",
        "account_impression",
        "account_interaction",
        "account_reach",
        "page_views",
        "new_followers"
    ]:
        if col in df.columns:

            df[col] = (
                df[col]
                .astype(str)
                .str.replace(",", "", regex=False)
                .str.extract(r"(-?\d+)", expand=False)
            )

            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            )

except Exception as e:
    st.error(f"Gagal load spreadsheet: {e}")
    st.stop()

# =========================================================
# FILTER 8 MINGGU TERAKHIR
# =========================================================
today = datetime.today()
eight_weeks_ago = today - timedelta(weeks=8)

df["Week_dt"] = pd.to_datetime(df["Week_code"], dayfirst=True, errors="coerce")
df = df[df["Week_dt"] >= eight_weeks_ago]
df["Periode"] = df["Date_Week"]

# =========================================================
# BUILD KPI TABLE PER PLATFORM
# =========================================================
def build_kpi_table(df_acc):
    grouped = df_acc.groupby("Date_Week", sort=False).agg(
        Total_Impression  = ("account_impression", "sum"),
        Total_Interaction = ("account_interaction", "sum"),
        Week_dt           = ("Week_dt", "max")
    ).reset_index().fillna(0)

    grouped["ER"] = grouped.apply(
        lambda r: round(r["Total_Interaction"] / r["Total_Impression"] * 100, 2)
        if r["Total_Impression"] > 0 else 0, axis=1
    )
    grouped["Achievement"] = (grouped["ER"] / 9 * 100).round(2)
    grouped = grouped.sort_values("Week_dt", ascending=True)

    grouped = grouped.rename(columns={
        "Date_Week":         "Periode",
        "Total_Impression":  "Total Impression",
        "Total_Interaction": "Total Interaction",
    })

    grouped["ER"]          = grouped["ER"].apply(lambda x: f"{x:.2f}%")
    grouped["Achievement"] = grouped["Achievement"].apply(lambda x: f"{x:.2f}%")
    grouped = grouped.drop(columns=["Week_dt"])
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
    # Filter account level (tanpa image)
    df_acc = df_p[df_p["image"].isna() | (df_p["image"].astype(str).str.strip() == "")]
    st.subheader(label)
    tbl = build_kpi_table(df_acc)
    st.dataframe(tbl, use_container_width=True)