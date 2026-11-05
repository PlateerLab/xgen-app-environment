// api() CALLS the backend and returns the parsed body. It is not a URL builder.
//
//   const items = await api('api/items')                       // GET
//   await api('api/items', { method: 'POST', body: { name } }) // POST (JSON)
//
// Do NOT wrap it in fetch(): `fetch(api('api/items'))` fetches the string
// "[object Promise]", which is not your API, and the page then fails with
// "Unexpected token '<', "<!doctype"... is not valid JSON".
//
// Paths are RELATIVE ('api/items', never '/api/items') so the app works under
// whatever path prefix the platform mounts it on.
export async function api(path, init = {}) {
  const url = String(path).replace(/^\/+/, '')
  const headers = { ...(init.headers || {}) }
  let body = init.body
  if (body && typeof body === 'object' && !(body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(body)
  }
  const res = await fetch(url, { ...init, headers, body })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`${res.status} ${res.statusText}${text ? ` — ${text.slice(0, 200)}` : ''}`)
  }
  const type = res.headers.get('content-type') || ''
  return type.includes('application/json') ? res.json() : res.text()
}
