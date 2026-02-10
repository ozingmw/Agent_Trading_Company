export interface AgentStatus {
  name: string;
  status: "idle" | "running" | "error";
  last_run: string | null;
  last_error: string | null;
}

export interface Trade {
  timestamp: string;
  stock_code: string;
  stock_name: string;
  action: "buy" | "sell";
  qty: number;
  price: number;
  status: "filled" | "pending" | "failed";
}

export interface Report {
  filename: string;
  agent: string;
  content?: string;
}

export interface Balance {
  items: BalanceItem[];
  total_evlu_amt: number;
  total_evlu_pfls_amt: number;
}

export interface BalanceItem {
  pdno: string;
  prdt_name: string;
  hldg_qty: number;
  pchs_avg_pric: number;
  prpr: number;
  evlu_pfls_amt: number;
  evlu_pfls_rt: number;
}

export interface StockQuote {
  stock_code: string;
  price: string;
  open: string;
  high: string;
  low: string;
  volume: string;
  change_rate: string;
  change_amount: string;
  change_sign: string;
}

export interface MarketInfo {
  phase: "pre_scan" | "open" | "closed";
  local_time: string;
  timezone: string;
  hours: string;
}

export interface MarketStatus {
  kr: MarketInfo;
  us: MarketInfo;
  any_active: boolean;
}

export interface WSEvent {
  type:
    | "agent_status_changed"
    | "new_report"
    | "trade_executed"
    | "risk_alert"
    | "price_update";
  data: Record<string, unknown>;
}
