/**
 * Unified error handler hook.
 */

import { useCallback } from 'react';
import { showToast } from '../utils/toast';
import { ErrorType, toAppError } from '../types/errors';
import { getErrorMessage } from '../constants/errorMessages';
import { useOnlineStatus } from './useOnlineStatus';

export const useErrorHandler = () => {
  const isOnline = useOnlineStatus();

  const handleError = useCallback(
    (error: unknown, context?: string) => {
      const appError = toAppError(error);

      if (context) {
        console.error(`Error in ${context}:`, appError);
      } else {
        console.error('Error:', appError);
      }

      switch (appError.type) {
        case ErrorType.AUTH_ERROR:
          showToast.error(getErrorMessage(appError.type, appError.message));
          break;
        case ErrorType.NETWORK_ERROR:
          showToast.error(
            isOnline ? 'Network request failed. Please try again.' : getErrorMessage(appError.type)
          );
          break;
        case ErrorType.TIMEOUT:
          showToast.error(getErrorMessage(appError.type, appError.message));
          break;
        case ErrorType.NOT_FOUND:
        case ErrorType.SERVER_ERROR:
        case ErrorType.VALIDATION_ERROR:
        case ErrorType.UNKNOWN:
        default:
          showToast.error(appError.message || getErrorMessage(appError.type));
          break;
      }

      return appError;
    },
    [isOnline]
  );

  return { handleError };
};
