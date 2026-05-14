# PKI Certificate Management Server — Frontend Design Spec

## Overview

React SPA frontend for the PKI certificate management server. Presentation only — all business logic lives on the FastAPI backend. The frontend calls the REST API and renders responses.

**Stack:** Vite + React 18, Tailwind CSS (darkMode: 'class'), TanStack Query v5, React Router v6, Axios

## Project Structure

```
frontend/
├── src/
│   ├── main.jsx                    # Entry point, providers (QueryClient, Router, AuthProvider)
│   ├── App.jsx                     # Router setup with route definitions
│   ├── api/
│   │   ├── client.js               # Axios instance with JWT interceptor + 401 redirect
│   │   ├── auth.js                 # login(), logout(), getMe()
│   │   ├── users.js                # getUsers(), createUser(), updateUser(), deleteUser()
│   │   ├── cas.js                  # getCAs(), getCATree(), createRootCA(), createIntermediateCA(), getCA(), updateCA(), getCAChain(), disableCA(), enableCA()
│   │   ├── certificates.js         # getCertificates(), createCertificate(), submitCSR(), getCertificate(), approveCert(), denyCert(), revokeCert(), renewCert(), downloadCert()
│   │   ├── crl.js                  # generateCRL(), downloadCRL()
│   │   ├── audit.js                # getAuditLogs(), exportAuditLogs()
│   │   └── dashboard.js            # getStats(), getExpiring()
│   ├── hooks/
│   │   ├── useAuth.js              # Auth context: user, login(), logout(), isAuthenticated
│   │   └── useTheme.js             # Dark/light toggle, persists to localStorage
│   ├── components/
│   │   ├── layout/
│   │   │   ├── AppLayout.jsx       # Sidebar + Navbar + Content wrapper
│   │   │   ├── Sidebar.jsx         # Left nav with grouped sections + badge counts
│   │   │   └── Navbar.jsx          # Top bar: branding, theme toggle, notifications, user dropdown
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
│   │   │   ├── SubjectDNFields.jsx  # CN, O, OU, C, ST, L input group
│   │   │   ├── SANFields.jsx        # Repeatable: type dropdown (DNS/IP/Email/URI) + value input
│   │   │   ├── KeyUsageCheckboxes.jsx
│   │   │   ├── EKUCheckboxes.jsx
│   │   │   └── CustomExtensions.jsx # Repeatable: OID input + critical checkbox + value input
│   │   └── shared/
│   │       ├── StatusBadge.jsx      # Single source of truth for status → color mapping
│   │       ├── CertChain.jsx        # Chain of trust breadcrumb visualization
│   │       └── ProtectedRoute.jsx   # Role-based route guard
│   ├── pages/
│   │   ├── Login.jsx
│   │   ├── Dashboard.jsx
│   │   ├── cas/
│   │   │   ├── CAList.jsx           # Table + tree view toggle
│   │   │   ├── CADetail.jsx         # Tabbed: Overview, Certificates, Sub-CAs, Settings
│   │   │   └── CACreate.jsx         # Root + Intermediate creation form
│   │   ├── certificates/
│   │   │   ├── CertificateList.jsx  # Filterable table
│   │   │   ├── CertificateDetail.jsx # Cert info, chain, downloads, actions
│   │   │   ├── CertificateCreate.jsx # Guided + advanced toggle
│   │   │   └── CSRSubmit.jsx        # Paste/upload CSR, review, submit
│   │   ├── PendingRequests.jsx      # Approve/deny queue
│   │   ├── AuditLog.jsx            # Filterable table + CSV export
│   │   └── Users.jsx               # User CRUD (admin only)
│   └── utils/
│       └── icons.jsx                # Monochrome SVG stroke icon components
├── index.html
├── tailwind.config.js
├── postcss.config.js
├── vite.config.js
└── package.json
```

## API Client & Auth

### Axios Client (`api/client.js`)

