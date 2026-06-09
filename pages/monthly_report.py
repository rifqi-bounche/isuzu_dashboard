import streamlit as st
import pandas as pd
import urllib.parse
from datetime import datetime
import requests
import json
import os

from auth import check_login
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

    for col in ["common_post_impressions", "common_post_reach", "common_likes_count",
                "common_comments_count", "common_shares_count", "profile_post_saved_total",
                "common_interactions_count", "Growth", "Impression", "Engagement",
                "account_impression", "account_interaction", "account_reach",
                "new_followers", "page_views", "Avg View Percentage", "Avg View Time"]:
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

# =========================================================
# DATE FILTER
# =========================================================

today= datetime.today()

df["date_valid"] = pd.to_datetime(df["date_valid"], errors="coerce")

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Start Date", value=today.replace(day=1))
with col2:
    end_date = st.date_input("End Date", value=today)

selected_start = pd.to_datetime(start_date)
selected_end = pd.to_datetime(end_date) + pd.Timedelta(days=1)

df_filtered = df[
    (df["date_valid"] >= selected_start) &
    (df["date_valid"] < selected_end)
]

# =========================================================
# SHARED HELPER FUNCTIONS
# =========================================================
def build_monthly_table(df_full, platform_name):
    p    = platform_name.lower()
    df_p = df_full[df_full["Platform"].str.strip().str.lower() == p]

    df_posts     = df_p[df_p["id"].notna() & (df_p["id"].astype(str).str.strip() != "")]
    df_followers = df_p[df_p["id"].isna()  | (df_p["id"].astype(str).str.strip() == "")]

    # =====================================================
    # POSTS GROUPED
    # =====================================================
    if p == "instagram":
        posts_grouped = df_posts.groupby("Month", sort=False).agg(
            Post_Amount = ("id", "count"),
        ).reset_index()

    elif p == "facebook":
        posts_grouped = df_posts.groupby("Month", sort=False).agg(
            Post_Amount = ("id", "count"),
        ).reset_index()

    elif p == "tiktok":
        posts_grouped = df_posts.groupby("Month", sort=False).agg(
            Post_Amount = ("id", "count"),
        ).reset_index()

    elif p == "youtube":
        posts_grouped = df_posts.groupby("Month", sort=False).agg(
            Post_Amount  = ("id", "count"),
            Avg_View_Pct = ("Avg View Percentage", "mean"),
            Avg_View_Dur = ("Avg View Time", "mean"),
        ).reset_index()

    else:
        posts_grouped = df_posts.groupby("Month", sort=False).agg(
            Post_Amount = ("id", "count"),
            Reach       = ("Reach", "sum"),
            Impression  = ("Impression", "sum"),
            Engagement  = ("Engagement", "sum"),
        ).reset_index()

    # =====================================================
    # FOLLOWERS GROUPED
    # =====================================================
    if p == "instagram":
        followers_grouped = df_followers.groupby("Month", sort=False).agg(
            Followers     = ("Last Followers", "last"),
            Growth        = ("Growth", "sum"),
            New_Followers = ("new_followers", "sum"),
            Reach         = ("account_reach", "sum"),
            Impression    = ("account_impression", "sum"),
            Engagement    = ("account_interaction", "sum"),
        ).reset_index()

    elif p == "facebook":
        followers_grouped = df_followers.groupby("Month", sort=False).agg(
            Followers     = ("Last Followers", "last"),
            Growth        = ("Growth", "sum"),
            New_Followers = ("new_followers", "sum"),
            Impression    = ("account_impression", "sum"),
            Engagement    = ("account_interaction", "sum"),
        ).reset_index()

    elif p == "tiktok":
        followers_grouped = df_followers.groupby("Month", sort=False).agg(
            Followers     = ("Last Followers", "last"),
            Growth        = ("Growth", "sum"),
            New_Followers = ("new_followers", "sum"),
            Profile_Views = ("page_views", "sum"),
            Impression    = ("account_impression", "sum"),
            Engagement    = ("account_interaction", "sum"),
        ).reset_index()

    elif p == "youtube":
        followers_grouped = df_followers.groupby("Month", sort=False).agg(
            Followers     = ("Last Followers", "last"),
            Growth        = ("Growth", "sum"),
            New_Followers = ("new_followers", "sum"),
            Impression    = ("account_impression", "sum"),
            Engagement    = ("account_interaction", "sum"),
            Interaction   = ("account_interaction", "sum"),
        ).reset_index()

    else:
        followers_grouped = df_followers.groupby("Month", sort=False).agg(
            Followers = ("Last Followers", "last"),
            Growth    = ("Growth", "sum"),
        ).reset_index()

    merged = pd.merge(posts_grouped, followers_grouped, on="Month", how="outer")
    merged["Month_dt"] = pd.to_datetime(merged["Month"], format="%b-%Y", errors="coerce")
    merged = merged.sort_values("Month_dt").drop(columns=["Month_dt"])

    for col in ["Post_Amount", "Reach", "Impression", "Engagement", "Interaction"]:
        if col in merged.columns:
            merged[col] = merged[col].fillna(0)

    merged["ER"] = (merged["Engagement"] / merged["Impression"] * 100).round(2)
    merged["ER"] = merged["ER"].fillna(0).apply(lambda x: f"{x:.2f}%")

    fmt_cols = ["Post_Amount", "Followers", "Growth", "Impression", "Engagement"]

    if p == "instagram":
        fmt_cols += ["Reach", "New_Followers"]

    elif p == "facebook":
        fmt_cols += ["New_Followers"]

    elif p == "tiktok":
        fmt_cols += ["New_Followers", "Profile_Views"]

    elif p == "youtube":
        fmt_cols += ["New_Followers", "Interaction"]

    for col in fmt_cols:
        if col in merged.columns:
            merged[col] = merged[col].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "0")

    if p == "youtube":
        if "Avg_View_Pct" in merged.columns:
            merged["Avg_View_Pct"] = merged["Avg_View_Pct"].fillna(0).round(2).astype(str) + "%"
        if "Avg_View_Dur" in merged.columns:
            merged["Avg_View_Dur"] = merged["Avg_View_Dur"].fillna(0).round(2)

    merged = merged.rename(columns={
        "Post_Amount":   "Post Amount",
        "New_Followers": "New Subs" if p == "youtube" else "New Followers",
        "Interaction":   "Total Interaction",

        "Impression": (
            "Impressions" if p == "instagram"
            else "Views" if p == "facebook"
            else "Post Views" if p == "tiktok"
            else "Total Views" if p == "youtube"
            else "Impression"
        ),

        "Engagement":    "Engagements",
        "Profile_Views": "Profile Views",
        "Avg_View_Pct":  "Avg. Percentage Views",
        "Avg_View_Dur":  "Avg. Views Duration",
        "Followers":     "Subs" if p == "youtube" else "Followers",
        "ER":            "ER%",
    })

    col_order = {
        "instagram": ["Month", "Post Amount", "Followers", "New Followers", "Reach", "Impressions", "Engagements", "ER%"],
        "facebook":  ["Month", "Post Amount", "Followers", "New Followers", "Views", "Engagements", "ER%"],
        "tiktok":    ["Month", "Post Amount", "Followers", "New Followers", "Post Views", "Profile Views", "Engagements", "ER%"],
        "youtube":   ["Month", "Post Amount", "Subs", "New Subs", "Total Views", "Total Interaction", "Avg. Percentage Views", "Avg. Views Duration", "ER%"],
    }

    if p in col_order:
        cols = [c for c in col_order[p] if c in merged.columns]
        return merged[cols].set_index("Month")

    merged = merged.rename(columns={"Post_Amount": "Post Amount"})
    return merged.set_index("Month")

