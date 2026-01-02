import React from 'react';
import { Routes, Route, Link, useLocation } from 'react-router-dom';
import { Activity, BarChart3, Home } from 'lucide-react';
import RunExplorer from './components/RunExplorer';
import RunDetail from './pages/RunDetail';
import Dashboard from './pages/Dashboard';
import BehaviorDashboard from './pages/BehaviorDashboard';
import BaselineManager from './pages/BaselineManager';
import DriftDetail from './pages/DriftDetail';

const App: React.FC = () => {
  const location = useLocation();

  const isActive = (path: string) => {
    return location.pathname === path;
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation */}
      <nav className="bg-white shadow-sm border-b border-gray-200">
        <div className="container mx-auto px-4">
          <div className="flex items-center justify-between h-16">
            {/* Logo and Brand */}
            <div className="flex items-center">
              <Activity className="w-8 h-8 text-blue-600 mr-2" />
              <h1 className="text-xl font-bold text-gray-900">
                AgentTracer
              </h1>
              <span className="ml-3 px-2 py-1 bg-blue-100 text-blue-800 text-xs font-semibold rounded">
                Phase 1
              </span>
            </div>

            {/* Navigation Links */}
            <div className="flex items-center space-x-4">
              <Link
                to="/"
                className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  isActive('/')
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                <Home className="w-4 h-4" />
                Dashboard
              </Link>
              <Link
                to="/runs"
                className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  isActive('/runs') || location.pathname.startsWith('/runs/')
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                <BarChart3 className="w-4 h-4" />
                Runs
              </Link>
              <Link
                to="/behaviors"
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  isActive('/behaviors')
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                Behaviors
              </Link>
              <Link
                to="/baselines"
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  isActive('/baselines')
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                Baselines
              </Link>

      
            </div>

            {/* Health Status */}
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              <span className="text-xs text-gray-600">System Healthy</span>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/runs" element={<RunExplorer />} />
          <Route path="/runs/:runId" element={<RunDetail />} />
          <Route path="/behaviors" element={<BehaviorDashboard />} />
          <Route path="/baselines" element={<BaselineManager />} />
          <Route path="/drift/:driftId" element={<DriftDetail />} />
        </Routes>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-12">
        <div className="container mx-auto px-4 py-6">
          <div className="flex items-center justify-between text-sm text-gray-600">
            <div>
              <p>
                AgentTracer Platform — Phase 1 MVP
              </p>
              <p className="text-xs text-gray-500 mt-1">
                Privacy-by-default • No prompts or responses stored
              </p>
            </div>
            <div className="flex items-center gap-4">
              <a
                href="http://localhost:8000/health"
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:text-blue-800"
              >
                Ingest API
              </a>
              <a
                href="http://localhost:8001/health"
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:text-blue-800"
              >
                Query API
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;
