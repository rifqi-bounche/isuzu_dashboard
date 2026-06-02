import streamlit as st

def check_login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.title("🔐 Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            if (
                username == st.secrets["credentials"]["username"]
                and password == st.secrets["credentials"]["password"]
            ):
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Username atau password salah.")

        st.stop()