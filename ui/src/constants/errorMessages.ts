/**
 * Centralized user-facing error messages.
 */

import { ErrorType } from '../types/errors';

export const ERROR_MESSAGES: Record<ErrorType, string> = {
  [ErrorType.NETWORK_ERROR]: 'You appear to be offline. Check your connection and try again.',
  [ErrorType.TIMEOUT]: 'Request timed out. The server took too long to respond.',
  [ErrorType.SERVER_ERROR]: 'Server error. Please try again later.',
  [ErrorType.VALIDATION_ERROR]: 'Some fields have invalid values. Please check and try again.',
  [ErrorType.AUTH_ERROR]: 'You do not have permission to perform this action.',
  [ErrorType.NOT_FOUND]: 'The requested resource was not found.',
  [ErrorType.UNKNOWN]: 'Something went wrong. Please try again.',
};

export const getErrorMessage = (type: ErrorType, fallback?: string) => {
  return ERROR_MESSAGES[type] || fallback || ERROR_MESSAGES[ErrorType.UNKNOWN];
};
