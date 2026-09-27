"""Explicit local admission estimates, not claims of provider tokenizer accuracy."""
from dataclasses import dataclass
from functools import lru_cache
import json
import math
import re

MARKDOWN_TRANSPORT = 'research-markdown-v1'


def account_input(system, prompt, transport):
    if transport == MARKDOWN_TRANSPORT:
        return system + '\n\n' + prompt
    return json.dumps({'conversation': [{'role': 'system', 'content': system},
                                       {'role': 'user', 'content': prompt}]}, ensure_ascii=False)


@dataclass(frozen=True)
class Margin:
    multiplier: float = 1.25
    overhead_tokens: int = 4096
    basis: str = 'Uncalibrated conservative fallback; provider usage may aggregate multiple model calls.'
    calibration_fingerprint: str | None = None

    def __post_init__(self):
        if not math.isfinite(self.multiplier) or self.multiplier < 1 or self.overhead_tokens < 0:
            raise ValueError('Token margin must be finite, >= 1, with nonnegative overhead.')
        if self.calibration_fingerprint is not None and not re.fullmatch('[a-f0-9]{64}', self.calibration_fingerprint):
            raise ValueError('Calibration requires a SHA-256 runtime fingerprint.')


class TokenBudget:
    def __init__(self, counter, margins=None, output_tokens_by_round=None):
        self.counter = lru_cache(maxsize=12)(counter)
        self.margins = {provider: Margin(**value) for provider, value in (margins or {}).items()}
        self.output_tokens_by_round = {1: 20000, 2: 24000, 3: 32000, **{
            int(k): int(v) for k, v in (output_tokens_by_round or {}).items()}}
        if any(v <= 0 for v in self.output_tokens_by_round.values()):
            raise ValueError('Forecast report budgets must be positive.')

    def measure(self, prompt, provider, limit, system, transport):
        raw = self.counter(prompt)
        cli_raw = self.counter(account_input(system, prompt, transport))
        return self.from_counts(raw, cli_raw, provider, limit, transport)

    def from_counts(self, raw, cli_raw, provider, limit, transport):
        margin = self.margins.get(provider, Margin())
        estimated = math.ceil(cli_raw * margin.multiplier) + margin.overhead_tokens
        return {'raw_tokens': raw, 'transport_raw_tokens': cli_raw,
                'counted_tokens': estimated, 'estimated_tokens': estimated,
                'tokenizer': 'o200k_base', 'token_margin': {
                    'multiplier': margin.multiplier, 'overhead_tokens': margin.overhead_tokens,
                    'basis': margin.basis, 'calibration_fingerprint': margin.calibration_fingerprint}, 'transport_format': transport,
                'automatic_input_limit': limit,
                'effective_raw_limit': max(0, math.floor((limit - margin.overhead_tokens) / margin.multiplier)),
                'remaining_input_tokens': limit - estimated,
                'utilization': estimated / limit, 'fits': estimated <= limit}
