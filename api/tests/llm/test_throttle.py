from app.llm.throttle import TokenBucket


async def test_bucket_waits_when_request_or_token_budget_exhausted():
    now = [0.0]
    slept = []

    async def fake_sleep(s):
        slept.append(s)
        now[0] += s

    b = TokenBucket(rpm=2, tpm=1000, clock=lambda: now[0], sleep=fake_sleep)
    await b.acquire(300)
    await b.acquire(300)
    assert slept == []
    await b.acquire(300)  # third request within 60 s -> must wait for the window
    assert slept and now[0] >= 60.0
    await b.acquire(900)  # tokens: 300 used in the new window + 900 > 1000 -> wait again
    assert len(slept) >= 2
