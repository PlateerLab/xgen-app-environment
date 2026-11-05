import { useEffect, useState } from 'react'
import { api } from './api.js'

export default function App() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api('api/example').then(setData).catch((e) => setError(e.message))
  }, [])

  return (
    <main className="app">
      <h1>App</h1>
      <p className="muted">FastAPI answers <code>api/*</code>; this page is the built React app.</p>
      {error && <p className="error">{error}</p>}
      {data && (
        <section>
          <p>{data.message}</p>
          <ul>
            {data.items.map((it) => (
              <li key={it.id}>
                {it.name}: <strong>{it.value}</strong>
              </li>
            ))}
          </ul>
        </section>
      )}
    </main>
  )
}
