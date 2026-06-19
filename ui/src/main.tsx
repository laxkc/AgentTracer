import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from './App';
import { showToast } from './utils/toast';
import './index.css';

// Create a query client for React Query
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

if (typeof window !== 'undefined') {
  const windowWithGuard = window as typeof window & {
    __agenttracerGlobalErrorHandlers?: boolean;
  };

  if (!windowWithGuard.__agenttracerGlobalErrorHandlers) {
    windowWithGuard.__agenttracerGlobalErrorHandlers = true;

    window.addEventListener('unhandledrejection', (event) => {
      console.error('Unhandled promise rejection:', event.reason);
      showToast.error('An unexpected error occurred. Please try again.');
    });

    window.addEventListener('error', (event) => {
      console.error('Global error:', event.error || event.message);
    });
  }
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>
);
