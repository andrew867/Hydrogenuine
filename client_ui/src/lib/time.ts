import { formatDistanceToNowStrict } from "date-fns";

export function relTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return formatDistanceToNowStrict(d, { addSuffix: true });
}
