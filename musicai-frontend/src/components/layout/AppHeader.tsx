import { Moon, Sun, Music2 } from 'lucide-react';

interface AppHeaderProps {
  darkMode: boolean;
  onToggleDark: () => void;
}

export default function AppHeader({ darkMode, onToggleDark }: AppHeaderProps) {
  return (
    <header className="h-12 border-b border-border flex items-center px-4 gap-3 shrink-0 bg-background z-50">
      <div className="flex items-center gap-2 text-foreground">
        <Music2 size={16} className="text-primary" />
        <span className="font-semibold text-sm tracking-tight">MusicAI</span>
      </div>
      <div className="ml-auto flex items-center gap-2">
        <button
          onClick={onToggleDark}
          className="h-8 w-8 rounded-md flex items-center justify-center text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
          title={darkMode ? 'Modo claro' : 'Modo oscuro'}
        >
          {darkMode ? <Sun size={15} /> : <Moon size={15} />}
        </button>
      </div>
    </header>
  );
}
