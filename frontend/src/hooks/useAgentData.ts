import { useState, useEffect, useCallback, useRef } from "react";
import type { AgentStatus, Trade, Balance, Report, StockQuote, MarketStatus } from "../types";
import {
  getAgents,
  getTrades,
  getBalance,
  getAllReports,
  getPrices,
  getMarketStatus,
} from "../api/client";
import { useWebSocket } from "./useWebSocket";

export function useAgentData() {
  const [agents, setAgents] = useState<AgentStatus[]>([]);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [balance, setBalance] = useState<Balance | null>(null);
  const [reports, setReports] = useState<Report[]>([]);
  const [quotes, setQuotes] = useState<StockQuote[]>([]);
  const [marketStatus, setMarketStatus] = useState<MarketStatus | null>(null);
  const [loading, setLoading] = useState(true);

  const { lastEvent, lastTick, isConnected } = useWebSocket();
  const prevConnectedRef = useRef(false);

  const fetchAll = useCallback(async () => {
    try {
      const [agentsRes, tradesRes, balanceRes, reportsRes, pricesRes, marketRes] = await Promise.allSettled([
        getAgents(),
        getTrades(),
        getBalance(),
        getAllReports(),
        getPrices(),
        getMarketStatus(),
      ]);
      if (agentsRes.status === "fulfilled") setAgents(agentsRes.value);
      if (tradesRes.status === "fulfilled") setTrades(tradesRes.value);
      if (balanceRes.status === "fulfilled") setBalance(balanceRes.value);
      if (reportsRes.status === "fulfilled") setReports(reportsRes.value);
      if (pricesRes.status === "fulfilled") setQuotes(pricesRes.value);
      if (marketRes.status === "fulfilled") setMarketStatus(marketRes.value);
    } catch (err) {
      console.error("Failed to fetch data:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  const refetchPrices = useCallback(() => {
    getPrices()
      .then(setQuotes)
      .catch((err) => console.error("Failed to refetch prices:", err));
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  // Refresh all data when WebSocket reconnects
  useEffect(() => {
    if (isConnected && !prevConnectedRef.current) {
      fetchAll();
    }
    prevConnectedRef.current = isConnected;
  }, [isConnected, fetchAll]);

  // Periodic agent status + market status polling every 10 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      getAgents()
        .then(setAgents)
        .catch((err) => console.error("Failed to poll agents:", err));
      getMarketStatus()
        .then(setMarketStatus)
        .catch((err) => console.error("Failed to refresh market status:", err));
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  // React to WebSocket events
  useEffect(() => {
    if (!lastEvent) return;

    switch (lastEvent.type) {
      case "agent_status_changed":
        getAgents()
          .then(setAgents)
          .catch((err) => console.error("Failed to refresh agents:", err));
        break;
      case "trade_executed":
        getTrades()
          .then(setTrades)
          .catch((err) => console.error("Failed to refresh trades:", err));
        getBalance()
          .then(setBalance)
          .catch((err) => console.error("Failed to refresh balance:", err));
        break;
      case "new_report":
        getAllReports()
          .then(setReports)
          .catch((err) => console.error("Failed to refresh reports:", err));
        break;
      case "risk_alert":
        getAgents()
          .then(setAgents)
          .catch((err) => console.error("Failed to refresh agents:", err));
        break;
    }
  }, [lastEvent]);

  // Handle high-frequency price ticks on a separate channel
  useEffect(() => {
    if (!lastTick) return;
    const tick = lastTick;
    const tickPrice = Number(tick.price) || 0;

    // Update watchlist quotes
    setQuotes((prev) => {
      const idx = prev.findIndex((q) => q.stock_code === tick.stock_code);
      const updated: StockQuote = {
        stock_code: tick.stock_code ?? "",
        price: tick.price ?? "0",
        open: tick.open ?? "0",
        high: tick.high ?? "0",
        low: tick.low ?? "0",
        volume: tick.volume ?? "0",
        change_rate: tick.change_rate ?? "0",
        change_amount: tick.change_amount ?? "0",
        change_sign: tick.change_sign ?? "3",
      };
      if (idx >= 0) {
        const next = [...prev];
        next[idx] = updated;
        return next;
      }
      return [...prev, updated];
    });

    // Update holdings if this stock is held
    if (tickPrice > 0) {
      setBalance((prev) => {
        if (!prev) return prev;
        const idx = prev.items.findIndex((item) => item.pdno === tick.stock_code);
        if (idx < 0) return prev;

        const items = [...prev.items];
        const item = { ...items[idx] };
        item.prpr = tickPrice;
        item.evlu_pfls_amt = (tickPrice - item.pchs_avg_pric) * item.hldg_qty;
        item.evlu_pfls_rt =
          item.pchs_avg_pric > 0
            ? ((tickPrice - item.pchs_avg_pric) / item.pchs_avg_pric) * 100
            : 0;
        items[idx] = item;

        const total_evlu_amt = items.reduce((sum, i) => sum + i.prpr * i.hldg_qty, 0);
        const total_evlu_pfls_amt = items.reduce((sum, i) => sum + i.evlu_pfls_amt, 0);

        return { items, total_evlu_amt, total_evlu_pfls_amt };
      });
    }
  }, [lastTick]);

  return {
    agents,
    trades,
    balance,
    reports,
    quotes,
    marketStatus,
    loading,
    isConnected,
    refetchPrices,
  };
}
