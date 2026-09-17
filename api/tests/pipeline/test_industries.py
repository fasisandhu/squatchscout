from app.pipeline.discover import build_overpass_query
from app.pipeline.industries import INDUSTRIES, list_industries


def test_sixteen_industries_with_unique_keys_and_selectors():
    assert len(INDUSTRIES) == 16
    assert all(ind.selectors for ind in INDUSTRIES.values())
    keys = [i["key"] for i in list_industries()]
    assert keys == sorted(keys) and len(set(keys)) == 16


def test_query_unions_nodes_and_ways_per_selector():
    q = build_overpass_query(INDUSTRIES["laundry"], 30.1, -97.9, 30.5, -97.5, 8)
    assert q.startswith("[out:json][timeout:25];")
    assert 'node["shop"="laundry"](30.1,-97.9,30.5,-97.5);' in q
    assert 'way["shop"="dry_cleaning"](30.1,-97.9,30.5,-97.5);' in q
    assert q.rstrip().endswith("out center tags 8;")
