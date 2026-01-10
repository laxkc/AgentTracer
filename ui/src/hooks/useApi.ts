/**
 * API Hooks
 * Custom hooks for data fetching and API calls
 */

import { useState, useEffect, useCallback } from 'react';
import { API_CONFIG } from '../config/api';
import { apiRequest } from '../lib/apiClient';
import { toAppError } from '../types/errors';
import { useErrorHandler } from './useErrorHandler';
import { showToast } from '../utils/toast';

export interface UseApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

/**
 * Generic API fetch hook
 */
export function useApi<T>(
  url: string,
  options?: {
    enabled?: boolean;
    onSuccess?: (data: T) => void;
    onError?: (error: string) => void;
    showErrorToast?: boolean;
  }
): UseApiState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { handleError } = useErrorHandler();

  const {
    enabled = true,
    onSuccess,
    onError,
    showErrorToast = true,
  } = options || {};

  const fetchData = useCallback(async (signal?: AbortSignal) => {
    if (!enabled) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const response = await apiRequest<T>(url, {
        baseUrl: API_CONFIG.QUERY_API_BASE_URL,
        method: 'GET',
        signal,
      });

      setData(response);

      if (onSuccess) {
        onSuccess(response);
      }
    } catch (err: any) {
      if (err instanceof DOMException && err.name === 'AbortError') {
        return;
      }
      const appError = showErrorToast ? handleError(err, 'useApi.fetchData') : toAppError(err);
      setError(appError.message);

      if (onError) {
        onError(appError.message);
      }
    } finally {
      setLoading(false);
    }
  }, [url, enabled, onSuccess, onError, showErrorToast, handleError]);

  useEffect(() => {
    const controller = new AbortController();
    fetchData(controller.signal);
    return () => controller.abort();
  }, [fetchData]);

  return {
    data,
    loading,
    error,
    refetch: fetchData,
  };
}

/**
 * API mutation hook (for POST, PUT, DELETE)
 */
export function useApiMutation<TData, TVariables = any>(
  method: 'post' | 'put' | 'delete' | 'patch',
  options?: {
    onSuccess?: (data: TData) => void;
    onError?: (error: string) => void;
    showSuccessToast?: boolean;
    showErrorToast?: boolean;
    successMessage?: string;
  }
) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { handleError } = useErrorHandler();

  const {
    onSuccess,
    onError,
    showSuccessToast = false,
    showErrorToast = true,
    successMessage = 'Operation completed successfully',
  } = options || {};

  const mutate = useCallback(
    async (url: string, variables?: TVariables): Promise<TData | null> => {
      try {
        setLoading(true);
        setError(null);

        const response = await apiRequest<TData>(url, {
          baseUrl: API_CONFIG.QUERY_API_BASE_URL,
          method: method.toUpperCase() as 'POST' | 'PUT' | 'DELETE' | 'PATCH',
          body: variables,
        });

        if (showSuccessToast) {
          showToast.success(successMessage);
        }

        if (onSuccess) {
          onSuccess(response);
        }

        return response;
      } catch (err: any) {
        if (err instanceof DOMException && err.name === 'AbortError') {
          return null;
        }
        const appError = showErrorToast ? handleError(err, 'useApiMutation') : toAppError(err);
        setError(appError.message);

        if (onError) {
          onError(appError.message);
        }

        return null;
      } finally {
        setLoading(false);
      }
    },
    [method, onSuccess, onError, showSuccessToast, showErrorToast, successMessage, handleError]
  );

  return {
    mutate,
    loading,
    error,
  };
}

/**
 * Paginated API hook
 */
export function usePaginatedApi<T>(
  baseUrl: string,
  options?: {
    limit?: number;
    enabled?: boolean;
  }
) {
  const [page, setPage] = useState(1);
  const { limit = 20, enabled = true } = options || {};

  const url = `${baseUrl}?limit=${limit}&offset=${(page - 1) * limit}`;

  const { data, loading, error, refetch } = useApi<T>(url, {
    enabled,
  });

  const nextPage = useCallback(() => {
    setPage((prev) => prev + 1);
  }, []);

  const prevPage = useCallback(() => {
    setPage((prev) => Math.max(1, prev - 1));
  }, []);

  const goToPage = useCallback((newPage: number) => {
    setPage(Math.max(1, newPage));
  }, []);

  return {
    data,
    loading,
    error,
    refetch,
    page,
    nextPage,
    prevPage,
    goToPage,
  };
}
