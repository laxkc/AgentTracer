/**
 * Design System Constants
 * Centralized design tokens, colors, and style utilities
 */

// ============================================================================
// Severity Levels
// ============================================================================

export const SEVERITY_LEVELS = {
  LOW: 'low',
  MEDIUM: 'medium',
  HIGH: 'high',
} as const;

export type SeverityLevel = typeof SEVERITY_LEVELS[keyof typeof SEVERITY_LEVELS];

export const SEVERITY_CONFIG: Record<SeverityLevel, {
  label: string;
  bgColor: string;
  textColor: string;
  borderColor: string;
  icon: string;
}> = {
  low: {
    label: 'Low',
    bgColor: 'bg-blue-50',
    textColor: 'text-blue-700',
    borderColor: 'border-blue-200',
    icon: 'info',
  },
  medium: {
    label: 'Medium',
    bgColor: 'bg-yellow-50',
    textColor: 'text-yellow-700',
    borderColor: 'border-yellow-200',
    icon: 'alert-triangle',
  },
  high: {
    label: 'High',
    bgColor: 'bg-orange-50',
    textColor: 'text-orange-700',
    borderColor: 'border-orange-200',
    icon: 'alert-circle',
  },
};

// ============================================================================
// Drift Types
// ============================================================================

export const DRIFT_TYPES = {
  DECISION: 'decision',
  SIGNAL: 'signal',
  LATENCY: 'latency',
} as const;

export type DriftType = typeof DRIFT_TYPES[keyof typeof DRIFT_TYPES];

export const DRIFT_TYPE_CONFIG: Record<DriftType, {
  label: string;
  bgColor: string;
  textColor: string;
  borderColor: string;
  icon: string;
}> = {
  decision: {
    label: 'Decision',
    bgColor: 'bg-purple-50',
    textColor: 'text-purple-700',
    borderColor: 'border-purple-200',
    icon: 'git-branch',
  },
  signal: {
    label: 'Signal',
    bgColor: 'bg-green-50',
    textColor: 'text-green-700',
    borderColor: 'border-green-200',
    icon: 'radio',
  },
  latency: {
    label: 'Latency',
    bgColor: 'bg-indigo-50',
    textColor: 'text-indigo-700',
    borderColor: 'border-indigo-200',
    icon: 'clock',
  },
};

// ============================================================================
// Baseline Types
// ============================================================================

export const BASELINE_TYPES = {
  VERSION: 'version',
  TIME_WINDOW: 'time_window',
  MANUAL: 'manual',
  EXPERIMENT: 'experiment',
} as const;

export type BaselineType = typeof BASELINE_TYPES[keyof typeof BASELINE_TYPES];

export const BASELINE_TYPE_CONFIG: Record<BaselineType, {
  label: string;
  bgColor: string;
  textColor: string;
  borderColor: string;
}> = {
  version: {
    label: 'Version',
    bgColor: 'bg-blue-50',
    textColor: 'text-blue-700',
    borderColor: 'border-blue-200',
  },
  time_window: {
    label: 'Time Window',
    bgColor: 'bg-purple-50',
    textColor: 'text-purple-700',
    borderColor: 'border-purple-200',
  },
  manual: {
    label: 'Manual',
    bgColor: 'bg-gray-50',
    textColor: 'text-gray-700',
    borderColor: 'border-gray-200',
  },
  experiment: {
    label: 'Experiment',
    bgColor: 'bg-amber-50',
    textColor: 'text-amber-700',
    borderColor: 'border-amber-200',
  },
};

// ============================================================================
// Environments
// ============================================================================

export const ENVIRONMENTS = {
  PRODUCTION: 'production',
  STAGING: 'staging',
  DEVELOPMENT: 'development',
} as const;

export type Environment = typeof ENVIRONMENTS[keyof typeof ENVIRONMENTS];

export const ENVIRONMENT_CONFIG: Record<Environment, {
  label: string;
  bgColor: string;
  textColor: string;
  borderColor: string;
}> = {
  production: {
    label: 'Production',
    bgColor: 'bg-green-50',
    textColor: 'text-green-700',
    borderColor: 'border-green-200',
  },
  staging: {
    label: 'Staging',
    bgColor: 'bg-yellow-50',
    textColor: 'text-yellow-700',
    borderColor: 'border-yellow-200',
  },
  development: {
    label: 'Development',
    bgColor: 'bg-gray-50',
    textColor: 'text-gray-700',
    borderColor: 'border-gray-200',
  },
};

