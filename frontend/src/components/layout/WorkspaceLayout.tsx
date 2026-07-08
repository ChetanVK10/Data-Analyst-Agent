import React from 'react';
import { Sidebar } from './Sidebar';
import { RightSidebar } from './RightSidebar';

interface WorkspaceLayoutProps {
  children: React.ReactNode;
  sidebarProps: React.ComponentProps<typeof Sidebar>;
  rightSidebarProps: React.ComponentProps<typeof RightSidebar>;
  showRightSidebar?: boolean;
}

export function WorkspaceLayout({
  children,
  sidebarProps,
  rightSidebarProps,
  showRightSidebar = true
}: WorkspaceLayoutProps) {
  return (
    <div className="flex h-screen w-full overflow-hidden bg-background text-foreground">
      {/* Left Sidebar */}
      <Sidebar {...sidebarProps} />

      {/* Main Content Area */}
      <main className="flex flex-1 flex-col min-w-0 overflow-hidden relative">
        {children}
      </main>

      {/* Right Sidebar */}
      {showRightSidebar && (
        <RightSidebar {...rightSidebarProps} />
      )}
    </div>
  );
}
