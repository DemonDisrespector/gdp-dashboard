interface Props {
  label: string;
  value: string | number;
  sub?: string;
  color?: "default" | "green" | "red" | "blue";
}

const COLOR_MAP = {
  default: "text-gray-900",
  green:   "text-green-600",
  red:     "text-red-600",
  blue:    "text-brand-600",
};

export default function StatCard({ label, value, sub, color = "default" }: Props) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
      <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">{label}</p>
      <p className={`text-3xl font-bold ${COLOR_MAP[color]}`}>{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  );
}