- `baseURL: http://localhost:8000/api/v1`
- Request interceptor: attaches `Authorization: Bearer <token>` from localStorage
- Response interceptor: catches 401 → clears token → redirects to `/login`

### Auth Flow

- Login page: `POST /auth/login` → receives `access_token` + `refresh_token` → stores in localStorage
- `useAuth` hook (React Context) provides: `user`, `login()`, `logout()`, `isAuthenticated`
- On app load: if token exists, calls `GET /auth/me` to validate and populate user info
- `ProtectedRoute` component: wraps authenticated pages, redirects to login if no token, checks role for restricted pages

### React Query Integration

- Query keys: `['cas']` for lists, `['ca', id]` for single items
- Mutations invalidate relevant query keys on success (e.g., `createRootCA` invalidates `['cas']`)
- Loading and error states handled by query hook return values (`isLoading`, `error`)

## Routing

| Path | Page | Access |
|------|------|--------|
| `/login` | Login | Public |
| `/` | Dashboard | All authenticated |
| `/cas` | CA List | admin, operator, auditor |
| `/cas/new` | Create Root CA | admin, operator |
| `/cas/:id` | CA Detail | admin, operator, auditor |
| `/cas/:id/intermediate/new` | Create Intermediate CA | admin, operator |
| `/certificates` | Certificate List | admin, operator, auditor |
| `/certificates/new` | Create Certificate | admin, operator, requester |
| `/certificates/csr` | Submit CSR | admin, operator, requester |
| `/certificates/:id` | Certificate Detail | admin, operator, auditor, requester (own) |
| `/pending` | Pending Requests | admin, operator |
| `/audit` | Audit Log | admin, auditor, operator |
| `/users` | Users Management | admin |

- Login page renders standalone (no sidebar/navbar)
- All other pages render inside `AppLayout` (sidebar + navbar + content area)

## Theme

### Obsidian Palette

Tailwind custom colors configured in `tailwind.config.js`:

- **Dark surfaces:** `surface-1: #161616`, `surface-2: #181818`, `surface-3: #1e1e1e`, `surface-4: #252525`
- **Dark text:** `#e0e0e0` (primary), `#aaa` (secondary), `#666` (muted)
- **Light mode:** uses Tailwind's built-in `white`, `gray-50`, `gray-100` scale
- **Light text:** `#222` (primary), `#555` (secondary), `#999` (muted)

### Theme Toggle

- `useTheme` hook manages state, persists to localStorage
- Adds/removes `dark` class on `<html>` element
- Tailwind `darkMode: 'class'` strategy
- Sun/moon icon toggle in the navbar
- All components use `dark:` prefix variants (e.g., `bg-white dark:bg-surface-3`)

### Color Rules

Color is used **only** for status indicators. Everything else is grayscale.

- **Green** (`text-emerald-500`) — active, healthy
- **Amber** (`text-amber-500`) — pending, warning
- **Red** (`text-red-500`) — revoked, expired, error

The `StatusBadge` component is the single source of truth for status → color mapping.

### Icons

All icons are monochrome SVG, stroke-style, single color matching text weight. No filled or multi-color icons. Defined as React components in `utils/icons.jsx`.

### Borders

Minimal — subtle 1px separators (`border-gray-200 dark:border-gray-800`). Cards use background contrast, not heavy borders.

## Layout

### Navbar (top)

- **Left:** App branding ("PKI Manager")
- **Right:** Theme toggle (sun/moon) → Notifications bell with badge count → User avatar + name + role with dropdown (Profile, Settings, Logout)

### Sidebar (left)

- Grouped navigation sections:
  - **Main:** Dashboard, Certificate Authorities, Certificates, Pending Requests
  - **Management:** Audit Log, Users
- Active page indicator: left border highlight + background tint
- Badge counts on actionable items (Pending Requests count from API)
- Collapsible on smaller screens (hamburger toggle in navbar)

### Content Area