def build_content_breakdown(df_full, platform_name):
    df_p     = df_full[df_full["Platform"].str.strip().str.lower() == platform_name.lower()]
    df_posts = df_p[df_p["id"].notna() & (df_p["id"].astype(str).str.strip() != "")]

    df_posts = df_posts.copy()
    df_posts["ER_raw"] = (df_posts["Engagement"] / df_posts["Impression"] * 100).round(2)
    df_posts["ER"]     = df_posts["ER_raw"].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "0.00%")

    is_instagram = platform_name.lower() == "instagram"
    is_youtube   = platform_name.lower() == "youtube"

    cols = ["Date", "link", "type", "Boosted", "message", "Impression", "Reach",
            "Likes", "Comments", "Share", "Save", "Engagement", "ER", "ER_raw"]
    if not is_instagram:
        cols = [c for c in cols if c != "Save"]
    if is_youtube:
        cols = [c for c in cols if c not in ["Reach", "Share"]]
    cols = [c for c in cols if c in df_posts.columns]

    df_posts = df_posts[cols]
    df_posts = df_posts.sort_values("ER_raw", ascending=False).drop(columns=["ER_raw"])
    df_posts = df_posts.rename(columns={
        "link":       "Link",
        "type":       "Type",
        "message":    "Message",
        "Engagement": "Total Engagement",
    })

    df = df_posts.reset_index(drop=True)

    column_config = {
        "Link":             st.column_config.LinkColumn("Link",            display_text="Link", width="small"),
        "Message":          st.column_config.TextColumn("Message",         width="medium"),
        "Date":             st.column_config.DateColumn("Date",            width="small"),
        "Type":             st.column_config.TextColumn("Type",            width="small"),
        "Boosted":          st.column_config.TextColumn("Boosted",         width="small"),
        "Impression":       st.column_config.NumberColumn("Impression",    width="small", format="%d"),
        "Reach":            st.column_config.NumberColumn("Reach",         width="small", format="%d"),
        "Likes":            st.column_config.NumberColumn("Likes",         width="small", format="%d"),
        "Comments":         st.column_config.NumberColumn("Comments",      width="small", format="%d"),
        "Share":            st.column_config.NumberColumn("Share",         width="small", format="%d"),
        "Total Engagement": st.column_config.NumberColumn("Total Engagement", width="small", format="%d"),
        "ER":               st.column_config.TextColumn("ER",              width="small"),
    }

    if is_instagram:
        column_config["Save"] = st.column_config.NumberColumn("Save", width="small", format="%d")

    st.dataframe(df, use_container_width=True, column_config=column_config, hide_index=True)
