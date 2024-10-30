import streamlit as st

from open_notebook.database.migrate import MigrationManager
from stream_app.utils import version_sidebar

version_sidebar()
mm = MigrationManager()
if mm.needs_migration:
    st.warning("The Open Notebook database needs a migration to run properly.")
    if st.button("Run Migration"):
        mm.run_migration_up()
        st.success("Migration successful")
        st.rerun()
else:
    st.switch_page("pages/2_📒_Notebooks.py")
