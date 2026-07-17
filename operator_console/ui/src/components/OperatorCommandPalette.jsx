import React, { useEffect, useMemo, useState } from 'react'
import { CommandPalette } from 'hg_ui_kit'
import { OPERATOR_NAV_GROUPS } from '../routes/manifest.js'
import { api } from '../lib/api.js'

export default function OperatorCommandPalette({ navigate }) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [searchItems, setSearchItems] = useState([])

  useEffect(() => {
    const onKeyDown = (event) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setOpen(true)
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  useEffect(() => {
    if (!open) {
      setQuery('')
      setSearchItems([])
      return undefined
    }
    let cancelled = false
    const timer = window.setTimeout(() => {
      api
        .search(query, 20)
        .then((r) => {
          if (!cancelled) setSearchItems(Array.isArray(r.items) ? r.items : [])
        })
        .catch(() => {
          if (!cancelled) setSearchItems([])
        })
    }, query.trim() ? 180 : 0)
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [open, query])

  const navActions = useMemo(
    () =>
      OPERATOR_NAV_GROUPS.flatMap((group) =>
        group.items.map((item) => ({
          id: item.href.replace(/[^a-z0-9]+/gi, '-'),
          label: `${group.title}: ${item.label}`,
          keywords: [group.title, item.label],
          run: () => {
            const path = item.href.replace(/^#\/?/, '/')
            navigate(path === '/' ? '/' : path)
          },
        })),
      ),
    [navigate],
  )

  const searchActions = useMemo(
    () =>
      searchItems.map((item) => {
        const type = String(item.type || 'item')
        const id = String(item.id || '')
        const title = String(item.title || id)
        return {
          id: `search-${type}-${id}`.replace(/[^a-z0-9-]+/gi, '-'),
          label: `${type}: ${title}`,
          keywords: [type, title, id, String(item.status || '')],
          run: () => {
            const href = String(item.href || '/')
            navigate(href.startsWith('/') ? href : `/${href}`)
          },
        }
      }),
    [searchItems, navigate],
  )

  const actions = useMemo(() => [...searchActions, ...navActions], [searchActions, navActions])

  return (
    <CommandPalette
      open={open}
      onClose={() => setOpen(false)}
      actions={actions}
      onQueryChange={setQuery}
    />
  )
}