def render_post_embed(post_url):
    try:
        shortcode = [x for x in post_url.split("/") if x][-1]
        st.components.v1.html(
            f'<iframe src="https://www.instagram.com/p/{shortcode}/embed/" '
            f'width="100%" height="460" frameborder="0" scrolling="no" style="border:none;"></iframe>',
            height=480, scrolling=False)
    except:
        st.markdown(f'<a href="{post_url}" target="_blank">📸 Lihat Post</a>', unsafe_allow_html=True)


            
def render_post_metrics(post_type, reach, impression, engagement, er):
    st.markdown(f"""
        <div style="background:#f8f9fa;border-radius:8px;padding:10px 12px;font-size:12px;line-height:2;">
        📌 <b>Post Type</b> &nbsp;&nbsp;&nbsp; {post_type}<br>
        👥 <b>Reach</b> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {reach:,}<br>
        👀 <b>Impression</b> &nbsp; {impression:,}<br>
        💬 <b>Engagement</b> &nbsp; {engagement:,}<br>
        ⚡ <b>ER</b> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {er:.2f}%
        </div>
    """, unsafe_allow_html=True)
    
def ai_summary_platform(platform_name, df_filtered, key_suffix):
    """AI Summary: highest reach, impression, engagement, followers growth per platform."""
    if st.button("🤖 Generate AI Summary", key=f"ai_summary_{key_suffix}"):
        with st.spinner("Generating AI Summary..."):

            df_all   = df_filtered[df_filtered["Platform"].str.strip().str.lower() == platform_name.lower()]
            df_posts = df_all[df_all["id"].notna() & (df_all["id"].astype(str).str.strip() != "")]
            df_flw   = df_all[df_all["id"].isna() | (df_all["id"].astype(str).str.strip() == "")]

            def get_top(df, col):
                if df.empty or col not in df.columns:
                    return {}
                row = df.nlargest(1, col).iloc[0]
                return {
                    "message": str(row.get("message", "-"))[:200],
                    "type":    str(row.get("type", "-")),
                    "boosted": str(row.get("Boosted", "-")),
                    col:       int(row[col]) if pd.notna(row[col]) else 0
                }

            summary_data = {
                "platform":           platform_name,
                "highest_reach":      get_top(df_posts, "Reach"),
                "highest_impression": get_top(df_posts, "Impression"),
                "highest_engagement": get_top(df_posts, "Engagement"),
                "highest_flw_growth": get_top(df_flw,   "Growth"),
            }

            prompt = f"""
You are a social media analyst. Below is the content performance data for {platform_name} in the selected period:

{json.dumps(summary_data, indent=2, default=str)}

Please write a concise summary in English covering:
1. Content with the highest Reach — what type of content, organic or boosted, and its topic
2. Content with the highest Impression — what type of content, organic or boosted, and its topic
3. Content with the highest Engagement — what type of content, organic or boosted, and its topic
4. Which content or activity drove the highest Followers Growth
5. Brief insights and recommendations based on the patterns above

Format: use bullet points per category, use relevant emojis, keep it concise and to the point.
"""

            try:
                openai_api_key = st.secrets["OPENAI_API_KEY"]
                response = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Content-Type":  "application/json",
                        "Authorization": f"Bearer {openai_api_key}"
                    },
                    json={
                        "model":      "gpt-4.1-mini",
                        "max_tokens": 1000,
                        "messages":   [{"role": "user", "content": prompt}]
                    }
                )
                result  = response.json()
                ai_text = result["choices"][0]["message"]["content"]

                st.markdown("### 🤖 AI Summary")
                st.markdown(f"""
                    <div style="background:#f0f4ff;border-left:4px solid #4A90D9;
                                border-radius:8px;padding:16px;font-size:13px;line-height:1.8;">
                        {ai_text.replace(chr(10), '<br>')}
                    </div>
                """, unsafe_allow_html=True)

            except KeyError:
                st.error("API key not found. Make sure OPENAI_API_KEY is set in .streamlit/secrets.toml")
            except Exception as e:
                st.error(f"Failed to generate summary: {e}")


