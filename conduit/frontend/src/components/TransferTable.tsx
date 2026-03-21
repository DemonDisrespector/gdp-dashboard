import { Link } from "react-router-dom";
import { formatDistanceToNow } from "date-fns";
import type { Transfer } from "../api/client";
import StatusBadge from "./StatusBadge";

interface Props {
  transfers: Transfer[];
}

export default function TransferTable({ transfers }: Props) {
  if (transfers.length === 0) {
    return (
      <div className="text-center py-16 text-gray-400">
        No transfers found.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white shadow-sm">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50 text-xs uppercase text-gray-500 tracking-wider">
          <tr>
            <th className="px-4 py-3 text-left">ID</th>
            <th className="px-4 py-3 text-left">Status</th>
            <th className="px-4 py-3 text-left">Source</th>
            <th className="px-4 py-3 text-left">Destination</th>
            <th className="px-4 py-3 text-left">Resources</th>
            <th className="px-4 py-3 text-left">Created</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {transfers.map((t) => (
            <tr key={t.id} className="hover:bg-gray-50 transition-colors">
              <td className="px-4 py-3 font-mono text-xs text-brand-600">
                <Link to={`/transfers/${t.id}`} className="hover:underline">
                  {t.id.slice(0, 8)}…
                </Link>
              </td>
              <td className="px-4 py-3">
                <StatusBadge status={t.status} />
              </td>
              <td className="px-4 py-3 text-gray-600">{t.source_system}</td>
              <td className="px-4 py-3">
                <span className="font-medium">{t.destination_name}</span>
                <span className="ml-1 text-xs text-gray-400">({t.destination_type})</span>
              </td>
              <td className="px-4 py-3 text-gray-600">
                {t.resource_count > 0 ? t.resource_count : "—"}
              </td>
              <td className="px-4 py-3 text-gray-500">
                {formatDistanceToNow(new Date(t.created_at), { addSuffix: true })}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
