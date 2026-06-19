/**
 * AgentTracer Application
 *
 * Main application component with routing and navigation.
 */

import React from "react";
import { Routes, Route } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import Sidebar from "./components/Sidebar";
import ErrorBoundary from "./components/ErrorBoundary";
import RunExplorer from "./components/RunExplorer";
import RunDetail from "./pages/RunDetail";
import Dashboard from "./pages/Dashboard";
import BehaviorDashboard from "./pages/BehaviorDashboard";
import BaselineManager from "./pages/BaselineManager";
import DriftDetail from "./pages/DriftDetail";
import DriftTimelinePage from "./pages/DriftTimelinePage";
import ProfileBuilder from "./pages/ProfileBuilder";
import DriftComparison from "./pages/DriftComparison";
import Decisions from "./pages/Decisions";
import QualitySignals from "./pages/QualitySignals";
import { useOnlineStatus } from "./hooks/useOnlineStatus";
import { API_CONFIG, API_ENDPOINTS } from "./config/api";

const App: React.FC = () => {
  const isOnline = useOnlineStatus();

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-gray-50">
        {/* Toast Notifications */}
        <Toaster position="top-right" />

        {/* Sidebar Navigation */}
        <Sidebar />

        {/* Main Content with sidebar offset */}
        <div className="lg:ml-64">
          {!isOnline && (
            <div className="sticky top-0 z-50 bg-yellow-500 text-white text-center text-sm py-2">
              You are offline. Some features may not be available.
            </div>
          )}
          <main className="pb-12">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/runs" element={<RunExplorer />} />
              <Route path="/runs/:runId" element={<RunDetail />} />
              <Route path="/decisions" element={<Decisions />} />
              <Route path="/signals" element={<QualitySignals />} />
              <Route path="/behaviors" element={<BehaviorDashboard />} />
              <Route path="/baselines" element={<BaselineManager />} />
              <Route path="/profiles" element={<ProfileBuilder />} />
              <Route path="/drift/compare" element={<DriftComparison />} />
              <Route path="/drift/:driftId" element={<DriftDetail />} />
              <Route path="/drift/timeline" element={<DriftTimelinePage />} />
            </Routes>
          </main>

        {/* Footer */}
          <footer className="bg-white border-t border-gray-200 mt-12">
            <div className="container mx-auto px-4 py-5">
              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 text-xs text-gray-500">
                <span>AgentTracer • Observability for AI Agents</span>
                <div className="flex items-center gap-4">
                  <a
                    href={`${API_CONFIG.INGEST_API_BASE_URL}${API_ENDPOINTS.HEALTH}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-gray-500 hover:text-gray-700"
                  >
                    Ingest API
                  </a>
                  <a
                    href={`${API_CONFIG.QUERY_API_BASE_URL}${API_ENDPOINTS.HEALTH}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-gray-500 hover:text-gray-700"
                  >
                    Query API
                  </a>
                </div>
              </div>
            </div>
          </footer>
        </div>
      </div>
    </ErrorBoundary>
  );
};

export default App;
