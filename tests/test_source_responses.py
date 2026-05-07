from api.services.source_responses import source_list_response_from_row


def test_source_list_response_includes_public_metrics():
    response = source_list_response_from_row(
        {
            "id": "source:example",
            "title": "Example source",
            "topics": [],
            "asset": None,
            "embedded": False,
            "kg_extracted": False,
            "insights_count": 2,
            "reference_count": 3,
            "view_count": 7,
            "created": "2026-04-30T00:00:00Z",
            "updated": "2026-04-30T00:00:00Z",
            "owner_id": "app_user:owner",
            "creator_username": "owner-login",
            "visibility": "public",
        }
    )

    assert response.reference_count == 3
    assert response.view_count == 7
    assert response.creator_username == "owner-login"
