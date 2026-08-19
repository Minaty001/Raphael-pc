import {
  WSEvent,
  SystemMetrics,
  RuntimeHeartbeat,
  RuntimeHealth,
  BackgroundTask,
  AudioStateType,
  RuntimeModeType,
} from "./types";

type Listener = (event: WSEvent) => void;

export class RaphaelWebSocketClient {
  private socket: WebSocket | null = null;
  private listeners: Set<Listener> = new Set();
  private reconnectAttempts = 0;
  private maxReconnectDelay = 10000;
  private isDemoMode = false;
  public isConnected = false;

  constructor(private url: string = "ws://localhost:8765/ws") {}

  public setDemoMode(demo: boolean) {
    this.isDemoMode = demo;
    if (demo) {
      this.isConnected = true;
      this.emit({ type: "connection.opened", timestamp: Date.now() / 1000 });
      this.emit({ type: "assistant.state", state: "IDLE", timestamp: Date.now() / 1000 });
    } else {
      this.connect();
    }
  }

  public connect() {
    if (this.isDemoMode) return;

    try {
      this.socket = new WebSocket(this.url);

      this.socket.onopen = () => {
        this.isConnected = true;
        this.reconnectAttempts = 0;
        this.emit({ type: "connection.opened", timestamp: Date.now() / 1000 });
      };

      this.socket.onmessage = (event) => {
        try {
          const parsed: WSEvent = JSON.parse(event.data);
          this.emit(parsed);
        } catch (err) {
          console.warn("Failed to parse WS message:", event.data);
        }
      };

      this.socket.onclose = () => {
        this.isConnected = false;
        this.emit({ type: "connection.closed", timestamp: Date.now() / 1000 });
        this.emit({ type: "assistant.state", state: "OFFLINE", timestamp: Date.now() / 1000 });
        this.scheduleReconnect();
      };

      this.socket.onerror = (err) => {
        console.error("WebSocket error:", err);
      };
    } catch (e) {
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect() {
    if (this.isDemoMode) return;
    this.reconnectAttempts++;
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), this.maxReconnectDelay);
    setTimeout(() => this.connect(), delay);
  }

  public subscribe(listener: Listener) {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  private emit(event: WSEvent) {
    this.listeners.forEach((listener) => listener(event));
  }

  public sendMessage(text: string) {
    if (this.isDemoMode) {
      this.simulateDemoFlow(text);
      return;
    }
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({ type: "user.message", text }));
    }
  }

  public sendVoiceInput(text: string, isFinal: boolean = true) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({ type: "voice.stt.input", text, is_final: isFinal }));
    }
  }

  public sendConfirmResponse(requestId: string, approved: boolean) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({ type: "security.confirm_response", request_id: requestId, approved }));
    }
  }

  private simulateDemoFlow(text: string) {
    const clean = text.toLowerCase();

    // Emit user input event
    this.emit({ type: "assistant.state", state: "THINKING", timestamp: Date.now() / 1000 });

    setTimeout(() => {
      if (clean.includes("chrome") || clean.includes("open")) {
        this.emit({ type: "assistant.state", state: "EXECUTING", timestamp: Date.now() / 1000 });
        this.emit({ type: "tool.started", tool: "open_application", args: { app_name: "chrome" }, timestamp: Date.now() / 1000 });
        setTimeout(() => {
          this.emit({ type: "tool.completed", tool: "open_application", status: "success", duration_ms: 180, result: { app_name: "chrome" }, timestamp: Date.now() / 1000 });
          this.emit({ type: "assistant.state", state: "SPEAKING", timestamp: Date.now() / 1000 });
          this.emit({ type: "assistant.response", text: "Chrome is open.", timestamp: Date.now() / 1000 });
          setTimeout(() => this.emit({ type: "assistant.state", state: "IDLE", timestamp: Date.now() / 1000 }), 1500);
        }, 800);
      } else {
        this.emit({ type: "assistant.state", state: "SPEAKING", timestamp: Date.now() / 1000 });
        this.emit({ type: "assistant.response", text: `Raphael Assistant (Demo Mode): Received '${text}'. Systems optimal.`, timestamp: Date.now() / 1000 });
        setTimeout(() => this.emit({ type: "assistant.state", state: "IDLE", timestamp: Date.now() / 1000 }), 1500);
      }
    }, 600);
  }

  // ---- REST helpers for the Always-Alive Runtime (Sections 65-71) --------
  private async rest<T = any>(path: string, method: string = "GET", body?: any): Promise<T | null> {
    try {
      const res = await fetch(`http://localhost:8765${path}`, {
        method,
        headers: body ? { "Content-Type": "application/json" } : undefined,
        body: body ? JSON.stringify(body) : undefined,
      });
      if (!res.ok) return null;
      return (await res.json()) as T;
    } catch {
      return null;
    }
  }

  public async fetchRuntimeHealth(): Promise<RuntimeHealth | null> {
    return this.rest<RuntimeHealth>("/api/runtime/health");
  }

  public async fetchTasks(): Promise<BackgroundTask[]> {
    return (await this.rest<BackgroundTask[]>("/api/tasks")) ?? [];
  }

  public async setRuntimeMode(mode: RuntimeModeType): Promise<boolean> {
    return !!(await this.rest("/api/runtime/mode", "POST", { mode }));
  }

  public async taskAction(id: string, action: "pause" | "resume" | "cancel" | "retry"): Promise<boolean> {
    return !!(await this.rest(`/api/tasks/${id}/${action}`, "POST"));
  }

  public async interrupt(): Promise<boolean> {
    return !!(await this.rest("/api/runtime/interrupt", "POST"));
  }

  public async executeTool(name: string, args: Record<string, any> = {}): Promise<any | null> {
    return this.rest("/api/tools/execute", "POST", { tool: name, args });
  }
}

export const wsClient = new RaphaelWebSocketClient();
