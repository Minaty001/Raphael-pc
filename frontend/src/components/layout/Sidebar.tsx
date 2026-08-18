import React from "react";
import { PageView } from "../../types";
import {
  Home,
  MessageSquare,
  Brain,
  Eye,
  Target,
  Repeat,
  Bell,
  Activity,
  Cpu,
  Wrench,
  Server,
  Terminal,
  Settings,
  ChevronLeft,
  ChevronRight
} from "lucide-react";

interface SidebarProps {
  currentPage: PageView;
  onNavigate: (page: PageView) => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentPage,
  onNavigate,
  collapsed,
  onToggleCollapse
}) => {
  const navItems: { id: PageView; label: string; icon: React.ReactNode }[] = [
    { id: "home", label: "HOME", icon: <Home className="w-4 h-4" /> },
    { id: "chat", label: "CHAT", icon: <MessageSquare className="w-4 h-4" /> },
    { id: "memory", label: "MEMORY", icon: <Brain className="w-4 h-4" /> },
    { id: "vision", label: "VISION", icon: <Eye className="w-4 h-4" /> },
    { id: "goals", label: "GOALS", icon: <Target className="w-4 h-4" /> },
    { id: "routines", label: "ROUTINES", icon: <Repeat className="w-4 h-4" /> },
    { id: "reminders", label: "REMINDERS", icon: <Bell className="w-4 h-4" /> },
    { id: "activity", label: "ACTIVITY", icon: <Activity className="w-4 h-4" /> },
    { id: "models", label: "MODELS", icon: <Cpu className="w-4 h-4" /> },
    { id: "tools", label: "TOOLS", icon: <Wrench className="w-4 h-4" /> },
    { id: "system", label: "SYSTEM", icon: <Server className="w-4 h-4" /> },
    { id: "developer", label: "DEVELOPER", icon: <Terminal className="w-4 h-4" /> },
    { id: "settings", label: "SETTINGS", icon: <Settings className="w-4 h-4" /> }
  ];

  return (
    <aside
      className={`border-r border-[var(--border)] bg-[#070c14]/95 backdrop-blur flex flex-col transition-all duration-300 shrink-0 z-30 select-none ${
        collapsed ? "w-14" : "w-52"
      }`}
    >
      {/* Navigation Items */}
      <div className="flex-1 overflow-y-auto py-3 px-2 space-y-1">
        {navItems.map((item) => {
          const isActive = currentPage === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              className={`w-full flex items-center gap-3 px-2.5 py-2 rounded-md font-mono text-xs transition-all ${
                isActive
                  ? "bg-[var(--accent-primary)]/15 border border-[var(--accent-primary)]/50 text-[var(--accent-primary)] font-bold shadow-[0_0_10px_var(--glow)]"
                  : "text-[var(--text-secondary)] hover:text-white hover:bg-[var(--bg-secondary)]"
              }`}
              title={item.label}
            >
              <div className="shrink-0">{item.icon}</div>
              {!collapsed && <span className="truncate tracking-wider">{item.label}</span>}
            </button>
          );
        })}
      </div>

      {/* Collapse Toggle Button */}
      <div className="p-2 border-t border-[var(--border)] shrink-0">
        <button
          onClick={onToggleCollapse}
          className="w-full flex items-center justify-center p-2 rounded hover:bg-[var(--bg-secondary)] text-[var(--text-secondary)] hover:text-white transition-colors"
          title={collapsed ? "Expand Sidebar" : "Collapse Sidebar"}
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>
    </aside>
  );
};
