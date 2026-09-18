const raw = (import.meta.env.VITE_API_URL as string | undefined) ?? "";
/** API origin. Empty string → same-origin (Vite dev proxy or a reverse proxy). Never throws at import. */
export const API_BASE = raw.replace(/\/+$/, "");
export const APP_NAME = "SquatchScout";
export const OSM_ATTRIBUTION = "© OpenStreetMap contributors";
