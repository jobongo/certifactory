# PKI Server Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the React SPA frontend for the PKI certificate management server, connecting to the existing FastAPI backend at localhost:8000.

**Architecture:** Vite-scaffolded React 18 SPA. Tailwind CSS with custom obsidian dark/light theme. TanStack Query v5 for all server state (caching, refetching, mutations). React Router v6 for routing. Axios for HTTP with JWT interceptor. All components built from scratch — no component library. Frontend is presentation only; all logic on backend.

**Tech Stack:** Vite, React 18, Tailwind CSS, TanStack Query v5, React Router v6, Axios

---

## File Structure

```
frontend/
├── src/
│   ├── main.jsx
│   ├── App.jsx
│   ├── api/
│   │   ├── client.js
│   │   ├── auth.js
│   │   ├── users.js
│   │   ├── cas.js
│   │   ├── certificates.js
│   │   ├── crl.js
│   │   ├── audit.js
│   │   └── dashboard.js
│   ├── hooks/
│   │   ├── useAuth.jsx
│   │   └── useTheme.js
│   ├── components/
│   │   ├── layout/
│   │   │   ├── AppLayout.jsx
│   │   │   ├── Sidebar.jsx
│   │   │   └── Navbar.jsx
│   │   ├── ui/
│   │   │   ├── Button.jsx
│   │   │   ├── Input.jsx
│   │   │   ├── Select.jsx
│   │   │   ├── Modal.jsx
│   │   │   ├── Table.jsx
│   │   │   ├── Badge.jsx
│   │   │   ├── Card.jsx
│   │   │   ├── Tabs.jsx
│   │   │   └── Dropdown.jsx
│   │   ├── forms/
│   │   │   ├── SubjectDNFields.jsx
│   │   │   ├── SANFields.jsx
│   │   │   ├── KeyUsageCheckboxes.jsx
│   │   │   ├── EKUCheckboxes.jsx
│   │   │   └── CustomExtensions.jsx
│   │   └── shared/
│   │       ├── StatusBadge.jsx
│   │       ├── CertChain.jsx
│   │       └── ProtectedRoute.jsx
│   ├── pages/
│   │   ├── Login.jsx
│   │   ├── Dashboard.jsx
│   │   ├── cas/
│   │   │   ├── CAList.jsx
│   │   │   ├── CADetail.jsx
│   │   │   └── CACreate.jsx
│   │   ├── certificates/
│   │   │   ├── CertificateList.jsx
│   │   │   ├── CertificateDetail.jsx
│   │   │   ├── CertificateCreate.jsx
│   │   │   └── CSRSubmit.jsx
│   │   ├── PendingRequests.jsx
│   │   ├── AuditLog.jsx
│   │   └── Users.jsx
│   └── utils/
│       └── icons.jsx
├── index.html
├── tailwind.config.js
├── postcss.config.js
├── vite.config.js
└── package.json
```

---

## Task 1: Project Scaffold & Tailwind Theme

**Files:**
- Create: `frontend/` (Vite scaffold)
- Create: `frontend/tailwind.config.js`
- Create: `frontend/src/index.css`

- [ ] **Step 1: Scaffold Vite project**

Run from `/home/jobongo/projects/pki_server`:

```bash
npm create vite@latest frontend -- --template react
cd frontend
npm install
npm install -D tailwindcss @tailwindcss/vite
npm install axios @tanstack/react-query react-router-dom
```

- [ ] **Step 2: Configure Tailwind with obsidian theme**

Replace `frontend/tailwind.config.js`:

```js
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        surface: {
          1: '#161616',
          2: '#181818',
          3: '#1e1e1e',
          4: '#252525',
        },
      },
    },
  },
  plugins: [],
}
```

- [ ] **Step 3: Set up CSS entry point**

Replace `frontend/src/index.css`:

```css
@import "tailwindcss";

@theme {
  --color-surface-1: #161616;
  --color-surface-2: #181818;
  --color-surface-3: #1e1e1e;
  --color-surface-4: #252525;
}
```

- [ ] **Step 4: Update vite.config.js with Tailwind plugin and API proxy**

Replace `frontend/vite.config.js`:

```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

- [ ] **Step 5: Clean up default files**

Delete `src/App.css` and `src/assets/`. Replace `src/App.jsx`:

```jsx
export default function App() {
  return (
    <div className="min-h-screen bg-white dark:bg-surface-1 text-gray-900 dark:text-gray-100">
      <h1 className="text-2xl p-8">PKI Manager</h1>
    </div>
  )
}
```

Replace `src/main.jsx`:

```jsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>
)
```

- [ ] **Step 6: Verify dev server starts**

Run: `cd frontend && npm run dev`

Open http://localhost:5173 — should show "PKI Manager" on a white background.

- [ ] **Step 7: Commit**

```bash
git add frontend/
git commit -m "feat: scaffold frontend with Vite, React, Tailwind obsidian theme"
```

---

## Task 2: Icons & Theme Hook

**Files:**
- Create: `frontend/src/utils/icons.jsx`
- Create: `frontend/src/hooks/useTheme.js`

- [ ] **Step 1: Create icon components**

Create `frontend/src/utils/icons.jsx`:

```jsx
export function DashboardIcon({ className = 'w-5 h-5' }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" />
      <rect x="3" y="14" width="7" height="7" /><rect x="14" y="14" width="7" height="7" />
    </svg>
  )
}

export function CertificateAuthorityIcon({ className = 'w-5 h-5' }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" />
    </svg>
  )
}

export function CertificateIcon({ className = 'w-5 h-5' }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
    </svg>
  )
}

export function ClockIcon({ className = 'w-5 h-5' }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" />
    </svg>
  )
}

export function AuditIcon({ className = 'w-5 h-5' }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" />
    </svg>
  )
}

export function UsersIcon({ className = 'w-5 h-5' }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  )
}

export function SunIcon({ className = 'w-5 h-5' }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="5" />
      <line x1="12" y1="1" x2="12" y2="3" /><line x1="12" y1="21" x2="12" y2="23" />
      <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" /><line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
      <line x1="1" y1="12" x2="3" y2="12" /><line x1="21" y1="12" x2="23" y2="12" />
      <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" /><line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
    </svg>
  )
}

export function MoonIcon({ className = 'w-5 h-5' }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
    </svg>
  )
}

export function BellIcon({ className = 'w-5 h-5' }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
      <path d="M13.73 21a2 2 0 0 1-3.46 0" />
    </svg>
  )
}

export function ChevronDownIcon({ className = 'w-4 h-4' }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="6 9 12 15 18 9" />
    </svg>
  )
}

export function ChevronRightIcon({ className = 'w-4 h-4' }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="9 18 15 12 9 6" />
    </svg>
  )
}

export function PlusIcon({ className = 'w-5 h-5' }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  )
}

export function XIcon({ className = 'w-5 h-5' }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  )
}

export function DownloadIcon({ className = 'w-5 h-5' }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" />
    </svg>
  )
}

export function SearchIcon({ className = 'w-5 h-5' }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  )
}

export function MenuIcon({ className = 'w-5 h-5' }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <line x1="3" y1="12" x2="21" y2="12" /><line x1="3" y1="6" x2="21" y2="6" /><line x1="3" y1="18" x2="21" y2="18" />
    </svg>
  )
}

export function CheckIcon({ className = 'w-5 h-5' }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  )
}

export function TreeIcon({ className = 'w-5 h-5' }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <line x1="6" y1="3" x2="6" y2="15" /><circle cx="18" cy="6" r="3" /><circle cx="6" cy="18" r="3" />
      <path d="M18 9a9 9 0 0 1-9 9" />
    </svg>
  )
}

export function TableIcon({ className = 'w-5 h-5' }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <line x1="3" y1="9" x2="21" y2="9" /><line x1="3" y1="15" x2="21" y2="15" />
      <line x1="9" y1="3" x2="9" y2="21" />
    </svg>
  )
}
```

- [ ] **Step 2: Create theme hook**

Create `frontend/src/hooks/useTheme.js`:

```js
import { useState, useEffect } from 'react'

export function useTheme() {
  const [isDark, setIsDark] = useState(() => {
    const saved = localStorage.getItem('theme')
    if (saved) return saved === 'dark'
    return window.matchMedia('(prefers-color-scheme: dark)').matches
  })

  useEffect(() => {
    const root = document.documentElement
    if (isDark) {
      root.classList.add('dark')
    } else {
      root.classList.remove('dark')
    }
    localStorage.setItem('theme', isDark ? 'dark' : 'light')
  }, [isDark])

  const toggle = () => setIsDark(prev => !prev)

  return { isDark, toggle }
}
```

- [ ] **Step 3: Verify icons render**

Temporarily import a few icons in `App.jsx` and render them to verify they display correctly.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/utils/icons.jsx frontend/src/hooks/useTheme.js
git commit -m "feat: monochrome SVG icons and dark/light theme hook"
```

---

## Task 3: API Client & Auth

**Files:**
- Create: `frontend/src/api/client.js`
- Create: `frontend/src/api/auth.js`
- Create: `frontend/src/api/dashboard.js`
- Create: `frontend/src/api/cas.js`
- Create: `frontend/src/api/certificates.js`
- Create: `frontend/src/api/users.js`
- Create: `frontend/src/api/audit.js`
- Create: `frontend/src/api/crl.js`
- Create: `frontend/src/hooks/useAuth.jsx`

- [ ] **Step 1: Create Axios client**

Create `frontend/src/api/client.js`:

```js
import axios from 'axios'

const client = axios.create({
  baseURL: '/api/v1',
})

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default client
```

- [ ] **Step 2: Create API modules**

Create `frontend/src/api/auth.js`:

```js
import client from './client'

export const login = async (username, password) => {
  const { data } = await client.post('/auth/login', { username, password })
  return data
}

export const getMe = async () => {
  const { data } = await client.get('/auth/me')
  return data
}

export const changePassword = async (currentPassword, newPassword) => {
  const { data } = await client.put('/auth/me/password', {
    current_password: currentPassword,
    new_password: newPassword,
  })
  return data
}
```

Create `frontend/src/api/dashboard.js`:

```js
import client from './client'

export const getStats = async () => {
  const { data } = await client.get('/dashboard/stats')
  return data
}

export const getExpiring = async (days) => {
  const params = days ? { days } : {}
  const { data } = await client.get('/dashboard/expiring', { params })
  return data
}
```

