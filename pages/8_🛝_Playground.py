import streamlit as st
import yaml

from open_notebook.graphs.multipattern import graph as pattern_graph
from stream_app.utils import version_sidebar

st.set_page_config(
    layout="wide", page_title="🛝 Playground", initial_sidebar_state="expanded"
)
version_sidebar()

st.title("🛝 Playground")
with open("transformations.yaml", "r") as file:
    transformations = yaml.safe_load(file)

insight_transformations = transformations["source_insights"]

transformation = st.selectbox(
    "Pick a transformation",
    insight_transformations,
    format_func=lambda x: x.get("name", "No Name"),
)

with st.expander("Details"):
    st.json(transformation)

input_text = st.text_area("Enter some text", height=200)

if st.button("Run"):
    output = pattern_graph.invoke(
        dict(
            content_stack=[input_text],
            patterns=transformation["patterns"],
        )
    )
    st.markdown(output["output"])
