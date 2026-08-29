import os
from datetime import datetime, timedelta, timezone
from typing import Any, ClassVar, Dict

from loguru import logger

from open_notebook.database.repository import repo_query
from open_notebook.domain.base import ObjectModel

# Mirrors api/usage_service.py's STUDY_BUDGET_USD default - duplicated (not
# imported) because open_notebook/domain must not depend on api/ (layering:
# api -> open_notebook, never the reverse). Budget-aware fallback selection
# (open_notebook/ai/models.py) needs this from the domain layer.
STUDY_BUDGET_ENV_VAR = "STUDY_BUDGET_USD"
DEFAULT_STUDY_BUDGET_USD = 10.0


class UsageEvent(ObjectModel):
    """One LLM call's token usage/estimated cost.

    Written by the callback handler `provision_langchain_model()` attaches
    to every provisioned chat model (see open_notebook/ai/provision.py) -
    chat, transformations, podcasts and study tools all flow through that
    single choke point, so no per-call-site instrumentation is needed.
    """

    table_name: ClassVar[str] = "usage_event"

    provider: str
    model_name: str
    task_type: str
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0

    @classmethod
    async def get_summary(cls, since: datetime) -> Dict[str, Any]:
        """Aggregate usage/cost since a cutoff: totals, plus cost grouped by task_type.

        Two small SurrealQL aggregation queries (server-side math::sum /
        GROUP BY) rather than fetching every row and summing in Python -
        usage_event can grow unbounded, and this mirrors the GROUP BY shape
        already used by get_provider_model_count() in
        open_notebook/ai/model_discovery.py.

        Bug fixed here: the totals query previously had no GROUP clause, so
        SurrealDB evaluated math::sum() per-row against a scalar instead of
        aggregating the matched rows into an array first - it silently
        errored on any non-zero value ("Expected a array but found <float>"),
        the exception was swallowed below, and the totals stayed at 0 even
        though individual usage_event rows were recorded correctly. `GROUP
        ALL` collapses all matched rows into one group before math::sum()
        runs, which is what was actually intended. Verified against real
        local usage_event rows before/after this fix.
        """
        total_cost_usd = 0.0
        input_tokens = 0
        output_tokens = 0
        try:
            totals_result = await repo_query(
                "SELECT "
                "math::sum(estimated_cost_usd) AS total_cost_usd, "
                "math::sum(input_tokens) AS input_tokens, "
                "math::sum(output_tokens) AS output_tokens "
                "FROM usage_event WHERE created >= $since GROUP ALL;",
                {"since": since},
            )
            if totals_result:
                row = totals_result[0]
                total_cost_usd = float(row.get("total_cost_usd") or 0.0)
                input_tokens = int(row.get("input_tokens") or 0)
                output_tokens = int(row.get("output_tokens") or 0)
        except Exception as e:
            logger.error(f"Error aggregating usage totals: {e}")

        by_task_type: Dict[str, float] = {}
        try:
            grouped_result = await repo_query(
                "SELECT task_type, math::sum(estimated_cost_usd) AS cost "
                "FROM usage_event WHERE created >= $since GROUP BY task_type;",
                {"since": since},
            )
            for row in grouped_result:
                task_type = row.get("task_type")
                if task_type:
                    by_task_type[task_type] = float(row.get("cost") or 0.0)
        except Exception as e:
            logger.error(f"Error aggregating usage by task_type: {e}")

        return {
            "total_cost_usd": total_cost_usd,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "by_task_type": by_task_type,
        }

    @classmethod
    async def get_current_spend_usd(cls, window_days: int = 30) -> float:
        """Total estimated cost over the trailing `window_days`.

        Default of 30 days matches the rolling "month" window api/usage_service.py
        uses for the Cost Meter and STUDY_BUDGET_USD's implicit monthly semantics.
        Used by the budget-aware fallback cutoff in open_notebook/ai/models.py to
        decide whether a paid fallback model may still be added to a resolved
        chain.
        """
        since = datetime.now(timezone.utc) - timedelta(days=window_days)
        summary = await cls.get_summary(since)
        return summary["total_cost_usd"]

    @classmethod
    async def is_within_budget(cls, window_days: int = 30) -> bool:
        """Whether trailing spend is still under STUDY_BUDGET_USD (default $10).

        Best-effort: any failure reading spend is treated as "not within
        budget" (fail closed) so a broken budget check can never silently let
        paid-fallback spend run away - it can only ever be overly cautious
        and skip a paid fallback that would have been affordable.
        """
        try:
            budget = float(
                os.getenv(STUDY_BUDGET_ENV_VAR, str(DEFAULT_STUDY_BUDGET_USD))
            )
            spend = await cls.get_current_spend_usd(window_days=window_days)
            return spend < budget
        except Exception as e:
            logger.warning(f"Budget check failed, treating as over-budget: {e}")
            return False
