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
    <div className="min-h-screen flex items-center justify-center bg-[#F3F6F5] px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <span className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[#0F6E66]">
            <span className="w-2 h-2 rounded-full bg-[#A9691C]" /> Shortage Cascade
          </span>
          <h1 className="text-2xl font-semibold mt-2 text-[#12292B]">
            Predicting a medicine shortage before it becomes regional
          </h1>
        </div>

        <div className="bg-white border border-[#D5DEDC] rounded-xl shadow-sm p-6 mb-6">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              doLogin(username, password);
            }}
            className="space-y-3"
          >
            <input
              className="w-full border border-[#D5DEDC] rounded-lg px-3 py-2 text-sm"
              placeholder="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
            <input
              className="w-full border border-[#D5DEDC] rounded-lg px-3 py-2 text-sm"
              placeholder="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            {error && <p className="text-sm text-[#C1443A]">{error}</p>}
            <button
              disabled={loading}
              className="w-full bg-[#0F6E66] text-white rounded-lg py-2 text-sm font-semibold disabled:opacity-50"
            >
              {loading ? "Signing in..." : "Sign in"}
            </button>
          </form>
        </div>

        <p className="text-xs uppercase tracking-wide text-[#4C6567] font-semibold mb-2">
          Or log in as a demo role
        </p>
        <div className="space-y-2">
          {accounts.map((a) => (
            <button
              key={a.username}
              onClick={() => doLogin(a.username, a.password)}
              className="w-full text-left bg-white border border-[#D5DEDC] rounded-lg px-4 py-3 hover:border-[#0F6E66] transition-colors"
            >
              <div className="font-semibold text-sm text-[#12292B]">{a.display_name}</div>
              <div className="text-xs text-[#4C6567]">{ROLE_LABELS[a.role]} &middot; scope: {a.scope}</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
