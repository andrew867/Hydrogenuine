import React, { useCallback } from 'react'
import { DataTable } from 'hg_ui_kit'
import { formatDateTime } from '../../lib/timezone.js'
import { readHashSearch, writeHashSearch } from '../../lib/hashUrlState.js'

const columns = [
  {
    id: 'run_id',
    header: 'run_id',
    accessor: (row) => row.run_id,
    sortable: true,
    render: (row) => (
      <a href={`#/runs/${encodeURIComponent(row.run_id)}`}>{row.run_id}</a>
    ),
  },
  {
    id: 'graph_id',
    header: 'graph_id',
    accessor: (row) => row.graph_id || '',
    sortable: true,
  },
  {
    id: 'status',
    header: 'status',
    accessor: (row) => row.status || '',
    sortable: true,
  },
  {
    id: 'started',
    header: 'started',
    accessor: (row) => row.started_at || '',
    sortable: true,
    render: (row) => formatDateTime(row.started_at),
  },
]

export default function RunsDataTable({ runs }) {
  const onUrlChange = useCallback((search) => {
    writeHashSearch(search)
  }, [])

  return (
    <div className="scroll-table-wrap" data-testid="runs-datatable">
      <DataTable
        columns={columns}
        rows={runs}
        rowKey={(row) => row.run_id}
        syncUrl
        initialUrlSearch={readHashSearch()}
        onUrlChange={onUrlChange}
        pageSize={25}
      />
    </div>
  )
}
