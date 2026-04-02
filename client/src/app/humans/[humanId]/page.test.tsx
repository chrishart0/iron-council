import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import HumanProfileRoutePage from "./page";

vi.mock("../../../components/public/public-human-profile-page", () => ({
  PublicHumanProfilePage: ({ humanId }: { humanId: string }) => <div>{`profile:${humanId}`}</div>
}));

describe("HumanProfileRoutePage", () => {
  it("passes the dynamic human id through to the public profile page", async () => {
    render(
      await HumanProfileRoutePage({
        params: Promise.resolve({
          humanId: "human:00000000-0000-0000-0000-000000000301"
        })
      })
    );

    expect(
      screen.getByText("profile:human:00000000-0000-0000-0000-000000000301")
    ).toBeVisible();
  });
});
