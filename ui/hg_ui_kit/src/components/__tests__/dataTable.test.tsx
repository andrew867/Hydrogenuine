import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { DataTable } from "../DataTable";
import { readTableStateFromUrl, writeTableStateToUrl } from "../DataTable/urlState";
import { rowsToCsv } from "../DataTable/csvExport";

type Row = { id: string; name: string; status: string };

function makeRows(n: number): Row[] {
  return Array.from({ length: n }, (_, i) => ({
    id: `r-${i}`,
    name: `Run ${i}`,
    status: i % 2 === 0 ? "ok" : "warn",
  }));
}

describe("U-K3 DataTable", () => {
  const columns = [
    { id: "name", header: "Name", accessor: (r: Row) => r.name },
    { id: "status", header: "Status", accessor: (r: Row) => r.status },
  ];

  it("syncs URL state and virtualizes large bodies", () => {
    const onUrlChange = vi.fn();
    render(
      <DataTable
        columns={columns}
        rows={makeRows(500)}
        rowKey={(r) => r.id}
        pageSize={25}
        syncUrl
        onUrlChange={onUrlChange}
      />,
    );
    const body = screen.getByTestId("hg-data-table-body");
    expect(body.querySelectorAll("tr").length).toBeLessThan(100);
    fireEvent.click(screen.getByRole("button", { name: /Name/ }));
    expect(onUrlChange).toHaveBeenCalled();
    const last = onUrlChange.mock.calls.at(-1)?.[0] as string;
    expect(last).toContain("sort=name");
  });

  it("exports filtered CSV", () => {
    const rows = makeRows(3);
    const csv = rowsToCsv(
      rows.filter((r) => r.status === "ok").map((r) => ({ name: r.name, status: r.status })),
      ["name", "status"],
    );
    expect(csv.split("\n").length).toBe(3);
    expect(csv).toContain("Run 0");
    expect(csv).not.toContain("Run 1");
  });

  it("round-trips url state helpers", () => {
    const qs = writeTableStateToUrl({ sort: "name", dir: "desc", page: 2, filters: { status: "ok" } });
    const parsed = readTableStateFromUrl(qs);
    expect(parsed.sort).toBe("name");
    expect(parsed.dir).toBe("desc");
    expect(parsed.page).toBe(2);
    expect(parsed.filters?.status).toBe("ok");
  });
});