def ai_summary_top_views(df_top, content_type, platform_name, key_suffix):
    """AI Summary for Top 3 content based on Views."""
    if st.button("🤖 Generate AI Summary", key=f"ai_summary_views_{key_suffix}"):
        with st.spinner("Generating AI Summary..."):

            top_data = df_top[["message", "type", "Boosted", "Engagement", "Impression", "Reach"]].copy()
            top_data["message"] = top_data["message"].astype(str).str[:200]
            top_data["ER"]      = (top_data["Engagement"] / top_data["Impression"] * 100).round(2)

            prompt = f"""
You are a social media analyst. Below is the Top 3 {platform_name} {content_type} content with the highest Views:

{json.dumps(top_data.to_dict(orient="records"), indent=2, default=str)}

Please write a concise summary in English covering:
1. What is the highest-views content about (based on message/caption)
2. Are there consistent patterns across the top 3 (theme, style, topic)
3. Brief insight: why did this content attract many views
4. Recommendations for the next {content_type} content based on these patterns

Format: use bullet points, use relevant emojis, keep it concise and to the point.
"""

            try:
                openai_api_key = st.secrets["OPENAI_API_KEY"]
                response = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Content-Type":  "application/json",
                        "Authorization": f"Bearer {openai_api_key}"
                    },
                    json={
                        "model":      "gpt-4.1-mini",
                        "max_tokens": 1000,
                        "messages":   [{"role": "user", "content": prompt}]
                    }
                )
                result  = response.json()
                ai_text = result["choices"][0]["message"]["content"]

                st.markdown("### 🤖 AI Summary")
                st.markdown(f"""
                    <div style="background:#f0f4ff;border-left:4px solid #4A90D9;
                                border-radius:8px;padding:16px;font-size:13px;line-height:1.8;">
                        {ai_text.replace(chr(10), '<br>')}
                    </div>
                """, unsafe_allow_html=True)

            except KeyError:
                st.error("API key not found. Make sure OPENAI_API_KEY is set in .streamlit/secrets.toml")
            except Exception as e:
                st.error(f"Failed to generate summary: {e}")


def ai_summary_top_engagement(df_top, content_type, platform_name, key_suffix):
    """AI Summary for Top 3 content based on Engagement."""
    if st.button("🤖 Generate AI Summary", key=f"ai_summary_engagement_{key_suffix}"):
        with st.spinner("Generating AI Summary..."):

            top_data = df_top[["message", "type", "Boosted", "Engagement", "Impression", "Reach"]].copy()
            top_data["message"] = top_data["message"].astype(str).str[:200]
            top_data["ER"]      = (top_data["Engagement"] / top_data["Impression"] * 100).round(2)

            prompt = f"""
You are a social media analyst. Below is the Top 3 {platform_name} {content_type} content with the highest Engagement:

{json.dumps(top_data.to_dict(orient="records"), indent=2, default=str)}

Please write a concise summary in English covering:
1. What is the highest-engagement content about (based on message/caption)
2. Are there consistent patterns across the top 3 (theme, style, topic)
3. Brief insight: why did this content engage the audience well
4. Recommendations for the next {content_type} content based on these patterns

Format: use bullet points, use relevant emojis, keep it concise and to the point.
"""

            try:
                openai_api_key = st.secrets["OPENAI_API_KEY"]
                response = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Content-Type":  "application/json",
                        "Authorization": f"Bearer {openai_api_key}"
                    },
                    json={
                        "model":      "gpt-4.1-mini",
                        "max_tokens": 1000,
                        "messages":   [{"role": "user", "content": prompt}]
                    }
                )
                result  = response.json()
                ai_text = result["choices"][0]["message"]["content"]

                st.markdown("### 🤖 AI Summary")
                st.markdown(f"""
                    <div style="background:#f0f4ff;border-left:4px solid #4A90D9;
                                border-radius:8px;padding:16px;font-size:13px;line-height:1.8;">
                        {ai_text.replace(chr(10), '<br>')}
                    </div>
                """, unsafe_allow_html=True)

            except KeyError:
                st.error("API key not found. Make sure OPENAI_API_KEY is set in .streamlit/secrets.toml")
            except Exception as e:
                st.error(f"Failed to generate summary: {e}")
                
# =========================================================
# KPI OVERVIEW - ALL PLATFORMS
# =========================================================
KPI_ER        = 9
KPI_FOLLOWERS = {"Instagram": 500, "Facebook": 100, "Tiktok": 1000, "Youtube": 100}
KPI_VIEWS     = {"Instagram": None, "Facebook": None, "Tiktok": 10000, "Youtube": 2000}

st.header("📊 KPI Overview")

st.subheader("Engagement Rate")

rows_er = []
for platform_name in ["Instagram", "Facebook", "Tiktok", "Youtube"]:
    df_p              = df_filtered[df_filtered["Platform"].str.strip().str.lower() == platform_name.lower()]
    total_impression  = df_p["account_impression"].sum()
    total_interaction = df_p["account_interaction"].sum()
    er                = (total_interaction / total_impression * 100) if total_impression > 0 else 0
    rows_er.append({
        "Platform":          platform_name,
        "KPI":               f"{KPI_ER}%",
        "Total Impression":  f"{int(total_impression):,}",
        "Total Interaction": f"{int(total_interaction):,}",
        "ER":                f"{er:.2f}%",
        "Achievement":       f"{(er / KPI_ER * 100):.2f}%",
    })

