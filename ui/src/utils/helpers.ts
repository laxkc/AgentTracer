/**
 * Utility Helper Functions
 * Common utility functions used throughout the application
 */

import { format, formatDistance, formatDistanceToNow, parseISO } from 'date-fns';
import {
  SEVERITY_CONFIG,
  DRIFT_TYPE_CONFIG,
  BASELINE_TYPE_CONFIG,
  ENVIRONMENT_CONFIG,
  STATUS_CONFIG,
  type SeverityLevel,
  type DriftType,
  type BaselineType,
  type Environment,
} from '../constants/design';

// ============================================================================
// Style Utilities
// ============================================================================

/**
 * Get severity badge classes
 */
export function getSeverityClasses(severity: SeverityLevel) {
  const config = SEVERITY_CONFIG[severity];
  if (!config) {
    return {
      bgColor: 'bg-gray-50',
      textColor: 'text-gray-700',
      borderColor: 'border-gray-200',
    };
  }
  return {
    bgColor: config.bgColor,
    textColor: config.textColor,
    borderColor: config.borderColor,
  };
}

/**
 * Get drift type badge classes
 */
export function getDriftTypeClasses(type: DriftType) {
  const config = DRIFT_TYPE_CONFIG[type];
  if (!config) {
    return {
      bgColor: 'bg-gray-50',
      textColor: 'text-gray-700',
      borderColor: 'border-gray-200',
    };
  }
  return {
    bgColor: config.bgColor,
    textColor: config.textColor,
    borderColor: config.borderColor,
  };
}

/**
 * Get baseline type badge classes
 */
export function getBaselineTypeClasses(type: BaselineType) {
  const config = BASELINE_TYPE_CONFIG[type];
  if (!config) {
    return {
      bgColor: 'bg-gray-50',
      textColor: 'text-gray-700',
      borderColor: 'border-gray-200',
    };
  }
  return {
    bgColor: config.bgColor,
    textColor: config.textColor,
    borderColor: config.borderColor,
  };
}

/**
 * Get environment badge classes
 */
export function getEnvironmentClasses(environment: Environment) {
  const config = ENVIRONMENT_CONFIG[environment];
  if (!config) {
    return {
      bgColor: 'bg-gray-50',
      textColor: 'text-gray-700',
      borderColor: 'border-gray-200',
    };
  }
  return {
    bgColor: config.bgColor,
    textColor: config.textColor,
    borderColor: config.borderColor,
  };
}

/**
 * Get status badge classes
 */
export function getStatusClasses(status: string) {
  const config = STATUS_CONFIG[status as keyof typeof STATUS_CONFIG];
  if (!config) {
    return {
      bgColor: 'bg-gray-50',
      textColor: 'text-gray-700',
      borderColor: 'border-gray-200',
      dotColor: 'bg-gray-400',
    };
  }
  return {
    bgColor: config.bgColor,
    textColor: config.textColor,
    borderColor: config.borderColor,
    dotColor: config.dotColor,
  };
}

// ============================================================================
// Date Utilities
// ============================================================================

/**
 * Format date to readable string
 */
export function formatDate(date: string | Date, formatStr: string = 'PPp'): string {
  try {
    const dateObj = typeof date === 'string' ? parseISO(date) : date;
    return format(dateObj, formatStr);
  } catch (error) {
    return 'Invalid date';
  }
}

/**
 * Format date as relative time (e.g., "2 hours ago")
 */
export function formatRelativeTime(date: string | Date): string {
  try {
    const dateObj = typeof date === 'string' ? parseISO(date) : date;
    return formatDistanceToNow(dateObj, { addSuffix: true });
  } catch (error) {
    return 'Invalid date';
  }
}

/**
 * Format duration between two dates
 */
export function formatDuration(startDate: string | Date, endDate: string | Date): string {
  try {
    const start = typeof startDate === 'string' ? parseISO(startDate) : startDate;
    const end = typeof endDate === 'string' ? parseISO(endDate) : endDate;
    return formatDistance(start, end);
  } catch (error) {
    return 'Invalid duration';
  }
}

