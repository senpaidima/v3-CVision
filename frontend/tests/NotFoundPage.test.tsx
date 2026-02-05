import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { MemoryRouter } from "react-router-dom";
import NotFoundPage from "../src/pages/NotFoundPage";

function renderNotFound() {
  return render(
    <MemoryRouter>
      <NotFoundPage />
    </MemoryRouter>,
  );
}

test("renders 404 page with correct content", () => {
  renderNotFound();
  expect(screen.getByTestId("not-found-page")).toBeDefined();
  expect(screen.getByText("404")).toBeDefined();
  expect(screen.getByText("notFound.message")).toBeDefined();
});

test("renders go home button", () => {
  renderNotFound();
  expect(screen.getByTestId("not-found-home-button")).toBeDefined();
  expect(screen.getByText("notFound.goHome")).toBeDefined();
});
