import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { RecognitionActiveBadge } from "../RecognitionActiveBadge";

describe("RecognitionActiveBadge", () => {
  it("renders when recognition is active", () => {
    render(<RecognitionActiveBadge active effectiveClass="workspace" />);
    expect(screen.getByTestId("hg-recognition-active-badge")).toHaveTextContent("Recognition active · workspace");
  });

  it("renders nothing when inactive", () => {
    const { container } = render(<RecognitionActiveBadge active={false} />);
    expect(container).toBeEmptyDOMElement();
  });
});
