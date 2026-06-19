/**
 * Error types and helpers for API and UI error handling.
 */

export enum ErrorType {
  NETWORK_ERROR = 'NETWORK_ERROR',
  SERVER_ERROR = 'SERVER_ERROR',
  VALIDATION_ERROR = 'VALIDATION_ERROR',
  AUTH_ERROR = 'AUTH_ERROR',
  NOT_FOUND = 'NOT_FOUND',
  TIMEOUT = 'TIMEOUT',
  UNKNOWN = 'UNKNOWN',
}

export interface AppError {
  type: ErrorType;
  message: string;
  details?: unknown;
  statusCode?: number;
  retryable: boolean;
}

export class ApiError extends Error {
  statusCode?: number;
  details?: unknown;
  appError: AppError;

  constructor(message: string, statusCode?: number, details?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.statusCode = statusCode;
    this.details = details;
    this.appError = categorizeError(this, statusCode, details);
  }
}

export const categorizeError = (
  error: unknown,
  statusCode?: number,
  details?: unknown
): AppError => {
  const message = error instanceof Error ? error.message : 'An unexpected error occurred';

  if (error instanceof DOMException && error.name === 'AbortError') {
    return {
      type: ErrorType.TIMEOUT,
      message: 'Request timed out. Please try again.',
      statusCode,
      retryable: true,
    };
  }

  if (!navigator.onLine || message.includes('Failed to fetch')) {
    return {
      type: ErrorType.NETWORK_ERROR,
      message: 'Network connection lost. Check your internet.',
      details,
      statusCode,
      retryable: true,
    };
  }

  if (statusCode === 401 || statusCode === 403) {
    return {
      type: ErrorType.AUTH_ERROR,
      message: statusCode === 401 ? 'Authentication required' : 'Permission denied',
      statusCode,
      retryable: false,
    };
  }

  if (statusCode === 400 || statusCode === 422) {
    return {
      type: ErrorType.VALIDATION_ERROR,
      message: message || 'Invalid input. Please check your data.',
      details,
      statusCode,
      retryable: false,
    };
  }

  if (statusCode === 404) {
    return {
      type: ErrorType.NOT_FOUND,
      message: 'Resource not found',
      statusCode,
      retryable: false,
    };
  }

  if (statusCode && statusCode >= 500) {
    return {
      type: ErrorType.SERVER_ERROR,
      message: 'Server error. Please try again later.',
      statusCode,
      retryable: true,
    };
  }

  return {
    type: ErrorType.UNKNOWN,
    message,
    details,
    statusCode,
    retryable: false,
  };
};

export const toAppError = (error: unknown): AppError => {
  if (error instanceof ApiError) {
    return error.appError;
  }

  if (error && typeof error === 'object' && 'type' in error && 'message' in error) {
    const maybeAppError = error as AppError;
    if (Object.values(ErrorType).includes(maybeAppError.type)) {
      return maybeAppError;
    }
  }

  return categorizeError(error);
};
