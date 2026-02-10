import { useAgentData } from "../hooks/useAgentData";
import AgentCard from "./AgentCard";
import TradeHistory from "./TradeHistory";
import ReportViewer from "./ReportViewer";
import StockQuotes from "./StockQuotes";
import type { Balance, MarketStatus } from "../types";
import { addToWatchlist, removeFromWatchlist } from "../api/client";

function formatWon(value: number): string {
  return `\u20A9${value.toLocaleString("ko-KR")}`;
}

function BalanceSummary({ balance }: { balance: Balance | null }) {
  if (!balance) {
    return (
      <div className="rounded-xl border border-gray-700/50 bg-gray-800/50 px-5 py-4">
        <p className="text-sm text-gray-500">Balance loading...</p>
      </div>
    );
  }

  const pnlPositive = balance.total_evlu_pfls_amt >= 0;
  const pnlPct =
    balance.total_evlu_amt > 0
      ? (
          (balance.total_evlu_pfls_amt /
            (balance.total_evlu_amt - balance.total_evlu_pfls_amt)) *
          100
        ).toFixed(2)
      : "0.00";

  return (
    <div className="rounded-xl border border-gray-700/50 bg-gray-800/50 px-5 py-4">
      <div className="flex flex-wrap items-center gap-x-8 gap-y-2">
        <div>
          <p className="text-xs text-gray-500">Total Valuation</p>
          <p className="text-lg font-bold tabular-nums text-gray-100">
            {formatWon(balance.total_evlu_amt)}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Unrealized P&L</p>
          <p
            className={`text-lg font-bold tabular-nums ${
              pnlPositive ? "text-emerald-400" : "text-red-400"
            }`}
          >
            {pnlPositive ? "+" : ""}
            {formatWon(balance.total_evlu_pfls_amt)}
            <span className="ml-1 text-sm font-normal">
              ({pnlPositive ? "+" : ""}
              {pnlPct}%)
            </span>
          </p>
        </div>
        <div className="ml-auto">
          <p className="text-xs text-gray-500">Holdings</p>
          <p className="text-lg font-bold tabular-nums text-gray-100">
            {balance.items.length}
          </p>
        </div>

        {balance.items.length > 0 && (
          <div className="mt-3 w-full overflow-x-auto">
            <table className="w-full border-collapse">
              <thead>
                <tr className="border-b border-gray-700/50">
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-400">
                    Stock
                  </th>
                  <th className="px-3 py-2 text-right text-xs font-medium text-gray-400">
                    Quantity
                  </th>
                  <th className="px-3 py-2 text-right text-xs font-medium text-gray-400">
                    Avg Price
                  </th>
                  <th className="px-3 py-2 text-right text-xs font-medium text-gray-400">
                    Current Price
                  </th>
                  <th className="px-3 py-2 text-right text-xs font-medium text-gray-400">
                    Eval Amount
                  </th>
                  <th className="px-3 py-2 text-right text-xs font-medium text-gray-400">
                    P&L Amount
                  </th>
                  <th className="px-3 py-2 text-right text-xs font-medium text-gray-400">
                    P&L Rate
                  </th>
                </tr>
              </thead>
              <tbody>
                {balance.items.map((item) => {
                  const positive = item.evlu_pfls_amt >= 0;
                  const evalAmount = item.prpr * item.hldg_qty;
                  return (
                    <tr
                      key={item.pdno}
                      className="border-b border-gray-700/30 hover:bg-gray-800/30"
                    >
                      <td className="px-3 py-2">
                        <div className="flex flex-col">
                          <span className="text-sm font-medium text-gray-200">
                            {item.prdt_name}
                          </span>
                          <span className="text-xs text-gray-500">
                            {item.pdno}
                          </span>
                        </div>
                      </td>
                      <td className="px-3 py-2 text-right text-sm tabular-nums text-gray-300">
                        {item.hldg_qty.toLocaleString()}
                      </td>
                      <td className="px-3 py-2 text-right text-sm tabular-nums text-gray-300">
                        {formatWon(item.pchs_avg_pric)}
                      </td>
                      <td className="px-3 py-2 text-right text-sm tabular-nums text-gray-300">
                        {formatWon(item.prpr)}
                      </td>
                      <td className="px-3 py-2 text-right text-sm tabular-nums text-gray-300">
                        {formatWon(evalAmount)}
                      </td>
                      <td
                        className={`px-3 py-2 text-right text-sm font-medium tabular-nums ${
                          positive ? "text-emerald-400" : "text-red-400"
                        }`}
                      >
                        {positive ? "+" : ""}
                        {formatWon(item.evlu_pfls_amt)}
                      </td>
                      <td
                        className={`px-3 py-2 text-right text-sm font-medium tabular-nums ${
                          positive ? "text-emerald-400" : "text-red-400"
                        }`}
                      >
                        {positive ? "+" : ""}
                        {item.evlu_pfls_rt.toFixed(2)}%
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function MarketPhraseBadge({ label, phase }: { label: string; phase: string }) {
  const colorMap: Record<string, string> = {
    open: "bg-emerald-500/20 text-emerald-400",
    pre_scan: "bg-yellow-500/20 text-yellow-400",
    closed: "bg-gray-500/20 text-gray-500",
  };
  const labelMap: Record<string, string> = {
    open: "Open",
    pre_scan: "Pre-scan",
    closed: "Closed",
  };
  return (
    <span className="flex items-center gap-1.5 text-xs">
      <span className="text-gray-500">{label}</span>
      <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${colorMap[phase] ?? colorMap.closed}`}>
        {labelMap[phase] ?? "Closed"}
      </span>
    </span>
  );
}

function MarketIndicator({ status }: { status: MarketStatus | null }) {
  if (!status) return null;
  return (
    <div className="flex items-center gap-3">
      <MarketPhraseBadge label="KR" phase={status.kr.phase} />
      <MarketPhraseBadge label="US" phase={status.us.phase} />
    </div>
  );
}

function ConnectionIndicator({ connected }: { connected: boolean }) {
  return (
    <span className="flex items-center gap-1.5 text-xs">
      <span
        className={`inline-block h-2 w-2 rounded-full ${
          connected ? "bg-emerald-400" : "bg-red-500 animate-pulse"
        }`}
      />
      <span className={connected ? "text-gray-400" : "text-red-400"}>
        {connected ? "Live" : "Disconnected"}
      </span>
    </span>
  );
}

export default function Dashboard() {
  const {
    agents,
    trades,
    balance,
    reports,
    quotes,
    marketStatus,
    loading,
    isConnected,
    refetchPrices,
  } = useAgentData();

  const handleAddStock = async (stockCode: string) => {
    try {
      await addToWatchlist(stockCode);
      refetchPrices();
    } catch (err) {
      console.error("Failed to add stock:", err);
    }
  };

  const handleRemoveStock = async (stockCode: string) => {
    try {
      await removeFromWatchlist(stockCode);
      refetchPrices();
    } catch (err) {
      console.error("Failed to remove stock:", err);
    }
  };

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-gray-600 border-t-blue-500" />
          <p className="text-sm text-gray-500">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col overflow-hidden">
      {/* Header */}
      <header className="flex items-center justify-between border-b border-gray-800 px-6 py-3">
        <div className="flex items-baseline gap-3">
          <h1 className="text-lg font-bold text-gray-100">
            Agent Trading Company
          </h1>
          <span className="text-xs text-gray-500">AI-Powered Trading</span>
        </div>
        <div className="flex items-center gap-4">
          <MarketIndicator status={marketStatus} />
          <ConnectionIndicator connected={isConnected} />
        </div>
      </header>

      {/* Content */}
      <main className="flex min-h-0 flex-1 flex-col gap-3 overflow-hidden p-4">
        {/* Agent cards */}
        <div className="shrink-0 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {agents.map((agent) => (
            <AgentCard
              key={agent.name}
              agent={agent}
              selected={false}
              onClick={() => {}}
            />
          ))}
        </div>

        {/* Balance summary */}
        <div className="shrink-0 max-h-48 overflow-y-auto">
          <BalanceSummary balance={balance} />
        </div>

        {/* Stock quotes */}
        <StockQuotes quotes={quotes} onAdd={handleAddStock} onRemove={handleRemoveStock} />

        {/* Bottom row: trades + reports */}
        <div className="grid min-h-0 flex-1 grid-cols-1 gap-3 lg:grid-cols-2">
          <TradeHistory trades={trades} />
          <ReportViewer reports={reports} />
        </div>
      </main>
    </div>
  );
}
