from app.pipeline.industries import Industry


def build_overpass_query(
    industry: Industry, s: float, w: float, n: float, e: float, limit: int
) -> str:
    bbox = f"({s},{w},{n},{e})"
    parts = []
    for key, value in industry.selectors:
        parts.append(f'node["{key}"="{value}"]{bbox};')
        parts.append(f'way["{key}"="{value}"]{bbox};')
    body = "\n  ".join(parts)
    return f"[out:json][timeout:25];\n(\n  {body}\n);\nout center tags {limit};"
