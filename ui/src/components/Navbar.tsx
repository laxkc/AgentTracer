/**
 * Professional Navigation Bar Component
 *
 * Features:
 * - Unified navigation
 * - Active state highlighting
 * - Responsive design
 * - System health indicator
 */

import React from "react";
import { Link, useLocation } from "react-router-dom";
import {
  Activity,
  Home,
  BarChart3,
  TrendingUp,
  Database,
  Layers,
  GitCompare,
  ChevronDown,
} from "lucide-react";
import { Button } from "./ui/button";

const Navbar: React.FC = () => {
  const location = useLocation();

  const isActive = (path: string) => {
    return location.pathname === path;
  };

  const isActiveGroup = (paths: string[]) => {
    return paths.some((path) => location.pathname.startsWith(path));
  };

  return (
    <nav className="bg-white shadow-sm border-b border-gray-200 sticky top-0 z-50">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo and Brand */}
          <Link to="/" className="flex items-center gap-3 hover:opacity-80 transition-opacity">
            <div className="p-2 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-lg">
              <Activity className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">AgentTracer</h1>
              <p className="text-xs text-gray-500">Observability Platform</p>
            </div>
          </Link>

          {/* Navigation Links */}
          <div className="flex items-center gap-1">
            {/* Home */}
            <Link to="/">
              <Button variant={isActive("/") ? "default" : "ghost"} size="sm" className="gap-2">
                <Home className="w-4 h-4" />
                Dashboard
              </Button>
            </Link>

            {/* Runs */}
            <Link to="/runs">
              <Button
                variant={
                  isActive("/runs") || location.pathname.startsWith("/runs/")
                    ? "default"
                    : "ghost"
                }
                size="sm"
                className="gap-2"
              >
                <BarChart3 className="w-4 h-4" />
                Runs
              </Button>
            </Link>

            {/* Divider */}
            <div className="h-6 w-px bg-gray-200 mx-2" />

            {/* Behaviors Dropdown */}
            <div className="relative group">
              <Button
                variant={
                  isActiveGroup(["/behaviors", "/baselines", "/profiles", "/drift"])
                    ? "default"
                    : "ghost"
                }
                size="sm"
                className="gap-2"
              >
                <TrendingUp className="w-4 h-4" />
                Behaviors
                <ChevronDown className="w-3 h-3" />
              </Button>

              {/* Dropdown Menu */}
              <div className="absolute top-full left-0 mt-1 w-56 bg-white rounded-lg shadow-lg border border-gray-200 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
                <div className="p-2 space-y-1">
                  <Link to="/behaviors">
                    <Button
                      variant={isActive("/behaviors") ? "secondary" : "ghost"}
                      size="sm"
                      className="w-full justify-start gap-2"
                    >
                      <Activity className="w-4 h-4" />
                      Dashboard
                    </Button>
                  </Link>
                  <Link to="/baselines">
                    <Button
                      variant={isActive("/baselines") ? "secondary" : "ghost"}
                      size="sm"
                      className="w-full justify-start gap-2"
                    >
                      <Database className="w-4 h-4" />
                      Baselines
                    </Button>
                  </Link>
                  <Link to="/profiles">
                    <Button
                      variant={isActive("/profiles") ? "secondary" : "ghost"}
                      size="sm"
                      className="w-full justify-start gap-2"
                    >
                      <Layers className="w-4 h-4" />
                      Profiles
                    </Button>
                  </Link>
                  <Link to="/drift/compare">
                    <Button
                      variant={isActive("/drift/compare") ? "secondary" : "ghost"}
                      size="sm"
                      className="w-full justify-start gap-2"
                    >
                      <GitCompare className="w-4 w-4" />
                      Drift Comparison
                    </Button>
                  </Link>
                </div>
              </div>
            </div>
          </div>

          {/* Right Side - Health Status */}
          <div className="flex items-center gap-3">
            {/* Health Status */}
            <div className="flex items-center gap-2 px-3 py-1.5 bg-green-50 rounded-full">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              <span className="text-xs font-medium text-green-700">Healthy</span>
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