st.dataframe(pd.DataFrame(rows_er).set_index("Platform"), use_container_width=True)
# =========================================================
# AI
# =========================================================
if st.button("🤖 Generate AI Summary", key="ai_summary_er"):
    with st.spinner("Generating AI Summary..."):

        summary_data = []
        for platform_name in ["Instagram", "Facebook", "Tiktok", "Youtube"]:
            df_p = df_filtered[df_filtered["Platform"].str.strip().str.lower() == platform_name.lower()]
            total_impression  = df_p["Impression"].sum()
            total_interaction = df_p["Engagement"].sum()
            er = (total_interaction / total_impression * 100) if total_impression > 0 else 0
            achieved = er >= KPI_ER

            df_p_posts = df_p[df_p["id"].notna() & (df_p["id"].astype(str).str.strip() != "")]
            top_posts = df_p_posts.nlargest(3, "Engagement")[
                ["message", "type", "Boosted", "Engagement", "Impression"]
            ].to_dict(orient="records")

            summary_data.append({
                "platform":  platform_name,
                "er":        round(er, 2),
                "kpi":       KPI_ER,
                "achieved":  achieved,
                "top_posts": top_posts
            })

        prompt = f"""
You are a social media analyst. Below is the Engagement Rate (ER) data per platform for the selected period:

{json.dumps(summary_data, indent=2, default=str)}

Please write a concise summary in English covering:
1. Which platforms achieved the KPI ER ({KPI_ER}%) and which did not
2. For those that achieved: which posts contributed the most (based on top posts), organic or boosted
3. For those that did not achieve: which posts had the highest engagement, organic or boosted, and possible reasons
4. Brief conclusion and recommendations

Format: use bullet points per platform, use relevant emojis, keep it concise and to the point.
"""

        try:
            openai_api_key = st.secrets["OPENAI_API_KEY"]

            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Content-Type":  "application/json",
                    "Authorization": f"Bearer {openai_api_key}"
                },
                json={
                    "model":      "gpt-4.1-mini",
                    "max_tokens": 1000,
                    "messages":   [{"role": "user", "content": prompt}]
                }
            )
            result  = response.json()
            ai_text = result["choices"][0]["message"]["content"]

            st.markdown("### 🤖 AI Summary")
            st.markdown(f"""
                <div style="background:#f0f4ff;border-left:4px solid #4A90D9;
                            border-radius:8px;padding:16px;font-size:13px;line-height:1.8;">
                    {ai_text.replace(chr(10), '<br>')}
                </div>
            """, unsafe_allow_html=True)

        except KeyError:
            st.error("API key not found. Make sure OPENAI_API_KEY is set in .streamlit/secrets.toml")
        except Exception as e:
            st.error(f"Failed to generate summary: {e}")
            
st.subheader("Followers Growth & Views")

rows_fv = []
for platform_name in ["Instagram", "Facebook", "Tiktok", "Youtube"]:
    df_p             = df_filtered[df_filtered["Platform"].str.strip().str.lower() == platform_name.lower()]
    df_followers     = df_p[df_p["id"].isna() | (df_p["id"].astype(str).str.strip() == "")]
    df_posts         = df_p[df_p["id"].notna() & (df_p["id"].astype(str).str.strip() != "")]
    followers_actual = df_followers["Growth"].sum()
    views_actual     = df_followers["account_impression"].sum()  
    kpi_f            = KPI_FOLLOWERS[platform_name]
    kpi_v            = KPI_VIEWS[platform_name]
    rows_fv.append({
        "Platform":     platform_name,
        "KPI Flw":      kpi_f if kpi_f else "-",
        "Flw Growth":   f"{int(followers_actual):,}",
        "Achv Flw":     f"{(followers_actual / kpi_f * 100):.2f}%" if kpi_f else "-",
        "KPI Views":    f"{int(kpi_v):,}" if kpi_v else "-",
        "Views Actual": f"{int(views_actual):,}",
        "Achv Views":   f"{(views_actual / kpi_v * 100):.2f}%" if kpi_v else "-",
    })

st.dataframe(pd.DataFrame(rows_fv).set_index("Platform"), use_container_width=True)

# --- AI SUMMARY FOLLOWERS GROWTH & VIEWS ---
if st.button("🤖 Generate AI Summary", key="ai_summary_fv"):
    with st.spinner("Generating AI Summary..."):

        summary_data = []
        for platform_name in ["Instagram", "Facebook", "Tiktok", "Youtube"]:
            df_p         = df_filtered[df_filtered["Platform"].str.strip().str.lower() == platform_name.lower()]
            df_followers = df_p[df_p["id"].isna() | (df_p["id"].astype(str).str.strip() == "")]
            df_posts     = df_p[df_p["id"].notna() & (df_p["id"].astype(str).str.strip() != "")]

            followers_actual = df_followers["Growth"].sum()
            views_actual     = df_posts["Impression"].sum()
            kpi_f            = KPI_FOLLOWERS[platform_name]
            kpi_v            = KPI_VIEWS[platform_name]

            achieved_flw   = (followers_actual >= kpi_f) if kpi_f else None
            achieved_views = (views_actual >= kpi_v)     if kpi_v else None

            top_posts = df_posts.nlargest(3, "Impression")[
                ["message", "type", "Boosted", "Impression", "Engagement"]
            ].to_dict(orient="records")

            summary_data.append({
                "platform":         platform_name,
                "followers_growth": int(followers_actual),
                "kpi_followers":    kpi_f,
                "achieved_flw":     achieved_flw,
                "views_actual":     int(views_actual),
                "kpi_views":        kpi_v,
                "achieved_views":   achieved_views,
                "top_posts":        top_posts
            })

        prompt = f"""
You are a social media analyst. Below is the Followers Growth and Views data per platform for the selected period:

{json.dumps(summary_data, indent=2, default=str)}

Please write a concise summary in English covering:
1. Which platforms achieved the KPI Followers Growth and which did not
2. Which platforms achieved the KPI Views and which did not
3. For those that achieved: which posts contributed the most (based on top posts), organic or boosted
4. For those that did not achieve: which posts had the highest views, organic or boosted, and possible reasons
5. Brief conclusion and recommendations

Format: use bullet points per platform, use relevant emojis, keep it concise and to the point.
"""

        try:
            openai_api_key = st.secrets["OPENAI_API_KEY"]

            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Content-Type":  "application/json",
                    "Authorization": f"Bearer {openai_api_key}"
                },
                json={
                    "model":      "gpt-4.1-mini",
                    "max_tokens": 1000,
                    "messages":   [{"role": "user", "content": prompt}]
                }
            )
            result  = response.json()
            ai_text = result["choices"][0]["message"]["content"]

            st.markdown("### 🤖 AI Summary")
            st.markdown(f"""
                <div style="background:#f0f4ff;border-left:4px solid #4A90D9;
                            border-radius:8px;padding:16px;font-size:13px;line-height:1.8;">
                    {ai_text.replace(chr(10), '<br>')}
                </div>
            """, unsafe_allow_html=True)

        except KeyError:
            st.error("API key not found. Make sure OPENAI_API_KEY is set in .streamlit/secrets.toml")
        except Exception as e:
            st.error(f"Failed to generate summary: {e}")

