import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import SearchPage from "../src/pages/SearchPage";
import { BrowserRouter } from "react-router-dom";

// Mock translations
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: any = {
        "search.title": "AI Employee Search",
        "search.placeholder": "Describe...",
        "search.submit": "Search",
        "search.loading": "Loading...",
        "search.error": "Error",
      };
      return translations[key] || key;
    },
    i18n: {
      language: "en",
      changeLanguage: vi.fn(),
    },
  }),
}));

// Mock useStreamingSearch
const mockSendQuery = vi.fn();
interface MockHookValues {
  isLoading: boolean;
  isStreaming: boolean;
  aiResponse: string;
  employees: any[];
  error: string | null;
  sendQuery: any;
  abort: any;
}

const mockHookValues: MockHookValues = {
  isLoading: false,
  isStreaming: false,
  aiResponse: "",
  employees: [],
  error: null,
  sendQuery: mockSendQuery,
  abort: vi.fn(),
};

vi.mock("../src/hooks/useStreamingSearch", () => ({
  useStreamingSearch: () => mockHookValues,
}));

// Setup function
const renderSearchPage = () => {
  return render(
    <BrowserRouter>
      <SearchPage />
    </BrowserRouter>,
  );
};

describe("SearchPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.assign(mockHookValues, {
      isLoading: false,
      isStreaming: false,
      aiResponse: "",
      employees: [],
      error: null,
    });
  });

  it("renders search page with input and submit button", () => {
    renderSearchPage();
    expect(screen.getByTestId("search-page")).toBeInTheDocument();
    expect(screen.getByTestId("chat-input")).toBeInTheDocument();
    expect(screen.getByTestId("chat-submit")).toBeInTheDocument();
  });

  it("disables submit button when input is empty", () => {
    renderSearchPage();
    const submitBtn = screen.getByTestId("chat-submit");
    expect(submitBtn).toBeDisabled();

    const input = screen.getByTestId("chat-input");
    fireEvent.change(input, { target: { value: "  " } });
    expect(submitBtn).toBeDisabled();
  });

  it("enables submit button when input has text", () => {
    renderSearchPage();
    const input = screen.getByTestId("chat-input");
    const submitBtn = screen.getByTestId("chat-submit");

    fireEvent.change(input, { target: { value: "developer" } });
    expect(submitBtn).not.toBeDisabled();
  });

  it("calls sendQuery when form is submitted", async () => {
    renderSearchPage();
    const input = screen.getByTestId("chat-input");
    const submitBtn = screen.getByTestId("chat-submit");

    fireEvent.change(input, { target: { value: "developer" } });
    fireEvent.click(submitBtn);

    expect(mockSendQuery).toHaveBeenCalledWith("developer");
  });

  it("displays streaming response", () => {
    mockHookValues.isStreaming = true;
    mockHookValues.aiResponse = "Streaming content...";
    renderSearchPage();

    expect(screen.getByText("Streaming content...")).toBeInTheDocument();
  });

  it("displays employee cards when present", () => {
    mockHookValues.isStreaming = true;
    mockHookValues.employees = [
      { name: "John Doe", title: "Developer", alias: "jdoe" },
    ];
    renderSearchPage();

    expect(screen.getByText("John Doe")).toBeInTheDocument();
    expect(screen.getByText("Developer")).toBeInTheDocument();
    expect(screen.getByText("@jdoe")).toBeInTheDocument();
  });

  it("displays error message", () => {
    mockHookValues.error = "Something went wrong";
    renderSearchPage();

    expect(screen.getByText("Error: Something went wrong")).toBeInTheDocument();
  });
});
