"""Fit a provider token margin from recorded usage, using only admissible measurements.

Usage fields can describe a single request or an aggregate, depending on the
adapter. Admit only explicitly identified single-context measurements of the
serialized input, from the same runtime and profile. Unknown billing aggregates
must not be used to loosen a margin. Bounding the observed points does not prove
accuracy for unseen models or input distributions; live margins remain separate.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import json
import math


@dataclass(frozen=True)
class Observation:
    run: str
    stage: str
    provider: str
    raw_tokens: int
    reported_tokens: int
    attempts: int
    tool_calls: int
    profile: str | None = None
    runtime_fingerprint: str | None = None
    measurement_kind: str = "unknown"
    representation: str = "unknown"

    @property
    def ratio(self):
        return self.reported_tokens / self.raw_tokens if self.raw_tokens else math.inf


def admissible(observation):
    """One prompt, one submission, no tools; anything else measures something else."""
    return (observation.attempts == 1 and observation.tool_calls == 0
            and observation.raw_tokens > 0 and observation.reported_tokens > 0
            and observation.measurement_kind == 'single_context'
            and observation.representation == 'serialized_input'
            and bool(observation.runtime_fingerprint)
            and observation.profile == 'research_synthesis')


def fit_margin(points, assumed_multiplier=None, reserve_tokens=2048):
    """Smallest multiplier/overhead pair that stays above every admissible point."""
    usable = [p for p in points if admissible(p)]
    if len({(p.provider,p.runtime_fingerprint,p.profile,p.representation) for p in usable})>1:
        raise ValueError('Calibration cannot mix providers, runtimes or request representations.')
    if not math.isfinite(reserve_tokens) or reserve_tokens<0:
        raise ValueError('Reserve must be finite and nonnegative.')
    if assumed_multiplier is not None and (not math.isfinite(float(assumed_multiplier)) or float(assumed_multiplier)<1):
        raise ValueError('Multiplier must be finite and at least one.')
    if not usable:
        raise ValueError('Kalibrasyon için uygun tek mesajlık ölçüm yok.')
    if assumed_multiplier is not None:
        multiplier = float(assumed_multiplier)
    elif len(usable) < 2:
        raise ValueError('Tek ölçümle eğim belirlenemez; assumed_multiplier açıkça verilmeli.')
    else:
        low = min(usable, key=lambda p: p.raw_tokens)
        high = max(usable, key=lambda p: p.raw_tokens)
        if high.raw_tokens == low.raw_tokens:
            raise ValueError('Ölçümler aynı boyutta; eğim belirlenemez.')
        slope = (high.reported_tokens - low.reported_tokens) / (high.raw_tokens - low.raw_tokens)
        multiplier = max(1.0, max(p.ratio for p in usable), slope)
    multiplier=math.ceil(multiplier*10000)/10000
    overhead = max(0.0, max(p.reported_tokens - multiplier * p.raw_tokens for p in usable))
    # The explicit reserve is independent of packet size. This fit only bounds
    # observed data; it does not assume that ratios fall on unseen larger packets.
    overhead = math.ceil(overhead) + int(reserve_tokens)
    return {'multiplier': round(multiplier, 4), 'overhead_tokens': int(overhead),
            'points': len(usable),
            'raw_range': [min(p.raw_tokens for p in usable), max(p.raw_tokens for p in usable)]}


def check_margin(margin, points):
    """Which admissible measurements the margin would have underestimated."""
    under = []
    worst = 0
    for point in points:
        if not admissible(point):
            continue
        estimate = margin['multiplier'] * point.raw_tokens + margin['overhead_tokens']
        if estimate < point.reported_tokens:
            shortfall = math.ceil(point.reported_tokens - estimate)
            worst = max(worst, shortfall)
            under.append({'run': point.run, 'stage': point.stage, 'raw_tokens': point.raw_tokens,
                          'reported_tokens': point.reported_tokens, 'estimate': int(estimate),
                          'shortfall': shortfall})
    return {'unsafe': bool(under), 'underestimated': under, 'worst_shortfall': worst}


def observations(runs, packet_tokens):
    """Every account-stage measurement on record, admissible or not; the caller filters."""
    result = []
    for run in runs:
        for stage in run['stages']:
            usage = stage.get('usage') or {}
            # Older CLI receipts could report only the last continuation as one
            # observation. A count alone is not evidence of a single context.
            single = (usage.get('context_observations_complete') is True
                      and type(usage.get('context_observations')) is int
                      and usage['context_observations'] == 1
                      and type(usage.get('cli_num_turns')) is int
                      and usage['cli_num_turns'] == 1
                      and stage.get('status') == 'completed')
            reported = usage.get('first_context_tokens') if single else usage.get('prompt_tokens')
            if not reported or stage['mode'] != 'account':
                continue
            raw = packet_tokens(run['id'], stage['id'])
            if raw is None:
                continue
            execution = usage.get('execution') or {}
            result.append(Observation(run=run['id'], stage=stage['id'], provider=stage['provider'],
                                      raw_tokens=raw, reported_tokens=int(reported),
                                      attempts=int(stage.get('attempts') or 0),
                                      tool_calls=len(execution.get('tool_calls') or []),
                                      profile=stage.get('account_profile','research_synthesis'),
                                      runtime_fingerprint=(stage.get('input_budget',{}).get('token_margin',{}).get('calibration_fingerprint')),
                                      measurement_kind='single_context' if single else 'unknown',
                                      representation='serialized_input'))
    return result


def report(points):
    """Per-provider fit and a verdict on the margin currently configured."""
    groups = {}
    for point in points:
        groups.setdefault(point.provider, []).append(point)
    return {provider: {'admissible': [asdict(p) for p in items if admissible(p)],
                       'rejected': [asdict(p) for p in items if not admissible(p)]}
            for provider, items in sorted(groups.items())}
