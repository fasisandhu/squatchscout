from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.deps import SessionDep
from app.models import Search
from app.pipeline.industries import INDUSTRIES
from app.pipeline.score import FACTORS, WEIGHT_PRESETS
from app.routers.searches import leads_for, not_found
from app.services.export import to_csv, to_hubspot_csv

router = APIRouter(prefix="/api/searches")

# UTF-8 byte-order mark, prefixed onto the generic (Excel-facing) CSV only — see the comment
# at its use below.
BOM = chr(0xFEFF)


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
    override = parse_weights(weights)
    # Labelling and recomputation are independent: the attribution line/column must always name
    # the weights actually behind the score column. With no override, that's the search's own
    # preset (not an empty dict) and the stored per-lead score/tier are used as-is; with an
    # override, both the label and the score column reflect it.
    effective = override or WEIGHT_PRESETS.get(search.weight_preset, WEIGHT_PRESETS["balanced"])
    label = (
        INDUSTRIES[search.industry_key].label
        if search.industry_key in INDUSTRIES
        else search.industry_key
    )
    recompute = override is not None
    body = (
        to_hubspot_csv(leads, effective, label, recompute=recompute)
        if format == "hubspot"
        else to_csv(leads, effective, recompute=recompute)
    )
    fname = f"squatchscout-{search_id[:8]}-{format}.csv"
    # The generic CSV is the artifact opened by double-clicking in Excel on Windows: without a
    # UTF-8 BOM, Excel falls back to the ANSI codepage and mangles the attribution's non-ASCII
    # "©"/"·" characters. The HubSpot CSV instead feeds an importer, where a leading BOM can
    # surface as a mangled first column header — so only the generic export gets the BOM.
    content = (BOM + body).encode("utf-8") if format == "csv" else body.encode("utf-8")
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )
