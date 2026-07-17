import { describe, expect, it } from "vitest";
import { parseNotificationPayload, parseNotificationSseChunk } from "../useNotificationStream";

describe("useNotificationStream", () => {
  it("parses notification SSE payloads", () => {
    const item = parseNotificationPayload(
      JSON.stringify({
        id: "approval-1",
        title: "Approval required",
        href: "/approvals",
        type: "approval.created",
      }),
    );
    expect(item?.id).toBe("approval-1");
    expect(item?.title).toBe("Approval required");
    expect(item?.href).toBe("/approvals");
  });

  it("extracts notification frames from SSE chunks", () => {
    const chunk =
      'event: notification\ndata: {"id":"n-1","title":"Export ready","href":"/settings"}\n\n' +
      "event: ping\ndata: {}\n\n";
    const parsed = parseNotificationSseChunk(chunk);
    expect(parsed.notifications).toHaveLength(1);
    expect(parsed.notifications[0]?.title).toBe("Export ready");
    expect(parsed.remainder).toBe("");
  });
});