Create `frontend/src/api/cas.js`:

```js
import client from './client'

export const getCAs = async (page = 1, perPage = 25) => {
  const { data } = await client.get('/cas', { params: { page, per_page: perPage } })
  return data
}

export const getCATree = async () => {
  const { data } = await client.get('/cas/tree')
  return data
}

export const getCA = async (id) => {
  const { data } = await client.get(`/cas/${id}`)
  return data
}

export const createRootCA = async (caData) => {
  const { data } = await client.post('/cas', caData)
  return data
}

export const createIntermediateCA = async (parentId, caData) => {
  const { data } = await client.post(`/cas/${parentId}/intermediate`, caData)
  return data
}

export const updateCA = async (id, caData) => {
  const { data } = await client.put(`/cas/${id}`, caData)
  return data
}

export const getCAChain = async (id) => {
  const { data } = await client.get(`/cas/${id}/chain`)
  return data
}

export const disableCA = async (id) => {
  const { data } = await client.post(`/cas/${id}/disable`)
  return data
}

export const enableCA = async (id) => {
  const { data } = await client.post(`/cas/${id}/enable`)
  return data
}
```

Create `frontend/src/api/certificates.js`:

```js
import client from './client'

export const getCertificates = async (params = {}) => {
  const { data } = await client.get('/certificates', { params })
  return data
}

export const getCertificate = async (id) => {
  const { data } = await client.get(`/certificates/${id}`)
  return data
}

export const createCertificate = async (certData) => {
  const { data } = await client.post('/certificates', certData)
  return data
}

export const submitCSR = async (csrData) => {
  const { data } = await client.post('/certificates/csr', csrData)
  return data
}

export const approveCert = async (id) => {
  const { data } = await client.post(`/certificates/${id}/approve`)
  return data
}

export const denyCert = async (id) => {
  const { data } = await client.post(`/certificates/${id}/deny`)
  return data
}

export const revokeCert = async (id, reason) => {
  const { data } = await client.post(`/certificates/${id}/revoke`, { reason })
  return data
}

export const renewCert = async (id) => {
  const { data } = await client.post(`/certificates/${id}/renew`)
  return data
}

export const downloadCert = async (id, format, passphrase) => {
  const params = { format }
  if (passphrase) params.passphrase = passphrase
  const { data } = await client.get(`/certificates/${id}/download`, {
    params,
    responseType: 'blob',
  })
  return data
}
```

Create `frontend/src/api/users.js`:

```js
import client from './client'

export const getUsers = async (page = 1, perPage = 25) => {
  const { data } = await client.get('/users', { params: { page, per_page: perPage } })
  return data
}

export const createUser = async (userData) => {
  const { data } = await client.post('/users', userData)
  return data
}

export const getUser = async (id) => {
  const { data } = await client.get(`/users/${id}`)
  return data
}

export const updateUser = async (id, userData) => {
  const { data } = await client.put(`/users/${id}`, userData)
  return data
}

export const deleteUser = async (id) => {
  await client.delete(`/users/${id}`)
}
```

Create `frontend/src/api/audit.js`:

```js
import client from './client'

export const getAuditLogs = async (params = {}) => {
  const { data } = await client.get('/audit/logs', { params })
  return data
}

export const exportAuditLogs = async (params = {}) => {
  const { data } = await client.get('/audit/logs/export', {
    params,
    responseType: 'blob',
  })
  return data
}
```

Create `frontend/src/api/crl.js`:

```js
import client from './client'

export const generateCRL = async (caId) => {
  const { data } = await client.post(`/cas/${caId}/crl/generate`)
  return data
}

export const downloadCRL = async (caId) => {
  const { data } = await client.get(`/cas/${caId}/crl`, {
    responseType: 'blob',
  })
  return data
}
```

- [ ] **Step 3: Create auth hook with context**

Create `frontend/src/hooks/useAuth.jsx`:

```jsx
import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { login as apiLogin, getMe } from '../api/auth'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (token) {
      getMe()
        .then(setUser)
        .catch(() => {
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
        })
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  const login = useCallback(async (username, password) => {
    const data = await apiLogin(username, password)
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    const me = await getMe()
    setUser(me)
    return me
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, login, logout, loading, isAuthenticated: !!user }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within AuthProvider')
  return context
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/ frontend/src/hooks/useAuth.jsx
git commit -m "feat: API client with JWT interceptor, all API modules, and auth context"
```

---

## Task 4: UI Components

**Files:**
- Create: all files under `frontend/src/components/ui/`

- [ ] **Step 1: Create Button component**

Create `frontend/src/components/ui/Button.jsx`:

```jsx
const variants = {
  primary: 'bg-gray-800 text-white hover:bg-gray-700 dark:bg-gray-200 dark:text-gray-900 dark:hover:bg-gray-300',
  secondary: 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-surface-4 dark:text-gray-300 dark:hover:bg-gray-700',
  danger: 'bg-red-600 text-white hover:bg-red-700',
  ghost: 'text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-surface-4',
}

const sizes = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2 text-sm',
  lg: 'px-6 py-3 text-base',
}

export default function Button({ children, variant = 'primary', size = 'md', className = '', ...props }) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded font-medium transition-colors
        disabled:opacity-50 disabled:cursor-not-allowed ${variants[variant]} ${sizes[size]} ${className}`}
      {...props}
    >
      {children}
    </button>
  )
}
```

- [ ] **Step 2: Create Input component**

Create `frontend/src/components/ui/Input.jsx`:

```jsx
export default function Input({ label, error, className = '', ...props }) {
  return (
    <div className={className}>
      {label && (
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          {label}
        </label>
      )}
      <input
        className={`w-full px-3 py-2 rounded border transition-colors text-sm
          bg-white dark:bg-surface-4 border-gray-300 dark:border-gray-700
          text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-600
          focus:outline-none focus:ring-1 focus:ring-gray-400 dark:focus:ring-gray-500
          ${error ? 'border-red-500 dark:border-red-500' : ''}`}
        {...props}
      />
      {error && <p className="mt-1 text-sm text-red-500">{error}</p>}
    </div>
  )
}
```

- [ ] **Step 3: Create Select component**

Create `frontend/src/components/ui/Select.jsx`:

```jsx
export default function Select({ label, options, error, className = '', ...props }) {
  return (
    <div className={className}>
      {label && (
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          {label}
        </label>
      )}
      <select
        className={`w-full px-3 py-2 rounded border transition-colors text-sm
          bg-white dark:bg-surface-4 border-gray-300 dark:border-gray-700
          text-gray-900 dark:text-gray-100
          focus:outline-none focus:ring-1 focus:ring-gray-400 dark:focus:ring-gray-500
          ${error ? 'border-red-500' : ''}`}
        {...props}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      {error && <p className="mt-1 text-sm text-red-500">{error}</p>}
    </div>
  )
}
```

- [ ] **Step 4: Create Badge component**

Create `frontend/src/components/ui/Badge.jsx`:

```jsx
const variants = {
  default: 'bg-gray-100 text-gray-700 dark:bg-surface-4 dark:text-gray-300',
  success: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
  warning: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  danger: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
}

