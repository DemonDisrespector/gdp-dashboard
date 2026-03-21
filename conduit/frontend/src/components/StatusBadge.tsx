import clsx from "clsx";
import type { TransferStatus } from "../api/client";

const STATUS_STYLES: Record<TransferStatus, string> = {
  pending:      "bg-gray-100 text-gray-700",
  fetching:     "bg-blue-100 text-blue-700",
  transforming: "bg-purple-100 text-purple-700",
  delivering:   "bg-yellow-100 text-yellow-700",
  completed:    "bg-green-100 text-green-700",
  failed:       "bg-red-100 text-red-700",
  retrying:     "bg-orange-100 text-orange-700",
};

interface Props {
  status: TransferStatus;
  className?: string;
}

export default function StatusBadge({ status, className }: Props) {
  return (
    <span
      className={clsx(
        "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize",
        STATUS_STYLES[status] ?? "bg-gray-100 text-gray-700",
        className
      )}
    >
      {status}
    </span>
  );
}
