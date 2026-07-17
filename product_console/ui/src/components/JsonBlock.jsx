import React from 'react'

export default function JsonBlock({ value }) {
  return (
    <pre className="code-block">
      {JSON.stringify(value, null, 2)}
    </pre>
  )
}
