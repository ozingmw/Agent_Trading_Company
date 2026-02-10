import type { Trade } from "../types";

function formatTime(timestamp: string): string {
  const d = new Date(timestamp);
  return d.toLocaleString("ko-KR", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function formatWon(value: number): string {
  return `\u20A9${value.toLocaleString("ko-KR")}`;
}

interface TradeHistoryProps {
  trades: Trade[];
}

export default function TradeHistory({ trades }: TradeHistoryProps) {
  return (
    <div className="flex min-h-0 h-full flex-col rounded-xl border border-gray-700/50 bg-gray-800/50 overflow-hidden">
      <div className="border-b border-gray-700/50 px-5 py-3">
        <h2 className="text-sm font-semibold text-gray-300">Trade History</h2>
      </div>
      {trades.length === 0 ? (
        <div className="flex flex-1 items-center justify-center p-8">
          <p className="text-sm text-gray-500">No trades recorded yet</p>
        </div>
      ) : (
        <div className="flex-1 overflow-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-700/30 text-left text-xs text-gray-500">
                <th className="px-4 py-2.5 font-medium">Time</th>
                <th className="px-4 py-2.5 font-medium">Stock</th>
                <th className="px-4 py-2.5 font-medium">Action</th>
                <th className="px-4 py-2.5 font-medium text-right">Qty</th>
                <th className="px-4 py-2.5 font-medium text-right">Price</th>
                <th className="px-4 py-2.5 font-medium text-center">Status</th>
              </tr>
            </thead>
            <tbody>
              {trades.map((trade, i) => (
                <tr
                  key={`${trade.timestamp}-${i}`}
                  className="border-b border-gray-700/20 transition-colors hover:bg-gray-700/20"
                >
                  <td className="whitespace-nowrap px-4 py-2.5 text-xs text-gray-400">
                    {formatTime(trade.timestamp)}
                  </td>
                  <td className="px-4 py-2.5">
                    <div className="font-medium text-gray-200">
                      {trade.stock_name}
                    </div>
                    <div className="text-xs text-gray-500">
                      {trade.stock_code}
                    </div>
                  </td>
                  <td className="px-4 py-2.5">
                    <span
                      className={`inline-block rounded px-2 py-0.5 text-xs font-semibold ${
                        trade.action === "buy"
                          ? "bg-emerald-500/15 text-emerald-400"
                          : "bg-red-500/15 text-red-400"
                      }`}
                    >
                      {trade.action === "buy" ? "BUY" : "SELL"}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-right tabular-nums text-gray-300">
                    {trade.qty.toLocaleString()}
                  </td>
                  <td className="px-4 py-2.5 text-right tabular-nums text-gray-300">
                    {formatWon(trade.price)}
                  </td>
                  <td className="px-4 py-2.5 text-center">
                    <span
                      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                        trade.status === "filled"
                          ? "bg-emerald-500/15 text-emerald-400"
                          : trade.status === "pending"
                            ? "bg-yellow-500/15 text-yellow-400"
                            : "bg-red-500/15 text-red-400"
                      }`}
                    >
                      {trade.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
