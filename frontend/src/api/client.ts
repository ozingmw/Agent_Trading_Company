import type { AgentStatus, Trade, Balance, Report, StockQuote, MarketStatus } from "../types";

const BASE_URL = "/api";
const FETCH_TIMEOUT_MS = 5000;

async function fetchJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    signal: AbortSignal.timeout(FETCH_TIMEOUT_MS),
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

async function fetchText(path: string): Promise<string> {
  const res = await fetch(`${BASE_URL}${path}`, {
    signal: AbortSignal.timeout(FETCH_TIMEOUT_MS),
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.text();
}

export function getAgents(): Promise<AgentStatus[]> {
  return fetchJSON<AgentStatus[]>("/agents");
}

export function getAgentReports(name: string): Promise<Report[]> {
  return fetchJSON<Report[]>(`/agents/${name}/reports`);
}

export function getReportContent(
  name: string,
  filename: string,
): Promise<string> {
  return fetchText(`/agents/${name}/reports/${filename}`);
}

export async function getTrades(): Promise<Trade[]> {
  const raw = await fetchJSON<Record<string, unknown>[]>("/trades");
  // API returns {content, agent} from report files — filter to valid Trade objects only
  return raw.filter(
    (item): item is Record<string, unknown> & Trade =>
      typeof item.timestamp === "string" &&
      typeof item.stock_code === "string" &&
      typeof item.qty === "number",
  ) as Trade[];
}

export async function getBalance(): Promise<Balance> {
  const raw = await fetchJSON<Record<string, unknown>>("/balance");
  const items = (raw.items as Record<string, unknown>[]) ?? [];
  return {
    total_evlu_amt: Number(raw.total_evlu_amt) || 0,
    total_evlu_pfls_amt: Number(raw.total_evlu_pfls_amt) || 0,
    items: items.map((item) => ({
      pdno: String(item.pdno ?? ""),
      prdt_name: String(item.prdt_name ?? ""),
      hldg_qty: Number(item.hldg_qty) || 0,
      pchs_avg_pric: Number(item.pchs_avg_pric) || 0,
      prpr: Number(item.prpr) || 0,
      evlu_pfls_amt: Number(item.evlu_pfls_amt) || 0,
      evlu_pfls_rt: Number(item.evlu_pfls_rt) || 0,
    })),
  };
}

export function getAllReports(limit = 30): Promise<Report[]> {
  return fetchJSON<Report[]>(`/reports?limit=${limit}`);
}

export function getPrices(): Promise<StockQuote[]> {
  return fetchJSON<StockQuote[]>("/prices");
}

export function getMarketStatus(): Promise<MarketStatus> {
  return fetchJSON<MarketStatus>("/market-status");
}

export async function addToWatchlist(stockCode: string): Promise<{ watchlist: string[] }> {
  const res = await fetch(`${BASE_URL}/watchlist`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ stock_code: stockCode }),
    signal: AbortSignal.timeout(FETCH_TIMEOUT_MS),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `API error: ${res.status}`);
  }
  return res.json();
}

export async function removeFromWatchlist(stockCode: string): Promise<{ watchlist: string[] }> {
  const res = await fetch(`${BASE_URL}/watchlist/${stockCode}`, {
    method: "DELETE",
    signal: AbortSignal.timeout(FETCH_TIMEOUT_MS),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `API error: ${res.status}`);
  }
  return res.json();
}
