export type PaletteAction = {
  id: string;
  label: string;
  keywords?: string[];
  recency?: number;
  run: () => void;
};

export function scoreAction(action: PaletteAction, query: string): number {
  const q = query.trim().toLowerCase();
  if (!q) return (action.recency ?? 0) * 0.01;
  const hay = [action.label, ...(action.keywords ?? [])].join(" ").toLowerCase();
  if (hay === q) return 100 + (action.recency ?? 0) * 0.01;
  if (hay.startsWith(q)) return 80 + (action.recency ?? 0) * 0.01;
  if (hay.includes(q)) return 50 + (action.recency ?? 0) * 0.01;
  let qi = 0;
  for (let i = 0; i < hay.length && qi < q.length; i += 1) {
    if (hay[i] === q[qi]) qi += 1;
  }
  if (qi === q.length) return 30 + (action.recency ?? 0) * 0.01;
  return -1;
}

export function searchActions(actions: PaletteAction[], query: string): PaletteAction[] {
  return actions
    .map((action) => ({ action, score: scoreAction(action, query) }))
    .filter((row) => row.score >= 0)
    .sort((a, b) => b.score - a.score)
    .map((row) => row.action);
}
