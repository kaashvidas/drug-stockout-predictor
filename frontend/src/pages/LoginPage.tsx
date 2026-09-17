import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import type { DemoAccount } from "../types";

const ROLE_LABELS: Record<string, string> = {
  facility: "Facility (PHC/CHC pharmacist)",
  district: "District program manager",
  state: "State procurement corporation",
  program: "Vertical program (Central TB Division etc.)",
  national: "National ministry / crisis task force",
};

const ROLE_DOT: Record<string, string> = {
  facility: "bg-[#2E8B57]",
  district: "bg-[#B4741B]",
  state: "bg-[#0F6E66]",
  program: "bg-[#8E2A2A]",
  national: "bg-[#12292B]",
};

export default function LoginPage() {
  const [accounts, setAccounts] = useState<DemoAccount[]>([]);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    api.get<DemoAccount[]>("/auth/demo-accounts").then((res) => setAccounts(res.data));
  }, []);

  async function doLogin(u: string, p: string) {
    setLoading(true);
    setError("");
    try {
      const res = await api.post("/auth/login", { username: u, password: p });
      login({
        token: res.data.access_token,
        role: res.data.role,
        scope: res.data.scope,
        displayName: res.data.display_name,
        username: u,
      });
      navigate(`/${res.data.role}`);
    } catch {
      setError("Invalid username or password");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      className="min-h-screen flex items-center justify-center px-4 py-10"
      style={{
        background:
          "radial-gradient(1200px 600px at 50% -10%, rgba(15,110,102,0.08), transparent), var(--bg)",
      }}
    >
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <span className="inline-flex items-center gap-2 font-mono text-xs font-semibold uppercase tracking-[0.14em] text-[#0F6E66]">
            <span className="w-2 h-2 rounded-full bg-[#A9691C]" /> Shortage Cascade
          </span>
          <h1 className="text-2xl font-semibold mt-3 text-[#12292B]">
            Predicting a medicine shortage before it becomes regional
          </h1>
          <p className="text-sm text-[#4C6567] mt-2 max-w-md mx-auto">
            A decision-support layer over Karnataka's own KSMSCL / e-Aushadhi
            procurement system — not a replacement for it. Every
            recommendation here is reviewed and approved by a person.
          </p>
        </div>

        <div className="panel p-6 mb-6">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              doLogin(username, password);
            }}
            className="space-y-3"
          >
            <input
              className="w-full border border-[#D5DEDC] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#0F6E66] focus:ring-2 focus:ring-[#0F6E66]/15 transition-shadow"
              placeholder="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
            <input
              className="w-full border border-[#D5DEDC] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#0F6E66] focus:ring-2 focus:ring-[#0F6E66]/15 transition-shadow"
              placeholder="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            {error && <p className="text-sm text-[#C1443A]">{error}</p>}
            <button
              disabled={loading}
              className="w-full bg-[#0F6E66] text-white rounded-lg py-2.5 text-sm font-semibold disabled:opacity-50 hover:bg-[#0C5A54] transition-colors"
            >
              {loading ? "Signing in..." : "Sign in"}
            </button>
          </form>
        </div>

        <p className="text-[11px] font-semibold uppercase tracking-wider text-[#4C6567] mb-2 px-1">
          Or log in as a demo role
        </p>
        <div className="space-y-2">
          {accounts.map((a) => (
            <button
              key={a.username}
              onClick={() => doLogin(a.username, a.password)}
              className="panel panel-interactive w-full text-left px-4 py-3 flex items-start gap-3"
            >
              <span className={`mt-1.5 w-2 h-2 rounded-full shrink-0 ${ROLE_DOT[a.role] ?? "bg-gray-400"}`} />
              <div>
                <div className="font-semibold text-sm text-[#12292B]">{a.display_name}</div>
                <div className="text-xs text-[#4C6567]">
                  {ROLE_LABELS[a.role]} &middot; <span className="font-mono">scope: {a.scope}</span>
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
