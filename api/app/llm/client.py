import asyncio
import json
import logging
import time
from datetime import UTC, datetime
from typing import Literal

import groq

from app.config import Settings
from app.llm.throttle import TokenBucket

log = logging.getLogger(__name__)
LLMStatus = Literal["ok", "disabled", "skipped_rate_limit", "skipped_budget", "error"]
RPM, TPM, RETRY_CAP_S = 6, 7000, 20.0


class LLMPool:
    def __init__(
        self, settings: Settings, groq_client=None, clock=time.monotonic, sleep=asyncio.sleep
    ):
        self.settings, self.clock, self.sleep = settings, clock, sleep
        self.enabled = settings.llm_enabled
        self.models = list(settings.groq_models)
        self._client = groq_client or (
            groq.AsyncGroq(api_key=settings.groq_api_key) if self.enabled else None
        )
        self._buckets = {m: TokenBucket(RPM, TPM, clock, sleep) for m in self.models}
        self._day = datetime.now(UTC).date()
        self._used_today = 0

    def _budget_ok(self) -> bool:
        today = datetime.now(UTC).date()
        if today != self._day:
            self._day, self._used_today = today, 0
        return self._used_today < self.settings.llm_daily_soft_cap

    @staticmethod
    def _estimate_tokens(system: str, user: str, max_tokens: int) -> int:
        return (len(system) + len(user)) // 4 + max_tokens

    async def _call(
        self, model: str, system: str, user: str, schema_name: str, schema: dict, max_tokens: int
    ) -> str:
        resp = await self._client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {"name": schema_name, "strict": True, "schema": schema},
            },
            max_completion_tokens=max_tokens,
        )
        return resp.choices[0].message.content or ""

    async def complete_json(
        self,
        *,
        schema_name: str,
        schema: dict,
        system: str,
        user: str,
        max_tokens: int = 300,
    ) -> tuple[dict | None, LLMStatus]:
        if not self.enabled:
            return None, "disabled"
        if not self._budget_ok():
            return None, "skipped_budget"
        est = self._estimate_tokens(system, user, max_tokens)
        for model in self.models:
            for attempt in range(2):
                await self._buckets[model].acquire(est)
                try:
                    self._used_today += 1
                    content = await self._call(model, system, user, schema_name, schema, max_tokens)
                    return json.loads(content), "ok"
                except groq.RateLimitError as e:
                    if attempt == 0:
                        ra = (
                            e.response.headers.get("retry-after")
                            if e.response is not None
                            else None
                        )
                        try:
                            wait = min(float(ra), RETRY_CAP_S) if ra else 2.0
                        except ValueError:
                            wait = 2.0
                        await self.sleep(wait)
                        continue
                    log.warning("llm.rate_limited", extra={"model": model})
                    break  # next model
                except (json.JSONDecodeError, groq.APIError, KeyError, IndexError) as e:
                    log.warning("llm.error", extra={"model": model, "err": type(e).__name__})
                    return None, "error"
        return None, "skipped_rate_limit"
