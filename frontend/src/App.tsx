import React, { useState, useEffect } from "react";
import { TopBar } from "./components/layout/TopBar";
import { Sidebar } from "./components/layout/Sidebar";
import { ContextPanel } from "./components/context/ContextPanel";
import { BottomCommandBar } from "./components/layout/BottomCommandBar";
import { ConfirmationModal } from "./components/ConfirmationModal";
import { AliveIndicator } from "./components/runtime/AliveIndicator";
import { VoiceStatus } from "./components/voice/VoiceStatus";
import { RuntimePanel } from "./components/runtime/RuntimePanel";
import { BackgroundTaskDrawer } from "./components/tasks/BackgroundTaskDrawer";

import { Home } from "./pages/Home";
import { ConversationPanel } from "./components/ConversationPanel";
import { Memory } from "./pages/Memory";
import { Vision } from "./pages/Vision";
import { Goals } from "./pages/Goals";
import { Routines } from "./pages/Routines";
import { Reminders } from "./pages/Reminders";
import { ActivityPage } from "./pages/Activity";
import { Models } from "./pages/Models";
import { Tools } from "./pages/Tools";
import { System } from "./pages/System";
import { Developer } from "./pages/Developer";
import { SettingsPage } from "./pages/Settings";

import { wsClient } from "./websocket";
import {
  PageView,
  RaphaelStateType,
  SystemMetrics,
  ChatMessage,
  ToolExecutionRecord,
  SecurityConfirmationRequest,
  WSEvent,
  RuntimeHeartbeat,
  RuntimeHealth,
  BackgroundTask,
  AudioStateType,
  RuntimeModeType,
} from "./types";

