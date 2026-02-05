import { useEffect, useMemo, useState } from "react";

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
  const [status, setStatus] = useState("connecting");

  useEffect(() => {
    const poll = async () => {
      try {
        const [pos, ord, pnlData, agentData, auditData] = await Promise.all([
          fetchJson<{ positions: Positions }>("/api/positions"),
          fetchJson<{ orders: Order[] }>("/api/orders"),
          fetchJson<{ cash: number; market_value: number; equity: number }>("/api/pnl"),
          fetchJson<{ agents: Record<string, AgentStatus> }>("/api/agents/status"),
          fetchJson<{ events: AuditEvent[] }>("/api/audit/latest"),
        ]);
        setPositions(pos.positions);
        setOrders(ord.orders ?? []);
        setPnl(pnlData);
        setAgents(agentData.agents);
        setAudit(auditData.events ?? []);
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
      setEvents((prev) => [data, ...prev].slice(0, 25));
    };
    source.onerror = () => {
      source.close();
    };
    return () => source.close();
  }, []);

  const positionRows = useMemo(() => Object.entries(positions), [positions]);
  const agentRows = useMemo(() => Object.values(agents), [agents]);

  return (
    <div className="app">
      <header className="hero">
        <div>
          <p className="eyebrow">Agent Trading Company</p>
          <h1>Ops Console</h1>
          <p className="sub">
            Live KR/US agent health, orders, and decision trace.
          </p>
        </div>
        <div className={`status ${status}`}>{status}</div>
      </header>

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
          <div className="list">
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
          <div className="list">
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
          <h2>Agent Status</h2>
          {agentRows.length === 0 && <p>No agents yet.</p>}
          <div className="list">
            {agentRows.map((agent) => (
              <div key={agent.name} className="row">
                <span>{agent.name}</span>
                <span>{agent.state}</span>
                <span>{agent.last_action ?? "-"}</span>
              </div>
            ))}
          </div>
        </article>

        <article className="card wide">
          <h2>Event Stream</h2>
          <div className="list">
            {events.length === 0 && <p>No events yet.</p>}
            {events.map((evt, idx) => (
              <div key={`${evt.ts}-${idx}`} className="row">
                <span>{evt.type}</span>
                <span>{evt.source}</span>
                <span>{evt.cycle_id ?? "-"}</span>
                <span>{evt.ts}</span>
              </div>
            ))}
          </div>
        </article>

        <article className="card wide">
          <h2>Audit Log</h2>
          <div className="list">
            {audit.length === 0 && <p>No audit events.</p>}
            {audit.map((evt, idx) => (
              <div key={`${evt.ts}-${idx}`} className="row">
                <span>{evt.event_type}</span>
                <span>{evt.agent}</span>
                <span>{evt.cycle_id ?? "-"}</span>
                <span>{evt.ts}</span>
              </div>
            ))}
          </div>
        </article>
      </section>
    </div>
  );
}
