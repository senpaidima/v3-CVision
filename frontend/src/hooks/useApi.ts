import { useState, useCallback } from "react";
import apiClient from "../services/apiClient";

interface UseApiState<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
}

interface UseApiOptions {
  immediate?: boolean;
}

function useApi<T>(endpoint: string, options?: UseApiOptions) {
  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    loading: !!options?.immediate,
    error: null,
  });

  const execute = useCallback(
    async (
      method: "get" | "post" | "put" | "delete" = "get",
      body?: unknown,
    ) => {
      setState((prev) => ({ ...prev, loading: true, error: null }));
      try {
        let result: T;
        switch (method) {
          case "post":
            result = await apiClient.post<T>(endpoint, body);
            break;
          case "put":
            result = await apiClient.put<T>(endpoint, body);
            break;
          case "delete":
            result = await apiClient.delete<T>(endpoint);
            break;
          case "get":
          default:
            result = await apiClient.get<T>(endpoint);
            break;
        }
        setState({ data: result, loading: false, error: null });
        return result;
      } catch (error) {
        const err = error instanceof Error ? error : new Error(String(error));
        setState({ data: null, loading: false, error: err });
        throw err;
      }
    },
    [endpoint],
  );

  return { ...state, execute };
}

export default useApi;
