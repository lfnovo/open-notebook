import streamlit as st
import yaml

from open_notebook.domain.models import Model
from open_notebook.graphs.multipattern import graph as pattern_graph
from stream_app.utils import page_commons

st.set_page_config(
    layout="wide", page_title="🛝 Playground", initial_sidebar_state="expanded"
)
page_commons()

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

models = Model.get_models_by_type("language")
model = st.selectbox(
    "Pick a pattern model",
    models,
    format_func=lambda x: x.name,
)
input_text = st.text_area("Enter some text", height=200)

if st.button("Run"):
    output = pattern_graph.invoke(
        dict(
            content_stack=[input_text],
            patterns=transformation["patterns"],
        ),
        config=dict(configurable={"model_id": model.id}),
    )
    st.markdown(output["output"])
