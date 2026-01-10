/**
 * Reusable Page Header Component
 *
 * Provides consistent page header with title, description, and refresh functionality
 */

import React from 'react';
import { RefreshCw } from 'lucide-react';
import { Button } from './ui/button';

interface PageHeaderProps {
  title: string;
  description: string;
  lastUpdated?: Date | null;
  onRefresh?: () => void;
  actions?: React.ReactNode;
  loading?: boolean;
}

export const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  description,
  lastUpdated,
  onRefresh,
  actions,
  loading = false,
}) => {
  return (
    <header className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between mb-8">
      <div>
        <h1 className="text-3xl font-semibold text-gray-900">{title}</h1>
        <p className="text-gray-600 mt-2">{description}</p>
      </div>
      <div className="flex items-center gap-3">
        {lastUpdated && (
          <p className="text-sm text-gray-500">
            Updated {lastUpdated.toLocaleTimeString()}
          </p>
        )}
        {onRefresh && (
          <Button
            onClick={onRefresh}
            variant="outline"
            disabled={loading}
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        )}
        {actions}
      </div>
    </header>
  );
};
