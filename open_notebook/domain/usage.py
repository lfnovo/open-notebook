from datetime import datetime
from typing import Any, ClassVar, Dict

from loguru import logger

from open_notebook.database.repository import repo_query
from open_notebook.domain.base import ObjectModel


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
                "FROM usage_event WHERE created >= $since;",
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
