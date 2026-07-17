import React, { useEffect, useMemo, useState } from "react";
import { Button } from "../Button";
import { Input } from "../Input";
import { readTableStateFromUrl, writeTableStateToUrl, type TableUrlState } from "./urlState";
import { rowsToCsv } from "./csvExport";

export type DataTableColumn<T> = {
  id: string;
  header: string;
  accessor: (row: T) => unknown;
  sortable?: boolean;
  render?: (row: T) => React.ReactNode;
};

export type DataTableProps<T extends Record<string, unknown>> = {
  columns: DataTableColumn<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  pageSize?: number;
  virtualizeThreshold?: number;
  syncUrl?: boolean;
  onUrlChange?: (search: string) => void;
  initialUrlSearch?: string;
};

function compareValues(a: unknown, b: unknown): number {
  if (a == null && b == null) return 0;
  if (a == null) return -1;
  if (b == null) return 1;
  if (typeof a === "number" && typeof b === "number") return a - b;
  return String(a).localeCompare(String(b));
}

export function DataTable<T extends Record<string, unknown>>({
  columns,
  rows,
  rowKey,
  pageSize = 25,
  virtualizeThreshold = 200,
  syncUrl = false,
  onUrlChange,
  initialUrlSearch = "",
}: DataTableProps<T>) {
  const [urlState, setUrlState] = useState<TableUrlState>(() =>
    syncUrl ? readTableStateFromUrl(initialUrlSearch) : {},
  );
  const [filters, setFilters] = useState<Record<string, string>>(urlState.filters ?? {});
  const sort = urlState.sort;
  const dir = urlState.dir ?? "asc";
  const page = urlState.page ?? 1;
  const effectivePageSize = urlState.pageSize ?? pageSize;

  useEffect(() => {
    if (!syncUrl) return;
    const next = writeTableStateToUrl({ ...urlState, filters, page, pageSize: effectivePageSize });
    onUrlChange?.(next);
  }, [syncUrl, urlState, filters, page, effectivePageSize, onUrlChange]);

  const filtered = useMemo(() => {
    const entries = Object.entries(filters).filter(([, v]) => v.trim());
    if (entries.length === 0) return rows;
    return rows.filter((row) =>
      entries.every(([col, value]) => {
        const column = columns.find((c) => c.id === col);
        if (!column) return true;
        return String(column.accessor(row)).toLowerCase().includes(value.toLowerCase());
      }),
    );
  }, [rows, filters, columns]);

  const sorted = useMemo(() => {
    if (!sort) return filtered;
    const column = columns.find((c) => c.id === sort);
    if (!column) return filtered;
    const copy = [...filtered];
    copy.sort((a, b) => {
      const cmp = compareValues(column.accessor(a), column.accessor(b));
      return dir === "asc" ? cmp : -cmp;
    });
    return copy;
  }, [filtered, sort, dir, columns]);

  const totalPages = Math.max(1, Math.ceil(sorted.length / effectivePageSize));
  const currentPage = Math.min(page, totalPages);
  const pageRows = sorted.slice((currentPage - 1) * effectivePageSize, currentPage * effectivePageSize);
  const virtualized = sorted.length > virtualizeThreshold;
  const visibleRows = virtualized ? pageRows.slice(0, Math.min(pageRows.length, 50)) : pageRows;

  const exportCsv = () => {
    const ids = columns.map((c) => c.id);
    const data = sorted.map((row) =>
      Object.fromEntries(columns.map((col) => [col.id, col.accessor(row)])),
    );
    const csv = rowsToCsv(data, ids);
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "export.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div data-testid="hg-data-table">
      <div style={{ display: "flex", gap: 8, marginBottom: 8, flexWrap: "wrap" }}>
        {columns.map((col) => (
          <Input
            key={col.id}
            placeholder={`Filter ${col.header}`}
            value={filters[col.id] ?? ""}
            onChange={(e) => {
              const next = { ...filters, [col.id]: e.target.value };
              setFilters(next);
              setUrlState((s) => ({ ...s, filters: next, page: 1 }));
            }}
            aria-label={`Filter ${col.header}`}
          />
        ))}
        <Button onClick={exportCsv}>Export CSV</Button>
      </div>
      <div style={{ overflow: "auto", maxHeight: virtualized ? 400 : undefined }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead style={{ position: "sticky", top: 0, background: "var(--hg-surface-raised)" }}>
            <tr>
              {columns.map((col) => (
                <th key={col.id} style={{ textAlign: "left", padding: 8, borderBottom: "1px solid var(--hg-border)" }}>
                  {col.sortable === false ? (
                    col.header
                  ) : (
                    <button
                      type="button"
                      className="hg-btn"
                      onClick={() =>
                        setUrlState((s) => ({
                          ...s,
                          sort: col.id,
                          dir: s.sort === col.id && s.dir === "asc" ? "desc" : "asc",
                        }))
                      }
                    >
                      {col.header}
                      {sort === col.id ? (dir === "asc" ? " ↑" : " ↓") : ""}
                    </button>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody data-testid="hg-data-table-body">
            {visibleRows.map((row) => (
              <tr key={rowKey(row)}>
                {columns.map((col) => (
                  <td key={col.id} style={{ padding: 8, borderBottom: "1px solid var(--hg-border)" }}>
                    {col.render ? col.render(row) : String(col.accessor(row) ?? "")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div style={{ display: "flex", gap: 8, marginTop: 8, alignItems: "center" }}>
        <Button
          disabled={currentPage <= 1}
          onClick={() => setUrlState((s) => ({ ...s, page: Math.max(1, (s.page ?? 1) - 1) }))}
        >
          Previous
        </Button>
        <span>
          Page {currentPage} / {totalPages} ({sorted.length} rows)
        </span>
        <Button
          disabled={currentPage >= totalPages}
          onClick={() => setUrlState((s) => ({ ...s, page: Math.min(totalPages, (s.page ?? 1) + 1) }))}
        >
          Next
        </Button>
      </div>
    </div>
  );
}

export { readTableStateFromUrl, writeTableStateToUrl, rowsToCsv };
