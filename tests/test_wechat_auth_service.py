from unittest.mock import AsyncMock

import pytest

from api.models import WeChatCallbackRequest
from api.services import wechat_auth_service
from api.services.wechat_auth_service import (
    WeChatOAuthTokens,
    WeChatUserInfo,
    build_wechat_authorize_url,
    handle_wechat_callback,
)


@pytest.mark.asyncio
async def test_build_wechat_authorize_url_uses_configured_web_scope(monkeypatch):
    monkeypatch.setenv("WECHAT_OPEN_APP_ID", "wx-app-id")
    monkeypatch.setenv("WECHAT_OPEN_REDIRECT_URI", "https://lumina.example.com/login/wechat/callback")

    response = await build_wechat_authorize_url("csrf-state")

    assert response.enabled is True
    assert "https://open.weixin.qq.com/connect/qrconnect" in response.authorize_url
    assert "appid=wx-app-id" in response.authorize_url
    assert "scope=snsapi_login" in response.authorize_url
    assert "state=csrf-state" in response.authorize_url
    assert "redirect_uri=https%3A%2F%2Flumina.example.com%2Flogin%2Fwechat%2Fcallback" in response.authorize_url


@pytest.mark.asyncio
async def test_handle_wechat_callback_logs_in_existing_bound_user(monkeypatch):
    user = {
        "id": "app_user:existing",
        "username": "existing",
        "display_name": "Existing User",
        "role": "user",
        "status": "active",
    }
    monkeypatch.setattr(
        wechat_auth_service,
        "_exchange_code_for_tokens",
        AsyncMock(
            return_value=WeChatOAuthTokens(
                access_token="wx-token",
                openid="openid-1",
                unionid="unionid-1",
            )
        ),
    )
    monkeypatch.setattr(
        wechat_auth_service,
        "_fetch_user_info",
        AsyncMock(
            return_value=WeChatUserInfo(
                openid="openid-1",
                unionid="unionid-1",
                nickname="WeChat Name",
                headimgurl="https://example.com/avatar.jpg",
            )
        ),
    )
    monkeypatch.setattr(
        wechat_auth_service.UserRepository,
        "get_user_by_wechat_identity",
        AsyncMock(return_value=user),
    )
    monkeypatch.setattr(wechat_auth_service.UserRepository, "update_user", AsyncMock(return_value=[user]))
    monkeypatch.setattr(wechat_auth_service.UserRepository, "create_wechat_user", AsyncMock())
    monkeypatch.setattr(wechat_auth_service, "create_jwt_token", lambda username, user_id, row: "jwt-token")
    monkeypatch.setattr(wechat_auth_service.AuditLogRepository, "create", AsyncMock())

    response = await handle_wechat_callback(WeChatCallbackRequest(code="auth-code", state="csrf-state"))

    assert response.success is True
    assert response.token == "jwt-token"
    assert response.username == "existing"
    wechat_auth_service.UserRepository.get_user_by_wechat_identity.assert_awaited_once_with(
        unionid="unionid-1",
        openid="openid-1",
    )
    wechat_auth_service.UserRepository.create_wechat_user.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_wechat_callback_creates_user_for_new_wechat_identity(monkeypatch):
    monkeypatch.setenv("ALLOW_PUBLIC_REGISTRATION", "true")
    created_user = {
        "id": "app_user:wx_openid_2",
        "username": "wx_openid_2",
        "display_name": "New WeChat User",
        "role": "user",
        "status": "active",
    }
    monkeypatch.setattr(
        wechat_auth_service,
        "_exchange_code_for_tokens",
        AsyncMock(
            return_value=WeChatOAuthTokens(
                access_token="wx-token",
                openid="openid-2",
                unionid=None,
            )
        ),
    )
    monkeypatch.setattr(
        wechat_auth_service,
        "_fetch_user_info",
        AsyncMock(
            return_value=WeChatUserInfo(
                openid="openid-2",
                unionid=None,
                nickname="New WeChat User",
                headimgurl="https://example.com/new-avatar.jpg",
            )
        ),
    )
    monkeypatch.setattr(
        wechat_auth_service.UserRepository,
        "get_user_by_wechat_identity",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        wechat_auth_service.UserRepository,
        "create_wechat_user",
        AsyncMock(return_value=created_user),
    )
    monkeypatch.setattr(wechat_auth_service.UserRepository, "update_user", AsyncMock())
    monkeypatch.setattr(wechat_auth_service, "create_jwt_token", lambda username, user_id, row: "jwt-token")
    monkeypatch.setattr(wechat_auth_service.AuditLogRepository, "create", AsyncMock())

    response = await handle_wechat_callback(WeChatCallbackRequest(code="auth-code", state=None))

    assert response.success is True
    assert response.token == "jwt-token"
    assert response.username == "wx_openid_2"
    wechat_auth_service.UserRepository.create_wechat_user.assert_awaited_once()
    create_payload = wechat_auth_service.UserRepository.create_wechat_user.await_args.args[0]
    assert create_payload["username"] == "wx_openid_2"
    assert create_payload["display_name"] == "New WeChat User"
    assert create_payload["wechat_openid"] == "openid-2"
    assert create_payload["avatar_url"] == "https://example.com/new-avatar.jpg"


@pytest.mark.asyncio
async def test_handle_wechat_callback_blocks_new_user_when_public_registration_disabled(monkeypatch):
    monkeypatch.setenv("ALLOW_PUBLIC_REGISTRATION", "false")
    monkeypatch.setattr(
        wechat_auth_service,
        "_exchange_code_for_tokens",
        AsyncMock(
            return_value=WeChatOAuthTokens(
                access_token="wx-token",
                openid="openid-3",
                unionid=None,
            )
        ),
    )
    monkeypatch.setattr(
        wechat_auth_service,
        "_fetch_user_info",
        AsyncMock(
            return_value=WeChatUserInfo(
                openid="openid-3",
                unionid=None,
                nickname="Blocked WeChat User",
                headimgurl=None,
            )
        ),
    )
    monkeypatch.setattr(
        wechat_auth_service.UserRepository,
        "get_user_by_wechat_identity",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        wechat_auth_service.UserRepository,
        "create_wechat_user",
        AsyncMock(),
    )

    with pytest.raises(wechat_auth_service.HTTPException) as exc_info:
        await handle_wechat_callback(WeChatCallbackRequest(code="auth-code", state=None))

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Public registration is disabled"
    wechat_auth_service.UserRepository.create_wechat_user.assert_not_awaited()
