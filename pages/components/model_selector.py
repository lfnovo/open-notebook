from typing import Literal

import streamlit as st

from open_notebook.domain.models import Model


def model_selector(
    label,
    key,
    selected_id=None,
    help=None,
    model_type: Literal[
        "language", "embedding", "speech_to_text", "text_to_speech"
    ] = "language",
) -> Model:
    models = Model.get_models_by_type(model_type)
    models.sort(key=lambda x: (x.provider, x.name))
    try:
        index = (
            next((i for i, m in enumerate(models) if m.id == selected_id), 0)
            if selected_id
            else 0
        )
    except Exception:
        index = 0

    return st.selectbox(
        label,
        models,
        format_func=lambda x: f"{x.provider} - {x.name}",
        help=help,
        index=index,
        key=key,
    )
