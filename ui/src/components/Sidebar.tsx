/**
 * Sidebar Navigation Component
 *
 * Provides persistent side navigation for the application
 * - Main navigation links
 * - Behaviors section with subsections
 * - Collapsible on mobile
 * - Active state highlighting
 */

import React, { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  Home,
  BarChart3,
  ListChecks,
  Sparkles,
  // Layers,
  Target,
  Activity,
  GitCompare,
  Menu,
  X,
} from "lucide-react";
import { Button } from "./ui/button";

const Sidebar: React.FC = () => {
  const location = useLocation();
  const [isOpen, setIsOpen] = useState(false);
  const navItems = [
    { label: "Overview", icon: Home, path: "/" },
    { label: "Runs", icon: BarChart3, path: "/runs" },
    { label: "Decisions", icon: ListChecks, path: "/decisions" },
    { label: "Quality Signals", icon: Sparkles, path: "/signals" },
    // { label: "Profiles", icon: Layers, path: "/profiles" },
    { label: "Baselines", icon: Target, path: "/baselines" },
    { label: "Drift", icon: Activity, path: "/behaviors", matchPaths: ["/behaviors", "/drift"] },
    { label: "Comparisons", icon: GitCompare, path: "/drift/compare" },
  ];

  const getMatchScore = (pathname: string, pattern: string) => {
    if (pattern === "/") {
      return pathname === "/" ? 1 : -1;
    }
    if (pathname === pattern || pathname.startsWith(`${pattern}/`)) {
      return pattern.length;
    }
    return -1;
  };

  const activePath = navItems.reduce((best, item) => {
    const patterns = item.matchPaths ?? [item.path];
    const bestForItem = patterns.reduce(
      (score, pattern) => Math.max(score, getMatchScore(location.pathname, pattern)),
      -1
    );

    if (bestForItem > best.score) {
      return { score: bestForItem, path: item.path };
    }
    return best;
  }, { score: -1, path: "" }).path;

  const isActive = (path: string) => path === activePath;

  const SidebarContent = () => (
    <div className="flex flex-col h-full">
      {/* Logo/Header */}
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-center gap-3">
          <div>
            <h2 className="text-lg font-bold text-gray-900">AgentTracer</h2>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => (
          <Link key={item.path} to={item.path}>
            <Button
              variant={isActive(item.path) ? "default" : "ghost"}
              className="w-full justify-start"
              size="default"
            >
              <item.icon className="w-5 h-5" />
              {item.label}
            </Button>
          </Link>
        ))}
      </nav>

      {/* Footer */}
      {/* <div className="p-4 border-t border-gray-200">
        <div className="flex flex-col gap-2 text-xs text-gray-500">
          <div className="flex items-center justify-between">
            <span>AgentTracer</span>
            <span>v1.0.0</span>
          </div>
        </div>
      </div> */}
    </div>
  );

  return (
    <>
      {/* Mobile Menu Toggle */}
      <div className="lg:hidden fixed top-4 left-4 z-50">
        <Button
          variant="outline"
          size="icon"
          onClick={() => setIsOpen(!isOpen)}
          className="bg-white shadow-md"
        >
          {isOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </Button>
      </div>

      {/* Mobile Overlay */}
      {isOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black bg-opacity-50 z-40"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed top-0 left-0 h-full bg-white border-r border-gray-200 z-40
          transition-transform duration-300 ease-in-out
          w-64
          ${isOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}
        `}
      >
        <SidebarContent />
      </aside>
    </>
  );
};

export default Sidebar;
