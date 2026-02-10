import { useState } from "react";
import type { StockQuote } from "../types";

function formatWon(value: number): string {
  return `\u20A9${value.toLocaleString("ko-KR")}`;
}

function getChangeColor(changeSign: string): string {
  // Korean market convention: red = up, blue = down
  if (changeSign === "1" || changeSign === "2") return "text-red-400";
  if (changeSign === "4" || changeSign === "5") return "text-blue-400";
  return "text-gray-400";
}

function getChangePrefix(changeSign: string): string {
  if (changeSign === "1" || changeSign === "2") return "+";
  if (changeSign === "4" || changeSign === "5") return "-";
  return "";
}

interface StockQuotesProps {
  quotes: StockQuote[];
  onAdd?: (stockCode: string) => void;
  onRemove?: (stockCode: string) => void;
}

export default function StockQuotes({ quotes, onAdd, onRemove }: StockQuotesProps) {
  const [input, setInput] = useState("");

  const handleAdd = () => {
    const code = input.trim();
    if (code && onAdd) {
      onAdd(code);
      setInput("");
    }
  };

  return (
    <div className="flex max-h-52 shrink-0 flex-col rounded-xl border border-gray-700/50 bg-gray-800/50">
      <div className="shrink-0 border-b border-gray-700/50 px-5 py-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-300">Watchlist Quotes</h2>
        {onAdd && (
          <form
            onSubmit={(e) => { e.preventDefault(); handleAdd(); }}
            className="flex items-center gap-2"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Stock code"
              maxLength={6}
              className="w-24 rounded bg-gray-700/50 px-2 py-1 text-xs text-gray-200 placeholder-gray-500 outline-none focus:ring-1 focus:ring-blue-500/50"
            />
            <button
              type="submit"
              className="rounded bg-blue-600/80 px-2.5 py-1 text-xs font-medium text-gray-100 hover:bg-blue-500/80 transition-colors"
            >
              Add
            </button>
          </form>
        )}
      </div>
      {quotes.length === 0 ? (
        <div className="flex items-center justify-center p-4">
          <p className="text-sm text-gray-500">No price data available</p>
        </div>
      ) : (
        <div className="min-h-0 flex-1 overflow-y-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-700/30 text-left text-xs text-gray-500">
                <th className="px-4 py-2.5 font-medium">Code</th>
                <th className="px-4 py-2.5 font-medium text-right">Price</th>
                <th className="px-4 py-2.5 font-medium text-right">Change</th>
                <th className="px-4 py-2.5 font-medium text-right">Change %</th>
                <th className="px-4 py-2.5 font-medium text-right">High</th>
                <th className="px-4 py-2.5 font-medium text-right">Low</th>
                <th className="px-4 py-2.5 font-medium text-right">Volume</th>
                {onRemove && <th className="w-8 px-2 py-2.5 font-medium" />}
              </tr>
            </thead>
            <tbody>
              {quotes.map((quote) => {
                const colorClass = getChangeColor(quote.change_sign);
                const prefix = getChangePrefix(quote.change_sign);
                const changeAmt = Number(quote.change_amount) || 0;
                return (
                  <tr
                    key={quote.stock_code}
                    className="border-b border-gray-700/20 transition-colors hover:bg-gray-700/20"
                  >
                    <td className="whitespace-nowrap px-4 py-2.5 font-medium text-gray-200">
                      {quote.stock_code}
                    </td>
                    <td className="px-4 py-2.5 text-right tabular-nums text-gray-100 font-medium">
                      {formatWon(Number(quote.price))}
                    </td>
                    <td className={`px-4 py-2.5 text-right tabular-nums font-medium ${colorClass}`}>
                      {prefix}{formatWon(Math.abs(changeAmt))}
                    </td>
                    <td className={`px-4 py-2.5 text-right tabular-nums font-medium ${colorClass}`}>
                      {prefix}{quote.change_rate}%
                    </td>
                    <td className="px-4 py-2.5 text-right tabular-nums text-gray-300">
                      {formatWon(Number(quote.high))}
                    </td>
                    <td className="px-4 py-2.5 text-right tabular-nums text-gray-300">
                      {formatWon(Number(quote.low))}
                    </td>
                    <td className="px-4 py-2.5 text-right tabular-nums text-gray-300">
                      {Number(quote.volume).toLocaleString("ko-KR")}
                    </td>
                    {onRemove && (
                      <td className="px-2 py-2.5 text-center">
                        <button
                          onClick={() => onRemove(quote.stock_code)}
                          className="text-gray-500 hover:text-red-400 transition-colors text-xs leading-none"
                          title="Remove from watchlist"
                        >
                          x
                        </button>
                      </td>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
