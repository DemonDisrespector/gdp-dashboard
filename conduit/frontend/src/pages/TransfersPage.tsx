import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import { transfersApi, type TransferStatus } from "../api/client";
import TransferTable from "../components/TransferTable";
import StatCard from "../components/StatCard";

const STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: "", label: "All" },
  { value: "pending", label: "Pending" },
  { value: "fetching", label: "Fetching" },
  { value: "transforming", label: "Transforming" },
  { value: "delivering", label: "Delivering" },
  { value: "completed", label: "Completed" },
  { value: "failed", label: "Failed" },
];

export default function TransfersPage() {
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [page, setPage] = useState(1);

  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ["transfers", statusFilter, page],
    queryFn: () =>
      transfersApi.list({
        status: statusFilter || undefined,
        page,
        page_size: 20,
      }),
    refetchInterval: 10_000,
  });

  // Summary stats from current page
  const items = data?.items ?? [];
  const completed = items.filter((t) => t.status === "completed").length;
  const failed = items.filter((t) => t.status === "failed").length;
  const inFlight = items.filter((t) =>
    ["fetching", "transforming", "delivering", "retrying"].includes(t.status)
  ).length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Transfers</h1>
        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="flex items-center gap-2 text-sm text-brand-600 hover:text-brand-700 disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${isFetching ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard label="Total (page)" value={data?.total ?? "—"} />
        <StatCard label="Completed" value={completed} color="green" />
        <StatCard label="In flight" value={inFlight} color="blue" />
        <StatCard label="Failed" value={failed} color="red" />
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <label className="text-sm font-medium text-gray-700">Status:</label>
        <div className="flex gap-2 flex-wrap">
          {STATUS_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => { setStatusFilter(opt.value); setPage(1); }}
              className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
                statusFilter === opt.value
                  ? "bg-brand-600 text-white border-brand-600"
                  : "bg-white text-gray-600 border-gray-300 hover:border-brand-400"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="text-center py-16 text-gray-400">Loading…</div>
      ) : (
        <TransferTable transfers={items} />
      )}

      {/* Pagination */}
      {data && data.total > 20 && (
        <div className="flex items-center justify-between text-sm text-gray-600">
          <span>
            Page {data.page} of {Math.ceil(data.total / data.page_size)}
          </span>
          <div className="flex gap-2">
            <button
              disabled={page === 1}
              onClick={() => setPage((p) => p - 1)}
              className="px-3 py-1 border rounded disabled:opacity-40 hover:bg-gray-50"
            >
              Previous
            </button>
            <button
              disabled={page * 20 >= data.total}
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
