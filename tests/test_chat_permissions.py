from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from api.routers.chat import _ensure_session_notebook_owner


@pytest.mark.asyncio
async def test_session_owner_check_rejects_non_owner():
    with patch(
        "api.routers.chat._notebook_id_for_session",
        new_callable=AsyncMock,
        return_value="notebook:team",
    ), patch(
        "api.routers.chat.Notebook.get",
        new_callable=AsyncMock,
        return_value=SimpleNamespace(owner_id="app_user:owner", visibility="team"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await _ensure_session_notebook_owner(
                "chat_session:one",
                user_id="app_user:member",
            )

    assert exc_info.value.status_code == 403
