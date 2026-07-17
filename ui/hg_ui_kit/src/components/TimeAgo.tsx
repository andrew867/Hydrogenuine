import React, { useEffect, useState } from "react";
import { formatRelativeTime, getEffectiveTimeZone, subscribeTimeZoneChange } from "../lib/timezone";

export function TimeAgo({ value, title }: { value: unknown; title?: string }) {
  const [now, setNow] = useState(() => Date.now());
  const [tz, setTz] = useState(getEffectiveTimeZone);

  useEffect(() => {
    const tick = window.setInterval(() => setNow(Date.now()), 30_000);
    const unsub = subscribeTimeZoneChange(setTz);
    return () => {
      window.clearInterval(tick);
      unsub();
    };
  }, []);

  const relative = formatRelativeTime(value, now);
  const absolute =
    value instanceof Date || typeof value === "string" || typeof value === "number"
      ? new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short", timeZone: tz }).format(
          new Date(value as string | number | Date),
        )
      : "";

  return (
    <time data-testid="hg-time-ago" dateTime={String(value)} title={title ?? absolute}>
      {relative}
    </time>
  );
}
