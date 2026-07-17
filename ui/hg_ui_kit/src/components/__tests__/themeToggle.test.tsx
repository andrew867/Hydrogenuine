import { describe, expect, it } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { ThemeProvider } from "../../theme/ThemeProvider";
import { ThemeToggle } from "../ThemeToggle";

describe("ThemeToggle (U5)", () => {
  it("switches between light and dark modes", () => {
    render(
      <ThemeProvider defaultMode="dark">
        <ThemeToggle showDensity={false} />
      </ThemeProvider>,
    );
    expect(screen.getByText(/active theme:/i)).toHaveTextContent(/dark/i);
    fireEvent.click(screen.getByRole("radio", { name: "Light" }));
    expect(screen.getByText(/active theme:/i)).toHaveTextContent(/light/i);
  });
});
