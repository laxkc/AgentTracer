/**
 * EmptyState Component
 * Display when no data is available
 */

import React from 'react';
import {
  Inbox,
  AlertCircle,
  Search,
  FileX,
  Database,
  Lock,
  WifiOff,
  ShieldX,
  LucideIcon
} from 'lucide-react';
import { cn } from '../../utils/helpers';

interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: LucideIcon;
  action?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  icon: Icon = Inbox,
  action,
  className,
}) => {
  return (
    <div className={cn(
      'flex flex-col items-center justify-center py-12 px-4 text-center',
      className
    )}>
      <div className="rounded-full bg-gray-100 p-4 mb-4">
        <Icon className="w-8 h-8 text-gray-400" />
      </div>
      <h3 className="text-lg font-semibold text-gray-900 mb-2">
        {title}
      </h3>
      {description && (
        <p className="text-sm text-gray-500 mb-6 max-w-md">
          {description}
        </p>
      )}
      {action && (
        <button
          onClick={action.onClick}
          className="bg-blue-600 hover:bg-blue-700 text-white font-medium px-4 py-2 rounded-lg transition-colors duration-200"
        >
          {action.label}
        </button>
      )}
    </div>
  );
};

// Specialized empty states
export const NoDataEmptyState: React.FC<{
  entityName: string;
  onAction?: () => void;
  actionLabel?: string;
}> = ({ entityName, onAction, actionLabel }) => (
  <EmptyState
    icon={Database}
    title={`No ${entityName} found`}
    description={`There are no ${entityName} to display yet. ${onAction ? actionLabel : 'Data will appear here once available.'}`}
    action={onAction ? { label: actionLabel || 'Create', onClick: onAction } : undefined}
  />
);

export const NoSearchResultsEmptyState: React.FC<{
  query?: string;
  onClear?: () => void;
}> = ({ query, onClear }) => (
  <EmptyState
    icon={Search}
    title="No results found"
    description={query ? `No results match "${query}". Try adjusting your search.` : 'Try adjusting your filters or search query.'}
    action={onClear ? { label: 'Clear filters', onClick: onClear } : undefined}
  />
);

export const ErrorEmptyState: React.FC<{
  message?: string;
  onRetry?: () => void;
}> = ({ message, onRetry }) => (
  <EmptyState
    icon={AlertCircle}
    title="Something went wrong"
    description={message || 'We encountered an error loading this data. Please try again.'}
    action={onRetry ? { label: 'Retry', onClick: onRetry } : undefined}
  />
);

export const NoFilesEmptyState: React.FC = () => (
  <EmptyState
    icon={FileX}
    title="No files yet"
    description="Upload files to get started."
  />
);

export const UnauthorizedEmptyState: React.FC<{ onLogin?: () => void }> = ({ onLogin }) => (
  <EmptyState
    icon={Lock}
    title="Authentication required"
    description="You need to sign in to view this content."
    action={onLogin ? { label: 'Sign in', onClick: onLogin } : undefined}
  />
);

export const OfflineEmptyState: React.FC<{ onRetry?: () => void }> = ({ onRetry }) => (
  <EmptyState
    icon={WifiOff}
    title="No connection"
    description="Check your internet connection and try again."
    action={onRetry ? { label: 'Retry', onClick: onRetry } : undefined}
  />
);

export const PermissionDeniedEmptyState: React.FC = () => (
  <EmptyState
    icon={ShieldX}
    title="Permission denied"
    description="You do not have access to view this resource."
  />
);
