import { useParams, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, RefreshCw, RotateCcw } from "lucide-react";
import { format } from "date-fns";
import { transfersApi, auditApi } from "../api/client";
import StatusBadge from "../components/StatusBadge";
import AuditTable from "../components/AuditTable";

export default function TransferDetailPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();

  const { data: transfer, isLoading } = useQuery({
    queryKey: ["transfer", id],
    queryFn: () => transfersApi.get(id!),
    refetchInterval: 5_000,
    enabled: !!id,
  });

  const { data: auditData } = useQuery({
    queryKey: ["audit", id],
    queryFn: () => auditApi.list({ transfer_id: id, page_size: 50 }),
    enabled: !!id,
  });

  const retryMutation = useMutation({
    mutationFn: () => transfersApi.retry(id!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["transfer", id] });
      qc.invalidateQueries({ queryKey: ["transfers"] });
    },
  });

  if (isLoading || !transfer) {
    return <div className="text-center py-16 text-gray-400">Loading…</div>;
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex items-center gap-3">
        <Link to="/" className="text-brand-600 hover:text-brand-700">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <h1 className="text-xl font-bold text-gray-900 font-mono">{transfer.id}</h1>
        <StatusBadge status={transfer.status} />
      </div>

      {/* Details card */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6 grid grid-cols-2 gap-4 text-sm">
        <Detail label="Source System" value={transfer.source_system} />
        <Detail label="Destination" value={`${transfer.destination_name} (${transfer.destination_type})`} />
        <Detail label="Resource Count" value={transfer.resource_count || "—"} />
        <Detail label="Retry Count" value={transfer.retry_count} />
        <Detail label="Created" value={format(new Date(transfer.created_at), "PPpp")} />
        <Detail label="Updated" value={format(new Date(transfer.updated_at), "PPpp")} />
        <div className="col-span-2">
          <Detail label="Resource Types" value={transfer.resource_types.join(", ") || "—"} />
        </div>
        {transfer.error_message && (
          <div className="col-span-2">
            <p className="text-xs text-gray-500 font-medium mb-1">Error</p>
            <pre className="text-xs text-red-600 bg-red-50 rounded p-3 overflow-auto whitespace-pre-wrap">
              {transfer.error_message}
            </pre>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex gap-3">
        {transfer.status === "failed" && (
          <button
            onClick={() => retryMutation.mutate()}
            disabled={retryMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg text-sm font-medium hover:bg-brand-700 disabled:opacity-50"
          >
            <RotateCcw className="w-4 h-4" />
            Retry Transfer
          </button>
        )}
      </div>

      {/* Audit events */}
      <div>
        <h2 className="text-lg font-semibold text-gray-800 mb-3">Audit Events</h2>
        <AuditTable logs={auditData?.items ?? []} />
      </div>
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <p className="text-xs text-gray-500 font-medium uppercase tracking-wide mb-0.5">{label}</p>
      <p className="text-gray-900">{value}</p>
    </div>
  );
}
