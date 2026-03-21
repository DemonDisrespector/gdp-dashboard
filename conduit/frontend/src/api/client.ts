import axios from "axios";

const api = axios.create({
  baseURL: "/api/v1",
  headers: { "Content-Type": "application/json" },
});

// ── Types ─────────────────────────────────────────────────────────────────────

export type TransferStatus =
  | "pending"
  | "fetching"
  | "transforming"
  | "delivering"
  | "completed"
  | "failed"
  | "retrying";

export interface Transfer {
  id: string;
  status: TransferStatus;
  source_system: string;
  destination_type: string;
  destination_name: string;
  resource_types: string[];
  resource_count: number;
  retry_count: number;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface TransferListResponse {
  items: Transfer[];
  total: number;
  page: number;
  page_size: number;
}

export interface CreateTransferRequest {
  source_patient_id: string;
  source_system?: string;
  destination_type: "api" | "fhir_write" | "browser";
  destination_name: string;
  destination_config?: Record<string, unknown>;
  resource_types?: string[];
}

export interface AuditLog {
  id: string;
  occurred_at: string;
  patient_token: string;
  transfer_id: string | null;
  event_type: string;
  actor_type: string;
  actor_id: string;
  source_system: string;
  destination_name: string | null;
  resource_types: string[];
  resource_count: number;
  outcome: string;
  detail: string | null;
}

export interface AuditListResponse {
  items: AuditLog[];
  total: number;
  page: number;
  page_size: number;
}

// ── API calls ─────────────────────────────────────────────────────────────────

export const transfersApi = {
  list: (params?: { status?: string; page?: number; page_size?: number }) =>
    api.get<TransferListResponse>("/transfers", { params }).then((r) => r.data),

  get: (id: string) =>
    api.get<Transfer>(`/transfers/${id}`).then((r) => r.data),

  create: (body: CreateTransferRequest) =>
    api.post<Transfer>("/transfers", body).then((r) => r.data),

  retry: (id: string) =>
    api.post<Transfer>(`/transfers/${id}/retry`).then((r) => r.data),
};

export const auditApi = {
  list: (params?: {
    event_type?: string;
    outcome?: string;
    transfer_id?: string;
    page?: number;
    page_size?: number;
  }) =>
    api.get<AuditListResponse>("/audit", { params }).then((r) => r.data),
};

export const healthApi = {
  check: () => api.get("/health").then((r) => r.data),
};

export default api;
