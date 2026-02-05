import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import App from "../src/App";

test("App renders and shows header", () => {
  render(<App />);
  expect(screen.getByTestId("header")).toBeDefined();
});
