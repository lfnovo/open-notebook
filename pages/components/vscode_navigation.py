import streamlit as st

def create_vscode_sidebar():
    """Create a VS Code-like sidebar navigation"""
    
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
            width: 100%;
            text-align: left;
            margin-bottom: 4px;
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
        h1, h2, h3 {
            color: #ffffff;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
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
        
        /* Container borders */
        .stContainer {
            border: 1px solid #3e3e42;
            border-radius: 5px;
            padding: 10px;
            margin: 10px 0;
        }
    </style>
    """, unsafe_allow_html=True)

    # Sidebar content
    st.sidebar.markdown('<div class="sidebar-title">📒 Open Notebook</div>', unsafe_allow_html=True)
    st.sidebar.markdown("---")
    
    # Navigation buttons
    if st.sidebar.button("🏠 Home", key="nav_home"):
        st.switch_page("pages/2_📒_Notebooks.py")
    
    if st.sidebar.button("📚 Notebooks", key="nav_notebooks"):
        st.switch_page("pages/2_📒_Notebooks.py")
    
    if st.sidebar.button("🔍 Search", key="nav_search"):
        st.switch_page("pages/3_🔍_Ask_and_Search.py")
    
    if st.sidebar.button("🤖 Models", key="nav_models"):
        st.switch_page("pages/7_🤖_Models.py")
    
    if st.sidebar.button("💱 Transformations", key="nav_transformations"):
        st.switch_page("pages/8_💱_Transformations.py")
    
    if st.sidebar.button("⚙️ Settings", key="nav_settings"):
        st.switch_page("pages/10_⚙️_Settings.py")

def add_back_button():
    """Add a back button to the current page"""
    if st.button("← Back", key="back_button"):
        # Go back to notebooks list
        if "current_notebook_id" in st.session_state:
            st.session_state["current_notebook_id"] = None
            st.rerun()
        else:
            st.switch_page("pages/2_📒_Notebooks.py")

