import {
  Activity,
  Award,
  BarChart2,
  ChevronLeft,
  ChevronRight,
  Grid3X3,
  LogOut,
  Menu,
  Settings2,
  Sparkles,
  Users,
  Zap,
} from "lucide-react";

type Tab = "mrr" | "cohort" | "metrics" | "benchmarks" | "crm" | "setup" | "settings" | "ai";

interface SidebarProps {
  activeTab: Tab;
  onTabChange: (tab: Tab) => void;
  collapsed: boolean;
  onToggle: () => void;
  userName: string | null;
  onSignOut: () => void;
  mobileSidebarOpen: boolean;
  onMobileSidebarClose: () => void;
}

interface NavItem {
  tab: Tab;
  icon: React.ElementType;
  label: string;
  dot?: boolean;
}

const ANALYTICS_ITEMS: NavItem[] = [
  { tab: "mrr",        icon: BarChart2, label: "MRR" },
  { tab: "cohort",     icon: Grid3X3,   label: "Cohort" },
  { tab: "metrics",    icon: Activity,  label: "Metrics" },
  { tab: "benchmarks", icon: Award,     label: "Benchmarks" },
];

const GROWTH_ITEMS: NavItem[] = [
  { tab: "crm", icon: Users,    label: "CRM" },
  { tab: "ai",  icon: Sparkles, label: "AI Copilot", dot: true },
];

const WORKSPACE_ITEMS: NavItem[] = [
  { tab: "setup",    icon: Zap,      label: "Setup" },
  { tab: "settings", icon: Settings2, label: "Settings" },
];

function initials(name: string | null): string {
  if (!name) return "RS";
  return name
    .split(" ")
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? "")
    .join("");
}

function SidebarContent({
  activeTab,
  onTabChange,
  collapsed,
  onToggle,
  userName,
  onSignOut,
  onClose,
}: SidebarProps & { onClose?: () => void }) {
  function NavGroup({ items }: { items: NavItem[] }) {
    return (
      <div className="space-y-0.5 px-2">
        {items.map(({ tab, icon: Icon, label, dot }) => {
          const active = tab === activeTab;
          return (
            <button
              key={tab}
              type="button"
              onClick={() => { onTabChange(tab); onClose?.(); }}
              className={`w-full flex items-center gap-3 rounded-lg px-2.5 py-2 text-sm transition-all duration-150 relative ${
                active
                  ? "bg-[var(--surface-2)] text-[var(--brand)] border-l-2 border-[var(--brand)] pl-[9px]"
                  : "text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-1)] border-l-2 border-transparent"
              }`}
            >
              <Icon size={16} className="shrink-0" />
              {!collapsed && (
                <span className="font-medium truncate">{label}</span>
              )}
              {!collapsed && dot && (
                <span className="ml-auto w-1.5 h-1.5 rounded-full bg-[var(--brand)] opacity-70" />
              )}
            </button>
          );
        })}
      </div>
    );
  }

  function GroupLabel({ label }: { label: string }) {
    if (collapsed) return <div className="h-px mx-4 bg-[var(--border-subtle)] my-2" />;
    return (
      <p className="px-4 pb-1 pt-3 text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--text-muted)]">
        {label}
      </p>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Logo */}
      <div className={`flex items-center gap-2.5 px-4 h-14 border-b border-[var(--border-subtle)] shrink-0 ${collapsed ? "justify-center" : ""}`}>
        <div className="w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold text-[var(--brand)] shrink-0"
          style={{ background: "var(--brand-dim)" }}>
          RS
        </div>
        {!collapsed && (
          <span className="text-sm font-semibold text-[var(--text-primary)] tracking-tight">
            RazorScope
          </span>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-2">
        <GroupLabel label="Analytics" />
        <NavGroup items={ANALYTICS_ITEMS} />

        <GroupLabel label="Growth" />
        <NavGroup items={GROWTH_ITEMS} />

        <div className="h-px mx-4 bg-[var(--border-subtle)] my-3" />

        <GroupLabel label="Workspace" />
        <NavGroup items={WORKSPACE_ITEMS} />
      </nav>

      {/* Bottom */}
      <div className="shrink-0 border-t border-[var(--border-subtle)] p-3 space-y-1">
        <div className={`flex items-center gap-2.5 px-2 py-1.5 rounded-lg ${collapsed ? "justify-center" : ""}`}>
          <div className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold shrink-0 text-[var(--brand)]"
            style={{ background: "var(--brand-dim)" }}>
            {initials(userName)}
          </div>
          {!collapsed && (
            <p className="text-xs font-medium text-[var(--text-secondary)] truncate flex-1">
              {userName ?? "Account"}
            </p>
          )}
          {!collapsed && (
            <button
              type="button"
              onClick={onSignOut}
              className="text-[var(--text-muted)] hover:text-[var(--text-secondary)] transition-colors"
              title="Sign out"
            >
              <LogOut size={14} />
            </button>
          )}
        </div>

        {collapsed && (
          <button
            type="button"
            onClick={onSignOut}
            className="w-full flex items-center justify-center py-1.5 text-[var(--text-muted)] hover:text-[var(--text-secondary)] transition-colors"
            title="Sign out"
          >
            <LogOut size={14} />
          </button>
        )}

        {/* Collapse toggle */}
        <button
          type="button"
          onClick={onToggle}
          className={`w-full flex items-center rounded-lg px-2.5 py-1.5 text-xs text-[var(--text-muted)] hover:text-[var(--text-secondary)] hover:bg-[var(--surface-1)] transition-all ${collapsed ? "justify-center" : "gap-2"}`}
        >
          {collapsed ? <ChevronRight size={14} /> : <><ChevronLeft size={14} /><span>Collapse</span></>}
        </button>
      </div>
    </div>
  );
}

export default function Sidebar(props: SidebarProps) {
  const { collapsed, mobileSidebarOpen, onMobileSidebarClose } = props;

  return (
    <>
      {/* Desktop sidebar */}
      <aside
        className={`hidden md:flex flex-col fixed inset-y-0 left-0 z-30 transition-[width] duration-200 border-r border-[var(--border-subtle)] ${
          collapsed ? "w-[52px]" : "w-[220px]"
        }`}
        style={{ background: "var(--bg-1)" }}
      >
        <SidebarContent {...props} />
      </aside>

      {/* Mobile backdrop */}
      {mobileSidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm md:hidden"
          onClick={onMobileSidebarClose}
        />
      )}

      {/* Mobile slide-over */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-[220px] flex flex-col border-r border-[var(--border-subtle)] transition-transform duration-200 md:hidden ${
          mobileSidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
        style={{ background: "var(--bg-1)" }}
      >
        <SidebarContent {...props} onClose={onMobileSidebarClose} />
      </aside>
    </>
  );
}

export { Menu };
