import { useState, useEffect } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import AppShell from './components/layout/AppShell';
import MainView from './components/MainView';
import './App.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { refetchOnWindowFocus: false, retry: 1 },
  },
});

function App() {
  const [darkMode, setDarkMode] = useState(() => {
    return (
      localStorage.getItem('theme') === 'dark' ||
      (!localStorage.getItem('theme') &&
        window.matchMedia('(prefers-color-scheme: dark)').matches)
    );
  });

  useEffect(() => {
    localStorage.setItem('theme', darkMode ? 'dark' : 'light');
  }, [darkMode]);

  return (
    <QueryClientProvider client={queryClient}>
      <div className={`app ${darkMode ? 'dark' : ''}`}>
        <AppShell darkMode={darkMode} onToggleDark={() => setDarkMode((d) => !d)}>
          <MainView />
        </AppShell>
      </div>
    </QueryClientProvider>
  );
}

export default App;