// ============================================================================
// Status Types
// ============================================================================

export const STATUS_CONFIG = {
  active: {
    label: 'Active',
    bgColor: 'bg-green-50',
    textColor: 'text-green-700',
    borderColor: 'border-green-200',
    dotColor: 'bg-green-500',
  },
  inactive: {
    label: 'Inactive',
    bgColor: 'bg-gray-50',
    textColor: 'text-gray-600',
    borderColor: 'border-gray-200',
    dotColor: 'bg-gray-400',
  },
  resolved: {
    label: 'Resolved',
    bgColor: 'bg-blue-50',
    textColor: 'text-blue-700',
    borderColor: 'border-blue-200',
    dotColor: 'bg-blue-500',
  },
  unresolved: {
    label: 'Unresolved',
    bgColor: 'bg-orange-50',
    textColor: 'text-orange-700',
    borderColor: 'border-orange-200',
    dotColor: 'bg-orange-500',
  },
  success: {
    label: 'Success',
    bgColor: 'bg-green-50',
    textColor: 'text-green-700',
    borderColor: 'border-green-200',
    dotColor: 'bg-green-500',
  },
  failure: {
    label: 'Failure',
    bgColor: 'bg-red-50',
    textColor: 'text-red-700',
    borderColor: 'border-red-200',
    dotColor: 'bg-red-500',
  },
  error: {
    label: 'Error',
    bgColor: 'bg-red-50',
    textColor: 'text-red-700',
    borderColor: 'border-red-200',
    dotColor: 'bg-red-500',
  },
  pending: {
    label: 'Pending',
    bgColor: 'bg-yellow-50',
    textColor: 'text-yellow-700',
    borderColor: 'border-yellow-200',
    dotColor: 'bg-yellow-500',
  },
} as const;

// ============================================================================
// Common Style Classes
// ============================================================================

export const CARD_STYLES = {
  base: 'bg-white rounded-lg shadow-sm border border-gray-200',
  hover: 'hover:shadow-md transition-shadow duration-200',
  interactive: 'cursor-pointer hover:border-gray-300 transition-all duration-200',
} as const;

export const BUTTON_STYLES = {
  primary: 'bg-blue-600 hover:bg-blue-700 text-white font-medium px-4 py-2 rounded-lg transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
  secondary: 'bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium px-4 py-2 rounded-lg transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2',
  danger: 'bg-red-600 hover:bg-red-700 text-white font-medium px-4 py-2 rounded-lg transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2',
  outline: 'border border-gray-300 hover:border-gray-400 bg-white text-gray-700 font-medium px-4 py-2 rounded-lg transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
  ghost: 'text-gray-700 hover:bg-gray-100 font-medium px-4 py-2 rounded-lg transition-colors duration-200',
  small: 'px-3 py-1.5 text-sm',
  large: 'px-6 py-3 text-base',
} as const;

export const INPUT_STYLES = {
  base: 'block w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 sm:text-sm',
  error: 'border-red-300 focus:ring-red-500 focus:border-red-500',
  disabled: 'bg-gray-50 text-gray-500 cursor-not-allowed',
} as const;

export const BADGE_STYLES = {
  base: 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border',
  small: 'px-2 py-0.5 text-xs',
  large: 'px-3 py-1 text-sm',
} as const;

// ============================================================================
// Animation Classes
// ============================================================================

export const ANIMATION_CLASSES = {
  fadeIn: 'animate-fadeIn',
  slideIn: 'animate-slideIn',
  pulse: 'animate-pulse',
  spin: 'animate-spin',
  bounce: 'animate-bounce',
} as const;

// ============================================================================
// Layout Constants
// ============================================================================

export const LAYOUT = {
  maxWidth: 'max-w-7xl',
  containerPadding: 'px-4 sm:px-6 lg:px-8',
  sectionSpacing: 'space-y-6',
  cardPadding: 'p-6',
} as const;
