import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { AppRoutes } from "../src/App";

test("redirects root to search", () => {
  render(
    <MemoryRouter initialEntries={["/"]}>
      <AppRoutes />
    </MemoryRouter>,
  );
  expect(screen.getByTestId("search-page")).toBeDefined();
});

test("navigates to lastenheft", () => {
  render(
    <MemoryRouter initialEntries={["/lastenheft"]}>
      <AppRoutes />
    </MemoryRouter>,
  );
  expect(screen.getByTestId("lastenheft-page")).toBeDefined();
});

test("navigates to employee detail", () => {
  render(
    <MemoryRouter initialEntries={["/employee/john-doe"]}>
      <AppRoutes />
    </MemoryRouter>,
  );
  expect(screen.getByTestId("employee-detail-page")).toBeDefined();
  expect(screen.getByText(/john-doe/)).toBeDefined();
});

test("navigates to login", () => {
  render(
    <MemoryRouter initialEntries={["/login"]}>
      <AppRoutes />
    </MemoryRouter>,
  );
  expect(screen.getByTestId("login-page")).toBeDefined();
});