export const App: React.FC = () => {
  const [currentPage, setCurrentPage] = useState<PageView>("home");
  const [state, setState] = useState<RaphaelStateType>("idle");
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [toolRecords, setToolRecords] = useState<ToolExecutionRecord[]>([]);
  const [events, setEvents] = useState<WSEvent[]>([]);
  const [confirmReq, setConfirmReq] = useState<SecurityConfirmationRequest | null>(null);
  const [isDemoMode, setIsDemoMode] = useState<boolean>(false);
  const [isListening, setIsListening] = useState<boolean>(false);
  const [partialText, setPartialText] = useState<string>("");
  const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(false);
  const [contextCollapsed, setContextCollapsed] = useState<boolean>(false);

  // Always-Alive runtime state (Sections 65-71)
  const [heartbeat, setHeartbeat] = useState<RuntimeHeartbeat | null>(null);
  const [health, setHealth] = useState<RuntimeHealth | null>(null);
  const [tasks, setTasks] = useState<BackgroundTask[]>([]);
  const [audioState, setAudioState] = useState<AudioStateType>("AUDIO_IDLE");
  const [runtimeMode, setRuntimeModeState] = useState<RuntimeModeType>("NORMAL");
  const [taskDrawerOpen, setTaskDrawerOpen] = useState<boolean>(false);
  const [runtimePanelOpen, setRuntimePanelOpen] = useState<boolean>(false);

  const [availableTools, setAvailableTools] = useState<any[]>([]);
  const [memories, setMemories] = useState<any[]>([]);

  const [contextData, setContextData] = useState<any>({
    application: "VS Code",
    window: "Raphael Workspace",
    activity: "Python Development",
    project: "Raphael v3",
    activeGoal: "Cognitive Memory & Vision System",
    confidence: 0.94
  });

  const fetchBrainData = () => {
    fetch("http://localhost:8765/api/brain/context")
      .then((res) => res.json())
      .then((data) => {
        if (data.recent_screen) {
          setContextData((prev: any) => ({
            ...prev,
            application: data.recent_screen.active_app || prev.application,
            window: data.recent_screen.window_title || prev.window,
            activity: data.recent_screen.activity || prev.activity
          }));
        }
        if (data.active_goal) {
          setContextData((prev: any) => ({ ...prev, activeGoal: data.active_goal }));
        }
      })
      .catch(() => {});

    fetch("http://localhost:8765/api/tools")
      .then((res) => res.json())
      .then((data) => setAvailableTools(data))
      .catch(() => {});

    fetch("http://localhost:8765/api/memories")
      .then((res) => res.json())
      .then((data) => setMemories(data))
      .catch(() => {});

    // Always-Alive runtime: pull health + task list on each refresh (Sections 65-71).
    wsClient.fetchRuntimeHealth().then((h) => h && setHealth(h));
    wsClient.fetchTasks().then((t) => t && setTasks(t));
  };

  useEffect(() => {
    wsClient.connect();

    const unsubscribe = wsClient.subscribe((event: WSEvent) => {
      setEvents((prev) => [...prev.slice(-100), event]);

      if (event.type === "assistant.state") {
        const rawState = (event.state || "idle").toLowerCase() as RaphaelStateType;
        setState(rawState);
        if (event.metrics) setMetrics(event.metrics);
      } else if (event.type === "system.metrics") {
        setMetrics(event);
      } else if (event.type === "assistant.response" || event.type === "assistant.message") {
        setMessages((prev) => [
          ...prev,
          {
            id: String(Date.now()),
            sender: "raphael",
            text: event.text || event.message,
            timestamp: event.timestamp || Date.now() / 1000,
            toolResult: event.tool_result
          }
        ]);
      } else if (event.type === "tool.started") {
        setToolRecords((prev) => [
          {
            id: String(Date.now()),
            action: event.tool,
            status: "started",
            timestamp: event.timestamp || Date.now() / 1000
          },
          ...prev
        ]);
      } else if (event.type === "tool.completed" || event.type === "tool.failed") {
        setToolRecords((prev) =>
          prev.map((t) =>
            t.action === event.tool && t.status === "started"
              ? {
                  ...t,
                  status: event.status || (event.type === "tool.completed" ? "success" : "failed"),
                  duration_ms: event.duration_ms,
                  result: event.result,
                  error: event.error
                }
              : t
          )
        );
      } else if (event.type === "voice.stt.partial") {
        setPartialText(event.text);
      } else if (event.type === "voice.stt.completed") {
        setPartialText("");
      } else if (event.type === "security.confirm_request") {
        setConfirmReq({
          request_id: event.request_id,
          tool_name: event.tool_name,
          args: event.args,
          reason: event.reason,
          timeout_seconds: event.timeout_seconds
        });
      } else if (event.type === "runtime.heartbeat") {
        setHeartbeat(event as unknown as RuntimeHeartbeat);
        if (event.components) {
          setHealth({ runtime: event.runtime, uptime_seconds: event.uptime, components: event.components, timestamp: event.timestamp || Date.now() / 1000 });
        }
      } else if (event.type === "runtime.health") {
        setHealth(event as unknown as RuntimeHealth);
      } else if (event.type === "runtime.mode") {
        setRuntimeModeState((event.mode as RuntimeModeType) || "NORMAL");
      } else if (event.type === "audio.state") {
        setAudioState((event.state as AudioStateType) || "AUDIO_IDLE");
      } else if (event.type?.startsWith("task.")) {
        // Task events (Section 70): refresh the task list from the backend.
        wsClient.fetchTasks().then((t) => t && setTasks(t));
      }
    });

    fetchBrainData();

    return () => {
      unsubscribe();
    };
  }, []);

  const handleSendMessage = (text: string) => {
    setMessages((prev) => [
      ...prev,
      {
        id: String(Date.now()),
        sender: "user",
        text,
        timestamp: Date.now() / 1000
      }
    ]);
    wsClient.sendMessage(text);
  };

  const handleToggleDemoMode = () => {
    const nextMode = !isDemoMode;
    setIsDemoMode(nextMode);
    wsClient.setDemoMode(nextMode);
  };

  const handleToggleListening = () => {
    if (!isListening) {
      setIsListening(true);
      if ("webkitSpeechRecognition" in window || "SpeechRecognition" in window) {
        const SpeechRec = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
        const recognition = new SpeechRec();
        recognition.continuous = false;
        recognition.interimResults = true;

        recognition.onresult = (e: any) => {
          const transcript = Array.from(e.results)
            .map((res: any) => res[0].transcript)
            .join("");
          const isFinal = e.results[0].isFinal;

          if (isFinal) {
            setIsListening(false);
            handleSendMessage(transcript);
          } else {
            setPartialText(transcript);
          }
        };

        recognition.onerror = () => setIsListening(false);
        recognition.onend = () => setIsListening(false);
        recognition.start();
      }
    } else {
      setIsListening(false);
      setPartialText("");
    }
  };

  const handleRespondConfirmation = (approved: boolean) => {
    if (confirmReq) {
      wsClient.sendConfirmResponse(confirmReq.request_id, approved);
      setConfirmReq(null);
    }
  };

  const handleForgetMemory = (keyword: string) => {
    fetch("http://localhost:8765/api/brain/forget", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ keyword })
    })
      .then((res) => res.json())
      .then(() => fetchBrainData())
      .catch(() => {});
  };

  return (
    <div className="h-screen w-screen bg-[#05080d] text-slate-100 flex flex-col font-primary overflow-hidden select-none">
      {/* Top Bar */}
      <TopBar
        status={wsClient.isConnected ? "online" : "offline"}
        state={state}
        modelName="Qwen / Ollama"
        metrics={metrics}
        currentPage={currentPage}
        onNavigate={setCurrentPage}
        onToggleDemoMode={handleToggleDemoMode}
        isDemoMode={isDemoMode}
        alive={!!heartbeat}
        health={health}
        heartbeat={heartbeat}
        runtimeMode={runtimeMode}
        onToggleRuntimePanel={() => setRuntimePanelOpen(true)}
        taskCount={tasks.filter((t) => ["RUNNING", "QUEUED", "WAITING", "PAUSED"].includes(t.status)).length}
        onToggleTaskDrawer={() => setTaskDrawerOpen(true)}
      />

      {/* Main Workspace Area (Sidebar + Center Content + Context Panel) */}
      <div className="flex-1 flex overflow-hidden min-h-0">
        {/* Left Collapsible Sidebar */}
        <Sidebar
          currentPage={currentPage}
          onNavigate={setCurrentPage}
          collapsed={sidebarCollapsed}
          onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        />

        {/* Center Primary Page Content */}
        <main className="flex-1 flex flex-col bg-[#05080d] overflow-hidden min-w-0">
          {currentPage === "home" && (
            <Home
              state={state}
              messages={messages}
              metrics={metrics}
              onSendMessage={handleSendMessage}
              onNavigate={setCurrentPage}
            />
          )}

          {currentPage === "chat" && (
            <div className="h-full p-4">
              <ConversationPanel
                messages={messages}
                partialText={partialText}
                onSendMessage={handleSendMessage}
                isListening={isListening}
                onToggleListening={handleToggleListening}
              />
            </div>
          )}

          {currentPage === "memory" && <Memory onForgetMemory={handleForgetMemory} />}
          {currentPage === "vision" && <Vision />}
          {currentPage === "goals" && <Goals />}
          {currentPage === "routines" && <Routines />}
          {currentPage === "reminders" && <Reminders />}
          {currentPage === "activity" && <ActivityPage />}
          {currentPage === "models" && <Models />}
          {currentPage === "tools" && <Tools />}
          {currentPage === "system" && <System metrics={metrics} />}
          {currentPage === "developer" && (
            <Developer events={events} tools={availableTools} memories={memories} />
          )}
          {currentPage === "settings" && <SettingsPage />}
        </main>

        {/* Right Collapsible Context Panel */}
        <ContextPanel
          context={contextData}
          onNavigate={setCurrentPage}
          collapsed={contextCollapsed}
          onToggleCollapse={() => setContextCollapsed(!contextCollapsed)}
        />
      </div>

      {/* Bottom Command Bar */}
      <BottomCommandBar
        onSendMessage={handleSendMessage}
        isListening={isListening}
        onToggleListening={handleToggleListening}
        partialText={partialText}
      />

      {/* Security Interactive Confirmation Modal */}
      <ConfirmationModal
        request={confirmReq}
        onRespond={handleRespondConfirmation}
      />

      {/* Always-Alive: Voice status (privacy-aware, Section 35) */}
      <VoiceStatus audioState={audioState} />

      {/* Always-Alive: Background Task Drawer (Section 66/38) */}
      <BackgroundTaskDrawer
        open={taskDrawerOpen}
        onClose={() => setTaskDrawerOpen(false)}
        tasks={tasks}
        onPause={(id) => { wsClient.taskAction(id, "pause"); }}
        onResume={(id) => { wsClient.taskAction(id, "resume"); }}
        onCancel={(id) => { wsClient.taskAction(id, "cancel"); }}
        onRetry={(id) => { wsClient.taskAction(id, "retry"); }}
      />

      {/* Always-Alive: Runtime Health Panel (Section 67/69) */}
      <RuntimePanel
        open={runtimePanelOpen}
        onClose={() => setRuntimePanelOpen(false)}
        health={health}
        heartbeat={heartbeat}
        runtimeMode={runtimeMode}
        onSetMode={(m) => { wsClient.setRuntimeMode(m); }}
        onInterrupt={() => { wsClient.interrupt(); }}
      />
    </div>
  );
};
