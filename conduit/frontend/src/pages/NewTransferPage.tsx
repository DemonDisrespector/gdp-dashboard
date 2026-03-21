import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { transfersApi, type CreateTransferRequest } from "../api/client";

const DEFAULT_RESOURCES = [
  "Patient", "Coverage", "Condition", "Procedure",
  "ServiceRequest", "Practitioner", "DocumentReference",
  "AllergyIntolerance", "MedicationRequest",
];

export default function NewTransferPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [form, setForm] = useState<CreateTransferRequest>({
    source_patient_id: "",
    source_system: "modmed",
    destination_type: "api",
    destination_name: "",
    destination_config: {},
    resource_types: DEFAULT_RESOURCES,
  });
  const [destConfigRaw, setDestConfigRaw] = useState("{}");
  const [configError, setConfigError] = useState("");

  const mutation = useMutation({
    mutationFn: (body: CreateTransferRequest) => transfersApi.create(body),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["transfers"] });
      navigate(`/transfers/${data.id}`);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    let config: Record<string, unknown> = {};
    try {
      config = JSON.parse(destConfigRaw);
      setConfigError("");
    } catch {
      setConfigError("Invalid JSON in destination config");
      return;
    }
    mutation.mutate({ ...form, destination_config: config });
  };

  const toggleResource = (rt: string) => {
    setForm((f) => ({
      ...f,
      resource_types: f.resource_types?.includes(rt)
        ? f.resource_types.filter((r) => r !== rt)
        : [...(f.resource_types ?? []), rt],
    }));
  };

  return (
    <div className="max-w-2xl space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">New Transfer</h1>

      <form onSubmit={handleSubmit} className="bg-white rounded-lg border border-gray-200 shadow-sm p-6 space-y-5">
        {/* Source */}
        <fieldset className="space-y-3">
          <legend className="text-sm font-semibold text-gray-700 uppercase tracking-wide">Source</legend>
          <Field
            label="Patient ID (FHIR)"
            required
            value={form.source_patient_id}
            onChange={(v) => setForm((f) => ({ ...f, source_patient_id: v }))}
            placeholder="e.g. 12345"
          />
          <Field
            label="Source System"
            value={form.source_system ?? "modmed"}
            onChange={(v) => setForm((f) => ({ ...f, source_system: v }))}
          />
        </fieldset>

        {/* Destination */}
        <fieldset className="space-y-3">
          <legend className="text-sm font-semibold text-gray-700 uppercase tracking-wide">Destination</legend>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
            <select
              value={form.destination_type}
              onChange={(e) =>
                setForm((f) => ({ ...f, destination_type: e.target.value as "api" | "fhir_write" | "browser" }))
              }
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              <option value="api">REST API</option>
              <option value="fhir_write">FHIR Write</option>
              <option value="browser">Browser Automation</option>
            </select>
          </div>
          <Field
            label="Destination Name"
            required
            value={form.destination_name}
            onChange={(v) => setForm((f) => ({ ...f, destination_name: v }))}
            placeholder="e.g. partner-ehr"
          />
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Destination Config (JSON)
            </label>
            <textarea
              rows={4}
              value={destConfigRaw}
              onChange={(e) => setDestConfigRaw(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
            {configError && <p className="text-xs text-red-600 mt-1">{configError}</p>}
          </div>
        </fieldset>

        {/* Resource types */}
        <fieldset className="space-y-2">
          <legend className="text-sm font-semibold text-gray-700 uppercase tracking-wide">Resource Types</legend>
          <div className="flex flex-wrap gap-2">
            {DEFAULT_RESOURCES.map((rt) => (
              <button
                key={rt}
                type="button"
                onClick={() => toggleResource(rt)}
                className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
                  form.resource_types?.includes(rt)
                    ? "bg-brand-600 text-white border-brand-600"
                    : "bg-white text-gray-600 border-gray-300 hover:border-brand-400"
                }`}
              >
                {rt}
              </button>
            ))}
          </div>
        </fieldset>

        {/* Submit */}
        {mutation.isError && (
          <p className="text-sm text-red-600">
            Error: {(mutation.error as Error).message}
          </p>
        )}
        <button
          type="submit"
          disabled={mutation.isPending}
          className="w-full py-2 bg-brand-600 text-white rounded-lg font-medium text-sm hover:bg-brand-700 disabled:opacity-50 transition-colors"
        >
          {mutation.isPending ? "Submitting…" : "Start Transfer"}
        </button>
      </form>
    </div>
  );
}

function Field({
  label, value, onChange, required, placeholder,
}: {
  label: string; value: string; onChange: (v: string) => void;
  required?: boolean; placeholder?: string;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {label} {required && <span className="text-red-500">*</span>}
      </label>
      <input
        type="text"
        required={required}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
      />
    </div>
  );
}
