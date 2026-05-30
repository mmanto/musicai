import { useState } from 'react';
import type { ReactNode } from 'react';
import AppHeader from './AppHeader';
import LeftSidebar from './LeftSidebar';
import { OllamaPanel } from '../OllamaPanel';

interface AppShellProps {
  children: ReactNode;
  darkMode: boolean;
  onToggleDark: () => void;
}

export default function AppShell({ children, darkMode, onToggleDark }: AppShellProps) {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <div className="h-screen flex flex-col bg-background text-foreground">
      <AppHeader darkMode={darkMode} onToggleDark={onToggleDark} />
      <div className="flex flex-1 overflow-hidden">
        <LeftSidebar open={sidebarOpen} onToggle={() => setSidebarOpen((s) => !s)} />
        <main className="flex-1 flex flex-col overflow-hidden min-w-0">
          {children}
        </main>
      </div>
      <OllamaPanel />
    </div>
  );
}
