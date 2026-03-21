import { formatDistanceToNow } from "date-fns";
import clsx from "clsx";
import type { AuditLog } from "../api/client";

interface Props {
  logs: AuditLog[];
}

const OUTCOME_STYLES: Record<string, string> = {
  success: "bg-green-100 text-green-700",
  failure: "bg-red-100 text-red-700",
  partial: "bg-yellow-100 text-yellow-700",
};

export default function AuditTable({ logs }: Props) {
  if (logs.length === 0) {
    return (
      <div className="text-center py-16 text-gray-400">No audit logs found.</div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white shadow-sm">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50 text-xs uppercase text-gray-500 tracking-wider">
          <tr>
            <th className="px-4 py-3 text-left">Time</th>
            <th className="px-4 py-3 text-left">Event</th>
            <th className="px-4 py-3 text-left">Outcome</th>
            <th className="px-4 py-3 text-left">Patient Token</th>
            <th className="px-4 py-3 text-left">Destination</th>
            <th className="px-4 py-3 text-left">Resources</th>
            <th className="px-4 py-3 text-left">Detail</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {logs.map((log) => (
            <tr key={log.id} className="hover:bg-gray-50 transition-colors">
              <td className="px-4 py-3 text-gray-500 whitespace-nowrap">
                {formatDistanceToNow(new Date(log.occurred_at), { addSuffix: true })}
              </td>
              <td className="px-4 py-3 font-medium capitalize">
                {log.event_type.replace("_", " ")}
              </td>
              <td className="px-4 py-3">
                <span
                  className={clsx(
                    "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize",
                    OUTCOME_STYLES[log.outcome] ?? "bg-gray-100 text-gray-700"
                  )}
                >
                  {log.outcome}
                </span>
              </td>
              <td className="px-4 py-3 font-mono text-xs text-gray-500">
                {log.patient_token.slice(0, 12)}…
              </td>
              <td className="px-4 py-3 text-gray-600">{log.destination_name ?? "—"}</td>
              <td className="px-4 py-3 text-gray-600">
                {log.resource_count > 0 ? `${log.resource_count} (${log.resource_types.join(", ")})` : "—"}
              </td>
              <td className="px-4 py-3 text-gray-500 max-w-xs truncate">
                {log.detail ?? "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
