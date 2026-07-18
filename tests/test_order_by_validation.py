"""
Regression tests for ObjectModel._validate_order_by() and its use by
Credential.get_all() (open_notebook/domain/credential.py), which builds its
own query instead of delegating to the base get_all() and previously
interpolated order_by into the SurrealQL unvalidated.
"""

import pytest

from open_notebook.domain.base import ObjectModel
from open_notebook.domain.credential import Credential
from open_notebook.exceptions import InvalidInputError


class TestValidateOrderBy:
    @pytest.mark.parametrize(
        "clause,expected",
        [
            ("provider", "provider"),
            ("provider, created", "provider, created"),
            ("created DESC", "created desc"),
            ("provider asc, created desc", "provider asc, created desc"),
        ],
    )
    def test_accepts_and_normalizes_valid_clauses(self, clause, expected):
        assert ObjectModel._validate_order_by(clause) == expected

    @pytest.mark.parametrize(
        "clause",
        [
            "field; DROP TABLE credential",
            "provider, created; REMOVE TABLE credential",
            "provider) FETCH (SELECT * FROM credential",
            "created LIMIT 1",
            "provider desc extra",
            "",
        ],
    )
    def test_rejects_injection_and_malformed_clauses(self, clause):
        with pytest.raises(InvalidInputError):
            ObjectModel._validate_order_by(clause)


class TestCredentialGetAllRejectsInjection:
    @pytest.mark.asyncio
    async def test_injection_in_order_by_raises_before_querying(self):
        # Must raise on validation - reaching the database with this string
        # (the pre-fix behavior) would execute the injected statement.
        with pytest.raises(InvalidInputError):
            await Credential.get_all(order_by="provider; DROP TABLE credential")