export default function Badge({ children, variant = 'default', className = '' }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${variants[variant]} ${className}`}>
      {children}
    </span>
  )
}
```

- [ ] **Step 5: Create Card component**

Create `frontend/src/components/ui/Card.jsx`:

```jsx
export default function Card({ children, className = '', onClick }) {
  return (
    <div
      className={`bg-white dark:bg-surface-4 rounded-lg border border-gray-200 dark:border-gray-800 ${onClick ? 'cursor-pointer hover:border-gray-300 dark:hover:border-gray-700' : ''} ${className}`}
      onClick={onClick}
    >
      {children}
    </div>
  )
}

export function CardHeader({ children, className = '' }) {
  return <div className={`px-4 py-3 border-b border-gray-200 dark:border-gray-800 ${className}`}>{children}</div>
}

export function CardBody({ children, className = '' }) {
  return <div className={`px-4 py-4 ${className}`}>{children}</div>
}
```

- [ ] **Step 6: Create Modal component**

Create `frontend/src/components/ui/Modal.jsx`:

```jsx
import { useEffect } from 'react'
import { XIcon } from '../../utils/icons'

export default function Modal({ isOpen, onClose, title, children, size = 'md' }) {
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
    return () => { document.body.style.overflow = '' }
  }, [isOpen])

  if (!isOpen) return null

  const widths = { sm: 'max-w-sm', md: 'max-w-md', lg: 'max-w-lg', xl: 'max-w-xl' }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="fixed inset-0 bg-black/50" onClick={onClose} />
      <div className={`relative bg-white dark:bg-surface-3 rounded-lg shadow-xl ${widths[size]} w-full mx-4`}>
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-800">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">{title}</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
            <XIcon />
          </button>
        </div>
        <div className="px-4 py-4">{children}</div>
      </div>
    </div>
  )
}
```

- [ ] **Step 7: Create Table component**

Create `frontend/src/components/ui/Table.jsx`:

```jsx
export default function Table({ columns, data, onRowClick }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 dark:border-gray-800">
            {columns.map((col) => (
              <th key={col.key} className="px-4 py-3 text-left font-medium text-gray-500 dark:text-gray-400">
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr
              key={row.id || i}
              className={`border-b border-gray-100 dark:border-gray-800/50 ${onRowClick ? 'cursor-pointer hover:bg-gray-50 dark:hover:bg-surface-4' : ''}`}
              onClick={() => onRowClick?.(row)}
            >
              {columns.map((col) => (
                <td key={col.key} className="px-4 py-3 text-gray-700 dark:text-gray-300">
                  {col.render ? col.render(row[col.key], row) : row[col.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {data.length === 0 && (
        <div className="text-center py-8 text-gray-400 dark:text-gray-600">No data</div>
      )}
    </div>
  )
}
```

- [ ] **Step 8: Create Tabs component**

Create `frontend/src/components/ui/Tabs.jsx`:

```jsx
import { useState } from 'react'

export default function Tabs({ tabs, defaultTab }) {
  const [active, setActive] = useState(defaultTab || tabs[0]?.key)

  const activeTab = tabs.find((t) => t.key === active)

  return (
    <div>
      <div className="flex border-b border-gray-200 dark:border-gray-800">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActive(tab.key)}
            className={`px-4 py-2 text-sm font-medium transition-colors
              ${active === tab.key
                ? 'border-b-2 border-gray-900 dark:border-gray-100 text-gray-900 dark:text-gray-100'
                : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}`}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div className="pt-4">{activeTab?.content}</div>
    </div>
  )
}
```

- [ ] **Step 9: Create Dropdown component**

Create `frontend/src/components/ui/Dropdown.jsx`:

```jsx
import { useState, useRef, useEffect } from 'react'

export default function Dropdown({ trigger, children, align = 'right' }) {
  const [isOpen, setIsOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    function handleClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setIsOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  return (
    <div className="relative" ref={ref}>
      <div onClick={() => setIsOpen(!isOpen)}>{trigger}</div>
      {isOpen && (
        <div className={`absolute z-40 mt-1 py-1 min-w-[160px] bg-white dark:bg-surface-3 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 ${align === 'right' ? 'right-0' : 'left-0'}`}>
          <div onClick={() => setIsOpen(false)}>{children}</div>
        </div>
      )}
    </div>
  )
}

export function DropdownItem({ children, onClick, className = '' }) {
  return (
    <button
      onClick={onClick}
      className={`w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-surface-4 ${className}`}
    >
      {children}
    </button>
  )
}
```

- [ ] **Step 10: Commit**

```bash
git add frontend/src/components/ui/
git commit -m "feat: UI component library — Button, Input, Select, Badge, Card, Modal, Table, Tabs, Dropdown"
```

---

## Task 5: Layout Components

**Files:**
- Create: `frontend/src/components/layout/Navbar.jsx`
- Create: `frontend/src/components/layout/Sidebar.jsx`
- Create: `frontend/src/components/layout/AppLayout.jsx`
- Create: `frontend/src/components/shared/StatusBadge.jsx`
- Create: `frontend/src/components/shared/ProtectedRoute.jsx`
- Create: `frontend/src/components/shared/CertChain.jsx`

- [ ] **Step 1: Create StatusBadge**

Create `frontend/src/components/shared/StatusBadge.jsx`:

```jsx
import Badge from '../ui/Badge'

const statusMap = {
  active: { variant: 'success', label: 'Active' },
  disabled: { variant: 'default', label: 'Disabled' },
  expired: { variant: 'danger', label: 'Expired' },
  revoked: { variant: 'danger', label: 'Revoked' },
  pending: { variant: 'warning', label: 'Pending' },
  denied: { variant: 'danger', label: 'Denied' },
}

export default function StatusBadge({ status }) {
  const config = statusMap[status] || { variant: 'default', label: status }
  return <Badge variant={config.variant}>{config.label}</Badge>
}
```

- [ ] **Step 2: Create ProtectedRoute**

Create `frontend/src/components/shared/ProtectedRoute.jsx`:

```jsx
import { Navigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'

export default function ProtectedRoute({ children, roles }) {
  const { user, loading, isAuthenticated } = useAuth()

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-white dark:bg-surface-1">
        <div className="text-gray-400">Loading...</div>
      </div>
    )
  }

  if (!isAuthenticated) return <Navigate to="/login" replace />

  if (roles && !roles.includes(user.role)) {
    return <Navigate to="/" replace />
  }

  return children
}
```

- [ ] **Step 3: Create CertChain**

Create `frontend/src/components/shared/CertChain.jsx`:

```jsx
import { ChevronRightIcon } from '../../utils/icons'

export default function CertChain({ chain }) {
  if (!chain || chain.length === 0) return null

  return (
    <div className="flex items-center gap-1 text-sm">
      {chain.map((item, i) => (
        <span key={i} className="flex items-center gap-1">
          {i > 0 && <ChevronRightIcon className="w-3 h-3 text-gray-400" />}
          <span className={i === chain.length - 1 ? 'font-medium text-gray-900 dark:text-gray-100' : 'text-gray-500 dark:text-gray-400'}>
            {item}
          </span>
        </span>
      ))}
    </div>
  )
}
```

- [ ] **Step 4: Create Sidebar**

Create `frontend/src/components/layout/Sidebar.jsx`:

```jsx
import { NavLink } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import {
  DashboardIcon, CertificateAuthorityIcon, CertificateIcon,
  ClockIcon, AuditIcon, UsersIcon,
} from '../../utils/icons'

const navItems = [
  { section: 'Main', items: [
    { to: '/', icon: DashboardIcon, label: 'Dashboard' },
    { to: '/cas', icon: CertificateAuthorityIcon, label: 'Authorities' },
    { to: '/certificates', icon: CertificateIcon, label: 'Certificates' },
    { to: '/pending', icon: ClockIcon, label: 'Pending Requests', roles: ['admin', 'operator'], badge: true },
  ]},
  { section: 'Management', items: [
    { to: '/audit', icon: AuditIcon, label: 'Audit Log', roles: ['admin', 'operator', 'auditor'] },
    { to: '/users', icon: UsersIcon, label: 'Users', roles: ['admin'] },
  ]},
]

export default function Sidebar({ pendingCount = 0, collapsed, onToggle }) {
  const { user } = useAuth()

  return (
    <aside className={`${collapsed ? 'hidden' : 'flex'} md:flex flex-col w-56 bg-white dark:bg-surface-2 border-r border-gray-200 dark:border-gray-800 min-h-0 overflow-y-auto`}>
      {navItems.map((group) => (
        <div key={group.section} className="px-3 py-3">
          <div className="text-[10px] uppercase tracking-wider text-gray-400 dark:text-gray-600 px-3 mb-1">
            {group.section}
          </div>
          {group.items
            .filter((item) => !item.roles || item.roles.includes(user?.role))
            .map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2 rounded text-sm transition-colors ${
                    isActive
                      ? 'bg-gray-100 dark:bg-surface-4 text-gray-900 dark:text-gray-100 border-l-2 border-gray-900 dark:border-gray-100 -ml-px'
                      : 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-surface-3'
                  }`
                }
              >
                <item.icon className="w-4 h-4" />
                <span className="flex-1">{item.label}</span>
                {item.badge && pendingCount > 0 && (
                  <span className="bg-amber-500 text-white text-[10px] px-1.5 py-0.5 rounded-full">
                    {pendingCount}
                  </span>
                )}
              </NavLink>
            ))}
        </div>
      ))}
    </aside>
  )
}
```

- [ ] **Step 5: Create Navbar**

Create `frontend/src/components/layout/Navbar.jsx`:

```jsx
import { useAuth } from '../../hooks/useAuth'
import { useTheme } from '../../hooks/useTheme'
import { useNavigate } from 'react-router-dom'
import Dropdown, { DropdownItem } from '../ui/Dropdown'
import { SunIcon, MoonIcon, BellIcon, MenuIcon, ChevronDownIcon } from '../../utils/icons'

export default function Navbar({ onMenuToggle }) {
  const { user, logout } = useAuth()
  const { isDark, toggle } = useTheme()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <header className="h-14 flex items-center justify-between px-4 bg-white dark:bg-surface-2 border-b border-gray-200 dark:border-gray-800">
      <div className="flex items-center gap-3">
        <button onClick={onMenuToggle} className="md:hidden text-gray-500 dark:text-gray-400">
          <MenuIcon />
        </button>
        <span className="text-base font-semibold text-gray-900 dark:text-gray-100 tracking-tight">
          PKI Manager
        </span>
      </div>

      <div className="flex items-center gap-3">
        <button onClick={toggle} className="p-2 rounded text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-surface-4">
          {isDark ? <SunIcon className="w-4 h-4" /> : <MoonIcon className="w-4 h-4" />}
        </button>

        <button className="p-2 rounded text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-surface-4">
          <BellIcon className="w-4 h-4" />
        </button>

        <Dropdown
          trigger={
            <button className="flex items-center gap-2 px-2 py-1 rounded hover:bg-gray-100 dark:hover:bg-surface-4">
              <div className="w-7 h-7 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center text-xs font-medium text-gray-600 dark:text-gray-300">
                {user?.username?.slice(0, 2).toUpperCase()}
              </div>
              <div className="hidden sm:block text-left">
                <div className="text-sm font-medium text-gray-900 dark:text-gray-100">{user?.username}</div>
                <div className="text-[10px] text-gray-500 dark:text-gray-500">{user?.role}</div>
              </div>
              <ChevronDownIcon className="w-3 h-3 text-gray-400" />
            </button>
          }
        >
          <DropdownItem onClick={handleLogout}>Logout</DropdownItem>
        </Dropdown>
      </div>
    </header>
  )
}
```

- [ ] **Step 6: Create AppLayout**

Create `frontend/src/components/layout/AppLayout.jsx`:

```jsx
import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import Navbar from './Navbar'
import Sidebar from './Sidebar'
import { getStats } from '../../api/dashboard'

export default function AppLayout() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const { data: stats } = useQuery({ queryKey: ['dashboard-stats'], queryFn: getStats, refetchInterval: 30000 })

  return (
    <div className="min-h-screen flex flex-col bg-gray-50 dark:bg-surface-1">
      <Navbar onMenuToggle={() => setSidebarCollapsed(!sidebarCollapsed)} />
      <div className="flex flex-1 min-h-0">
        <Sidebar pendingCount={stats?.pending_requests || 0} collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed(!sidebarCollapsed)} />
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
```

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/layout/ frontend/src/components/shared/
git commit -m "feat: app layout with sidebar, navbar, protected route, status badge, cert chain"
```

---

## Task 6: Router Setup & Login Page

