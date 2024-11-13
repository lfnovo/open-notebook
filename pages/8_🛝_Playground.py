import streamlit as st
import yaml

from open_notebook.graphs.multipattern import graph as pattern_graph
from pages.components.model_selector import model_selector
from pages.stream_app.utils import setup_page

setup_page("🛝 Playground")

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

model = model_selector(
    "Pick a pattern model",
    key="model",
    help="This is the model that will be used to run the transformation",
    model_type="language",
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
