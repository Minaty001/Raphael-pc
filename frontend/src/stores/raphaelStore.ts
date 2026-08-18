import { useState, useEffect } from "react";
import { PageView, RaphaelStateType, SystemMetrics, ChatMessage, ActivityEvent, MemoryRecord, GoalItem, WSEvent } from "../types";

export interface RaphaelStoreState {
  currentPage: PageView;
  assistantState: RaphaelStateType;
  isListening: boolean;
  isDemoMode: boolean;
  activeModel: string;
  metrics: SystemMetrics | null;
  messages: ChatMessage[];
  events: WSEvent[];
  memories: MemoryRecord[];
  goals: GoalItem[];
  context: {
    application?: string;
    window?: string;
    activity?: string;
    project?: string;
    activeGoal?: string;
    confidence?: number;
  };
}

let storeState: RaphaelStoreState = {
  currentPage: "home",
  assistantState: "idle",
  isListening: false,
  isDemoMode: false,
  activeModel: "Ollama / Qwen",
  metrics: { cpu_percent: 12, memory_percent: 42, disk_percent: 18 },
  messages: [],
  events: [],
  memories: [],
  goals: [],
  context: {
    application: "VS Code",
    window: "Raphael Workspace",
    activity: "Python Development",
    project: "Raphael v3",
    activeGoal: "Cognitive Memory & Vision System",
    confidence: 0.94
  }
};

const listeners = new Set<() => void>();

export const getRaphaelStore = () => storeState;

export const setRaphaelStore = (updater: (prev: RaphaelStoreState) => RaphaelStoreState) => {
  storeState = updater(storeState);
  listeners.forEach((listener) => listener());
};

export const useRaphaelStore = () => {
  const [state, setState] = useState<RaphaelStoreState>(storeState);

  useEffect(() => {
    const listener = () => setState(storeState);
    listeners.add(listener);
    return () => {
      listeners.delete(listener);
    };
  }, []);

  return state;
};
