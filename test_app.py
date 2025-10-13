import streamlit as st

st.set_page_config(
    page_title="Open Notebook Test",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📒 Open Notebook - Test Page")
st.write("This is a test page to verify Streamlit is working.")

st.sidebar.title("Navigation")
st.sidebar.write("This is the sidebar")

st.write("If you can see this page, Streamlit is working correctly!")
st.write("The main application should be accessible once all dependencies are resolved.")