**Files:**
- Create: `frontend/src/pages/Login.jsx`
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/main.jsx`

- [ ] **Step 1: Create Login page**

Create `frontend/src/pages/Login.jsx`:

```jsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import Input from '../components/ui/Input'
import Button from '../components/ui/Button'

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(username, password)
      navigate('/')
    } catch {
      setError('Invalid username or password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-surface-1">
      <div className="w-full max-w-sm">
        <h1 className="text-2xl font-semibold text-center text-gray-900 dark:text-gray-100 mb-8">
          PKI Manager
        </h1>
        <div className="bg-white dark:bg-surface-3 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input label="Username" value={username} onChange={(e) => setUsername(e.target.value)} required />
            <Input label="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
            {error && <p className="text-sm text-red-500">{error}</p>}
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? 'Signing in...' : 'Sign In'}
            </Button>
          </form>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Set up router in App.jsx**

Replace `frontend/src/App.jsx`:

```jsx
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import AppLayout from './components/layout/AppLayout'
import ProtectedRoute from './components/shared/ProtectedRoute'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import CAList from './pages/cas/CAList'
import CADetail from './pages/cas/CADetail'
import CACreate from './pages/cas/CACreate'
import CertificateList from './pages/certificates/CertificateList'
import CertificateDetail from './pages/certificates/CertificateDetail'
import CertificateCreate from './pages/certificates/CertificateCreate'
import CSRSubmit from './pages/certificates/CSRSubmit'
import PendingRequests from './pages/PendingRequests'
import AuditLog from './pages/AuditLog'
import Users from './pages/Users'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/cas" element={<ProtectedRoute roles={['admin', 'operator', 'auditor']}><CAList /></ProtectedRoute>} />
          <Route path="/cas/new" element={<ProtectedRoute roles={['admin', 'operator']}><CACreate /></ProtectedRoute>} />
          <Route path="/cas/:id" element={<ProtectedRoute roles={['admin', 'operator', 'auditor']}><CADetail /></ProtectedRoute>} />
          <Route path="/cas/:id/intermediate/new" element={<ProtectedRoute roles={['admin', 'operator']}><CACreate /></ProtectedRoute>} />
          <Route path="/certificates" element={<ProtectedRoute roles={['admin', 'operator', 'auditor']}><CertificateList /></ProtectedRoute>} />
          <Route path="/certificates/new" element={<ProtectedRoute roles={['admin', 'operator', 'requester']}><CertificateCreate /></ProtectedRoute>} />
          <Route path="/certificates/csr" element={<ProtectedRoute roles={['admin', 'operator', 'requester']}><CSRSubmit /></ProtectedRoute>} />
          <Route path="/certificates/:id" element={<CertificateDetail />} />
          <Route path="/pending" element={<ProtectedRoute roles={['admin', 'operator']}><PendingRequests /></ProtectedRoute>} />
          <Route path="/audit" element={<ProtectedRoute roles={['admin', 'auditor', 'operator']}><AuditLog /></ProtectedRoute>} />
          <Route path="/users" element={<ProtectedRoute roles={['admin']}><Users /></ProtectedRoute>} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
```

- [ ] **Step 3: Update main.jsx with providers**

Replace `frontend/src/main.jsx`:

```jsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from './hooks/useAuth'
import './index.css'
import App from './App'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30000, retry: 1 },
  },
})

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <App />
      </AuthProvider>
    </QueryClientProvider>
  </StrictMode>
)
```

- [ ] **Step 4: Create stub pages so the app compiles**

Create stub files for every page that doesn't exist yet. Each is a simple placeholder:

`frontend/src/pages/Dashboard.jsx`:
```jsx
export default function Dashboard() {
  return <div><h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Dashboard</h1></div>
}
```

Create identical stubs for:
- `frontend/src/pages/cas/CAList.jsx`
- `frontend/src/pages/cas/CADetail.jsx`
- `frontend/src/pages/cas/CACreate.jsx`
- `frontend/src/pages/certificates/CertificateList.jsx`
- `frontend/src/pages/certificates/CertificateDetail.jsx`
- `frontend/src/pages/certificates/CertificateCreate.jsx`
- `frontend/src/pages/certificates/CSRSubmit.jsx`
- `frontend/src/pages/PendingRequests.jsx`
- `frontend/src/pages/AuditLog.jsx`
- `frontend/src/pages/Users.jsx`

Each exports a default function with the page name as heading.

- [ ] **Step 5: Verify login flow works**

Start backend: `cd backend && source .venv/bin/activate && python seed.py && uvicorn app.main:app --reload`

Start frontend: `cd frontend && npm run dev`

Open http://localhost:5173 → should redirect to /login → login with admin/admin → should see Dashboard stub with sidebar and navbar.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/
git commit -m "feat: router setup, login page, stub pages, full app shell working"
```

---

## Task 7: Form Components

**Files:**
- Create: `frontend/src/components/forms/SubjectDNFields.jsx`
- Create: `frontend/src/components/forms/SANFields.jsx`
- Create: `frontend/src/components/forms/KeyUsageCheckboxes.jsx`
- Create: `frontend/src/components/forms/EKUCheckboxes.jsx`
- Create: `frontend/src/components/forms/CustomExtensions.jsx`

- [ ] **Step 1: Create SubjectDNFields**

```jsx
import Input from '../ui/Input'

export default function SubjectDNFields({ value, onChange }) {
  const update = (field, val) => onChange({ ...value, [field]: val })

  return (
    <div className="space-y-3">
      <Input label="Common Name (CN) *" value={value.CN || ''} onChange={(e) => update('CN', e.target.value)} required placeholder="e.g. example.com" />
      <div className="grid grid-cols-2 gap-3">
        <Input label="Organization (O)" value={value.O || ''} onChange={(e) => update('O', e.target.value)} />
        <Input label="Org Unit (OU)" value={value.OU || ''} onChange={(e) => update('OU', e.target.value)} />
      </div>
      <div className="grid grid-cols-3 gap-3">
        <Input label="Country (C)" value={value.C || ''} onChange={(e) => update('C', e.target.value)} maxLength={2} placeholder="US" />
        <Input label="State (ST)" value={value.ST || ''} onChange={(e) => update('ST', e.target.value)} />
        <Input label="Locality (L)" value={value.L || ''} onChange={(e) => update('L', e.target.value)} />
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Create SANFields**

```jsx
import Select from '../ui/Select'
import Input from '../ui/Input'
import Button from '../ui/Button'
import { PlusIcon, XIcon } from '../../utils/icons'

const sanTypes = [
  { value: 'DNS', label: 'DNS' },
  { value: 'IP', label: 'IP' },
  { value: 'Email', label: 'Email' },
  { value: 'URI', label: 'URI' },
]

export default function SANFields({ value = [], onChange }) {
  const add = () => onChange([...value, { type: 'DNS', value: '' }])
  const remove = (i) => onChange(value.filter((_, idx) => idx !== i))
  const update = (i, field, val) => {
    const next = [...value]
    next[i] = { ...next[i], [field]: val }
    onChange(next)
  }

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
        Subject Alternative Names
      </label>
      {value.map((san, i) => (
        <div key={i} className="flex gap-2 items-start">
          <Select options={sanTypes} value={san.type} onChange={(e) => update(i, 'type', e.target.value)} className="w-28" />
          <Input value={san.value} onChange={(e) => update(i, 'value', e.target.value)} placeholder="e.g. example.com" className="flex-1" />
          <button onClick={() => remove(i)} className="p-2 text-gray-400 hover:text-red-500 mt-0.5">
            <XIcon className="w-4 h-4" />
          </button>
        </div>
      ))}
      <Button variant="ghost" size="sm" onClick={add} type="button">
        <PlusIcon className="w-4 h-4" /> Add SAN
      </Button>
    </div>
  )
}
```

- [ ] **Step 3: Create KeyUsageCheckboxes**

```jsx
const KEY_USAGES = [
  { key: 'digital_signature', label: 'Digital Signature' },
  { key: 'key_encipherment', label: 'Key Encipherment' },
  { key: 'data_encipherment', label: 'Data Encipherment' },
  { key: 'key_agreement', label: 'Key Agreement' },
  { key: 'key_cert_sign', label: 'Certificate Sign' },
  { key: 'crl_sign', label: 'CRL Sign' },
  { key: 'content_commitment', label: 'Content Commitment' },
]

export default function KeyUsageCheckboxes({ value = [], onChange }) {
  const toggle = (key) => {
    if (value.includes(key)) {
      onChange(value.filter((k) => k !== key))
    } else {
      onChange([...value, key])
    }
  }

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Key Usage</label>
      <div className="grid grid-cols-2 gap-2">
        {KEY_USAGES.map((ku) => (
          <label key={ku.key} className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
            <input type="checkbox" checked={value.includes(ku.key)} onChange={() => toggle(ku.key)} className="rounded border-gray-300 dark:border-gray-600" />
            {ku.label}
          </label>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Create EKUCheckboxes**

```jsx
const EKUS = [
  { key: 'server_auth', label: 'TLS Web Server Auth' },
  { key: 'client_auth', label: 'TLS Web Client Auth' },
  { key: 'code_signing', label: 'Code Signing' },
  { key: 'email_protection', label: 'Email Protection' },
  { key: 'ocsp_signing', label: 'OCSP Signing' },
]

export default function EKUCheckboxes({ value = [], onChange }) {
  const toggle = (key) => {
    if (value.includes(key)) {
      onChange(value.filter((k) => k !== key))
    } else {
      onChange([...value, key])
    }
  }

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Extended Key Usage</label>
      <div className="grid grid-cols-2 gap-2">
        {EKUS.map((eku) => (
          <label key={eku.key} className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
            <input type="checkbox" checked={value.includes(eku.key)} onChange={() => toggle(eku.key)} className="rounded border-gray-300 dark:border-gray-600" />
            {eku.label}
          </label>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 5: Create CustomExtensions**

```jsx
import Input from '../ui/Input'
import Button from '../ui/Button'
import { PlusIcon, XIcon } from '../../utils/icons'

export default function CustomExtensions({ value = [], onChange }) {
  const add = () => onChange([...value, { oid: '', critical: false, value: '' }])
  const remove = (i) => onChange(value.filter((_, idx) => idx !== i))
  const update = (i, field, val) => {
    const next = [...value]
    next[i] = { ...next[i], [field]: val }
    onChange(next)
  }

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Custom Extensions</label>
      {value.map((ext, i) => (
        <div key={i} className="flex gap-2 items-start">
          <Input value={ext.oid} onChange={(e) => update(i, 'oid', e.target.value)} placeholder="OID (e.g. 1.2.3.4)" className="w-40" />
          <label className="flex items-center gap-1 text-sm text-gray-600 dark:text-gray-400 pt-2">
            <input type="checkbox" checked={ext.critical} onChange={(e) => update(i, 'critical', e.target.checked)} />
            Critical
          </label>
          <Input value={ext.value} onChange={(e) => update(i, 'value', e.target.value)} placeholder="Value" className="flex-1" />
          <button onClick={() => remove(i)} className="p-2 text-gray-400 hover:text-red-500 mt-0.5">
            <XIcon className="w-4 h-4" />
          </button>
        </div>
      ))}
      <Button variant="ghost" size="sm" onClick={add} type="button">
        <PlusIcon className="w-4 h-4" /> Add Extension
      </Button>
    </div>
  )
}
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/forms/
git commit -m "feat: form components — SubjectDN, SANs, KeyUsage, EKU, CustomExtensions"
```

---

## Task 8: Dashboard Page

**Files:**
- Modify: `frontend/src/pages/Dashboard.jsx`

- [ ] **Step 1: Implement Dashboard**

Replace `frontend/src/pages/Dashboard.jsx`:

```jsx
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { getStats, getExpiring } from '../api/dashboard'
import { getAuditLogs } from '../api/audit'
import Card, { CardBody } from '../components/ui/Card'
import StatusBadge from '../components/shared/StatusBadge'

function StatCard({ label, value, color, to }) {
  const navigate = useNavigate()
  return (
    <Card onClick={() => to && navigate(to)} className="p-4">
      <div className={`text-2xl font-bold ${color || 'text-gray-900 dark:text-gray-100'}`}>{value}</div>
      <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">{label}</div>
    </Card>
  )
}

export default function Dashboard() {
  const { data: stats } = useQuery({ queryKey: ['dashboard-stats'], queryFn: getStats })
  const { data: expiring } = useQuery({ queryKey: ['dashboard-expiring'], queryFn: () => getExpiring() })
  const { data: activity } = useQuery({ queryKey: ['dashboard-activity'], queryFn: () => getAuditLogs({ per_page: 5 }) })

  return (
    <div>
      <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-1">Dashboard</h1>
      <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">Overview of your PKI infrastructure</p>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard label="Active CAs" value={stats?.active_cas ?? '—'} to="/cas" />
        <StatCard label="Active Certs" value={stats?.active_certs ?? '—'} color="text-emerald-500" to="/certificates" />
        <StatCard label="Pending Requests" value={stats?.pending_requests ?? '—'} color="text-amber-500" to="/pending" />
        <StatCard label="Expiring Soon" value={stats?.expiring_soon ?? '—'} color="text-red-500" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardBody>
            <h2 className="font-semibold text-gray-900 dark:text-gray-100 mb-3">Expiring Certificates</h2>
            {expiring?.items?.length === 0 && <p className="text-sm text-gray-400">None expiring soon</p>}
            <div className="space-y-2">
              {expiring?.items?.slice(0, 5).map((cert) => {
                const days = Math.ceil((new Date(cert.not_after) - new Date()) / 86400000)
                return (
                  <div key={cert.id} className="flex justify-between text-sm">
                    <span className="text-gray-700 dark:text-gray-300">{cert.subject_dn}</span>
                    <span className={days <= 7 ? 'text-red-500' : 'text-amber-500'}>{days}d</span>
                  </div>
                )
              })}
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardBody>
            <h2 className="font-semibold text-gray-900 dark:text-gray-100 mb-3">Recent Activity</h2>
            {activity?.items?.length === 0 && <p className="text-sm text-gray-400">No recent activity</p>}
            <div className="space-y-2">
              {activity?.items?.map((log) => (
                <div key={log.id} className="text-sm text-gray-600 dark:text-gray-400">
                  <span className="text-gray-900 dark:text-gray-200">{log.user_id?.slice(0, 8)}</span>
                  {' '}{log.action.replace(/_/g, ' ')} — {new Date(log.created_at).toLocaleString()}
                </div>
              ))}
            </div>
          </CardBody>
        </Card>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verify in browser**

Login, check dashboard renders stat cards and tables.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Dashboard.jsx
git commit -m "feat: dashboard page with stats, expiring certs, and activity feed"
```

---

## Task 9: CA Pages

**Files:**
- Modify: `frontend/src/pages/cas/CAList.jsx`
- Modify: `frontend/src/pages/cas/CADetail.jsx`
- Modify: `frontend/src/pages/cas/CACreate.jsx`

- [ ] **Step 1: Implement CAList**

Replace `frontend/src/pages/cas/CAList.jsx`:

```jsx
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { getCAs, getCATree } from '../../api/cas'
import Button from '../../components/ui/Button'
import Table from '../../components/ui/Table'
import StatusBadge from '../../components/shared/StatusBadge'
import { PlusIcon, TableIcon, TreeIcon, ChevronRightIcon, ChevronDownIcon } from '../../utils/icons'

function TreeNode({ node, level = 0 }) {
  const [expanded, setExpanded] = useState(true)
  const navigate = useNavigate()
  const hasChildren = node.children?.length > 0

  return (
    <div>
      <div
        className="flex items-center gap-2 py-2 px-3 hover:bg-gray-50 dark:hover:bg-surface-4 cursor-pointer rounded text-sm"
        style={{ paddingLeft: `${level * 24 + 12}px` }}
      >
        {hasChildren ? (
          <button onClick={() => setExpanded(!expanded)} className="text-gray-400">
            {expanded ? <ChevronDownIcon className="w-3 h-3" /> : <ChevronRightIcon className="w-3 h-3" />}
          </button>
        ) : <span className="w-3" />}
        <span className="flex-1 text-gray-900 dark:text-gray-100" onClick={() => navigate(`/cas/${node.id}`)}>
          {node.name}
        </span>
        <StatusBadge status={node.status} />
      </div>
      {expanded && hasChildren && node.children.map((child) => (
        <TreeNode key={child.id} node={child} level={level + 1} />
      ))}
    </div>
  )
}

export default function CAList() {
  const [view, setView] = useState('table')
  const navigate = useNavigate()
  const { data: cas, isLoading } = useQuery({ queryKey: ['cas'], queryFn: () => getCAs(1, 100) })
  const { data: tree } = useQuery({ queryKey: ['cas-tree'], queryFn: getCATree, enabled: view === 'tree' })

  const columns = [
    { key: 'name', label: 'Name' },
    { key: 'type', label: 'Type' },
    { key: 'status', label: 'Status', render: (val) => <StatusBadge status={val} /> },
    { key: 'subject_dn', label: 'Subject DN' },
    { key: 'not_after', label: 'Expires', render: (val) => new Date(val).toLocaleDateString() },
    { key: 'auto_approve', label: 'Auto-Approve', render: (val) => val ? 'Yes' : 'No' },
  ]

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Certificate Authorities</h1>
        <div className="flex items-center gap-2">
          <div className="flex border border-gray-200 dark:border-gray-700 rounded">
            <button onClick={() => setView('table')} className={`p-2 ${view === 'table' ? 'bg-gray-100 dark:bg-surface-4' : ''}`}>
              <TableIcon className="w-4 h-4 text-gray-500" />
            </button>
            <button onClick={() => setView('tree')} className={`p-2 ${view === 'tree' ? 'bg-gray-100 dark:bg-surface-4' : ''}`}>
              <TreeIcon className="w-4 h-4 text-gray-500" />
            </button>
          </div>
          <Button onClick={() => navigate('/cas/new')}><PlusIcon className="w-4 h-4" /> Create Root CA</Button>
        </div>
      </div>

      {isLoading ? (
        <div className="text-center py-8 text-gray-400">Loading...</div>
      ) : view === 'table' ? (
        <Table columns={columns} data={cas?.items || []} onRowClick={(row) => navigate(`/cas/${row.id}`)} />
      ) : (
        <div className="bg-white dark:bg-surface-3 rounded-lg border border-gray-200 dark:border-gray-800 py-2">
          {tree?.map((node) => <TreeNode key={node.id} node={node} />)}
          {tree?.length === 0 && <div className="text-center py-8 text-gray-400">No CAs created yet</div>}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Implement CACreate**

Replace `frontend/src/pages/cas/CACreate.jsx`:

```jsx
import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createRootCA, createIntermediateCA } from '../../api/cas'
import SubjectDNFields from '../../components/forms/SubjectDNFields'
import Input from '../../components/ui/Input'
import Select from '../../components/ui/Select'
import Button from '../../components/ui/Button'

export default function CACreate() {
  const { id: parentId } = useParams()
  const isIntermediate = !!parentId
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [name, setName] = useState('')
  const [subject, setSubject] = useState({ CN: '' })
  const [keyAlgorithm, setKeyAlgorithm] = useState('RSA')
  const [keySize, setKeySize] = useState(2048)
  const [validityDays, setValidityDays] = useState(3650)
  const [autoApprove, setAutoApprove] = useState(false)
  const [error, setError] = useState('')

  const mutation = useMutation({
    mutationFn: (data) => isIntermediate ? createIntermediateCA(parentId, data) : createRootCA(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cas'] })
      navigate('/cas')
    },
    onError: (err) => setError(err.response?.data?.detail || 'Failed to create CA'),
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    setError('')
    mutation.mutate({
      name,
      subject,
      key_algorithm: keyAlgorithm,
      key_size: Number(keySize),
      validity_days: Number(validityDays),
      auto_approve: autoApprove,
    })
  }

  return (
    <div className="max-w-2xl">
      <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-6">
        {isIntermediate ? 'Create Intermediate CA' : 'Create Root CA'}
      </h1>
      <form onSubmit={handleSubmit} className="space-y-6 bg-white dark:bg-surface-3 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
        <Input label="CA Name" value={name} onChange={(e) => setName(e.target.value)} required placeholder="e.g. My Root CA" />
        <SubjectDNFields value={subject} onChange={setSubject} />
        <div className="grid grid-cols-2 gap-4">
          <Select label="Key Algorithm" options={[{ value: 'RSA', label: 'RSA' }, { value: 'EC', label: 'EC' }]} value={keyAlgorithm} onChange={(e) => setKeyAlgorithm(e.target.value)} />
          <Select label="Key Size" options={
            keyAlgorithm === 'RSA'
              ? [{ value: '2048', label: '2048' }, { value: '4096', label: '4096' }]
              : [{ value: '256', label: 'P-256' }, { value: '384', label: 'P-384' }]
          } value={String(keySize)} onChange={(e) => setKeySize(e.target.value)} />
        </div>
        <Input label="Validity (days)" type="number" value={validityDays} onChange={(e) => setValidityDays(e.target.value)} />
        <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
          <input type="checkbox" checked={autoApprove} onChange={(e) => setAutoApprove(e.target.checked)} />
          Auto-approve certificate requests
        </label>
        {error && <p className="text-sm text-red-500">{error}</p>}
        <div className="flex gap-3">
          <Button type="submit" disabled={mutation.isPending}>{mutation.isPending ? 'Creating...' : 'Create CA'}</Button>
          <Button variant="secondary" type="button" onClick={() => navigate('/cas')}>Cancel</Button>
        </div>
      </form>
    </div>
  )
}
```

- [ ] **Step 3: Implement CADetail**

Replace `frontend/src/pages/cas/CADetail.jsx`:

```jsx
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getCA, getCAChain, disableCA, enableCA, updateCA } from '../../api/cas'
import { getCertificates } from '../../api/certificates'
import Tabs from '../../components/ui/Tabs'
import Table from '../../components/ui/Table'
import Button from '../../components/ui/Button'
import StatusBadge from '../../components/shared/StatusBadge'
import CertChain from '../../components/shared/CertChain'
import { useAuth } from '../../hooks/useAuth'

export default function CADetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  const queryClient = useQueryClient()

  const { data: ca, isLoading } = useQuery({ queryKey: ['ca', id], queryFn: () => getCA(id) })
  const { data: chain } = useQuery({ queryKey: ['ca-chain', id], queryFn: () => getCAChain(id) })
  const { data: certs } = useQuery({ queryKey: ['ca-certs', id], queryFn: () => getCertificates({ ca_id: id }) })

  const toggleStatus = useMutation({
    mutationFn: () => ca?.status === 'active' ? disableCA(id) : enableCA(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['ca', id] }),
  })

  if (isLoading) return <div className="text-gray-400 py-8">Loading...</div>
  if (!ca) return <div className="text-gray-400 py-8">CA not found</div>

  const certColumns = [
    { key: 'subject_dn', label: 'Subject' },
    { key: 'type', label: 'Type' },
    { key: 'status', label: 'Status', render: (val) => <StatusBadge status={val} /> },
    { key: 'not_after', label: 'Expires', render: (val) => val ? new Date(val).toLocaleDateString() : '—' },
  ]

  const tabs = [
    {
      key: 'overview', label: 'Overview',
      content: (
        <div className="space-y-4 text-sm">
          <CertChain chain={chain?.chain?.map((_, i) => i === 0 ? ca.subject_dn : `Parent ${i}`).reverse()} />
          <div className="grid grid-cols-2 gap-4 mt-4">
            <div><span className="text-gray-500 dark:text-gray-400">Subject DN:</span> <span className="text-gray-900 dark:text-gray-100 ml-2">{ca.subject_dn}</span></div>
            <div><span className="text-gray-500 dark:text-gray-400">Serial:</span> <span className="text-gray-900 dark:text-gray-100 ml-2">{ca.serial_number}</span></div>
            <div><span className="text-gray-500 dark:text-gray-400">Valid From:</span> <span className="ml-2">{new Date(ca.not_before).toLocaleDateString()}</span></div>
            <div><span className="text-gray-500 dark:text-gray-400">Valid Until:</span> <span className="ml-2">{new Date(ca.not_after).toLocaleDateString()}</span></div>
            <div><span className="text-gray-500 dark:text-gray-400">Algorithm:</span> <span className="ml-2">{ca.key_algorithm} {ca.key_size}</span></div>
            <div><span className="text-gray-500 dark:text-gray-400">Type:</span> <span className="ml-2">{ca.type}</span></div>
          </div>
        </div>
      ),
    },
    {
      key: 'certificates', label: 'Certificates',
      content: <Table columns={certColumns} data={certs?.items || []} onRowClick={(row) => navigate(`/certificates/${row.id}`)} />,
    },
    {
      key: 'settings', label: 'Settings',
      content: (
        <div className="space-y-3 text-sm">
          <div><span className="text-gray-500 dark:text-gray-400">Auto-Approve:</span> <span className="ml-2">{ca.auto_approve ? 'Yes' : 'No'}</span></div>
          <div><span className="text-gray-500 dark:text-gray-400">OCSP Signing:</span> <span className="ml-2">{ca.ocsp_signing_mode}</span></div>
          <div><span className="text-gray-500 dark:text-gray-400">CRL Interval:</span> <span className="ml-2">{ca.crl_regen_interval_hours}h</span></div>
        </div>
      ),
    },
  ]

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">{ca.name}</h1>
          <div className="flex items-center gap-2 mt-1"><StatusBadge status={ca.status} /></div>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => navigate(`/cas/${id}/intermediate/new`)}>Create Intermediate</Button>
          {user?.role === 'admin' && (
            <Button variant={ca.status === 'active' ? 'danger' : 'primary'} onClick={() => toggleStatus.mutate()}>
              {ca.status === 'active' ? 'Disable' : 'Enable'}
            </Button>
          )}
        </div>
      </div>
      <div className="bg-white dark:bg-surface-3 rounded-lg border border-gray-200 dark:border-gray-800 p-4">
        <Tabs tabs={tabs} />
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Verify in browser**

Navigate to /cas, create a root CA, view CA detail with tabs.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/cas/
git commit -m "feat: CA pages — list with table/tree toggle, create root/intermediate, detail with tabs"
```

---

## Task 10: Certificate Pages

**Files:**
- Modify: `frontend/src/pages/certificates/CertificateList.jsx`
- Modify: `frontend/src/pages/certificates/CertificateCreate.jsx`
- Modify: `frontend/src/pages/certificates/CertificateDetail.jsx`
- Modify: `frontend/src/pages/certificates/CSRSubmit.jsx`

- [ ] **Step 1: Implement CertificateList**

Replace `frontend/src/pages/certificates/CertificateList.jsx`:

```jsx
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { getCertificates } from '../../api/certificates'
import { getCAs } from '../../api/cas'
import Table from '../../components/ui/Table'
import Select from '../../components/ui/Select'
import Button from '../../components/ui/Button'
import Input from '../../components/ui/Input'
import StatusBadge from '../../components/shared/StatusBadge'
import { PlusIcon } from '../../utils/icons'

export default function CertificateList() {
  const navigate = useNavigate()
  const [caId, setCaId] = useState('')
  const [status, setStatus] = useState('')
  const [page, setPage] = useState(1)

  const params = { page, per_page: 25 }
  if (caId) params.ca_id = caId
  if (status) params.status = status

  const { data: certs, isLoading } = useQuery({ queryKey: ['certificates', params], queryFn: () => getCertificates(params) })
  const { data: cas } = useQuery({ queryKey: ['cas-select'], queryFn: () => getCAs(1, 100) })

  const caOptions = [{ value: '', label: 'All CAs' }, ...(cas?.items?.map((ca) => ({ value: ca.id, label: ca.name })) || [])]
  const statusOptions = [
    { value: '', label: 'All Statuses' },
    { value: 'active', label: 'Active' },
    { value: 'pending', label: 'Pending' },
    { value: 'revoked', label: 'Revoked' },
    { value: 'expired', label: 'Expired' },
  ]

  const columns = [
    { key: 'subject_dn', label: 'Subject' },
    { key: 'type', label: 'Type' },
    { key: 'status', label: 'Status', render: (val) => <StatusBadge status={val} /> },
    { key: 'not_after', label: 'Expires', render: (val) => val ? new Date(val).toLocaleDateString() : '—' },
  ]

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Certificates</h1>
        <div className="flex gap-2">
          <Button onClick={() => navigate('/certificates/new')}><PlusIcon className="w-4 h-4" /> New Certificate</Button>
          <Button variant="secondary" onClick={() => navigate('/certificates/csr')}>Submit CSR</Button>
        </div>
      </div>

      <div className="flex gap-3 mb-4">
        <Select options={caOptions} value={caId} onChange={(e) => { setCaId(e.target.value); setPage(1) }} className="w-48" />
        <Select options={statusOptions} value={status} onChange={(e) => { setStatus(e.target.value); setPage(1) }} className="w-40" />
      </div>

      {isLoading ? (
        <div className="text-center py-8 text-gray-400">Loading...</div>
      ) : (
        <>
          <Table columns={columns} data={certs?.items || []} onRowClick={(row) => navigate(`/certificates/${row.id}`)} />
          {certs?.total > 25 && (
            <div className="flex gap-2 mt-4 justify-center">
              <Button variant="ghost" size="sm" disabled={page === 1} onClick={() => setPage(page - 1)}>Previous</Button>
              <span className="text-sm text-gray-500 py-1.5">Page {page}</span>
              <Button variant="ghost" size="sm" disabled={certs?.items?.length < 25} onClick={() => setPage(page + 1)}>Next</Button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Implement CertificateCreate**

Replace `frontend/src/pages/certificates/CertificateCreate.jsx`:

```jsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createCertificate } from '../../api/certificates'
import { getCAs } from '../../api/cas'
import SubjectDNFields from '../../components/forms/SubjectDNFields'
import SANFields from '../../components/forms/SANFields'
import KeyUsageCheckboxes from '../../components/forms/KeyUsageCheckboxes'
import EKUCheckboxes from '../../components/forms/EKUCheckboxes'
import CustomExtensions from '../../components/forms/CustomExtensions'
import Select from '../../components/ui/Select'
import Input from '../../components/ui/Input'
import Button from '../../components/ui/Button'

export default function CertificateCreate() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { data: cas } = useQuery({ queryKey: ['cas-select'], queryFn: () => getCAs(1, 100) })

  const [caId, setCaId] = useState('')
  const [subject, setSubject] = useState({ CN: '' })
  const [sans, setSans] = useState([{ type: 'DNS', value: '' }])
  const [certType, setCertType] = useState('server')
  const [keyAlgorithm, setKeyAlgorithm] = useState('RSA')
  const [keySize, setKeySize] = useState(2048)
  const [validityDays, setValidityDays] = useState(365)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [keyUsage, setKeyUsage] = useState([])
  const [eku, setEku] = useState([])
  const [customExts, setCustomExts] = useState([])
  const [error, setError] = useState('')

  const mutation = useMutation({
    mutationFn: createCertificate,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['certificates'] })
      navigate(`/certificates/${data.id}`)
    },
    onError: (err) => setError(err.response?.data?.detail || 'Failed to create certificate'),
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    setError('')
    const data = {
      ca_id: caId,
      subject,
      san: sans.filter((s) => s.value),
      type: certType,
      key_algorithm: keyAlgorithm,
      key_size: Number(keySize),
      validity_days: Number(validityDays),
    }
    if (showAdvanced) {
      if (keyUsage.length) data.key_usage = keyUsage
      if (eku.length) data.extended_key_usage = eku
      if (customExts.length) data.custom_extensions = customExts.filter((e) => e.oid)
    }
    mutation.mutate(data)
  }

  const caOptions = [{ value: '', label: 'Select CA...' }, ...(cas?.items?.map((ca) => ({ value: ca.id, label: ca.name })) || [])]

  return (
    <div className="max-w-2xl">
      <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-6">Create Certificate</h1>
      <form onSubmit={handleSubmit} className="space-y-6 bg-white dark:bg-surface-3 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
        <Select label="Issuing CA *" options={caOptions} value={caId} onChange={(e) => setCaId(e.target.value)} required />
        <SubjectDNFields value={subject} onChange={setSubject} />
        <SANFields value={sans} onChange={setSans} />
        <div className="grid grid-cols-3 gap-4">
          <Select label="Type" options={[{ value: 'server', label: 'Server' }, { value: 'client', label: 'Client' }, { value: 'custom', label: 'Custom' }]} value={certType} onChange={(e) => setCertType(e.target.value)} />
          <Select label="Key Algorithm" options={[{ value: 'RSA', label: 'RSA' }, { value: 'EC', label: 'EC' }]} value={keyAlgorithm} onChange={(e) => setKeyAlgorithm(e.target.value)} />
          <Input label="Validity (days)" type="number" value={validityDays} onChange={(e) => setValidityDays(e.target.value)} />
        </div>

        <button type="button" onClick={() => setShowAdvanced(!showAdvanced)} className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300">
          {showAdvanced ? '▾ Hide Advanced' : '▸ Show Advanced'}
        </button>

        {showAdvanced && (
          <div className="space-y-4 border-t border-gray-200 dark:border-gray-800 pt-4">
            <KeyUsageCheckboxes value={keyUsage} onChange={setKeyUsage} />
            <EKUCheckboxes value={eku} onChange={setEku} />
            <CustomExtensions value={customExts} onChange={setCustomExts} />
          </div>
        )}

        {error && <p className="text-sm text-red-500">{error}</p>}
        <div className="flex gap-3">
          <Button type="submit" disabled={mutation.isPending || !caId}>{mutation.isPending ? 'Creating...' : 'Create Certificate'}</Button>
          <Button variant="secondary" type="button" onClick={() => navigate('/certificates')}>Cancel</Button>
        </div>
      </form>
    </div>
  )
}
```

- [ ] **Step 3: Implement CertificateDetail**

Replace `frontend/src/pages/certificates/CertificateDetail.jsx`:

```jsx
import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getCertificate, revokeCert, renewCert, downloadCert, approveCert, denyCert } from '../../api/certificates'
import Button from '../../components/ui/Button'
import Modal from '../../components/ui/Modal'
import Input from '../../components/ui/Input'
import Select from '../../components/ui/Select'
import StatusBadge from '../../components/shared/StatusBadge'
import { useAuth } from '../../hooks/useAuth'
import { DownloadIcon } from '../../utils/icons'

export default function CertificateDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [showRevoke, setShowRevoke] = useState(false)
  const [revokeReason, setRevokeReason] = useState('unspecified')
  const [showPkcs12, setShowPkcs12] = useState(false)
  const [passphrase, setPassphrase] = useState('')

  const { data: cert, isLoading } = useQuery({ queryKey: ['certificate', id], queryFn: () => getCertificate(id) })

  const revoke = useMutation({
    mutationFn: () => revokeCert(id, revokeReason),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['certificate', id] }); setShowRevoke(false) },
  })

  const renew = useMutation({
    mutationFn: () => renewCert(id),
    onSuccess: (data) => navigate(`/certificates/${data.id}`),
  })

  const approve = useMutation({
    mutationFn: () => approveCert(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['certificate', id] }),
  })

  const deny = useMutation({
    mutationFn: () => denyCert(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['certificate', id] }),
  })

  const handleDownload = async (format) => {
    if (format === 'pkcs12') { setShowPkcs12(true); return }
    const blob = await downloadCert(id, format)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `certificate.${format === 'der' ? 'der' : 'pem'}`
    a.click()
    URL.revokeObjectURL(url)
  }

  const handlePkcs12Download = async () => {
    const blob = await downloadCert(id, 'pkcs12', passphrase)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'certificate.p12'
    a.click()
    URL.revokeObjectURL(url)
    setShowPkcs12(false)
    setPassphrase('')
  }

  if (isLoading) return <div className="text-gray-400 py-8">Loading...</div>
  if (!cert) return <div className="text-gray-400 py-8">Certificate not found</div>

  const isAdmin = user?.role === 'admin' || user?.role === 'operator'
  const revokeReasons = [
    { value: 'unspecified', label: 'Unspecified' }, { value: 'key_compromise', label: 'Key Compromise' },
    { value: 'ca_compromise', label: 'CA Compromise' }, { value: 'superseded', label: 'Superseded' },
    { value: 'cessation_of_operation', label: 'Cessation of Operation' },
  ]

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">{cert.subject_dn}</h1>
          <div className="flex items-center gap-2 mt-1"><StatusBadge status={cert.status} /></div>
        </div>
        <div className="flex gap-2">
          {cert.status === 'active' && isAdmin && (
            <>
              <Button variant="secondary" onClick={() => renew.mutate()}>Renew</Button>
              <Button variant="danger" onClick={() => setShowRevoke(true)}>Revoke</Button>
            </>
          )}
          {cert.status === 'pending' && isAdmin && (
            <>
              <Button onClick={() => approve.mutate()}>Approve</Button>
              <Button variant="danger" onClick={() => deny.mutate()}>Deny</Button>
            </>
          )}
        </div>
      </div>

      <div className="bg-white dark:bg-surface-3 rounded-lg border border-gray-200 dark:border-gray-800 p-6 space-y-4 text-sm">
        <div className="grid grid-cols-2 gap-4">
          <div><span className="text-gray-500 dark:text-gray-400">Subject DN:</span><span className="ml-2 text-gray-900 dark:text-gray-100">{cert.subject_dn}</span></div>
          <div><span className="text-gray-500 dark:text-gray-400">Serial:</span><span className="ml-2">{cert.serial_number}</span></div>
          <div><span className="text-gray-500 dark:text-gray-400">Type:</span><span className="ml-2">{cert.type}</span></div>
          <div><span className="text-gray-500 dark:text-gray-400">Algorithm:</span><span className="ml-2">{cert.key_algorithm} {cert.key_size}</span></div>
          <div><span className="text-gray-500 dark:text-gray-400">Valid From:</span><span className="ml-2">{cert.not_before ? new Date(cert.not_before).toLocaleDateString() : '—'}</span></div>
          <div><span className="text-gray-500 dark:text-gray-400">Valid Until:</span><span className="ml-2">{cert.not_after ? new Date(cert.not_after).toLocaleDateString() : '—'}</span></div>
        </div>

        {cert.san?.length > 0 && (
          <div>
            <span className="text-gray-500 dark:text-gray-400">SANs:</span>
            <div className="mt-1 flex flex-wrap gap-1">
              {cert.san.map((s, i) => (
                <span key={i} className="px-2 py-0.5 bg-gray-100 dark:bg-surface-4 rounded text-xs">{s.type}: {s.value}</span>
              ))}
            </div>
          </div>
        )}

        {cert.certificate_pem && (
          <div className="border-t border-gray-200 dark:border-gray-800 pt-4">
            <span className="text-gray-500 dark:text-gray-400 block mb-2">Download</span>
            <div className="flex gap-2">
              <Button variant="secondary" size="sm" onClick={() => handleDownload('pem')}><DownloadIcon className="w-4 h-4" /> PEM</Button>
              <Button variant="secondary" size="sm" onClick={() => handleDownload('der')}><DownloadIcon className="w-4 h-4" /> DER</Button>
              <Button variant="secondary" size="sm" onClick={() => handleDownload('pkcs12')}><DownloadIcon className="w-4 h-4" /> PKCS12</Button>
            </div>
          </div>
        )}
      </div>

      <Modal isOpen={showRevoke} onClose={() => setShowRevoke(false)} title="Revoke Certificate">
        <div className="space-y-4">
          <Select label="Revocation Reason" options={revokeReasons} value={revokeReason} onChange={(e) => setRevokeReason(e.target.value)} />
          <div className="flex gap-2 justify-end">
            <Button variant="secondary" onClick={() => setShowRevoke(false)}>Cancel</Button>
            <Button variant="danger" onClick={() => revoke.mutate()}>Revoke</Button>
          </div>
        </div>
      </Modal>

      <Modal isOpen={showPkcs12} onClose={() => setShowPkcs12(false)} title="PKCS12 Passphrase">
        <div className="space-y-4">
          <Input label="Passphrase" type="password" value={passphrase} onChange={(e) => setPassphrase(e.target.value)} />
          <div className="flex gap-2 justify-end">
            <Button variant="secondary" onClick={() => setShowPkcs12(false)}>Cancel</Button>
            <Button onClick={handlePkcs12Download}>Download</Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
```

- [ ] **Step 4: Implement CSRSubmit**

Replace `frontend/src/pages/certificates/CSRSubmit.jsx`:

```jsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { submitCSR } from '../../api/certificates'
import { getCAs } from '../../api/cas'
import Select from '../../components/ui/Select'
import Input from '../../components/ui/Input'
import Button from '../../components/ui/Button'

export default function CSRSubmit() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { data: cas } = useQuery({ queryKey: ['cas-select'], queryFn: () => getCAs(1, 100) })

  const [csrPem, setCsrPem] = useState('')
  const [caId, setCaId] = useState('')
  const [validityDays, setValidityDays] = useState(365)
  const [error, setError] = useState('')

  const mutation = useMutation({
    mutationFn: submitCSR,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['certificates'] })
      navigate(`/certificates/${data.id}`)
    },
    onError: (err) => setError(err.response?.data?.detail || 'Failed to submit CSR'),
  })

  const handleFileUpload = (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (ev) => setCsrPem(ev.target.result)
    reader.readAsText(file)
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    setError('')
    mutation.mutate({ ca_id: caId, csr_pem: csrPem, type: 'server', validity_days: Number(validityDays) })
  }

  const caOptions = [{ value: '', label: 'Select CA...' }, ...(cas?.items?.map((ca) => ({ value: ca.id, label: ca.name })) || [])]

  return (
    <div className="max-w-2xl">
      <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-6">Submit CSR</h1>
      <form onSubmit={handleSubmit} className="space-y-6 bg-white dark:bg-surface-3 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">CSR (PEM)</label>
          <textarea
            className="w-full h-40 px-3 py-2 rounded border bg-white dark:bg-surface-4 border-gray-300 dark:border-gray-700 text-gray-900 dark:text-gray-100 font-mono text-xs focus:outline-none focus:ring-1 focus:ring-gray-400"
            value={csrPem}
            onChange={(e) => setCsrPem(e.target.value)}
            placeholder="-----BEGIN CERTIFICATE REQUEST-----"
          />
          <input type="file" accept=".pem,.csr,.req" onChange={handleFileUpload} className="mt-2 text-sm text-gray-500" />
        </div>
        <Select label="Issuing CA *" options={caOptions} value={caId} onChange={(e) => setCaId(e.target.value)} required />
        <Input label="Validity (days)" type="number" value={validityDays} onChange={(e) => setValidityDays(e.target.value)} />
        {error && <p className="text-sm text-red-500">{error}</p>}
        <div className="flex gap-3">
          <Button type="submit" disabled={mutation.isPending || !caId || !csrPem}>{mutation.isPending ? 'Submitting...' : 'Submit CSR'}</Button>
          <Button variant="secondary" type="button" onClick={() => navigate('/certificates')}>Cancel</Button>
        </div>
      </form>
    </div>
  )
}
```

- [ ] **Step 5: Verify in browser**

Create a CA, then create a certificate from it. View certificate detail. Test download buttons.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/certificates/
git commit -m "feat: certificate pages — list, create with guided/advanced, detail with downloads, CSR submit"
```

---

## Task 11: Pending Requests, Audit Log, and Users Pages

**Files:**
- Modify: `frontend/src/pages/PendingRequests.jsx`
- Modify: `frontend/src/pages/AuditLog.jsx`
- Modify: `frontend/src/pages/Users.jsx`

- [ ] **Step 1: Implement PendingRequests**

Replace `frontend/src/pages/PendingRequests.jsx`:

```jsx
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getCertificates, approveCert, denyCert } from '../api/certificates'
import Card, { CardBody } from '../components/ui/Card'
import Button from '../components/ui/Button'

export default function PendingRequests() {
  const queryClient = useQueryClient()
  const { data, isLoading } = useQuery({ queryKey: ['pending'], queryFn: () => getCertificates({ status: 'pending', per_page: 100 }) })

  const approve = useMutation({
    mutationFn: approveCert,
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['pending'] }); queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] }) },
  })

  const deny = useMutation({
    mutationFn: denyCert,
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['pending'] }); queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] }) },
  })

  if (isLoading) return <div className="text-gray-400 py-8">Loading...</div>

  return (
    <div>
      <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-6">Pending Requests</h1>
      {data?.items?.length === 0 && <p className="text-gray-400">No pending requests</p>}
      <div className="space-y-4">
        {data?.items?.map((cert) => (
          <Card key={cert.id}>
            <CardBody>
              <div className="flex items-start justify-between">
                <div>
                  <div className="font-medium text-gray-900 dark:text-gray-100">{cert.subject_dn}</div>
                  <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">Type: {cert.type} · Requested: {new Date(cert.created_at).toLocaleDateString()}</div>
                  {cert.san?.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {cert.san.map((s, i) => (
                        <span key={i} className="px-2 py-0.5 bg-gray-100 dark:bg-surface-3 rounded text-xs text-gray-600 dark:text-gray-400">{s.type}: {s.value}</span>
                      ))}
                    </div>
                  )}
                </div>
                <div className="flex gap-2">
                  <Button size="sm" onClick={() => approve.mutate(cert.id)}>Approve</Button>
                  <Button size="sm" variant="danger" onClick={() => deny.mutate(cert.id)}>Deny</Button>
                </div>
              </div>
            </CardBody>
          </Card>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Implement AuditLog**

Replace `frontend/src/pages/AuditLog.jsx`:

```jsx
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getAuditLogs, exportAuditLogs } from '../api/audit'
import Table from '../components/ui/Table'
import Select from '../components/ui/Select'
import Button from '../components/ui/Button'
import { DownloadIcon } from '../utils/icons'

const actionOptions = [
  { value: '', label: 'All Actions' },
  { value: 'created_ca', label: 'Created CA' },
  { value: 'issued_cert', label: 'Issued Cert' },
  { value: 'revoked_cert', label: 'Revoked Cert' },
  { value: 'approved_request', label: 'Approved Request' },
  { value: 'denied_request', label: 'Denied Request' },
  { value: 'login', label: 'Login' },
  { value: 'generated_crl', label: 'Generated CRL' },
]

export default function AuditLog() {
  const [action, setAction] = useState('')
  const [page, setPage] = useState(1)

  const params = { page, per_page: 25 }
  if (action) params.action = action

  const { data, isLoading } = useQuery({ queryKey: ['audit', params], queryFn: () => getAuditLogs(params) })

  const handleExport = async () => {
    const blob = await exportAuditLogs(action ? { action } : {})
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'audit_logs.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  const columns = [
    { key: 'created_at', label: 'Timestamp', render: (val) => new Date(val).toLocaleString() },
    { key: 'action', label: 'Action', render: (val) => val.replace(/_/g, ' ') },
    { key: 'resource_type', label: 'Resource Type' },
    { key: 'resource_id', label: 'Resource ID', render: (val) => val?.slice(0, 8) + '...' },
    { key: 'ip_address', label: 'IP' },
  ]

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Audit Log</h1>
        <Button variant="secondary" onClick={handleExport}><DownloadIcon className="w-4 h-4" /> Export CSV</Button>
      </div>
      <div className="flex gap-3 mb-4">
        <Select options={actionOptions} value={action} onChange={(e) => { setAction(e.target.value); setPage(1) }} className="w-48" />
      </div>
      {isLoading ? <div className="text-center py-8 text-gray-400">Loading...</div> : (
        <>
          <Table columns={columns} data={data?.items || []} />
          {data?.total > 25 && (
            <div className="flex gap-2 mt-4 justify-center">
              <Button variant="ghost" size="sm" disabled={page === 1} onClick={() => setPage(page - 1)}>Previous</Button>
              <span className="text-sm text-gray-500 py-1.5">Page {page}</span>
              <Button variant="ghost" size="sm" disabled={data?.items?.length < 25} onClick={() => setPage(page + 1)}>Next</Button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
```

- [ ] **Step 3: Implement Users**

Replace `frontend/src/pages/Users.jsx`:

```jsx
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getUsers, createUser, updateUser, deleteUser } from '../api/users'
import Table from '../components/ui/Table'
import Button from '../components/ui/Button'
import Modal from '../components/ui/Modal'
import Input from '../components/ui/Input'
import Select from '../components/ui/Select'
import Badge from '../components/ui/Badge'
import { PlusIcon } from '../utils/icons'

export default function Users() {
  const queryClient = useQueryClient()
  const { data, isLoading } = useQuery({ queryKey: ['users'], queryFn: () => getUsers(1, 100) })
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({ username: '', email: '', password: '', role: 'requester' })
  const [error, setError] = useState('')

  const create = useMutation({
    mutationFn: createUser,
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['users'] }); setShowCreate(false); setForm({ username: '', email: '', password: '', role: 'requester' }) },
    onError: (err) => setError(err.response?.data?.detail || 'Failed'),
  })

  const roleChange = useMutation({
    mutationFn: ({ id, role }) => updateUser(id, { role }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['users'] }),
  })

  const deactivate = useMutation({
    mutationFn: deleteUser,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['users'] }),
  })

  const roleOptions = [
    { value: 'admin', label: 'Admin' }, { value: 'operator', label: 'Operator' },
    { value: 'requester', label: 'Requester' }, { value: 'auditor', label: 'Auditor' },
  ]

  const columns = [
    { key: 'username', label: 'Username' },
    { key: 'email', label: 'Email' },
    {
      key: 'role', label: 'Role',
      render: (val, row) => (
        <select value={val} onChange={(e) => roleChange.mutate({ id: row.id, role: e.target.value })}
          className="bg-transparent border border-gray-200 dark:border-gray-700 rounded px-2 py-1 text-sm">
          {roleOptions.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
        </select>
      ),
    },
    { key: 'is_active', label: 'Status', render: (val) => <Badge variant={val ? 'success' : 'danger'}>{val ? 'Active' : 'Inactive'}</Badge> },
    {
      key: 'id', label: '',
      render: (_, row) => row.is_active ? (
        <Button variant="ghost" size="sm" onClick={() => { if (confirm('Deactivate this user?')) deactivate.mutate(row.id) }}>
          Deactivate
        </Button>
      ) : null,
    },
  ]

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Users</h1>
        <Button onClick={() => setShowCreate(true)}><PlusIcon className="w-4 h-4" /> Create User</Button>
      </div>
      {isLoading ? <div className="text-center py-8 text-gray-400">Loading...</div> : (
        <Table columns={columns} data={data?.items || []} />
      )}
      <Modal isOpen={showCreate} onClose={() => setShowCreate(false)} title="Create User">
        <form onSubmit={(e) => { e.preventDefault(); setError(''); create.mutate(form) }} className="space-y-4">
          <Input label="Username" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} required />
          <Input label="Email" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
          <Input label="Password" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required />
          <Select label="Role" options={roleOptions} value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} />
          {error && <p className="text-sm text-red-500">{error}</p>}
          <div className="flex gap-2 justify-end">
            <Button variant="secondary" type="button" onClick={() => setShowCreate(false)}>Cancel</Button>
            <Button type="submit" disabled={create.isPending}>Create</Button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
```

- [ ] **Step 4: Verify all pages in browser**

Test: Pending Requests (create a cert with approval CA, then approve/deny), Audit Log (filter, export), Users (create, change role, deactivate).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/PendingRequests.jsx frontend/src/pages/AuditLog.jsx frontend/src/pages/Users.jsx
git commit -m "feat: pending requests, audit log with CSV export, and user management pages"
```

---

## Summary

11 tasks covering the complete frontend:

1. Project scaffold & Tailwind theme
2. Icons & theme hook
3. API client & auth
4. UI components (9 components)
5. Layout (sidebar, navbar, app layout, shared components)
6. Router setup & login page
7. Form components (5 PKI-specific form groups)
8. Dashboard page
9. CA pages (list, create, detail)
10. Certificate pages (list, create, detail, CSR submit)
11. Pending requests, audit log, users pages

**Backend plan** is at `docs/superpowers/plans/2026-05-14-pki-server-backend.md` (already implemented).
