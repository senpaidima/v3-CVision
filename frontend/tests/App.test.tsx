import { render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import App from "../src/App";

const mockMsalInstance = {
  initialize: vi.fn().mockResolvedValue(undefined),
  handleRedirectPromise: vi.fn().mockResolvedValue(null),
  loginRedirect: vi.fn(),
  logoutRedirect: vi.fn(),
  acquireTokenSilent: vi.fn().mockResolvedValue({ accessToken: "mock-token" }),
  acquireTokenPopup: vi.fn().mockResolvedValue({ accessToken: "mock-token" }),
  getAllAccounts: () => [],
};

test("App renders and shows header for authenticated user", () => {
  render(<App msalInstance={mockMsalInstance as any} />);
  expect(screen.getByTestId("header")).toBeDefined();
});
