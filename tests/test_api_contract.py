from api.main import app


def _schema_ref_for(path: str, method: str, status: str = "200") -> str:
    response = app.openapi()["paths"][path][method]["responses"][status]
    schema = response["content"]["application/json"]["schema"]
    if "items" in schema:
        return schema["items"]["$ref"]
    return schema["$ref"]


def test_notebooks_list_response_contract():
    assert (
        _schema_ref_for("/api/notebooks", "get")
        == "#/components/schemas/NotebookResponse"
    )


def test_sources_list_response_contract():
    assert (
        _schema_ref_for("/api/sources", "get")
        == "#/components/schemas/SourceListResponse"
    )


def test_sources_list_response_includes_reference_count():
    schema = app.openapi()["components"]["schemas"]["SourceListResponse"]

    assert "reference_count" in schema["properties"]
    assert "creator_username" in schema["properties"]


def test_public_resource_responses_include_ranking_metrics():
    schemas = app.openapi()["components"]["schemas"]

    assert "view_count" in schemas["SourceListResponse"]["properties"]
    assert "view_count" in schemas["SourceResponse"]["properties"]
    assert "view_count" in schemas["NotebookResponse"]["properties"]
    assert "reference_count" in schemas["NotebookResponse"]["properties"]


def test_source_detail_response_contract():
    assert (
        _schema_ref_for("/api/sources/{source_id}", "get")
        == "#/components/schemas/SourceResponse"
    )


def test_source_create_response_contract():
    assert _schema_ref_for("/api/sources", "post") == "#/components/schemas/SourceResponse"


def test_source_status_response_contract():
    assert (
        _schema_ref_for("/api/sources/{source_id}/status", "get")
        == "#/components/schemas/SourceStatusResponse"
    )


def test_embedding_response_contract():
    assert _schema_ref_for("/api/embed", "post") == "#/components/schemas/EmbedResponse"


def test_command_submit_response_contract():
    assert (
        _schema_ref_for("/api/commands/jobs", "post")
        == "#/components/schemas/CommandJobResponse"
    )


def test_command_status_response_contract():
    assert (
        _schema_ref_for("/api/commands/jobs/{job_id}", "get")
        == "#/components/schemas/CommandJobStatusResponse"
    )


def test_auth_status_response_contract():
    assert (
        _schema_ref_for("/api/auth/status", "get")
        == "#/components/schemas/AuthStatusResponse"
    )


def test_auth_login_response_contract():
    assert (
        _schema_ref_for("/api/auth/login", "post")
        == "#/components/schemas/LoginResponse"
    )
