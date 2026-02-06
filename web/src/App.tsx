import { useEffect, useMemo, useRef, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

type Positions = Record<string, number>;

type Order = {
  order_id?: string;
  symbol?: string;
  side?: string;
  quantity?: number;
  status?: string;
  filled_price?: number;
};

type AgentStatus = {
  name: string;
  state: string;
  last_action?: string;
  last_error?: string;
  updated_at: string;
};

type AuditEvent = {
  ts: string;
  agent: string;
  event_type: string;
  cycle_id?: string;
  payload: Record<string, unknown>;
};

type StreamEvent = {
  type: string;
  source: string;
  ts: string;
  cycle_id?: string;
  payload: Record<string, unknown>;
};

type Universe = {
  symbols_kr: string[];
  symbols_us: string[];
  trends: string[];
};

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch ${path}`);
  }
  return res.json() as Promise<T>;
}

export default function App() {
  const [positions, setPositions] = useState<Positions>({});
  const [orders, setOrders] = useState<Order[]>([]);
  const [pnl, setPnl] = useState({ cash: 0, market_value: 0, equity: 0 });
  const [agents, setAgents] = useState<Record<string, AgentStatus>>({});
  const [audit, setAudit] = useState<AuditEvent[]>([]);
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [universe, setUniverse] = useState<Universe>({
    symbols_kr: [],
    symbols_us: [],
    trends: []
  });
  const [status, setStatus] = useState("connecting");
  const [agentFlashKeys, setAgentFlashKeys] = useState<Set<string>>(new Set());
  const [logFlash, setLogFlash] = useState(false);
  const agentListRef = useRef<HTMLDivElement | null>(null);
  const prevAuditKey = useRef<string | null>(null);
  const prevAgents = useRef<Record<string, AgentStatus>>({});
  const logFlashTimer = useRef<number | null>(null);
  const agentFlashTimers = useRef<Record<string, number>>({});

  const triggerLogFlash = () => {
    setLogFlash(true);
    if (logFlashTimer.current !== null) {
      window.clearTimeout(logFlashTimer.current);
    }
    logFlashTimer.current = window.setTimeout(() => {
      setLogFlash(false);
      logFlashTimer.current = null;
    }, 1200);
  };

  const flashAgentRows = (keys: string[]) => {
    if (keys.length === 0) {
      return;
    }
    setAgentFlashKeys((prev) => {
      const next = new Set(prev);
      keys.forEach((key) => next.add(key));
      return next;
    });
    keys.forEach((key) => {
      const existing = agentFlashTimers.current[key];
      if (existing) {
        window.clearTimeout(existing);
      }
      agentFlashTimers.current[key] = window.setTimeout(() => {
        setAgentFlashKeys((prev) => {
          const next = new Set(prev);
          next.delete(key);
          return next;
        });
        delete agentFlashTimers.current[key];
      }, 1600);
    });
  };

  const auditKey = (evt: AuditEvent) =>
    `${evt.ts}-${evt.agent}-${evt.event_type}-${evt.cycle_id ?? "-"}`;

  useEffect(() => {
    const poll = async () => {
      try {
        const [pos, ord, pnlData, agentData, auditData, universeData] = await Promise.all([
          fetchJson<{ positions: Positions }>("/api/positions"),
          fetchJson<{ orders: Order[] }>("/api/orders"),
          fetchJson<{ cash: number; market_value: number; equity: number }>("/api/pnl"),
          fetchJson<{ agents: Record<string, AgentStatus> }>("/api/agents/status"),
          fetchJson<{ events: AuditEvent[] }>("/api/audit/latest"),
          fetchJson<Universe>("/api/universe")
        ]);
        setPositions(pos.positions);
        setOrders(ord.orders ?? []);
        setPnl(pnlData);
        setAgents(agentData.agents);
        setAudit(auditData.events ?? []);
        setUniverse(universeData);
        setStatus("online");
      } catch {
        setStatus("offline");
      }
    };

    poll();
    const id = setInterval(poll, 5000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    const source = new EventSource(`${API_BASE}/api/stream`);
    source.onmessage = (event) => {
      const data = JSON.parse(event.data) as StreamEvent;
      setEvents((prev) => [data, ...prev].slice(0, 60));
      triggerLogFlash();
    };
    source.onerror = () => {
      source.close();
    };
    return () => source.close();
  }, []);

  useEffect(() => {
    if (audit.length === 0) {
      prevAuditKey.current = null;
      return;
    }
    const latestKey = auditKey(audit[0]);
    if (prevAuditKey.current && prevAuditKey.current !== latestKey) {
      triggerLogFlash();
    }
    prevAuditKey.current = latestKey;
  }, [audit]);

  useEffect(() => {
    const prev = prevAgents.current;
    const changed: string[] = [];
    Object.values(agents).forEach((agent) => {
      const prevAgent = prev[agent.name];
      if (prevAgent && prevAgent.updated_at !== agent.updated_at) {
        changed.push(agent.name);
      }
    });
    if (changed.length > 0) {
      flashAgentRows(changed);
      agentListRef.current?.scrollTo({ top: 0, behavior: "smooth" });
    }
    prevAgents.current = agents;
  }, [agents]);

  useEffect(() => {
    return () => {
      if (logFlashTimer.current !== null) {
        window.clearTimeout(logFlashTimer.current);
      }
      Object.values(agentFlashTimers.current).forEach((timerId) => {
        window.clearTimeout(timerId);
      });
      agentFlashTimers.current = {};
    };
  }, []);

  const positionRows = useMemo(() => Object.entries(positions), [positions]);
  const agentRows = useMemo(() => Object.values(agents), [agents]);
  const trendRows = useMemo(() => universe.trends, [universe.trends]);
  const logLine = useMemo(() => {
    const entries: Array<{ ts: string; text: string }> = [];
    const formatTs = (ts: string) => (ts.length >= 19 ? ts.slice(11, 19) : ts);
    events.forEach((evt) => {
      entries.push({
        ts: evt.ts,
        text: `${formatTs(evt.ts)} ${evt.source} ${evt.type} ${evt.cycle_id ?? "-"}`
      });
    });
    audit.forEach((evt) => {
      entries.push({
        ts: evt.ts,
        text: `${formatTs(evt.ts)} ${evt.agent} ${evt.event_type} ${evt.cycle_id ?? "-"}`
      });
    });
    if (entries.length === 0) {
      return "";
    }
    entries.sort((a, b) => Date.parse(b.ts) - Date.parse(a.ts));
    return entries.slice(0, 24).map((entry) => entry.text).join(" | ");
  }, [events, audit]);

  return (
    <div className="app">
      <div className={`status badge ${status}`}>{status}</div>

      <section className="grid">
        <article className="card">
          <h2>Portfolio</h2>
          <div className="metric">
            <span>Equity</span>
            <strong>{pnl.equity.toFixed(2)}</strong>
          </div>
          <div className="metric">
            <span>Cash</span>
            <strong>{pnl.cash.toFixed(2)}</strong>
          </div>
          <div className="metric">
            <span>Market Value</span>
            <strong>{pnl.market_value.toFixed(2)}</strong>
          </div>
          <div className="list scroll">
            {positionRows.length === 0 && <p>No positions.</p>}
            {positionRows.map(([symbol, qty]) => (
              <div key={symbol} className="row">
                <span>{symbol}</span>
                <span>{qty}</span>
              </div>
            ))}
          </div>
        </article>

        <article className="card">
          <h2>Open Orders</h2>
          {orders.length === 0 && <p>No orders yet.</p>}
          <div className="list scroll">
            {orders.map((order, idx) => (
              <div key={`${order.symbol}-${idx}`} className="row">
                <span>{order.symbol}</span>
                <span>{order.side}</span>
                <span>{order.quantity}</span>
                <span>{order.status}</span>
              </div>
            ))}
          </div>
        </article>

        <article className="card">
          <h2>Universe</h2>
          <div className="metric">
            <span>KR Symbols</span>
            <strong>{universe.symbols_kr.length}</strong>
          </div>
          <div className="metric">
            <span>US Symbols</span>
            <strong>{universe.symbols_us.length}</strong>
          </div>
          <div className="list scroll">
            {trendRows.length === 0 && <p>No trend keywords yet.</p>}
            {trendRows.map((trend) => (
              <div key={trend} className="row single">
                <span>{trend}</span>
              </div>
            ))}
          </div>
        </article>

        <article className="card">
          <h2>Agent Status</h2>
          {agentRows.length === 0 && <p>No agents yet.</p>}
          <div className="list scroll" ref={agentListRef}>
            {agentRows.map((agent) => (
              <div
                key={agent.name}
                className={`row ${agentFlashKeys.has(agent.name) ? "flash" : ""}`}
              >
                <span>{agent.name}</span>
                <span>{agent.state}</span>
                <span>{agent.last_action ?? "-"}</span>
              </div>
            ))}
          </div>
        </article>
      </section>

      <footer className={`log-bar ${logFlash ? "flash" : ""}`}>
        <span className="log-label">log</span>
        <div className="log-line">{logLine || "No log events yet."}</div>
      </footer>
    </div>
  );
}