st.markdown("---")

# =========================================================
# INSTAGRAM
# =========================================================
st.header("📸 Instagram")

st.subheader("📋 Monthly Breakdown")
st.dataframe(build_monthly_table(df, "instagram"), use_container_width=True)

#ai summary monthly breakdown
ai_summary_platform("Instagram", df_filtered, key_suffix="ig_monthly")
            
# --- Top 3 Posts by ER ---
st.subheader("🏆 Top 3 Posts by ER")

df_ig       = df_filtered[df_filtered["Platform"].str.strip().str.lower() == "instagram"]
df_ig_posts = df_ig[df_ig["id"].notna() & (df_ig["id"].astype(str).str.strip() != "")]

df_ig_organic           = df_ig_posts[
    df_ig_posts["type"].str.strip().str.lower().isin(["photo", "carousel"]) &
    df_ig_posts["Boosted"].str.strip().str.lower().eq("organic")
].copy()
df_ig_organic["ER_raw"] = (df_ig_organic["Engagement"] / df_ig_organic["Impression"] * 100).round(2)
df_top_er               = df_ig_organic.sort_values("ER_raw", ascending=False).head(3)

if not df_top_er.empty:
    cols = st.columns(3)
    for idx, (_, row) in enumerate(df_top_er.iterrows()):
        post_url   = str(row["link"]).rstrip("/")
        post_type  = str(row.get("type", "-")).strip()
        reach      = int(row["Reach"])      if pd.notna(row.get("Reach"))      else 0
        impression = int(row["Impression"]) if pd.notna(row.get("Impression")) else 0
        engagement = int(row["Engagement"]) if pd.notna(row.get("Engagement")) else 0
        with cols[idx]:
            render_post_embed(post_url)
            render_post_metrics(post_type, reach, impression, engagement, row["ER_raw"])
else:
    st.info("Tidak ada data organic Photo/Carousel Instagram di periode ini.")            

ai_summary_top_engagement(df_top_er,         content_type="Feed (Photo/Carousel)", platform_name="Instagram", key_suffix="ig_er")
            
# --- Top 3 Reels by Views ---
st.subheader("🎬 Top 3 Reels by Views")

df_ig_reels  = df_ig_posts[
    df_ig_posts["type"].str.strip().str.lower().eq("reel") &
    df_ig_posts["Boosted"].str.strip().str.lower().eq("organic")
].copy()
df_top_reels = df_ig_reels.sort_values("Impression", ascending=False).head(3)

if not df_top_reels.empty:
    cols = st.columns(3)
    for idx, (_, row) in enumerate(df_top_reels.iterrows()):
        post_url   = str(row["link"]).rstrip("/")
        post_type  = str(row.get("type", "-")).strip()
        reach      = int(row["Reach"])      if pd.notna(row.get("Reach"))      else 0
        impression = int(row["Impression"]) if pd.notna(row.get("Impression")) else 0
        engagement = int(row["Engagement"]) if pd.notna(row.get("Engagement")) else 0
        er         = round(engagement / impression * 100, 2) if impression > 0 else 0
        with cols[idx]:
            render_post_embed(post_url)
            render_post_metrics(post_type, reach, impression, engagement, er)
else:
    st.info("Tidak ada data organic Reel Instagram di periode ini.")
ai_summary_top_views(df_top_reels,  content_type="Reels",   platform_name="Instagram", key_suffix="ig_reels")


st.subheader("📋 Content Breakdown")
build_content_breakdown(df_filtered, "instagram")
st.markdown("---")

# =========================================================
# FACEBOOK
# =========================================================
st.header("👥 Facebook")

