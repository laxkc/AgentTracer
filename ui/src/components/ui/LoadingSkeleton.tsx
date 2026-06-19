/**
 * LoadingSkeleton Component
 * Skeleton screens for loading states
 */

import React from 'react';
import { cn } from '../../utils/helpers';

interface LoadingSkeletonProps {
  className?: string;
  variant?: 'text' | 'card' | 'table' | 'stat' | 'chart' | 'custom';
  rows?: number;
  height?: string;
}

export const LoadingSkeleton: React.FC<LoadingSkeletonProps> = ({
  className,
  variant = 'text',
  rows = 3,
  height,
}) => {
  const baseClass = 'animate-pulse bg-gray-200 rounded';

  if (variant === 'text') {
    return (
      <div className={cn('space-y-3', className)}>
        {Array.from({ length: rows }).map((_, i) => (
          <div
            key={i}
            className={cn(
              baseClass,
              'h-4',
              i === rows - 1 ? 'w-3/4' : 'w-full'
            )}
          />
        ))}
      </div>
    );
  }

  if (variant === 'card') {
    return (
      <div className={cn('bg-white rounded-lg shadow-sm border border-gray-200 p-6 space-y-4', className)}>
        <div className={cn(baseClass, 'h-6 w-2/3')} />
        <div className="space-y-2">
          <div className={cn(baseClass, 'h-4 w-full')} />
          <div className={cn(baseClass, 'h-4 w-5/6')} />
          <div className={cn(baseClass, 'h-4 w-4/6')} />
        </div>
      </div>
    );
  }

  if (variant === 'table') {
    return (
      <div className={cn('space-y-3', className)}>
        {/* Table header */}
        <div className="flex gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className={cn(baseClass, 'h-8 flex-1')} />
          ))}
        </div>
        {/* Table rows */}
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="flex gap-4">
            {[1, 2, 3, 4].map((j) => (
              <div key={j} className={cn(baseClass, 'h-12 flex-1')} />
            ))}
          </div>
        ))}
      </div>
    );
  }

  if (variant === 'stat') {
    return (
      <div className={cn('bg-white rounded-lg shadow-sm border border-gray-200 p-6', className)}>
        <div className={cn(baseClass, 'h-4 w-1/3 mb-3')} />
        <div className={cn(baseClass, 'h-8 w-2/3')} />
      </div>
    );
  }

  if (variant === 'chart') {
    return (
      <div className={cn('bg-white rounded-lg shadow-sm border border-gray-200 p-6', className)}>
        <div className={cn(baseClass, 'h-6 w-1/3 mb-4')} />
        <div className={cn(baseClass, height || 'h-64')} />
      </div>
    );
  }

  // Custom variant
  return (
    <div className={cn(baseClass, height || 'h-32', className)} />
  );
};

// Specialized skeleton components
export const CardSkeleton: React.FC<{ className?: string }> = ({ className }) => (
  <LoadingSkeleton variant="card" className={className} />
);

export const TableSkeleton: React.FC<{ rows?: number; className?: string }> = ({ rows, className }) => (
  <LoadingSkeleton variant="table" rows={rows} className={className} />
);

export const StatCardSkeleton: React.FC<{ className?: string }> = ({ className }) => (
  <LoadingSkeleton variant="stat" className={className} />
);

export const ChartSkeleton: React.FC<{ className?: string; height?: string }> = ({ className, height }) => (
  <LoadingSkeleton variant="chart" className={className} height={height} />
);
