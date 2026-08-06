"""RDLens 嵌入式作用域 API 屏蔽矩阵（SPK-03）。

REQ-SCOPE-03 / REQ-AUTH-03 / REQ-DIS-01 / REQ-DIS-02 的 Fork 侧边界：
嵌入式模式下浏览器只允许访问固定 Notebook 及其研究产物 CRUD 与来源只读
API；全局 Notebook、认证、Provider/凭据、模型、系统设置、原生 AI、
媒体、直接上传/URL 来源一律 403。默认关闭（RD_EMBEDDED_MODE 未启用）
时完全透传，保持上游行为。

说明：本中间件是应用层防线；网络层隔离（浏览器只能访问 Research
Gateway）由 SPK-01 部署探针与 REQ-DEP-02 覆盖。
"""

from fastapi.responses import JSONResponse

from open_notebook import config

# 全局/管理/系统/AI/媒体表面（嵌入式模式下整体屏蔽）
_BLOCKED_PREFIXES = (
    "/api/auth",
    "/api/chat",
    "/api/search",
    "/api/source-chat",
    "/api/embed",
    "/api/rebuild",
    "/api/credentials",
    "/api/providers",
    "/api/models",
    "/api/config",
    "/api/settings",
    "/api/podcasts",
    "/api/episode-profiles",
    "/api/speaker-profiles",
    "/api/languages",
)


def is_blocked(method: str, path: str) -> bool:
    """嵌入式作用域屏蔽矩阵；非嵌入式模式一律放行。"""
    if not config.RD_EMBEDDED_MODE:
        return False

    path = path.split("?")[0]

    if any(path.startswith(p) for p in _BLOCKED_PREFIXES):
        return True

    if path.startswith("/api/notebooks"):
        # 客户端不能获取或切换 Notebook ID（REQ-AUTH-03）：
        # 仅允许读取固定 notebook_id，列表/创建/改写/删除全部屏蔽。
        notebook_id = path[len("/api/notebooks/"):]
        return not (
            method == "GET"
            and notebook_id
            and "/" not in notebook_id
            and notebook_id == config.RD_EMBEDDED_NOTEBOOK_ID
        )

    if path == "/api/recently-viewed":
        return True

    # 禁止用户直接上传文件或添加 URL/YouTube 来源（REQ-SCOPE-03）
    if method == "POST" and path.startswith("/api/sources"):
        return True

    return False


class EmbeddedScopeMiddleware:
    """嵌入式模式下对屏蔽路径返回 403；默认透传。"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not is_blocked(
            scope.get("method", ""), scope.get("path", "")
        ):
            return await self.app(scope, receive, send)
        response = JSONResponse(
            status_code=403,
            content={"detail": "blocked by RDLens embedded scope"},
        )
        return await response(scope, receive, send)