st.subheader("📋 Monthly Breakdown")
st.dataframe(build_monthly_table(df, "facebook"), use_container_width=True)

# Facebook
ai_summary_platform("Facebook", df_filtered, key_suffix="fb_monthly")

# --- Top 3 Posts by Total Engagement ---
st.subheader("🏆 Top 3 Posts by Total Engagement")

df_fb       = df_filtered[df_filtered["Platform"].str.strip().str.lower() == "facebook"]
df_fb_posts = df_fb[df_fb["id"].notna() & (df_fb["id"].astype(str).str.strip() != "")]

df_fb_organic = df_fb_posts[
    df_fb_posts["Boosted"].str.strip().str.lower().eq("organic")
].copy()
df_fb_organic["ER_raw"] = (df_fb_organic["Engagement"] / df_fb_organic["Impression"] * 100).round(2)
df_top_engagement       = df_fb_organic.sort_values("Engagement", ascending=False).head(3)

if not df_top_engagement.empty:
    cols = st.columns(3)
    for idx, (_, row) in enumerate(df_top_engagement.iterrows()):
        post_url   = str(row["link"]).rstrip("/")
        post_type  = str(row.get("type", "-")).strip()
        reach      = int(row["Reach"])      if pd.notna(row.get("Reach"))      else 0
        impression = int(row["Impression"]) if pd.notna(row.get("Impression")) else 0
        engagement = int(row["Engagement"]) if pd.notna(row.get("Engagement")) else 0
        er         = row["ER_raw"]
        with cols[idx]:
            # Embed Facebook post via Facebook plugin iframe
            st.components.v1.html(
                f"""
                <iframe
                    src="https://www.facebook.com/plugins/post.php?href={urllib.parse.quote(post_url)}&show_text=true&width=500"
                    width="100%"
                    height="500"
                    style="border:none;overflow:hidden;"
                    scrolling="no"
                    frameborder="0"
                    allowfullscreen="true"
                    allow="autoplay; clipboard-write; encrypted-media; picture-in-picture; web-share">
                </iframe>
                """,
                height=520, scrolling=False)
            render_post_metrics(post_type, reach, impression, engagement, er)
else:
    st.info("Tidak ada data organic Facebook di periode ini.")
ai_summary_top_engagement(df_top_engagement, content_type="Post",                  platform_name="Facebook",  key_suffix="fb_engagement")
    
st.subheader("📋 Content Breakdown")
build_content_breakdown(df_filtered, "facebook")

st.markdown("---")

# =========================================================
# TIKTOK
# =========================================================
st.header("🎵 TikTok")

st.subheader("📋 Monthly Breakdown")
st.dataframe(build_monthly_table(df, "tiktok"), use_container_width=True)

# TikTok
ai_summary_platform("Tiktok", df_filtered, key_suffix="tt_monthly")

# --- Top 3 Posts by Views ---
st.subheader("🏆 Top 3 Posts by Views")

df_tt       = df_filtered[df_filtered["Platform"].str.strip().str.lower() == "tiktok"]
df_tt_posts = df_tt[df_tt["id"].notna() & (df_tt["id"].astype(str).str.strip() != "")]

df_tt_organic = df_tt_posts[
    df_tt_posts["Boosted"].str.strip().str.lower().eq("organic")
].copy()
df_top_views = df_tt_organic.sort_values("Impression", ascending=False).head(3)

if not df_top_views.empty:
    cols = st.columns(3)
    for idx, (_, row) in enumerate(df_top_views.iterrows()):
        post_url   = str(row["link"]).rstrip("/")
        impression = int(row["Impression"]) if pd.notna(row.get("Impression")) else 0
        watch_rate = row.get("Watch Rate", None)
        try:
            watch_str = f"{float(str(watch_rate).replace('%', '').strip()):.2f}%"
        except:
            watch_str = "-"

        with cols[idx]:
            try:
                video_id = post_url.rstrip("/").split("/")[-1]
                st.components.v1.html(
                    f"""
                    <div style="width:100%;overflow:hidden;border-radius:8px;background:#000;">
                        <iframe
                            src="https://www.tiktok.com/embed/v2/{video_id}"
                            width="100%"
                            height="420"
                            frameborder="0"
                            scrolling="no"
                            allow="encrypted-media"
                            style="border:none;display:block;">
                        </iframe>
                    </div>
                    """,
                    height=425, scrolling=False)
            except:
                st.markdown(f'<a href="{post_url}" target="_blank">🎵 Lihat Post</a>', unsafe_allow_html=True)

            st.markdown(f"""
                <div style="background:#f8f9fa;border-radius:8px;padding:10px 12px;font-size:12px;line-height:2;margin-top:6px;">
                📢 <b>Impression</b> &nbsp; {impression:,}<br>
                🎯 <b>Watch Rate</b> &nbsp; {watch_str}
                </div>
            """, unsafe_allow_html=True)
else:
    st.info("Tidak ada data organic TikTok di periode ini.")
ai_summary_top_views(df_top_views, content_type="TikTok",  platform_name="TikTok",    key_suffix="tt_views")

st.subheader("📋 Content Breakdown")
build_content_breakdown(df_filtered, "tiktok")

