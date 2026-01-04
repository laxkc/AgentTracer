/**
 * AgentTracer Application
 *
 * Main application component with routing and navigation.
 */

import React from "react";
import { Routes, Route } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import Sidebar from "./components/Sidebar";
import RunExplorer from "./components/RunExplorer";
import RunDetail from "./pages/RunDetail";
import Dashboard from "./pages/Dashboard";
import BehaviorDashboard from "./pages/BehaviorDashboard";
import BaselineManager from "./pages/BaselineManager";
import DriftDetail from "./pages/DriftDetail";
import DriftTimelinePage from "./pages/DriftTimelinePage";
import ProfileBuilder from "./pages/ProfileBuilder";
import DriftComparison from "./pages/DriftComparison";

const App: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Toast Notifications */}
      <Toaster position="top-right" />

      {/* Sidebar Navigation */}
      <Sidebar />

      {/* Main Content with sidebar offset */}
      <div className="lg:ml-64">
        <main className="pb-12">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/runs" element={<RunExplorer />} />
            <Route path="/runs/:runId" element={<RunDetail />} />
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
          <div className="container mx-auto px-4 py-6">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 text-sm text-gray-600">
              <div>
                <p className="font-medium text-gray-900">
                  AgentTracer Platform — Observability for AI Agents
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  Privacy-by-default • No prompts or responses stored • Observational only
                </p>
              </div>
              <div className="flex items-center gap-4">
                <a
                  href="http://localhost:8000/health"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:text-blue-800 text-xs font-medium"
                >
                  Ingest API
                </a>
                <a
                  href="http://localhost:8001/health"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:text-blue-800 text-xs font-medium"
                >
                  Query API
                </a>
                <a
                  href="https://github.com/anthropics/agenttracer"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-gray-600 hover:text-gray-800 text-xs"
                >
                  Documentation
                </a>
              </div>
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
};

export default App;
