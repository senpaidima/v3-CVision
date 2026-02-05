const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

interface ApiClientOptions extends RequestInit {
  timeout?: number;
}

// Placeholder for auth token injection
let getAuthToken: (() => Promise<string | null>) | null = null;

export const setAuthTokenProvider = (
  provider: () => Promise<string | null>,
) => {
  getAuthToken = provider;
};

const getHeaders = async (options?: ApiClientOptions): Promise<HeadersInit> => {
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(options?.headers || {}),
  };

  if (getAuthToken) {
    const token = await getAuthToken();
    if (token) {
      (headers as any)["Authorization"] = `Bearer ${token}`;
    }
  }

  return headers;
};

const handleResponse = async <T>(response: Response): Promise<T> => {
  if (!response.ok) {
    const contentType = response.headers.get("content-type");
    let errorMessage = `API Request failed: ${response.status} ${response.statusText}`;

    try {
      if (contentType && contentType.includes("application/json")) {
        const errorData = await response.json();
        errorMessage = errorData.detail || errorData.message || errorMessage;
      } else {
        errorMessage = (await response.text()) || errorMessage;
      }
    } catch (e) {
      // ignore parsing errors
    }

    throw new Error(errorMessage);
  }

  // Handle empty responses
  if (response.status === 204) {
    return {} as T;
  }

  const contentType = response.headers.get("content-type");
  if (contentType && contentType.includes("application/json")) {
    return response.json();
  }

  return response.text() as unknown as T;
};

const apiClient = {
  async get<T>(endpoint: string, options?: ApiClientOptions): Promise<T> {
    const headers = await getHeaders(options);
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      method: "GET",
      headers,
    });
    return handleResponse<T>(response);
  },

  async post<T>(
    endpoint: string,
    data: unknown,
    options?: ApiClientOptions,
  ): Promise<T> {
    const headers = await getHeaders(options);
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      method: "POST",
      headers,
      body: JSON.stringify(data),
    });
    return handleResponse<T>(response);
  },

  async put<T>(
    endpoint: string,
    data: unknown,
    options?: ApiClientOptions,
  ): Promise<T> {
    const headers = await getHeaders(options);
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      method: "PUT",
      headers,
      body: JSON.stringify(data),
    });
    return handleResponse<T>(response);
  },

  async delete<T>(endpoint: string, options?: ApiClientOptions): Promise<T> {
    const headers = await getHeaders(options);
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      method: "DELETE",
      headers,
    });
    return handleResponse<T>(response);
  },

  // Basic streaming implementation
  async stream(
    endpoint: string,
    data: unknown,
    onToken: (token: string) => void,
    options?: ApiClientOptions,
  ): Promise<void> {
    const headers = await getHeaders(options);
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      method: "POST",
      headers,
      body: JSON.stringify(data),
    });

    if (!response.ok || !response.body) {
      throw new Error(
        `Streaming failed: ${response.status} ${response.statusText}`,
      );
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const text = decoder.decode(value, { stream: true });
      // Simple parsing assuming text chunks - real SSE might need more robust parsing
      onToken(text);
    }
  },
};

export default apiClient;
