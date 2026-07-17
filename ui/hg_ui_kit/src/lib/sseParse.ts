export type SseFrame = {
  id?: string;
  event: string;
  data: string;
};

export function parseSseFrame(frame: string): SseFrame | null {
  const lines = frame.split(/\r?\n/);
  let event = "message";
  let id: string | undefined;
  const dataLines: string[] = [];
  for (const line of lines) {
    if (!line || line.startsWith(":")) continue;
    if (line.startsWith("event:")) event = line.slice(6).trim() || "message";
    else if (line.startsWith("id:")) id = line.slice(3).trim() || undefined;
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).trimStart());
  }
  if (dataLines.length === 0) return null;
  return { id, event, data: dataLines.join("\n") };
}

export function parseSseChunk<T>(
  buffer: string,
  onFrame: (frame: SseFrame) => T | null,
): { remainder: string; items: T[] } {
  const items: T[] = [];
  let remainder = buffer;
  while (true) {
    const boundary = remainder.indexOf("\n\n");
    if (boundary < 0) break;
    const frameText = remainder.slice(0, boundary);
    remainder = remainder.slice(boundary + 2);
    const frame = parseSseFrame(frameText);
    if (!frame || frame.event === "ping") continue;
    const item = onFrame(frame);
    if (item != null) items.push(item);
  }
  return { remainder, items };
}
