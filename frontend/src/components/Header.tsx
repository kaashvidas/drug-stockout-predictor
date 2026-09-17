import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

const ROLE_LABELS: Record<string, string> = {
  facility: "Facility layer",
  district: "District layer",
  state: "State layer",
  program: "Vertical program",
  national: "National layer",
};

export default function Header() {
  const { auth, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <header className="sticky top-0 z-10 border-b border-[#D5DEDC] bg-[#F3F6F5]/95 backdrop-blur-sm px-6 py-4 flex items-center justify-between">
      <div>
        <span className="inline-flex items-center gap-2 font-mono text-[11px] font-semibold uppercase tracking-[0.12em] text-[#0F6E66]">
          <span className="w-1.5 h-1.5 rounded-full bg-[#A9691C]" /> Shortage Cascade
        </span>
        <h1 className="text-lg font-semibold text-[#12292B] mt-0.5">{auth ? ROLE_LABELS[auth.role] : ""}</h1>
      </div>
      {auth && (
        <div className="flex items-center gap-4">
          <div className="text-right">
            <div className="text-sm font-medium text-[#12292B]">{auth.displayName}</div>
            <div className="font-mono text-[11px] text-[#4C6567]">
              scope <span className="text-[#0F6E66] font-semibold">{auth.scope}</span>
            </div>
          </div>
          <button
            onClick={() => {
              logout();
              navigate("/login");
            }}
            className="text-xs font-semibold border border-[#D5DEDC] rounded-full px-3 py-1.5 text-[#4C6567] hover:text-[#12292B] hover:border-[#0F6E66] transition-colors"
          >
            Sign out
          </button>
        </div>
      )}
    </header>
  );
}
