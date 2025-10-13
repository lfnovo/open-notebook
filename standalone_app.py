import streamlit as st

# Page config
st.set_page_config(
    page_title="Open Notebook",
    layout="wide",
    initial_sidebar_state="expanded"
)

# VS Code-like CSS styling
st.markdown("""
<style>
    /* VS Code Dark Theme */
    .stApp {
        background-color: #1e1e1e;
        color: #d4d4d4;
    }
    
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        max-width: 100%;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background-color: #252526;
        border-right: 1px solid #3e3e42;
    }
    
    /* VS Code-like buttons */
    .stButton > button {
        background-color: #0e639c;
        color: white;
        border: none;
        border-radius: 3px;
        padding: 8px 16px;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-size: 13px;
        transition: background-color 0.2s;
    }
    
    .stButton > button:hover {
        background-color: #1177bb;
    }
    
    /* Back button styling */
    .back-button {
        background-color: #3c3c3c !important;
        border: 1px solid #5a5a5a !important;
        color: #cccccc !important;
        margin-bottom: 10px;
    }
    
    .back-button:hover {
        background-color: #4a4a4a !important;
    }
    
    /* Title styling */
    h1 {
        color: #ffffff;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-size: 24px;
        margin-bottom: 20px;
    }
    
    /* Content styling */
    .content-area {
        background-color: #1e1e1e;
        padding: 20px;
        border-radius: 5px;
        margin: 10px 0;
    }
    
    /* Sidebar title */
    .sidebar-title {
        color: #ffffff;
        font-size: 16px;
        font-weight: 600;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
st.sidebar.markdown('<div class="sidebar-title">📒 Open Notebook</div>', unsafe_allow_html=True)
st.sidebar.markdown("---")

# Navigation
if st.sidebar.button("🏠 Home"):
    navigate_to_page("home")
    st.rerun()
if st.sidebar.button("📚 Notebooks"):
    navigate_to_page("notebooks")
    st.rerun()
if st.sidebar.button("🔍 Search"):
    navigate_to_page("search")
    st.rerun()
if st.sidebar.button("🤖 Models"):
    navigate_to_page("models")
    st.rerun()
if st.sidebar.button("⚙️ Settings"):
    navigate_to_page("settings")
    st.rerun()

# Initialize session state
if "page" not in st.session_state:
    st.session_state.page = "home"
if "page_history" not in st.session_state:
    st.session_state.page_history = ["home"]

# Back button functionality
def go_back():
    if len(st.session_state.page_history) > 1:
        st.session_state.page_history.pop()  # Remove current page
        st.session_state.page = st.session_state.page_history[-1]  # Go to previous page

def navigate_to_page(page):
    if st.session_state.page != page:
        st.session_state.page_history.append(page)
        st.session_state.page = page

# Back button (only show if not on home page)
if st.session_state.page != "home" and len(st.session_state.page_history) > 1:
    if st.button("← Back", key="back_button"):
        go_back()
        st.rerun()

# Main content
if st.session_state.page == "home":
    st.markdown('<div class="content-area">', unsafe_allow_html=True)
    st.title("📒 Open Notebook")
    st.markdown("Welcome to Open Notebook - AI-powered research and note-taking companion")
    
    st.markdown("### Quick Actions")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📚 **Notebooks**\n\nCreate and manage your research notebooks", key="home_notebooks"):
            navigate_to_page("notebooks")
            st.rerun()
    
    with col2:
        if st.button("🔍 **Search**\n\nSearch through your knowledge base", key="home_search"):
            navigate_to_page("search")
            st.rerun()
    
    with col3:
        if st.button("🤖 **AI Models**\n\nConfigure AI models for your research", key="home_models"):
            navigate_to_page("models")
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state.page == "notebooks":
    st.markdown('<div class="content-area">', unsafe_allow_html=True)
    st.title("📚 Notebooks")
    st.markdown("Manage your research notebooks")
    
    # Simple notebook creation
    with st.expander("Create New Notebook"):
        name = st.text_input("Notebook Name")
        description = st.text_area("Description")
        if st.button("Create Notebook"):
            st.success(f"Created notebook: {name}")
    st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state.page == "search":
    st.markdown('<div class="content-area">', unsafe_allow_html=True)
    st.title("🔍 Search")
    st.markdown("Search through your knowledge base")
    
    query = st.text_input("Enter your search query")
    if st.button("Search"):
        st.info(f"Searching for: {query}")
    st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state.page == "models":
    st.markdown('<div class="content-area">', unsafe_allow_html=True)
    st.title("🤖 AI Models")
    st.markdown("Configure AI models for your research")
    
    st.info("Model configuration will be available in the full version")
    st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state.page == "settings":
    st.markdown('<div class="content-area">', unsafe_allow_html=True)
    st.title("⚙️ Settings")
    st.markdown("Application settings")
    
    st.info("Settings will be available in the full version")
    st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("**Open Notebook** - Standalone Version")
