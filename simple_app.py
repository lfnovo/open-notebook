import streamlit as st
import os

# Simple page config
st.set_page_config(
    page_title="Open Notebook - Simple Version",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Simple sidebar
st.sidebar.title("📒 Open Notebook")
st.sidebar.markdown("---")

# Navigation
if st.sidebar.button("🏠 Home"):
    st.session_state.page = "home"
if st.sidebar.button("📚 Notebooks"):
    st.session_state.page = "notebooks"
if st.sidebar.button("🔍 Search"):
    st.session_state.page = "search"
if st.sidebar.button("🤖 Models"):
    st.session_state.page = "models"
if st.sidebar.button("⚙️ Settings"):
    st.session_state.page = "settings"

# Initialize session state
if "page" not in st.session_state:
    st.session_state.page = "home"

# Main content
if st.session_state.page == "home":
    st.title("📒 Open Notebook")
    st.markdown("Welcome to Open Notebook - AI-powered research and note-taking companion")
    
    st.markdown("### Quick Actions")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.info("📚 **Notebooks**\n\nCreate and manage your research notebooks")
    
    with col2:
        st.info("🔍 **Search**\n\nSearch through your knowledge base")
    
    with col3:
        st.info("🤖 **AI Models**\n\nConfigure AI models for your research")

elif st.session_state.page == "notebooks":
    st.title("📚 Notebooks")
    st.markdown("Manage your research notebooks")
    
    # Simple notebook creation
    with st.expander("Create New Notebook"):
        name = st.text_input("Notebook Name")
        description = st.text_area("Description")
        if st.button("Create Notebook"):
            st.success(f"Created notebook: {name}")

elif st.session_state.page == "search":
    st.title("🔍 Search")
    st.markdown("Search through your knowledge base")
    
    query = st.text_input("Enter your search query")
    if st.button("Search"):
        st.info(f"Searching for: {query}")

elif st.session_state.page == "models":
    st.title("🤖 AI Models")
    st.markdown("Configure AI models for your research")
    
    st.info("Model configuration will be available in the full version")

elif st.session_state.page == "settings":
    st.title("⚙️ Settings")
    st.markdown("Application settings")
    
    st.info("Settings will be available in the full version")

# Footer
st.markdown("---")
st.markdown("**Open Notebook** - Simple Version | For full functionality, use the complete application")

