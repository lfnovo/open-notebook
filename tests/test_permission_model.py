from fastapi import HTTPException
from fastapi.routing import APIRoute
import pytest

from api.auth import CurrentUser, require_admin
from api.main import app


def _route(path: str, method: str) -> APIRoute:
    for route in app.routes:
        if isinstance(route, APIRoute) and route.path == path and method in route.methods:
            return route
    raise AssertionError(f"Route {method} {path} not found")


def _dependency_calls(route: APIRoute) -> set[object]:
    return {dependency.call for dependency in route.dependant.dependencies}


@pytest.mark.asyncio
async def test_require_admin_rejects_regular_user():
    user = CurrentUser(id="app_user:regular", username="regular", role="user")

    with pytest.raises(HTTPException) as exc:
        await require_admin(user)

    assert exc.value.status_code == 403
    assert exc.value.detail == "Admin privileges required"


@pytest.mark.asyncio
async def test_require_admin_allows_system_admin():
    admin = CurrentUser(id="app_user:admin", username="admin", role="admin")

    result = await require_admin(admin)

    assert result is admin


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/api/models"),
        ("DELETE", "/api/models/{model_id}"),
        ("POST", "/api/models/{model_id}/test"),
        ("PUT", "/api/models/defaults"),
        ("GET", "/api/models/discover/{provider}"),
        ("POST", "/api/models/sync/{provider}"),
        ("POST", "/api/models/sync"),
        ("POST", "/api/models/auto-assign"),
        ("POST", "/api/credentials"),
        ("PUT", "/api/credentials/{credential_id}"),
        ("DELETE", "/api/credentials/{credential_id}"),
        ("POST", "/api/credentials/{credential_id}/test"),
        ("POST", "/api/credentials/{credential_id}/discover"),
        ("POST", "/api/credentials/{credential_id}/register-models"),
        ("POST", "/api/credentials/migrate-from-provider-config"),
        ("POST", "/api/credentials/migrate-from-env"),
        ("POST", "/api/transformations"),
        ("PUT", "/api/transformations/default-prompt"),
        ("PUT", "/api/transformations/{transformation_id}"),
        ("DELETE", "/api/transformations/{transformation_id}"),
        ("PUT", "/api/settings"),
    ],
)
def test_system_management_write_routes_require_admin(method: str, path: str):
    route = _route(path, method)

    assert require_admin in _dependency_calls(route)
