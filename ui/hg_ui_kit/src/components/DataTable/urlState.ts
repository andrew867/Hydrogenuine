export type TableUrlState = {
  sort?: string;
  dir?: "asc" | "desc";
  page?: number;
  pageSize?: number;
  filters?: Record<string, string>;
};

export function readTableStateFromUrl(search: string): TableUrlState {
  const params = new URLSearchParams(search.startsWith("?") ? search.slice(1) : search);
  const filters: Record<string, string> = {};
  params.forEach((value, key) => {
    if (key.startsWith("f.")) filters[key.slice(2)] = value;
  });
  return {
    sort: params.get("sort") ?? undefined,
    dir: (params.get("dir") as "asc" | "desc" | null) ?? undefined,
    page: params.get("page") ? Number(params.get("page")) : undefined,
    pageSize: params.get("pageSize") ? Number(params.get("pageSize")) : undefined,
    filters: Object.keys(filters).length ? filters : undefined,
  };
}

export function writeTableStateToUrl(state: TableUrlState, base = ""): string {
  const params = new URLSearchParams(base.startsWith("?") ? base.slice(1) : base);
  if (state.sort) params.set("sort", state.sort);
  else params.delete("sort");
  if (state.dir) params.set("dir", state.dir);
  else params.delete("dir");
  if (state.page) params.set("page", String(state.page));
  else params.delete("page");
  if (state.pageSize) params.set("pageSize", String(state.pageSize));
  else params.delete("pageSize");
  Array.from(params.keys())
    .filter((k) => k.startsWith("f."))
    .forEach((k) => params.delete(k));
  if (state.filters) {
    Object.entries(state.filters).forEach(([k, v]) => {
      if (v) params.set(`f.${k}`, v);
    });
  }
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}
