import { render, screen, fireEvent } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import ErrorBoundary from "../src/components/common/ErrorBoundary";

function ThrowingComponent({ message }: { message: string }) {
  throw new Error(message);
}

function SafeComponent() {
  return <div data-testid="safe-child">All good</div>;
}

test("renders children when no error occurs", () => {
  render(
    <ErrorBoundary>
      <SafeComponent />
    </ErrorBoundary>,
  );
  expect(screen.getByTestId("safe-child")).toBeDefined();
});

test("renders fallback UI when child throws", () => {
  const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

  render(
    <ErrorBoundary>
      <ThrowingComponent message="Test crash" />
    </ErrorBoundary>,
  );

  expect(screen.getByTestId("error-boundary-fallback")).toBeDefined();
  expect(screen.getByText("Something went wrong")).toBeDefined();
  expect(screen.getByText("Test crash")).toBeDefined();

  consoleSpy.mockRestore();
});

test("renders custom fallback when provided", () => {
  const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

  render(
    <ErrorBoundary fallback={<div data-testid="custom-fallback">Custom</div>}>
      <ThrowingComponent message="boom" />
    </ErrorBoundary>,
  );

  expect(screen.getByTestId("custom-fallback")).toBeDefined();

  consoleSpy.mockRestore();
});

test("reset button navigates to /search", () => {
  const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

  delete (window as any).location;
  (window as any).location = { href: "" };

  render(
    <ErrorBoundary>
      <ThrowingComponent message="crash" />
    </ErrorBoundary>,
  );

  fireEvent.click(screen.getByText("Go to Home"));
  expect(window.location.href).toBe("/search");

  consoleSpy.mockRestore();
});
