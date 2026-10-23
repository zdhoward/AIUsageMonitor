"""API-equivalent cost estimates from T3's downloaded price table (LiteLLM format).

These are estimates of what the tokens would cost at public API rates. They are not
what a Claude/ChatGPT subscription bills.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from . import log


class Pricing:
    def __init__(self, rates: dict[str, dict] | None = None):
        self._rates = rates or {}
        self._memo: dict[str, dict | None] = {}

    @classmethod
    def load(cls, path: Path) -> "Pricing":
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
            return cls(doc.get("document", doc))
        except (OSError, ValueError) as e:
            log.warn("pricing.unavailable", path=path, err=type(e).__name__)
            return cls()

    def _lookup(self, model: str) -> dict | None:
        if model in self._memo:
            return self._memo[model]
        candidates = [model, model.split("/")[-1], re.sub(r"-\d{8}$", "", model.split("/")[-1])]
        found = None
        for c in candidates:
            r = self._rates.get(c)
            if isinstance(r, dict) and "input_cost_per_token" in r:
                found = r
                break
        self._memo[model] = found
        return found

    def cost(self, model: str, uncached_in: int, cache_read: int, cache_write: int, out: int) -> float | None:
        """USD estimate, or None when the model has no known price."""
        r = self._lookup(model)
        if r is None:
            return None
        inp = r.get("input_cost_per_token")
        if inp is None:
            inp = 0.0
        cache_read_rate = r.get("cache_read_input_token_cost")
        if cache_read_rate is None:
            cache_read_rate = inp
        cache_write_rate = r.get("cache_creation_input_token_cost")
        if cache_write_rate is None:
            cache_write_rate = inp
        output_rate = r.get("output_cost_per_token")
        if output_rate is None:
            output_rate = 0.0
        return (
            uncached_in * inp
            + cache_read * cache_read_rate
            + cache_write * cache_write_rate
            + out * output_rate
        )
