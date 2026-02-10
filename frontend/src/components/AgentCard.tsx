import type { AgentStatus } from "../types";
import StatusBadge from "./StatusBadge";

const FRIENDLY_NAMES: Record<string, string> = {
  data_collector: "Data Collector",
  data_analyst: "Data Analyst",
  trade_executor: "Trade Executor",
  risk_manager: "Risk Manager",
};

const AGENT_ICONS: Record<string, string> = {
  data_collector: "DB",
  data_analyst: "AN",
  trade_executor: "TX",
  risk_manager: "RM",
};

interface AgentCardProps {
  agent: AgentStatus;
  selected: boolean;
  onClick: () => void;
}

export default function AgentCard({ agent, selected, onClick }: AgentCardProps) {
  const friendlyName = FRIENDLY_NAMES[agent.name] ?? agent.name;
  const icon = AGENT_ICONS[agent.name] ?? "AG";

  return (
    <button
      onClick={onClick}
      className={`w-full text-left rounded-xl border p-4 transition-all duration-200 hover:border-blue-500/50 hover:bg-gray-800/80 ${
        selected
          ? "border-blue-500 bg-gray-800/90 shadow-lg shadow-blue-500/10"
          : "border-gray-700/50 bg-gray-800/50"
      }`}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div
            className={`flex h-10 w-10 items-center justify-center rounded-lg text-sm font-bold ${
              agent.status === "error"
                ? "bg-red-500/20 text-red-400"
                : agent.status === "running"
                  ? "bg-yellow-500/20 text-yellow-400"
                  : "bg-emerald-500/20 text-emerald-400"
            }`}
          >
            {icon}
          </div>
          <div>
            <h3 className="font-semibold text-gray-100">{friendlyName}</h3>
          </div>
        </div>
        <StatusBadge status={agent.status} />
      </div>
      {agent.status === "error" && agent.last_error && (
        <div className="mt-3 rounded-lg bg-red-500/10 px-3 py-2">
          <p className="text-xs text-red-400 line-clamp-2">{agent.last_error}</p>
        </div>
      )}
    </button>
  );
}
