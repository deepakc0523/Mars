"use client";

/**
 * useWebSocket — React hook for a MARS WebSocket connection.
 *
 * Manages the MarsWebSocket lifecycle (connect on mount, destroy on unmount)
 * and exposes connection status and the last received message.
 *
 * Usage:
 *   const { status, lastMessage, send } = useWebSocket({ path: "/ws/events" });
 */

import { useCallback, useEffect, useRef, useState } from "react";

import { MarsWebSocket } from "@/lib/websocket";
import type { WsMessage } from "@/types/mars";

type ConnectionStatus = "idle" | "connecting" | "connected" | "disconnected" | "error";

interface UseWebSocketOptions {
  /** WebSocket path, e.g. "/ws/events". */
  path: string;
  /** Whether to connect immediately (default: true). */
  enabled?: boolean;
}

interface UseWebSocketReturn {
  status: ConnectionStatus;
  lastMessage: WsMessage | null;
  send: (data: unknown) => void;
}

export function useWebSocket({
  path,
  enabled = true,
}: UseWebSocketOptions): UseWebSocketReturn {
  const [status, setStatus] = useState<ConnectionStatus>("idle");
  const [lastMessage, setLastMessage] = useState<WsMessage | null>(null);
  const wsRef = useRef<MarsWebSocket | null>(null);

  useEffect(() => {
    if (!enabled) return;

    const ws = new MarsWebSocket({
      path,
      onMessage: (msg) => setLastMessage(msg),
      onStatus: (s) => setStatus(s),
    });

    wsRef.current = ws;
    ws.connect();

    return () => {
      ws.destroy();
      wsRef.current = null;
    };
  }, [path, enabled]);

  const send = useCallback((data: unknown) => {
    wsRef.current?.send(data);
  }, []);

  return { status, lastMessage, send };
}
