import asyncio

import nest_asyncio
import streamlit as st
from dotenv import load_dotenv

from open_notebook.domain.base import ObjectModel

nest_asyncio.apply()
from open_notebook.exceptions import NotFoundError
from pages.components import note_panel, source_insight_panel, source_panel
from pages.stream_app.utils import setup_page

load_dotenv()
setup_page("📒 Open Notebook", sidebar_state="collapsed")

if "object_id" not in st.query_params:
    st.switch_page("pages/2_📒_Notebooks.py")
    st.stop()

object_id = st.query_params["object_id"]

obj_type = object_id.split(":")[0]

if obj_type == "note":
    note_panel(object_id)
elif obj_type == "source":
    source_panel(object_id)
elif obj_type == "source_insight":
    source_insight_panel(object_id)
