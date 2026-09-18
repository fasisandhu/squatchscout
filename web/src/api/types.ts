export type Factor = "reachability" | "establishment" | "digital_gap" | "buybox" | "succession";
export type Weights = Record<Factor, number>;
export type Tier = "A" | "B" | "C" | "D";

export interface Address { street: string | null; housenumber: string | null; city: string | null;
  state: string | null; postcode: string | null; country: string | null; }
export interface Contact { kind: "email" | "phone" | "social"; value: string; source: string; verification_status: string; }
export interface Signal { key: string; value: string; source: "osm" | "regex" | "llm"; confidence: number; }
export interface FactorScore { factor: Factor; points: number; max_points: number; reasons: string[]; }

export interface Lead {
  id: string; name: string; display_name: string; address: Address; address_source: string;
  lat: number; lon: number; website: string | null; domain: string | null; is_chain_suspected: boolean;
  enrichment_status: string; llm_status: string; score: number | null; tier: Tier | null;
  contacts: Contact[]; signals: Signal[]; factor_scores: FactorScore[];
}

export interface SearchRow { id: string; industry_key: string; location_query: string; geocoded_name: string | null;
  weight_preset: string; status: "running" | "done" | "failed"; lead_count: number; llm_pending: number;
  error: string | null; created_at: string; finished_at: string | null; }

export interface Industry { key: string; label: string; }
export interface IndustriesResponse { industries: Industry[]; presets: Record<string, Weights>; }
export interface SearchCreate { industry_key: string; location: string; limit: number; weight_preset?: string; nl_query?: string | null; }
export interface IntentResult { industry_key: string | null; location: string | null; limit: number | null;
  weight_preset: string; rationale: string; }

export interface StatusEvent { stage: string; message: string; count: number; }
export interface LeadUpdatedEvent { lead_id: string; display_name: string; address: Address; address_source: string;
  signals: Signal[]; factor_scores: FactorScore[]; score: number | null; tier: Tier | null; llm_status: string; }
export interface DoneEvent { lead_count: number; llm_pending: number; }
export interface ErrorEvent { message: string; }
export interface HealthResponse { status: string; db: string; llm_enabled: boolean; version: string; }
