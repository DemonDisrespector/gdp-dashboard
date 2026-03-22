import { Routes, Route, NavLink } from "react-router-dom";
import { Activity, List, FileText, PlusCircle } from "lucide-react";
import TransfersPage from "./pages/TransfersPage";
import TransferDetailPage from "./pages/TransferDetailPage";
import AuditPage from "./pages/AuditPage";
import NewTransferPage from "./pages/NewTransferPage";

export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      {/* ── Nav ── */}
      <header className="bg-brand-700 text-white shadow-md">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-6">
          <span className="font-bold text-xl tracking-tight flex items-center gap-2">
            <Activity className="w-5 h-5" />
            QuantumBridge
          </span>
          <nav className="flex gap-4 text-sm font-medium">
            <NavLink
              to="/"
              end
              className={({ isActive }) =>
                isActive ? "text-white underline" : "text-brand-100 hover:text-white"
              }
            >
              <span className="flex items-center gap-1">
                <List className="w-4 h-4" /> Transfers
              </span>
            </NavLink>
            <NavLink
              to="/new"
              className={({ isActive }) =>
                isActive ? "text-white underline" : "text-brand-100 hover:text-white"
              }
            >
              <span className="flex items-center gap-1">
                <PlusCircle className="w-4 h-4" /> New Transfer
              </span>
            </NavLink>
            <NavLink
              to="/audit"
              className={({ isActive }) =>
                isActive ? "text-white underline" : "text-brand-100 hover:text-white"
              }
            >
              <span className="flex items-center gap-1">
                <FileText className="w-4 h-4" /> Audit Log
              </span>
            </NavLink>
          </nav>
        </div>
      </header>

      {/* ── Main ── */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 py-6">
        <Routes>
          <Route path="/" element={<TransfersPage />} />
          <Route path="/transfers/:id" element={<TransferDetailPage />} />
          <Route path="/new" element={<NewTransferPage />} />
          <Route path="/audit" element={<AuditPage />} />
        </Routes>
      </main>

      <footer className="text-center text-xs text-gray-400 py-3 border-t">
        QuantumBridge v0.1.0 – HIPAA-compliant referral transfer agent
      </footer>
    </div>
  );
}
