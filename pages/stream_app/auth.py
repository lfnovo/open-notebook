import os
import streamlit as st


def check_password():
    """
    Check if the user has entered the correct password.
    Returns True if authenticated or no password is set.
    """
    # Get the password from environment variable
    app_password = os.environ.get("OPEN_NOTEBOOK_PASSWORD")
    
    # If no password is set, skip authentication
    if not app_password:
        return True
    
    # Check if already authenticated in this session
    if "authenticated" in st.session_state and st.session_state.authenticated:
        return True
    
    # Show login form
    with st.container():
        st.markdown("### 🔒 Authentication Required")
        st.markdown("This Open Notebook instance is password protected.")
        
        with st.form("login_form"):
            password = st.text_input(
                "Password", 
                type="password", 
                placeholder="Enter password"
            )
            submitted = st.form_submit_button("Login")
            
            if submitted:
                if password == app_password:
                    st.session_state.authenticated = True
                    st.success("Successfully authenticated!")
                    st.rerun()
                else:
                    st.error("Incorrect password. Please try again.")
    
    # Stop execution if not authenticated
    if "authenticated" not in st.session_state or not st.session_state.authenticated:
        st.stop()
    
    return True


def logout():
    """Clear authentication from session state."""
    if "authenticated" in st.session_state:
        del st.session_state.authenticated