import json
from types import SimpleNamespace

import groq
import httpx

from app.config import Settings
from app.llm.client import LLMPool
from app.llm.schemas import OPENER_SCHEMA


def rate_limit_error(retry_after="0"):
    req = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    return groq.RateLimitError(
        "rate limited",
        response=httpx.Response(429, headers={"retry-after": retry_after}, request=req),
        body=None,
    )


class FakeGroq:
    """Scripted responses per model: list of callables returning content or raising."""

    def __init__(self, script: dict[str, list]):
        self.script, self.calls = script, []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    async def _create(self, *, model, messages, response_format, max_completion_tokens):
        self.calls.append(model)
        step = self.script[model].pop(0)
        if isinstance(step, Exception):
            raise step
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=step))])


def settings(**over):
    return Settings(groq_api_key="k", groq_models=["m1", "m2"], llm_daily_soft_cap=3, **over)


async def fast_sleep(_s):
    return None


async def test_disabled_without_key():
    pool = LLMPool(Settings(groq_api_key=None), groq_client=FakeGroq({}))
    assert not pool.enabled
    assert await pool.complete_json(
        schema_name="o", schema=OPENER_SCHEMA, system="s", user="u"
    ) == (None, "disabled")


async def test_ok_parses_json():
    fake = FakeGroq({"m1": [json.dumps({"opener": "hi"})]})
    pool = LLMPool(settings(), groq_client=fake, sleep=fast_sleep)
    data, status = await pool.complete_json(
        schema_name="o", schema=OPENER_SCHEMA, system="s", user="u"
    )
    assert status == "ok" and data == {"opener": "hi"} and fake.calls == ["m1"]


async def test_429_retries_once_then_falls_to_next_model_then_skips():
    fake = FakeGroq(
        {"m1": [rate_limit_error(), rate_limit_error()], "m2": [json.dumps({"opener": "from m2"})]}
    )
    pool = LLMPool(settings(), groq_client=fake, sleep=fast_sleep)
    data, status = await pool.complete_json(
        schema_name="o", schema=OPENER_SCHEMA, system="s", user="u"
    )
    assert status == "ok" and data["opener"] == "from m2" and fake.calls == ["m1", "m1", "m2"]

    fake2 = FakeGroq(
        {
            "m1": [rate_limit_error(), rate_limit_error()],
            "m2": [rate_limit_error(), rate_limit_error()],
        }
    )
    pool2 = LLMPool(settings(), groq_client=fake2, sleep=fast_sleep)
    assert await pool2.complete_json(
        schema_name="o", schema=OPENER_SCHEMA, system="s", user="u"
    ) == (None, "skipped_rate_limit")


async def test_daily_soft_cap_and_bad_json():
    fake = FakeGroq(
        {
            "m1": [
                "not json",
                json.dumps({"opener": "a"}),
                json.dumps({"opener": "b"}),
                json.dumps({"opener": "c"}),
            ]
        }
    )
    pool = LLMPool(settings(), groq_client=fake, sleep=fast_sleep)
    assert (await pool.complete_json(schema_name="o", schema=OPENER_SCHEMA, system="s", user="u"))[
        1
    ] == "error"
    for _ in range(2):
        assert (
            await pool.complete_json(schema_name="o", schema=OPENER_SCHEMA, system="s", user="u")
        )[1] == "ok"
    assert (await pool.complete_json(schema_name="o", schema=OPENER_SCHEMA, system="s", user="u"))[
        1
    ] == "skipped_budget"