- Right of sidebar, full remaining width
- Page title + optional subtitle at top
- Content below

## Page Behaviors

### Dashboard

- Stat cards: Active CAs, Active Certs, Pending Requests, Expiring Soon. Each card links to its respective page.
- Expiring certificates table: shows subject, CA, days remaining (color-coded)
- Recent activity feed: pulls from audit logs API

### Certificate Authorities — List

- Two view modes toggled by button: table view (sortable columns) and tree view (expandable hierarchy)
- "Create Root CA" button at top
- Table columns: Name, Type, Status, Subject DN, Expires, Auto-Approve
- Clicking a row navigates to `/cas/:id`

### Certificate Authorities — Detail

- Tabbed layout:
  - **Overview:** cert info fields, chain of trust visualization, serial number, validity dates
  - **Certificates:** table of certs issued by this CA
  - **Sub-CAs:** child CAs with "Create Intermediate" button
  - **Settings:** auto_approve toggle, OCSP signing mode selector, CRL regeneration interval
- Action buttons: Disable/Enable (admin only), Create Intermediate CA

### Certificates — List

- Filterable by: CA (dropdown), Status (dropdown), search (subject DN text)
- Table columns: Subject, CA, Type, Status, Expires, Requested By
- Clicking a row navigates to `/certificates/:id`

### Certificates — Detail

- Structured display of all cert fields (not raw PEM)
- Chain of trust as visual breadcrumb: Root → Intermediate → This Cert
- Status badge (color-coded)
- Download section: PEM, DER, PKCS12 buttons. PKCS12 prompts for passphrase via modal.
- Action buttons based on status + user role:
  - Active: Revoke, Renew
  - Pending: Approve, Deny (operator/admin only)
  - Revoked/Expired: no actions

### Create Certificate

- CA selector dropdown at top
- Guided mode (default): Common Name, SANs (repeatable), Type (server/client/custom), Key Algorithm, Key Size, Validity Days
- Advanced toggle reveals: Key Usage checkboxes, EKU checkboxes, Custom Extensions (repeatable OID/value)
- Client-side validation of required fields before submit
- On submit: shows result (certificate details) or error

### Submit CSR

- Textarea for pasting PEM content, or file upload button
- Once pasted/uploaded, calls backend to parse CSR → displays subject and SANs for review
- User selects issuing CA, sets validity, then submits
- Result shows issued certificate or pending status

### Pending Requests

- Card-based layout: each pending request shows subject, SANs, requester, requested date
- Approve/Deny buttons on each card
- Clicking a card expands to show full CSR details
- After approve/deny, card animates out and counts update

### Audit Log

- Table with filters: date range picker, action type dropdown, user dropdown
- Table columns: Timestamp, User, Action, Resource Type, Resource ID, IP Address
- CSV export button triggers download via `/audit/logs/export`
- Paginated

### Users (admin only)

- Table: Username, Email, Role, Status, Created
- "Create User" button opens modal with form (username, email, password, role)
- Inline role dropdown to change roles
- Deactivate button (soft delete, with confirmation)

## Form Components

### SubjectDNFields

Input group with labeled fields for: Common Name (required), Organization, Organizational Unit, Country, State, Locality. All optional except CN.

### SANFields

Repeatable field group. Each row: type dropdown (DNS, IP, Email, URI) + value text input + remove button. "Add SAN" button appends a new row.

### KeyUsageCheckboxes

Checkbox group: Digital Signature, Key Encipherment, Data Encipherment, Key Agreement, Certificate Sign, CRL Sign, Content Commitment. Shown only in advanced mode.

### EKUCheckboxes

Checkbox group: TLS Web Server Auth, TLS Web Client Auth, Code Signing, Email Protection, OCSP Signing. Shown only in advanced mode.

### CustomExtensions

Repeatable field group. Each row: OID text input + Critical checkbox + Value text input + remove button. "Add Extension" button appends a new row. Advanced mode only.
