import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider } from "../src/context/AuthContext";
import { AppRoutes } from "../src/App";

function renderWithAuth(initialEntries: string[]) {
  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={initialEntries}>
        <AppRoutes />
      </MemoryRouter>
    </AuthProvider>,
  );
}

test("redirects root to search", () => {
  renderWithAuth(["/"]);
  expect(screen.getByTestId("search-page")).toBeDefined();
});

test("navigates to lastenheft", () => {
  renderWithAuth(["/lastenheft"]);
  expect(screen.getByTestId("lastenheft-page")).toBeDefined();
});

test("navigates to employee detail", () => {
  renderWithAuth(["/employee/john-doe"]);
  expect(screen.getByTestId("employee-detail-page")).toBeDefined();
  expect(screen.getByText(/john-doe/)).toBeDefined();
});

test("authenticated user at /login redirects to search", () => {
  renderWithAuth(["/login"]);
  expect(screen.getByTestId("search-page")).toBeDefined();
});
