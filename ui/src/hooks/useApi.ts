/**
 * API Hooks
 * Custom hooks for data fetching and API calls
 */

import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { API_CONFIG } from '../config/api';
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

  const {
    enabled = true,
    onSuccess,
    onError,
    showErrorToast = true,
  } = options || {};

  const fetchData = useCallback(async () => {
    if (!enabled) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const response = await axios.get<T>(`${API_CONFIG.QUERY_API_BASE_URL}${url}`, {
        timeout: API_CONFIG.TIMEOUT,
      });

      setData(response.data);

      if (onSuccess) {
        onSuccess(response.data);
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to fetch data';
      setError(errorMessage);

      if (showErrorToast) {
        showToast.error(errorMessage);
      }

      if (onError) {
        onError(errorMessage);
      }
    } finally {
      setLoading(false);
    }
  }, [url, enabled, onSuccess, onError, showErrorToast]);

  useEffect(() => {
    fetchData();
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

        const fullUrl = `${API_CONFIG.QUERY_API_BASE_URL}${url}`;

        const response = await axios[method]<TData>(fullUrl, variables, {
          timeout: API_CONFIG.TIMEOUT,
        });

        if (showSuccessToast) {
          showToast.success(successMessage);
        }

        if (onSuccess) {
          onSuccess(response.data);
        }

        return response.data;
      } catch (err: any) {
        const errorMessage = err.response?.data?.detail || err.message || 'Operation failed';
        setError(errorMessage);

        if (showErrorToast) {
          showToast.error(errorMessage);
        }

        if (onError) {
          onError(errorMessage);
        }

        return null;
      } finally {
        setLoading(false);
      }
    },
    [method, onSuccess, onError, showSuccessToast, showErrorToast, successMessage]
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
