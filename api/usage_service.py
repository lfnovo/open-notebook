import os
from datetime import datetime, timedelta, timezone
from typing import Literal

from open_notebook.domain.usage import UsageEvent

DEFAULT_STUDY_BUDGET_USD = 10.0


def _since_cutoff(period: Literal["month", "year"]) -> datetime:
    """Rolling window cutoff for the given period (30 / 365 days)."""
    now = datetime.now(timezone.utc)
    days = 365 if period == "year" else 30
    return now - timedelta(days=days)


async def get_usage_summary(period: Literal["month", "year"]) -> dict:
    """Aggregate LLM usage/cost for the given period, plus the configured budget."""
    since = _since_cutoff(period)
    summary = await UsageEvent.get_summary(since)
    budget_usd = float(os.getenv("STUDY_BUDGET_USD", DEFAULT_STUDY_BUDGET_USD))

    return {
        "total_cost_usd": summary["total_cost_usd"],
        "budget_usd": budget_usd,
        "by_task_type": summary["by_task_type"],
        "input_tokens": summary["input_tokens"],
        "output_tokens": summary["output_tokens"],
    }
