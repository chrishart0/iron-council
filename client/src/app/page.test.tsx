import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import HomePage from "./page";

describe("HomePage", () => {
  it("links into the public browser routes, including leaderboard and completed matches", () => {
    render(<HomePage />);

    expect(screen.getByRole("link", { name: "View public matches" })).toHaveAttribute(
      "href",
      "/matches"
    );
    expect(screen.getByRole("link", { name: "View leaderboard" })).toHaveAttribute(
      "href",
      "/leaderboard"
    );
    expect(screen.getByRole("link", { name: "Browse completed matches" })).toHaveAttribute(
      "href",
      "/matches/completed"
    );
  });
});