/**
 * Format date as short date (e.g., "Jan 3, 2026")
 */
export function formatShortDate(date: string | Date): string {
  return formatDate(date, 'MMM d, yyyy');
}

/**
 * Format date as date and time (e.g., "Jan 3, 2026 10:30 AM")
 */
export function formatDateTime(date: string | Date): string {
  return formatDate(date, 'MMM d, yyyy h:mm a');
}

// ============================================================================
// Number Utilities
// ============================================================================

/**
 * Format number with commas
 */
export function formatNumber(num: number): string {
  return new Intl.NumberFormat('en-US').format(num);
}

/**
 * Format percentage
 */
export function formatPercent(num: number, decimals: number = 1): string {
  return `${num.toFixed(decimals)}%`;
}

/**
 * Format large numbers with K, M, B suffix
 */
export function formatCompactNumber(num: number): string {
  if (num >= 1000000000) {
    return `${(num / 1000000000).toFixed(1)}B`;
  }
  if (num >= 1000000) {
    return `${(num / 1000000).toFixed(1)}M`;
  }
  if (num >= 1000) {
    return `${(num / 1000).toFixed(1)}K`;
  }
  return num.toString();
}

/**
 * Format duration in milliseconds to human readable
 */
export function formatLatency(ms: number): string {
  if (ms < 1000) {
    return `${Math.round(ms)}ms`;
  }
  return `${(ms / 1000).toFixed(2)}s`;
}

// ============================================================================
// String Utilities
// ============================================================================

/**
 * Truncate string to max length with ellipsis
 */
export function truncate(str: string, maxLength: number): string {
  if (str.length <= maxLength) {
    return str;
  }
  return `${str.substring(0, maxLength)}...`;
}

/**
 * Capitalize first letter
 */
export function capitalize(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

/**
 * Convert snake_case to Title Case
 */
export function snakeToTitle(str: string): string {
  return str
    .split('_')
    .map(word => capitalize(word))
    .join(' ');
}

// ============================================================================
// Classification Utilities
// ============================================================================

/**
 * Get severity from percentage change
 */
export function getSeverityFromChange(percentChange: number): SeverityLevel {
  const absChange = Math.abs(percentChange);
  if (absChange > 30) {
    return 'high';
  }
  if (absChange > 15) {
    return 'medium';
  }
  return 'low';
}

/**
 * Get change direction text
 */
export function getChangeDirection(delta: number): 'increased' | 'decreased' | 'unchanged' {
  if (delta > 0) {
    return 'increased';
  }
  if (delta < 0) {
    return 'decreased';
  }
  return 'unchanged';
}

/**
 * Format change with direction
 */
export function formatChange(delta: number, deltaPercent: number): string {
  const direction = getChangeDirection(delta);
  const sign = delta > 0 ? '+' : '';

  if (direction === 'unchanged') {
    return 'no change';
  }

  return `${direction} by ${sign}${formatPercent(deltaPercent)}`;
}

// ============================================================================
// Validation Utilities
// ============================================================================

/**
 * Check if value is defined and not null
 */
export function isDefined<T>(value: T | null | undefined): value is T {
  return value !== null && value !== undefined;
}

/**
 * Check if string is valid UUID
 */
export function isUUID(str: string): boolean {
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  return uuidRegex.test(str);
}

/**
 * Safely parse JSON with fallback
 */
export function safeJsonParse<T>(json: string, fallback: T): T {
  try {
    return JSON.parse(json) as T;
  } catch {
    return fallback;
  }
}

// ============================================================================
// Class Name Utilities
// ============================================================================

/**
 * Combine class names (simple version of classnames library)
 */
export function cn(...classes: (string | boolean | undefined | null)[]): string {
  return classes.filter(Boolean).join(' ');
}
