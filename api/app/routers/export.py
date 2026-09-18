from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.deps import SessionDep
from app.models import Search
from app.pipeline.industries import INDUSTRIES
from app.pipeline.score import FACTORS
from app.routers.searches import leads_for, not_found
from app.services.export import to_csv, to_hubspot_csv

router = APIRouter(prefix="/api/searches")


def parse_weights(raw: str | None) -> dict[str, float] | None:
    if not raw:
        return None
    parts = raw.split(",")
    if len(parts) != 5:
        raise HTTPException(
            status_code=400,
            detail={"code": "bad_weights", "message": "weights must be 5 comma-separated numbers"},
        )
    try:
        return dict(zip(FACTORS, (float(p) for p in parts), strict=True))
    except ValueError as e:
        raise HTTPException(
            status_code=400, detail={"code": "bad_weights", "message": "weights must be numeric"}
        ) from e


@router.get("/{search_id}/export")
def export(
    search_id: str,
    s: SessionDep,
    format: str = Query("csv", pattern="^(csv|hubspot)$"),
    ids: str | None = None,
    weights: str | None = None,
) -> Response:
    search = s.get(Search, search_id)
    if not search:
        raise not_found("Search")
    leads = leads_for(s, search_id)
    if ids:
        wanted = set(ids.split(","))
        leads = [x for x in leads if x.id in wanted]
    w = parse_weights(weights)
    label = (
        INDUSTRIES[search.industry_key].label
        if search.industry_key in INDUSTRIES
        else search.industry_key
    )
    body = to_hubspot_csv(leads, w, label) if format == "hubspot" else to_csv(leads, w)
    fname = f"squatchscout-{search_id[:8]}-{format}.csv"
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )
