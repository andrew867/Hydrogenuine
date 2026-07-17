import React from 'react'

export default function JsonBlock({ value }) {
  return (
    <pre className="code-block" style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', overflowWrap: 'break-word' }}>
      {JSON.stringify(value, null, 2)}
    </pre>
  )
}


