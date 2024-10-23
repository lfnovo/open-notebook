import streamlit as st

from open_notebook.exceptions import InvalidDatabaseSchema, NoSchemaFound
from open_notebook.repository import check_version, execute_migration

try:
    check_version()
    st.switch_page("pages/2_📒_Notebooks.py")
except NoSchemaFound as e:
    st.warning(e)
    if st.button("Create Schema.."):
        try:
            execute_migration("db_setup.surrealql")
            st.success("Schema created successfully")
            st.rerun()
        except Exception as e:
            st.error(e)
except InvalidDatabaseSchema as e:
    st.warning(e)
    if st.button("Execute Migration.."):
        try:
            execute_migration("0_0_1_to_0_0_2.surrealql")
            st.success("Migration executed successfully")
            st.rerun()
        except Exception as e:
            st.error(e)
    st.stop()
