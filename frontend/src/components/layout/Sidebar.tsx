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
  ChevronRight,
} from "lucide-react";

interface SidebarProps {
  currentPage: PageView;
  onNavigate: (page: PageView) => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
}

type NavItem = { id: PageView; label: string; icon: React.ReactNode; group: string };

const navItems: NavItem[] = [
  { id: "home", label: "Home", icon: <Home className="w-4 h-4" />, group: "Core" },
  { id: "chat", label: "Chat", icon: <MessageSquare className="w-4 h-4" />, group: "Core" },
  { id: "memory", label: "Memory", icon: <Brain className="w-4 h-4" />, group: "Core" },
  { id: "vision", label: "Vision", icon: <Eye className="w-4 h-4" />, group: "Awareness" },
  { id: "goals", label: "Goals", icon: <Target className="w-4 h-4" />, group: "Awareness" },
  { id: "routines", label: "Routines", icon: <Repeat className="w-4 h-4" />, group: "Awareness" },
  { id: "reminders", label: "Reminders", icon: <Bell className="w-4 h-4" />, group: "Awareness" },
  { id: "activity", label: "Activity", icon: <Activity className="w-4 h-4" />, group: "System" },
  { id: "models", label: "Models", icon: <Cpu className="w-4 h-4" />, group: "System" },
  { id: "tools", label: "Tools", icon: <Wrench className="w-4 h-4" />, group: "System" },
  { id: "system", label: "System", icon: <Server className="w-4 h-4" />, group: "System" },
  { id: "developer", label: "Developer", icon: <Terminal className="w-4 h-4" />, group: "System" },
  { id: "settings", label: "Settings", icon: <Settings className="w-4 h-4" />, group: "System" },
];

const groupOrder = ["Core", "Awareness", "System"];

export const Sidebar: React.FC<SidebarProps> = ({ currentPage, onNavigate, collapsed, onToggleCollapse }) => {
  return (
    <aside
      className={`shrink-0 z-30 flex flex-col border-r border-[var(--border)] bg-[#070c14]/95 backdrop-blur transition-all duration-300 ${
        collapsed ? "w-16" : "w-56"
      }`}
    >
      <div className="flex-1 overflow-y-auto py-3 px-2 space-y-3">
        {groupOrder.map((group) => (
          <div key={group} className="space-y-1">
            {!collapsed && (
              <div className="px-2.5 pb-1 text-[9px] font-mono uppercase tracking-[0.2em] text-[var(--text-muted)]">
                {group}
              </div>
            )}
            {navItems
              .filter((i) => i.group === group)
              .map((item) => {
                const isActive = currentPage === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => onNavigate(item.id)}
                    title={collapsed ? item.label : undefined}
                    className={`nav-item ${isActive ? "nav-item-active" : "nav-item-idle"} ${
                      collapsed ? "justify-center" : ""
                    }`}
                  >
                    <div className="shrink-0">{item.icon}</div>
                    {!collapsed && <span className="truncate">{item.label}</span>}
                  </button>
                );
              })}
          </div>
        ))}
      </div>

      <div className="p-2 border-t border-[var(--border)] shrink-0">
        <button
          onClick={onToggleCollapse}
          className="btn-ghost w-full flex items-center justify-center p-2"
          title={collapsed ? "Expand Sidebar" : "Collapse Sidebar"}
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>
    </aside>
  );
};
