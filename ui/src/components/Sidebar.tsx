/**
 * Sidebar Navigation Component
 *
 * Provides persistent side navigation for the application
 * - Main navigation links
 * - Behaviors section with subsections
 * - Collapsible on mobile
 * - Active state highlighting
 */

import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  Home,
  BarChart3,
  Activity,
  Target,
  Layers,
  GitCompare,
  ChevronDown,
  ChevronRight,
  Menu,
  X,
} from 'lucide-react';
import { Button } from './ui/button';

const Sidebar: React.FC = () => {
  const location = useLocation();
  const [isOpen, setIsOpen] = useState(false);
  const [behaviorExpanded, setBehaviorExpanded] = useState(
    location.pathname.startsWith('/behaviors') ||
    location.pathname.startsWith('/baselines') ||
    location.pathname.startsWith('/profiles') ||
    location.pathname.startsWith('/drift')
  );

  const isActive = (path: string) => location.pathname === path;
  const isActiveGroup = (paths: string[]) =>
    paths.some(path => location.pathname.startsWith(path));

  const navItems = [
    {
      label: 'Dashboard',
      icon: Home,
      path: '/',
    },
    {
      label: 'Runs',
      icon: BarChart3,
      path: '/runs',
    },
  ];

  const behaviorItems = [
    {
      label: 'Dashboard',
      icon: Activity,
      path: '/behaviors',
    },
    {
      label: 'Baselines',
      icon: Target,
      path: '/baselines',
    },
    {
      label: 'Profiles',
      icon: Layers,
      path: '/profiles',
    },
    {
      label: 'Drift Comparison',
      icon: GitCompare,
      path: '/drift/compare',
    },
  ];

  const SidebarContent = () => (
    <div className="flex flex-col h-full">
      {/* Logo/Header */}
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center">
            <Activity className="w-6 h-6 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-gray-900">AgentTracer</h2>
            <p className="text-xs text-gray-500">Observability Platform</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
        {/* Main Navigation */}
        {navItems.map((item) => (
          <Link key={item.path} to={item.path}>
            <Button
              variant={isActive(item.path) ? 'default' : 'ghost'}
              className="w-full justify-start"
              size="default"
            >
              <item.icon className="w-5 h-5" />
              {item.label}
            </Button>
          </Link>
        ))}

        {/* Behaviors Section */}
        <div className="pt-2">
          <Button
            variant={isActiveGroup(['/behaviors', '/baselines', '/profiles', '/drift']) ? 'secondary' : 'ghost'}
            className="w-full justify-between"
            onClick={() => setBehaviorExpanded(!behaviorExpanded)}
          >
            <div className="flex items-center gap-2">
              <Activity className="w-5 h-5" />
              Behaviors
            </div>
            {behaviorExpanded ? (
              <ChevronDown className="w-4 h-4" />
            ) : (
              <ChevronRight className="w-4 h-4" />
            )}
          </Button>

          {behaviorExpanded && (
            <div className="ml-4 mt-1 space-y-1 border-l-2 border-gray-200 pl-2">
              {behaviorItems.map((item) => (
                <Link key={item.path} to={item.path}>
                  <Button
                    variant={isActive(item.path) ? 'default' : 'ghost'}
                    className="w-full justify-start"
                    size="sm"
                  >
                    <item.icon className="w-4 h-4" />
                    {item.label}
                  </Button>
                </Link>
              ))}
            </div>
          )}
        </div>
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-gray-200">
        <div className="text-xs text-gray-500 text-center">
          <p>Agent Observability Platform</p>
          <p className="mt-1">Powered by AgentTracer</p>
        </div>
      </div>
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
          ${isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
        `}
      >
        <SidebarContent />
      </aside>
    </>
  );
};

export default Sidebar;
