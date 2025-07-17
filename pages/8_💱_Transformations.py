import streamlit as st

from api.transformations_service import transformations_service
from open_notebook.domain.transformation import DefaultPrompts, Transformation
from pages.components.model_selector import model_selector
from pages.stream_app.utils import setup_page

setup_page("🧩 Transformations")

transformations_tab, playground_tab = st.tabs(["🧩 Transformations", "🛝 Playground"])


if "transformations" not in st.session_state:
    st.session_state.transformations = transformations_service.get_all_transformations()
else:
    # work-around for streamlit losing typing on session state
    st.session_state.transformations = [
        Transformation(**trans.model_dump())
        for trans in st.session_state.transformations
    ]

with transformations_tab:
    st.header("🧩 Transformations")

    st.markdown(
        "Transformations are prompts that will be used by the LLM to process a source and extract insights, summaries, etc. "
    )
    default_prompts: DefaultPrompts = DefaultPrompts()
    with st.expander("**⚙️ Default Transformation Prompt**"):
        default_prompts.transformation_instructions = st.text_area(
            "Default Transformation Prompt",
            default_prompts.transformation_instructions,
            height=300,
        )
        st.caption("This will be added to all your transformation prompts.")
        if st.button("Save", key="save_default_prompt"):
            default_prompts.update()
            st.toast("Default prompt saved successfully!")
    if st.button("Create new Transformation", icon="➕", key="new_transformation"):
        new_transformation = transformations_service.create_transformation(
            name="New Transformation",
            title="New Transformation Title",
            description="New Transformation Description",
            prompt="New Transformation Prompt",
            apply_default=False,
        )
        st.session_state.transformations.insert(0, new_transformation)
        st.rerun()

    st.divider()
    st.markdown("Your Transformations")
    if len(st.session_state.transformations) == 0:
        st.markdown(
            "No transformation created yet. Click 'Create new transformation' to get started."
        )
    else:
        for idx, transformation in enumerate(st.session_state.transformations):
            transform_expander = f"**{transformation.name}**" + (
                " - default" if transformation.apply_default else ""
            )
            with st.expander(
                transform_expander,
                expanded=(transformation.id is None),
            ):
                name = st.text_input(
                    "Transformation Name",
                    transformation.name,
                    key=f"{transformation.id}_name",
                )
                title = st.text_input(
                    "Card Title (this will be the title of all cards created by this transformation). ie 'Key Topics'",
                    transformation.title,
                    key=f"{transformation.id}_title",
                )
                description = st.text_area(
                    "Description (displayed as a hint in the UI so you know what you are selecting)",
                    transformation.description,
                    key=f"{transformation.id}_description",
                )
                prompt = st.text_area(
                    "Prompt",
                    transformation.prompt,
                    key=f"{transformation.id}_prompt",
                    height=300,
                )
                st.markdown(
                    "You can use the prompt to summarize, expand, extract insights and much more. Example: `Translate this text to French`. For inspiration, check out this [great resource](https://github.com/danielmiessler/fabric/tree/main/patterns)."
                )

                apply_default = st.checkbox(
                    "Suggest by default on new sources",
                    transformation.apply_default,
                    key=f"{transformation.id}_apply_default",
                )
                if st.button("Save", key=f"{transformation.id}_save"):
                    transformation.name = name
                    transformation.title = title
                    transformation.description = description
                    transformation.prompt = prompt
                    transformation.apply_default = apply_default
                    st.toast(f"Transformation '{name}' saved successfully!")
                    transformations_service.update_transformation(transformation)
                    st.rerun()

                if transformation.id:
                    with st.popover("Other actions"):
                        if st.button(
                            "Use in Playground",
                            icon="🛝",
                            key=f"{transformation.id}_playground",
                        ):
                            st.stop()
                        if st.button(
                            "Delete", icon="❌", key=f"{transformation.id}_delete"
                        ):
                            transformations_service.delete_transformation(transformation.id)
                            st.session_state.transformations.remove(transformation)
                            st.toast(f"Transformation '{name}' deleted successfully!")
                            st.rerun()

with playground_tab:
    st.title("🛝 Playground")

    transformation = st.selectbox(
        "Pick a transformation",
        st.session_state.transformations,
        format_func=lambda x: x.name,
    )

    model = model_selector(
        "Pick a pattern model",
        key="model",
        help="This is the model that will be used to run the transformation",
        model_type="language",
    )

    input_text = st.text_area("Enter some text", height=200)

    if st.button("Run"):
        if transformation and model and input_text:
            result = transformations_service.execute_transformation(
                transformation_id=transformation.id,
                input_text=input_text,
                model_id=model.id
            )
            st.markdown(result["output"])
        else:
            st.warning("Please select a transformation, model, and enter some text.")
