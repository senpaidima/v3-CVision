import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { MemoryRouter } from "react-router-dom";
import Layout from "../src/components/layout/Layout";

test("Header renders with nav links", () => {
  render(
    <MemoryRouter>
      <Layout />
    </MemoryRouter>,
  );
  expect(screen.getByTestId("header")).toBeDefined();
  expect(screen.getByTestId("nav-search")).toBeDefined();
  expect(screen.getByTestId("nav-lastenheft")).toBeDefined();
});

test("Language toggle is present", () => {
  render(
    <MemoryRouter>
      <Layout />
    </MemoryRouter>,
  );
  expect(screen.getByTestId("language-toggle")).toBeDefined();
});
