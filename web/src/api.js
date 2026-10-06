export const API_BASE = (import.meta.env.VITE_API_BASE || '').replace(/\/$/, '')
export const apiUrl = (path) => `${API_BASE}${path}`
