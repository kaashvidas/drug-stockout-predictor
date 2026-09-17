export type Role = "facility" | "district" | "state" | "program" | "national";

export interface AuthState {
  token: string;
  role: Role;
  scope: string;
  displayName: string;
  username: string;
}

export interface DemoAccount {
  username: string;
  role: Role;
  scope: string;
  display_name: string;
  password: string;
}

export interface RiskAlert {
  facility_id: string;
  facility_name?: string;
  facility_type?: string;
  drug: string;
  district: string;
  state: string;
  current_days_of_cover: number;
  current_stock: number;
  trend_slope_56d: number;
  is_structural_decline: boolean;
  trust_score: number;
  risk_probability: number;
  risk_level: "low" | "medium" | "high" | "critical";
  drug_category?: string;
}

export interface Facility {
  facility_id: string;
  facility_name: string;
  facility_type: string;
  district: string;
  state: string;
  lat: number;
  lon: number;
  source: string;
}

export interface HeatmapRow {
  district: string;
  state: string;
  avg_risk: number;
  max_risk: number;
  n_critical: number;
  n_high: number;
  lat: number;
  lon: number;
}

export interface ExplainResponse {
  facility_id: string;
  drug: string;
  drug_category: string;
  dates: string[];
  consumption: number[];
  stock: number[];
  days_of_cover: number[];
  trend: number[];
  seasonal: number[];
  residual: number[];
  trend_slope_per_day: number;
  is_structural_decline: boolean;
  current_risk: RiskAlert | null;
  reconstructed_notice: string;
}

export interface CascadeResponse {
  facility_id: string;
  own_stress: number;
  propagated_stress: number;
  neighbor_propagation_paths: {
    to: string;
    facility_name?: string;
    travel_time_min: number;
    weight: number;
  }[];
}

export interface RedistributionCandidate {
  donor_facility_id: string;
  donor_facility_name?: string;
  donor_district?: string;
  recipient_facility_id: string;
  drug: string;
  score: number;
  travel_time_min: number;
  effective_travel_time_min: number;
  weather_flag: boolean;
  urgency: number;
  donor_shortfall_risk: number;
  donor_surplus_days_of_cover: number;
}

export interface AvailabilityRow {
  facility_id: string;
  facility_name: string;
  facility_type: string;
  district: string;
  state: string;
  current_days_of_cover: number;
  current_stock: number;
  risk_level: string;
  risk_probability: number;
  trust_score: number;
  travel_time_min?: number;
}

export interface TransferRequestRow {
  id: number;
  requesting_facility_id: string;
  requesting_facility_name?: string;
  requesting_district?: string;
  drug: string;
  suggested_donor_facility_id?: string;
  note?: string;
  requested_by: string;
  status: "pending" | "approved" | "dismissed";
  resolved_by?: string;
  resolved_donor_facility_id?: string;
  created_at: string;
}

export interface DrugRanking {
  drug: string;
  drug_category: string;
  avg_risk: number;
  max_risk: number;
  n_critical: number;
  n_high: number;
  n_facilities: number;
  n_structural_decline: number;
}

export interface FacilityRanking {
  facility_id: string;
  facility_name: string;
  facility_type: string;
  district: string;
  state: string;
  avg_risk: number;
  max_risk: number;
  n_critical: number;
  n_high: number;
  n_drugs: number;
  worst_drug: string;
}

export interface AuditLogRow {
  id: number;
  actor: string;
  role: string;
  action: string;
  detail: string;
  created_at: string;
}