st.markdown("---")

# =========================================================
# YOUTUBE
# =========================================================
st.header("▶️ YouTube")

st.subheader("📋 Monthly Breakdown")
st.dataframe(build_monthly_table(df, "youtube"), use_container_width=True)

# YouTube
ai_summary_platform("Youtube", df_filtered, key_suffix="yt_monthly")

# --- Top 3 YouTube Shorts by Views ---
st.subheader("🏆 Top 3 YouTube Shorts by Views")

def extract_yt_id(url):
    """Ekstrak video ID dari berbagai format URL YouTube."""
    url = str(url).strip()
    # Format: youtu.be/ID
    if "youtu.be/" in url:
        return url.split("youtu.be/")[-1].split("?")[0]
    # Format: youtube.com/shorts/ID
    if "/shorts/" in url:
        return url.split("/shorts/")[-1].split("?")[0]
    # Format: youtube.com/watch?v=ID
    if "v=" in url:
        return url.split("v=")[-1].split("&")[0]
    return None

df_yt = df_filtered[df_filtered["Platform"].str.strip().str.lower() == "youtube"]
df_yt_posts = df_yt[df_yt["id"].notna() & (df_yt["id"].astype(str).str.strip() != "")]

df_yt_shorts = df_yt_posts[
    df_yt_posts["Boosted"].str.strip().str.lower().eq("organic") &
    df_yt_posts["type"].str.strip().str.upper().eq("SHORTS")
].copy()

df_yt_shorts["completion_rate"] = pd.to_numeric(
    df_yt_shorts["Avg View Percentage"], errors="coerce"
).round(2)

df_top_shorts = df_yt_shorts.sort_values("Impression", ascending=False).head(3)
if not df_top_shorts.empty:
    cols = st.columns(3)
    for idx, (_, row) in enumerate(df_top_shorts.iterrows()):
        post_url        = str(row["link"]).rstrip("/")
        video_id        = extract_yt_id(post_url)
        views           = int(row["Impression"])    if pd.notna(row.get("Impression"))        else 0
        completion_rate = row["completion_rate"]    if pd.notna(row.get("completion_rate"))    else 0.0

        with cols[idx]:
            if video_id:
                st.components.v1.html(
                    f"""
                    <iframe
                        src="https://www.youtube.com/embed/{video_id}"
                        width="100%"
                        height="500"
                        style="border:none;border-radius:12px;"
                        frameborder="0"
                        allowfullscreen
                        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture">
                    </iframe>
                    """,
                    height=520, scrolling=False)
            else:
                st.warning("URL tidak valid.")

            # Metrics
            st.markdown(f"""
                <div style="margin-top:8px;">
                    <p>👁️ <b>Views:</b> {views:,}</p>
                    <p>✅ <b>Completion Rate:</b> {completion_rate:.2f}%</p>
                </div>
            """, unsafe_allow_html=True)
else:
    st.info("Tidak ada data organic YouTube Shorts di periode ini.")
ai_summary_top_views(df_top_shorts, content_type="Shorts",  platform_name="YouTube",   key_suffix="yt_shorts")

# --- Top 3 YouTube Videos by Views ---
st.subheader("🏆 Top 3 YouTube Videos by Views")

df_yt_videos = df_yt_posts[
    df_yt_posts["Boosted"].str.strip().str.lower().eq("organic") &
    df_yt_posts["type"].str.strip().str.upper().eq("VIDEO")
].copy()

df_yt_videos["completion_rate"] = pd.to_numeric(
    df_yt_videos["Avg View Percentage"], errors="coerce"
).round(2)

df_top_videos = df_yt_videos.sort_values("Impression", ascending=False).head(3)

if not df_top_videos.empty:
    cols = st.columns(3)
    for idx, (_, row) in enumerate(df_top_videos.iterrows()):
        post_url        = str(row["link"]).rstrip("/")
        video_id        = extract_yt_id(post_url)
        views           = int(row["Impression"])  if pd.notna(row.get("Impression"))    else 0
        completion_rate = row["completion_rate"]  if pd.notna(row.get("completion_rate")) else 0.0

        with cols[idx]:
            if video_id:
                st.components.v1.html(
                    f"""
                    <iframe
                        src="https://www.youtube.com/embed/{video_id}"
                        width="100%"
                        height="500"
                        style="border:none;border-radius:12px;"
                        frameborder="0"
                        allowfullscreen
                        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture">
                    </iframe>
                    """,
                    height=520, scrolling=False)
            else:
                st.warning("URL tidak valid.")

            st.markdown(f"""
                <div style="margin-top:8px;">
                    <p>👁️ <b>Views:</b> {views:,}</p>
                    <p>✅ <b>Completion Rate:</b> {completion_rate:.2f}%</p>
                </div>
            """, unsafe_allow_html=True)
else:
    st.info("Tidak ada data organic YouTube Video di periode ini.")
ai_summary_top_views(df_top_videos, content_type="Video",   platform_name="YouTube",   key_suffix="yt_videos")
   
    
st.subheader("📋 Content Breakdown")
build_content_breakdown(df_filtered, "youtube")
