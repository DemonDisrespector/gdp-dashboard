import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { auditApi } from "../api/client";
import AuditTable from "../components/AuditTable";

const EVENT_TYPES = ["", "fhir_fetch", "transform", "deliver", "error", "access"];
const OUTCOMES = ["", "success", "failure", "partial"];

export default function AuditPage() {
  const [eventType, setEventType] = useState("");
  const [outcome, setOutcome] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ["audit-logs", eventType, outcome, page],
    queryFn: () =>
      auditApi.list({
        event_type: eventType || undefined,
        outcome: outcome || undefined,
        page,
        page_size: 25,
      }),
    refetchInterval: 30_000,
  });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Audit Log</h1>
      <p className="text-sm text-gray-500">
        De-identified transfer events. Patient identifiers are replaced with HMAC tokens. No PHI is stored.
      </p>

      {/* Filters */}
      <div className="flex gap-4 text-sm flex-wrap">
        <div className="flex items-center gap-2">
          <label className="font-medium text-gray-700">Event:</label>
          <select
            value={eventType}
            onChange={(e) => { setEventType(e.target.value); setPage(1); }}
            className="border border-gray-300 rounded px-2 py-1 text-sm"
          >
            {EVENT_TYPES.map((t) => (
              <option key={t} value={t}>{t || "All"}</option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-2">
          <label className="font-medium text-gray-700">Outcome:</label>
          <select
            value={outcome}
            onChange={(e) => { setOutcome(e.target.value); setPage(1); }}
            className="border border-gray-300 rounded px-2 py-1 text-sm"
          >
            {OUTCOMES.map((o) => (
              <option key={o} value={o}>{o || "All"}</option>
            ))}
          </select>
        </div>
        <span className="text-gray-400 self-center">
          {data ? `${data.total} total events` : ""}
        </span>
      </div>

      {isLoading ? (
        <div className="text-center py-16 text-gray-400">Loading…</div>
      ) : (
        <AuditTable logs={data?.items ?? []} />
      )}

      {data && data.total > 25 && (
        <div className="flex items-center justify-between text-sm text-gray-600">
          <span>Page {data.page} of {Math.ceil(data.total / data.page_size)}</span>
          <div className="flex gap-2">
            <button
              disabled={page === 1}
              onClick={() => setPage((p) => p - 1)}
              className="px-3 py-1 border rounded disabled:opacity-40 hover:bg-gray-50"
            >
              Previous
            </button>
            <button
              disabled={page * 25 >= data.total}
              onClick={() => setPage((p) => p + 1)}
              className="px-3 py-1 border rounded disabled:opacity-40 hover:bg-gray-50"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
