type UnauthorizedHandler = () => void

export async function apiRequest<T>(
  url: string,
  token: string,
  onUnauthorized: UnauthorizedHandler,
  init?: RequestInit
): Promise<T> {
  const headers = new Headers(init?.headers)
  if (!headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  if (token) headers.set('X-Api-Key', token)

  const res = await fetch(url, {
    ...init,
    headers
  })
  if (res.status === 401) {
    onUnauthorized()
    throw new Error('访问令牌不正确或已失效')
  }
  if (!res.ok) {
    throw new Error(await readErrorMessage(res))
  }
  return (await res.json()) as T
}

export async function verifyToken(token: string) {
  const res = await fetch('/Auth/verify', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token })
  })
  if (!res.ok) {
    let message = '访问令牌不正确'
    try {
      const payload = await res.json()
      message = payload?.message ?? message
    } catch {
      // Keep the friendly default message.
    }
    throw new Error(message)
  }
}

async function readErrorMessage(res: Response) {
  let message = `${res.status} ${res.statusText}`
  try {
    const payload = await res.json()
    const errors = payload?.errors ? Object.values(payload.errors).flat().join('；') : ''
    return payload?.message ?? payload?.Message ?? errors ?? payload?.title ?? message
  } catch {
    const text = await res.text()
    if (text) message = text
  }
  return message
}

