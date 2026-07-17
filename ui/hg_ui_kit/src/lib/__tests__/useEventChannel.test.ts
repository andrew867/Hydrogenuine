import { describe, expect, it } from "vitest";
import { parseSseChunk, parseSseFrame } from "../sseParse";

describe("useEventChannel (U-K9)", () => {
  it("parses SSE id, event, and data fields", () => {
    const frame = parseSseFrame('id: evt-42\nevent: swarm.workspace\ndata: {"ok":true}\n');
    expect(frame?.id).toBe("evt-42");
    expect(frame?.event).toBe("swarm.workspace");
    expect(frame?.data).toBe('{"ok":true}');
  });

  it("extracts frames from chunked buffers", () => {
    const chunk =
      'id: 1\nevent: runs.delta\ndata: {"runs":[]}\n\n' +
      "event: ping\ndata: {}\n\n" +
      'id: 2\nevent: runs.delta\ndata: {"runs":[{"run_id":"r1"}]}\n\n';
    const parsed = parseSseChunk(chunk, (frame) => frame);
    expect(parsed.items).toHaveLength(2);
    expect(parsed.items[1]?.id).toBe("2");
    expect(parsed.remainder).toBe("");
  });
});
