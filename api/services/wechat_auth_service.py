from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException
from loguru import logger

from api.auth import invalidate_has_users_cache
from api.jwt_auth import create_jwt_token
from api.models import LoginResponse, WeChatAuthorizeUrlResponse, WeChatCallbackRequest
from open_notebook.database.repositories.audit_log_repository import AuditLogRepository
from open_notebook.database.repositories.user_repository import UserRepository
from open_notebook.utils.encryption import get_secret_from_env

WECHAT_QRCONNECT_URL = "https://open.weixin.qq.com/connect/qrconnect"
WECHAT_ACCESS_TOKEN_URL = "https://api.weixin.qq.com/sns/oauth2/access_token"
WECHAT_USERINFO_URL = "https://api.weixin.qq.com/sns/userinfo"


@dataclass(frozen=True)
class WeChatOAuthTokens:
    access_token: str
    openid: str
    unionid: Optional[str] = None


@dataclass(frozen=True)
class WeChatUserInfo:
    openid: str
    unionid: Optional[str]
    nickname: Optional[str]
    headimgurl: Optional[str]


def _wechat_app_id() -> Optional[str]:
    return os.getenv("WECHAT_OPEN_APP_ID") or os.getenv("WECHAT_APP_ID")


def _wechat_app_secret() -> Optional[str]:
    return get_secret_from_env("WECHAT_OPEN_APP_SECRET") or get_secret_from_env(
        "WECHAT_APP_SECRET"
    )


def _wechat_redirect_uri() -> Optional[str]:
    return os.getenv("WECHAT_OPEN_REDIRECT_URI") or os.getenv("WECHAT_REDIRECT_URI")


def _allow_wechat_user_creation() -> bool:
    return os.getenv("ALLOW_PUBLIC_REGISTRATION", "false").lower() in {
        "true",
        "1",
        "yes",
        "on",
    }


async def build_wechat_authorize_url(state: str) -> WeChatAuthorizeUrlResponse:
    app_id = _wechat_app_id()
    redirect_uri = _wechat_redirect_uri()
    if not app_id or not redirect_uri:
        return WeChatAuthorizeUrlResponse(
            enabled=False,
            state=state,
            message="WeChat web login is not configured",
        )

    query = urlencode(
        {
            "appid": app_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "snsapi_login",
            "state": state,
        }
    )
    return WeChatAuthorizeUrlResponse(
        enabled=True,
        authorize_url=f"{WECHAT_QRCONNECT_URL}?{query}#wechat_redirect",
        state=state,
    )


async def _exchange_code_for_tokens(code: str) -> WeChatOAuthTokens:
    app_id = _wechat_app_id()
    app_secret = _wechat_app_secret()
    if not app_id or not app_secret:
        raise HTTPException(status_code=500, detail="WeChat login is not configured")

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            WECHAT_ACCESS_TOKEN_URL,
            params={
                "appid": app_id,
                "secret": app_secret,
                "code": code,
                "grant_type": "authorization_code",
            },
        )
        response.raise_for_status()
        data = response.json()

    if data.get("errcode"):
        logger.warning(f"WeChat access token exchange failed: {data}")
        raise HTTPException(status_code=401, detail="WeChat authorization failed")
    if not data.get("access_token") or not data.get("openid"):
        raise HTTPException(status_code=401, detail="WeChat authorization response is incomplete")

    return WeChatOAuthTokens(
        access_token=data["access_token"],
        openid=data["openid"],
        unionid=data.get("unionid"),
    )


async def _fetch_user_info(tokens: WeChatOAuthTokens) -> WeChatUserInfo:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            WECHAT_USERINFO_URL,
            params={
                "access_token": tokens.access_token,
                "openid": tokens.openid,
                "lang": "zh_CN",
            },
        )
        response.raise_for_status()
        data = response.json()

    if data.get("errcode"):
        logger.warning(f"WeChat userinfo fetch failed: {data}")
        raise HTTPException(status_code=401, detail="Unable to fetch WeChat user info")

    return WeChatUserInfo(
        openid=data.get("openid") or tokens.openid,
        unionid=data.get("unionid") or tokens.unionid,
        nickname=data.get("nickname"),
        headimgurl=data.get("headimgurl"),
    )


def _username_from_wechat(user_info: WeChatUserInfo) -> str:
    basis = user_info.unionid or user_info.openid
    normalized = re.sub(r"[^a-zA-Z0-9_]+", "_", basis).strip("_").lower()
    return f"wx_{normalized[:48]}"


async def handle_wechat_callback(request: WeChatCallbackRequest) -> LoginResponse:
    tokens = await _exchange_code_for_tokens(request.code)
    user_info = await _fetch_user_info(tokens)
    openid = user_info.openid or tokens.openid
    unionid = user_info.unionid or tokens.unionid

    user = await UserRepository.get_user_by_wechat_identity(
        unionid=unionid,
        openid=openid,
    )

    if user:
        user_id = str(user.get("id", ""))
        updates = {
            "last_login_at": datetime.now(timezone.utc),
            "login_provider": "wechat",
            "wechat_openid": openid,
            "wechat_unionid": unionid,
        }
        if user_info.nickname and not user.get("display_name"):
            updates["display_name"] = user_info.nickname
        if user_info.headimgurl:
            updates["avatar_url"] = user_info.headimgurl
        updated = await UserRepository.update_user(user_id, updates)
        user = updated[0] if updated else {**user, **updates}
    else:
        if not _allow_wechat_user_creation():
            raise HTTPException(status_code=403, detail="Public registration is disabled")

        user = await UserRepository.create_wechat_user(
            {
                "username": _username_from_wechat(user_info),
                "display_name": user_info.nickname or "WeChat User",
                "avatar_url": user_info.headimgurl,
                "wechat_openid": openid,
                "wechat_unionid": unionid,
            }
        )
        if not user:
            raise HTTPException(status_code=500, detail="Failed to create WeChat user")
        invalidate_has_users_cache()

    if user.get("status", "active") != "active":
        raise HTTPException(status_code=403, detail="Account is disabled")

    user_id = str(user.get("id", ""))
    username = user.get("username") or _username_from_wechat(user_info)
    token = create_jwt_token(username, user_id, user)
    try:
        await AuditLogRepository.create(
            action="auth.wechat.login.success",
            actor_id=user_id,
            actor_username=username,
            target_type="app_user",
            target_id=user_id,
            metadata={"wechat_unionid_present": bool(unionid)},
        )
    except Exception as audit_error:
        logger.warning(f"Failed to write WeChat login audit log: {audit_error}")

    return LoginResponse(
        success=True,
        token=token,
        username=username,
        message="Login successful",
    )
