import React from 'react';
import { motion } from 'framer-motion';
import {
  BarChart3, Settings, Bell, Sun, Moon, ChevronDown, Sparkles, Layers
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface TopNavProps {
  activeView: 'workspace' | 'analytics' | 'settings';
  onViewChange: (v: 'workspace' | 'analytics' | 'settings') => void;
  isDark: boolean;
  onThemeToggle: () => void;
}

const NAV_ITEMS = [
  { id: 'workspace', label: 'Workspace', icon: Layers },
  { id: 'analytics', label: 'Analytics', icon: BarChart3 },
  { id: 'settings',  label: 'Settings',  icon: Settings },
] as const;

export const TopNav: React.FC<TopNavProps> = ({
  activeView, onViewChange, isDark, onThemeToggle
}) => {
  return (
    <header className="fixed top-0 left-0 right-0 z-50 h-[58px] flex items-center px-5 border-b border-white/[0.06] glass-nav">
      {/* ── Brand ── */}
      <div className="flex items-center gap-3 w-[264px] shrink-0">
        <div className="flex items-center justify-center w-8 h-8 rounded-xl bg-gradient-to-br from-violet-500/20 to-indigo-500/10 border border-violet-500/20 shadow-[0_0_12px_rgba(139,92,246,0.15)]">
          <Sparkles size={14} className="text-violet-400" />
        </div>
        <div className="flex items-center gap-2">
          <span className="font-bold text-[13.5px] text-white tracking-tight leading-none">
            DataAgent
          </span>
          <span className="badge badge-accent text-[9px] px-1.5 py-0.5 tracking-widest">PRO</span>
        </div>
      </div>

      {/* ── Center Navigation ── */}
      <nav className="flex items-center gap-0.5 flex-1 justify-center" role="navigation" aria-label="Main navigation">
        {NAV_ITEMS.map(({ id, label, icon: Icon }) => {
          const isActive = activeView === id;
          return (
            <button
              key={id}
              onClick={() => onViewChange(id)}
              aria-current={isActive ? 'page' : undefined}
              className={cn(
                'relative flex items-center gap-2 px-4 h-9 rounded-xl text-[13px] font-medium transition-all duration-150 cursor-pointer focus-ring',
                isActive
                  ? 'text-white'
                  : 'text-[#6B6B80] hover:text-[#A0A0B0] hover:bg-white/[0.04]'
              )}
            >
              <Icon size={14} className="relative z-10 shrink-0" />
              <span className="relative z-10">{label}</span>

              {isActive && (
                <motion.div
                  layoutId="nav-pill"
                  className="absolute inset-0 rounded-xl bg-white/[0.06] border border-white/[0.08]"
                  transition={{ type: 'spring', stiffness: 420, damping: 34 }}
                />
              )}

              {/* Active underline accent */}
              {isActive && (
                <motion.div
                  layoutId="nav-underline"
                  className="absolute bottom-0 left-1/2 -translate-x-1/2 h-[2px] w-4 rounded-full bg-violet-400"
                  transition={{ type: 'spring', stiffness: 420, damping: 34 }}
                />
              )}
            </button>
          );
        })}
      </nav>

      {/* ── Right Actions ── */}
      <div className="flex items-center gap-1.5 ml-auto">
        {/* Theme Toggle */}
        <button
          onClick={onThemeToggle}
          className="flex items-center justify-center w-8 h-8 rounded-lg text-[#6B6B80] hover:text-[#A0A0B0] hover:bg-white/[0.05] transition-all cursor-pointer focus-ring"
          title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
          aria-label="Toggle theme"
        >
          {isDark ? <Sun size={14} /> : <Moon size={14} />}
        </button>

        {/* Notifications */}
        <button
          className="relative flex items-center justify-center w-8 h-8 rounded-lg text-[#6B6B80] hover:text-[#A0A0B0] hover:bg-white/[0.05] transition-all cursor-pointer focus-ring"
          title="Notifications"
          aria-label="Notifications"
        >
          <Bell size={14} />
          <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-violet-500 shadow-[0_0_6px_rgba(139,92,246,0.5)]" />
        </button>

        {/* Divider */}
        <div className="w-px h-5 bg-white/[0.07] mx-1.5" aria-hidden="true" />

        {/* User Avatar */}
        <button
          className="flex items-center gap-2 pl-2 pr-2.5 h-8 rounded-xl hover:bg-white/[0.05] border border-transparent hover:border-white/[0.06] transition-all cursor-pointer focus-ring"
          aria-label="User menu"
        >
          <div className="w-6 h-6 rounded-full bg-gradient-to-br from-violet-500 to-indigo-500 flex items-center justify-center shrink-0 shadow-[0_0_8px_rgba(139,92,246,0.3)]">
            <span className="text-[10px] font-bold text-white leading-none">A</span>
          </div>
          <span className="text-[12.5px] font-semibold text-[#A0A0B0]">Analyst</span>
          <ChevronDown size={11} className="text-[#46465A]" />
        </button>
      </div>
    </header>
  );
};

export default TopNav;
