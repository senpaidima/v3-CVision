import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import LastenheftPage from "../src/pages/LastenheftPage";
import apiClient from "../src/services/apiClient";
import { BrowserRouter } from "react-router-dom";

// Mock i18next
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, options?: any) => {
      if (key === "lastenheft.candidatesFound") {
        return `${options.count} candidates found`;
      }
      return key;
    },
    i18n: {
      language: "en",
      changeLanguage: vi.fn(),
    },
  }),
}));

// Mock AuthContext
vi.mock("../src/context/AuthContext", () => ({
  useAuth: () => ({
    getAccessToken: vi.fn().mockResolvedValue("mock-token"),
  }),
}));

// Mock API Client
vi.mock("../src/services/apiClient", () => ({
  default: {
    post: vi.fn(),
  },
}));

// Mock fetch for file upload
(globalThis as any).fetch = vi.fn();

describe("LastenheftPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderComponent = () =>
    render(
      <BrowserRouter>
        <LastenheftPage />
      </BrowserRouter>,
    );

  it("renders upload phase initially", () => {
    renderComponent();
    expect(screen.getByTestId("lastenheft-page")).toBeDefined();
    expect(screen.getByTestId("file-upload")).toBeDefined();
    expect(screen.getByTestId("file-upload-tab")).toHaveClass("active");
  });

  it("switches to text paste tab", () => {
    renderComponent();
    const textTab = screen.getByTestId("text-paste-tab");
    fireEvent.click(textTab);
    expect(textTab).toHaveClass("active");
    expect(screen.getByTestId("text-input")).toBeDefined();
    expect(screen.getByTestId("analyze-btn")).toBeDisabled();
  });

  it("handles text input and analysis", async () => {
    const mockUploadResponse = {
      extracted_text: "Requirements text",
      char_count: 100,
      format: "text",
    };
    const mockAnalysisResponse = {
      quality_assessment: {
        overall: 85,
        summary: "Good quality",
        completeness: 80,
        clarity: 90,
        specificity: 85,
        feasibility: 85,
      },
      open_questions: [
        { question: "Q1", priority: "high", category: "technical" },
      ],
      extracted_skills: [{ name: "React", mandatory: true, category: "tech" }],
    };

    (apiClient.post as any)
      .mockResolvedValueOnce(mockUploadResponse)
      .mockResolvedValueOnce(mockAnalysisResponse);

    renderComponent();

    // Switch to text tab
    fireEvent.click(screen.getByTestId("text-paste-tab"));

    // Enter text
    const textarea = screen.getByTestId("text-input");
    fireEvent.change(textarea, { target: { value: "Requirements text" } });

    // Click analyze
    const analyzeBtn = screen.getByTestId("analyze-btn");
    expect(analyzeBtn).not.toBeDisabled();
    fireEvent.click(analyzeBtn);

    // Verify loading state handled implicitly by checking result appearance
    await waitFor(() => {
      expect(screen.getByTestId("quality-score")).toBeDefined();
    });

    // Check displayed results
    expect(screen.getByText("85/100")).toBeDefined();
    expect(screen.getByText("Good quality")).toBeDefined();
    expect(screen.getByText("Q1")).toBeDefined();
    expect(screen.getByText("React")).toBeDefined();
    expect(screen.getByTestId("find-candidates-btn")).toBeDefined();
  });

  it("handles file upload error (unsupported format)", async () => {
    renderComponent();
    const file = new File(["dummy"], "test.txt", { type: "text/plain" });
    const dropZone = screen.getByTestId("file-upload");

    fireEvent.drop(dropZone, {
      dataTransfer: {
        files: [file],
      },
    });

    await waitFor(() => {
      expect(screen.getByText("lastenheft.unsupportedFormat")).toBeDefined();
    });
  });

  it("handles candidate matching flow", async () => {
    // Setup analysis state
    const mockUploadResponse = {
      extracted_text: "text",
      char_count: 10,
      format: "text",
    };
    const mockAnalysisResponse = {
      quality_assessment: {
        overall: 80,
        summary: "ok",
        completeness: 80,
        clarity: 80,
        specificity: 80,
        feasibility: 80,
      },
      open_questions: [],
      extracted_skills: [],
    };
    const mockMatchResponse = {
      matches: [
        {
          employee_name: "John Doe",
          employee_alias: "jdoe",
          title: "Dev",
          location: "Berlin",
          skills: ["React"],
          total_score: 0.9,
          breakdown: {
            skill_match: 0.9,
            experience: 0.8,
            semantic_similarity: 0.85,
            availability: 1.0,
          },
          explanation: "Good match",
        },
      ],
      total_candidates_searched: 10,
      query_skills: [],
    };

    (apiClient.post as any)
      .mockResolvedValueOnce(mockUploadResponse) // Text upload
      .mockResolvedValueOnce(mockAnalysisResponse) // Analysis
      .mockResolvedValueOnce(mockMatchResponse); // Matching

    renderComponent();

    // Text flow to get to analysis
    fireEvent.click(screen.getByTestId("text-paste-tab"));
    fireEvent.change(screen.getByTestId("text-input"), {
      target: { value: "text" },
    });
    fireEvent.click(screen.getByTestId("analyze-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("find-candidates-btn")).toBeDefined();
    });

    // Click find candidates
    fireEvent.click(screen.getByTestId("find-candidates-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("matched-candidates")).toBeDefined();
    });

    expect(screen.getByText("John Doe")).toBeDefined();
    expect(screen.getByText("1 candidates found")).toBeDefined();
  });

  it("handles API errors gracefully", async () => {
    (apiClient.post as any).mockRejectedValue(new Error("API Error"));

    renderComponent();
    fireEvent.click(screen.getByTestId("text-paste-tab"));
    fireEvent.change(screen.getByTestId("text-input"), {
      target: { value: "text" },
    });
    fireEvent.click(screen.getByTestId("analyze-btn"));

    await waitFor(() => {
      expect(screen.getByText("lastenheft.error")).toBeDefined();
    });
  });
});
