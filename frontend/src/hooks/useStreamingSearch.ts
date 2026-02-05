import { useState, useRef, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { useTranslation } from "react-i18next";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export interface Employee {
  name: string;
  alias: string;
  title: string;
}

interface UseStreamingSearchReturn {
  isLoading: boolean;
  isStreaming: boolean;
  aiResponse: string;
  employees: Employee[];
  error: string | null;
  sendQuery: (query: string) => Promise<void>;
  abort: () => void;
}

export const useStreamingSearch = (): UseStreamingSearchReturn => {
  const { getAccessToken } = useAuth();
  const { i18n } = useTranslation();
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [aiResponse, setAiResponse] = useState("");
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const abort = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setIsLoading(false);
      setIsStreaming(false);
    }
  }, []);

  const sendQuery = useCallback(
    async (query: string) => {
      abort();
      abortControllerRef.current = new AbortController();

      setIsLoading(true);
      setIsStreaming(true);
      setAiResponse("");
      setEmployees([]);
      setError(null);

      try {
        const token = await getAccessToken();
        const headers: HeadersInit = {
          "Content-Type": "application/json",
        };
        if (token) {
          headers["Authorization"] = `Bearer ${token}`;
        }

        const response = await fetch(`${API_BASE_URL}/api/v1/chat/stream`, {
          method: "POST",
          headers,
          body: JSON.stringify({
            query,
            history: [],
            language: i18n.language,
          }),
          signal: abortControllerRef.current.signal,
        });

        if (!response.ok) {
          throw new Error(`Search failed: ${response.statusText}`);
        }

        if (!response.body) {
          throw new Error("No response body");
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const parts = buffer.split("\n\n");
          buffer = parts.pop() || "";

          for (const part of parts) {
            if (!part.trim()) continue;

            const lines = part.split("\n");
            let eventType = "";
            let eventData = "";

            for (const line of lines) {
              if (line.startsWith("event: ")) {
                eventType = line.substring(7).trim();
              } else if (line.startsWith("data: ")) {
                eventData = line.substring(6).trim();
              }
            }

            if (eventData) {
              try {
                const data = JSON.parse(eventData);

                if (eventType === "token") {
                  setAiResponse((prev) => prev + (data.content || ""));
                } else if (eventType === "search_complete") {
                  if (data.employees) {
                    setEmployees(data.employees);
                  }
                } else if (eventType === "complete") {
                  setIsStreaming(false);
                  setIsLoading(false);
                } else if (eventType === "error") {
                  setError(data.error);
                  setIsStreaming(false);
                  setIsLoading(false);
                }
              } catch (e) {
                console.error("Failed to parse event data", e);
              }
            }
          }
        }
      } catch (err: any) {
        if (err.name === "AbortError") {
          console.log("Search aborted");
        } else {
          setError(err.message || "An error occurred");
          setIsLoading(false);
          setIsStreaming(false);
        }
      } finally {
        if (!abortControllerRef.current?.signal.aborted) {
          // Ensure loading state is correct if loop finishes
          // Note: We might want to keep isLoading true if we are waiting for something else,
          // but here the loop finishes when stream is done.
          setIsLoading(false);
          setIsStreaming(false);
        }
      }
    },
    [getAccessToken, abort, i18n.language],
  );

  return {
    isLoading,
    isStreaming,
    aiResponse,
    employees,
    error,
    sendQuery,
    abort,
  };
};
