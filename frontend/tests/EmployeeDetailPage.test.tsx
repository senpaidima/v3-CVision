import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import EmployeeDetailPage from "../src/pages/EmployeeDetailPage";
import { MemoryRouter, Routes, Route } from "react-router-dom";

// Mock translations
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: any = {
        "employee.loading": "Loading...",
        "employee.notFound": "Employee not found",
        "employee.back": "Back",
        "employee.title": "Title",
        "employee.department": "Department",
        "employee.location": "Location",
        "common.error": "Error",
      };
      return translations[key] || key;
    },
    i18n: { language: "en" },
  }),
}));

// Mock useApi
const mockExecute = vi.fn();
let mockHookValues: any = {
  data: null,
  loading: false,
  error: null,
  execute: mockExecute,
};

vi.mock("../src/hooks/useApi", () => ({
  default: () => mockHookValues,
}));

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe("EmployeeDetailPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockHookValues = {
      data: null,
      loading: false,
      error: null,
      execute: mockExecute,
    };
  });

  const renderComponent = () => {
    return render(
      <MemoryRouter initialEntries={["/employee/jdoe"]}>
        <Routes>
          <Route path="/employee/:alias" element={<EmployeeDetailPage />} />
        </Routes>
      </MemoryRouter>,
    );
  };

  it("renders loading state", () => {
    mockHookValues.loading = true;
    renderComponent();
    expect(screen.getByTestId("loading-state")).toBeInTheDocument();
  });

  it("calls fetchEmployee on mount", () => {
    renderComponent();
    expect(mockExecute).toHaveBeenCalled();
  });

  it("renders employee data", () => {
    mockHookValues.data = {
      name: "John Doe",
      title: "Senior Dev",
      department: "Engineering",
      location: "Berlin",
      email: "john@example.com",
      phone: "123456",
      years_of_experience: "5",
    };

    renderComponent();

    expect(screen.getByTestId("employee-name")).toHaveTextContent("John Doe");
    expect(screen.getByTestId("employee-title")).toHaveTextContent(
      "Senior Dev",
    );
    expect(screen.getByTestId("employee-department")).toHaveTextContent(
      "Engineering",
    );
    expect(screen.getByTestId("employee-location")).toHaveTextContent("Berlin");
  });

  it("renders error state on API error", () => {
    mockHookValues.error = { message: "Failed to fetch" };
    renderComponent();
    expect(screen.getByTestId("error-state")).toBeInTheDocument();
    expect(screen.getByText("Failed to fetch")).toBeInTheDocument();
  });

  it("renders not found state when data is null and not loading", () => {
    mockHookValues.data = null;
    mockHookValues.loading = false;
    renderComponent();
    expect(screen.getByTestId("error-state")).toBeInTheDocument();
    expect(screen.getByText("Employee not found")).toBeInTheDocument();
  });

  it("navigates back when back button clicked", () => {
    mockHookValues.data = { name: "John Doe" };
    renderComponent();

    const backBtn = screen.getByTestId("back-button");
    fireEvent.click(backBtn);
    expect(mockNavigate).toHaveBeenCalledWith("/search");
  });
});
