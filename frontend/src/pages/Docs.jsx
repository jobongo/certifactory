import { useState } from 'react'

function Code({ children }) {
  return <code className="px-1.5 py-0.5 bg-gray-100 dark:bg-surface-4 rounded text-xs font-mono text-gray-800 dark:text-gray-200">{children}</code>
}

function CodeBlock({ children }) {
  const [copied, setCopied] = useState(false)
  const text = typeof children === 'string' ? children : String(children)
  return (
    <div className="relative group my-3">
      <pre className="bg-gray-100 dark:bg-surface-4 rounded-lg p-4 pr-12 text-xs font-mono text-gray-800 dark:text-gray-200 overflow-x-auto whitespace-pre">
        {children}
      </pre>
      <button
        type="button"
        onClick={() => { navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 2000) }}
        className="absolute top-2 right-2 px-2 py-1 text-xs rounded bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-gray-300 dark:hover:bg-gray-600"
      >
        {copied ? 'Copied' : 'Copy'}
      </button>
    </div>
  )
}

function Section({ title, children, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="border-b border-gray-100 dark:border-gray-800 last:border-0">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex items-center justify-between w-full py-3 text-left"
      >
        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">{title}</h3>
        <span className="text-xs text-gray-400 dark:text-gray-500 ml-2">{open ? '▾' : '▸'}</span>
      </button>
      {open && <div className="pb-4">{children}</div>}
    </div>
  )
}

function H2({ children }) {
  return <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100 mb-4">{children}</h2>
}

function P({ children }) {
  return <p className="text-sm text-gray-700 dark:text-gray-300 mb-2 leading-relaxed">{children}</p>
}

function Li({ children }) {
  return <li className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">{children}</li>
}

function Note({ children }) {
  return (
    <div className="bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-800/50 rounded-lg p-3 my-3">
      <p className="text-sm text-amber-800 dark:text-amber-300">{children}</p>
    </div>
  )
}

function GettingStarted() {
  return (
    <div>
      <H2>Welcome to Certifactory</H2>
      <P>Certifactory is a platform for managing your organization's digital certificates. It lets you create Certificate Authorities (CAs), issue SSL/TLS certificates, track their lifecycle, and handle revocation — all from a web interface, REST API, or MCP server for AI agents.</P>

      <Section title="Logging In" defaultOpen>
        <P>Open Certifactory in your browser and enter your username and password. If this is your first time, ask your administrator for credentials. The default admin account is <Code>admin</Code> / <Code>admin</Code> — change this password immediately after first login.</P>
      </Section>

      <Section title="Navigating the Interface">
        <P>The left sidebar contains the main navigation:</P>
        <ul className="list-disc list-inside space-y-1 mb-3">
          <Li><strong>Dashboard</strong> — Overview of your PKI: active CAs, certificates, pending requests, and expiring certificates.</Li>
          <Li><strong>Authorities</strong> — Manage Certificate Authorities (Root CAs and Intermediate CAs).</Li>
          <Li><strong>Certificates</strong> — View, search, sort, and manage certificates.</Li>
          <Li><strong>Pending Requests</strong> — Review and approve or deny certificate requests (Operators and Admins only).</Li>
          <Li><strong>Audit Log</strong> — See a record of every action taken in the system.</Li>
          <Li><strong>Users</strong> — Manage user accounts and permissions (Admins only).</Li>
          <Li><strong>Settings</strong> — Configure system-wide settings, MCP server, and TLS certificates (Admins only).</Li>
        </ul>
      </Section>

      <Section title="Your Profile">
        <P>Click your name in the top-right corner and select <strong>Profile</strong> to:</P>
        <ul className="list-disc list-inside space-y-1 mb-3">
          <Li>View your account information</Li>
          <Li>Switch between light and dark mode</Li>
          <Li>Change your password</Li>
          <Li>Create and manage API tokens for automated access</Li>
        </ul>
      </Section>

      <Section title="What is a Certificate Authority (CA)?">
        <P>A Certificate Authority is a trusted entity that issues digital certificates. Think of it like a notary — it vouches that a certificate belongs to who it claims. In Certifactory, you can create your own CAs to issue certificates for your servers, applications, and users.</P>
      </Section>

      <Section title="What is a Certificate?">
        <P>A digital certificate is an electronic document that proves the identity of a server, device, or person. When you visit a website with HTTPS, your browser checks the site's certificate to make sure it's legitimate. Certifactory helps you create and manage these certificates.</P>
      </Section>
    </div>
  )
}

function AuthoritiesGuide() {
  return (
    <div>
      <H2>Certificate Authorities</H2>
      <P>Certificate Authorities (CAs) are the foundation of your PKI. They sign and issue certificates. Certifactory supports a flexible hierarchy — you can have a simple single CA or a multi-tier structure.</P>

      <Section title="Creating a Root CA" defaultOpen>
        <P>A Root CA is the top-level authority in your certificate chain. To create one:</P>
        <ol className="list-decimal list-inside space-y-1 mb-3">
          <Li>Go to <strong>Authorities</strong> in the sidebar.</Li>
          <Li>Click <strong>Create Root CA</strong>.</Li>
          <Li>Enter a <strong>CA Name</strong> (e.g., "My Organization Root CA").</Li>
          <Li>Fill in the <strong>Common Name</strong> (CN) — this identifies the CA.</Li>
          <Li>Optionally fill in Organization, Country, etc.</Li>
          <Li>Choose a <strong>Key Algorithm</strong> — RSA 2048 is a safe default. Use RSA 4096 or EC P-256 for higher security.</Li>
          <Li>Set the <strong>Validity</strong> — Root CAs typically last 10-20 years (3650-7300 days).</Li>
          <Li>Click <strong>Create CA</strong>.</Li>
        </ol>
        <Note>The Root CA's private key is encrypted and stored securely. Keep your Certifactory master key safe — it protects all stored private keys.</Note>
      </Section>

      <Section title="Creating an Intermediate CA">
        <P>Intermediate CAs sit between the Root CA and end-entity certificates. This is a best practice for production environments because if an intermediate is compromised, the root remains safe.</P>
        <ol className="list-decimal list-inside space-y-1 mb-3">
          <Li>Go to the Root CA's detail page (click it in the list).</Li>
          <Li>Click <strong>Create Intermediate</strong>.</Li>
          <Li>Fill in the details (same as Root CA, but validity is usually shorter — e.g., 5 years / 1825 days).</Li>
          <Li>The intermediate will be automatically signed by the parent CA.</Li>
        </ol>
      </Section>

      <Section title="Importing an Existing CA">
        <P>If you already have a CA certificate and private key, you can import them:</P>
        <ol className="list-decimal list-inside space-y-1 mb-3">
          <Li>Click <strong>Import CA</strong> on the Authorities page.</Li>
          <Li>Choose the format — PEM/DER (separate cert and key files) or PKCS12/PFX (single bundled file).</Li>
          <Li>Upload the files and enter a name.</Li>
          <Li>Certifactory will automatically detect the parent CA if it exists in the system.</Li>
        </ol>
        <Note>A private key is required when importing a CA — without it, the CA cannot sign new certificates.</Note>
      </Section>

      <Section title="CA Settings">
        <P>On the CA detail page, the <strong>Settings</strong> tab lets admins configure:</P>
        <ul className="list-disc list-inside space-y-1 mb-3">
          <Li><strong>Auto-Approve:</strong> Toggle on/off. When enabled, certificate requests are signed immediately. When disabled, requests go to the Pending queue for review.</Li>
          <Li><strong>OCSP Signing Mode:</strong> Choose whether OCSP responses are signed by the CA key directly or by a dedicated OCSP signing certificate.</Li>
          <Li><strong>CRL Interval:</strong> Hours between CRL regeneration for this CA.</Li>
        </ul>
      </Section>

      <Section title="Downloading CA Certificates">
        <P>On the CA detail page, you can download:</P>
        <ul className="list-disc list-inside space-y-1 mb-3">
          <Li><strong>Certificate</strong> — The CA certificate as a <Code>.crt</Code> file. Distribute this to systems that need to trust certificates issued by this CA.</Li>
          <Li><strong>Full Chain</strong> — The CA certificate plus all parent certificates as a <Code>.crt</Code> file. Use this when a client needs the complete chain of trust.</Li>
          <Li><strong>View PEM</strong> — View the certificate PEM directly in the browser with a copy-to-clipboard button. Toggle between the single certificate and the full chain.</Li>
          <Li><strong>CRL</strong> — The current Certificate Revocation List for this CA.</Li>
        </ul>
      </Section>

      <Section title="CRL Management">
        <P>Each CA maintains a Certificate Revocation List (CRL) — a signed list of revoked certificate serial numbers. CRLs are regenerated automatically based on the configured interval (see Settings). You can also:</P>
        <ul className="list-disc list-inside space-y-1 mb-3">
          <Li>Click <strong>Regenerate CRL</strong> on the CA overview tab to force an immediate regeneration.</Li>
          <Li>View CRL status (CRL number, last generated, next update) on the CA's <strong>Settings</strong> tab.</Li>
        </ul>
      </Section>

      <Section title="Certificate Templates">
        <P>Templates let you define reusable certificate profiles for a CA — pre-configured type, algorithm, validity, key usage, EKU, and subject defaults (Organization, OU, Country, State, Locality). Templates are per-CA and managed by admins.</P>
        <P>To create a template:</P>
        <ol className="list-decimal list-inside space-y-1 mb-3">
          <Li>Go to a CA's detail page and open the <strong>Templates</strong> tab.</Li>
          <Li>Click <strong>New Template</strong>.</Li>
          <Li>Enter a name (e.g., "Web Server", "Client Auth") and configure the defaults.</Li>
          <Li>Click <strong>Create</strong>.</Li>
        </ol>
        <P>When creating a certificate, select a CA that has templates — a <strong>Template</strong> dropdown appears. Selecting a template pre-fills all configured fields. You can still override any value before submitting.</P>
      </Section>

      <Section title="MCP Access Settings">
        <P>Control which CAs are accessible to AI agents via the MCP server. On the CA detail page's <strong>Settings</strong> tab:</P>
        <ul className="list-disc list-inside space-y-1 mb-3">
          <Li><strong>MCP Enabled:</strong> Toggle whether AI agents can access this CA at all.</Li>
          <Li><strong>Allowed Operations:</strong> Restrict which operations agents can perform — issue certificates, download certificates/keys. Leave all unchecked to allow all operations.</Li>
        </ul>
      </Section>
    </div>
  )
}

function CertificatesGuide() {
  return (
    <div>
      <H2>Certificates</H2>

      <Section title="Certificate List" defaultOpen>
        <P>The Certificates page shows all certificates in a structured table with columns for Common Name, Organization, SAN, Type, Status, and Expiry. You can:</P>
        <ul className="list-disc list-inside space-y-1 mb-3">
          <Li><strong>Search</strong> — Filter by subject DN using the search bar.</Li>
          <Li><strong>Sort</strong> — Click column headers (Common Name, Type, Status, Expires) to sort ascending/descending.</Li>
          <Li><strong>Filter</strong> — Use the CA and Status dropdowns to narrow results.</Li>
        </ul>
      </Section>

      <Section title="Creating a Certificate">
        <P>To create a new certificate (the server generates the key pair for you):</P>
        <ol className="list-decimal list-inside space-y-1 mb-3">
          <Li>Go to <strong>Certificates</strong> and click <strong>New Certificate</strong>.</Li>
          <Li>Select the <strong>Issuing CA</strong> that will sign this certificate.</Li>
          <Li>Optionally select a <strong>Template</strong> to pre-fill fields.</Li>
          <Li>Enter the <strong>Common Name</strong> — usually the server's hostname (e.g., <Code>webserver.example.com</Code>).</Li>
          <Li>Add <strong>Subject Alternative Names (SANs)</strong> — additional hostnames or IPs the certificate covers.</Li>
          <Li>Choose the <strong>Type</strong>: Server (for web servers, APIs), Client (for mutual TLS), or Custom.</Li>
          <Li>Set the <strong>Validity</strong> in days (defaults to the global setting).</Li>
          <Li>Click <strong>Create Certificate</strong>.</Li>
        </ol>
        <P>If the CA has auto-approve enabled, the certificate is issued immediately. Otherwise, it enters the Pending queue.</P>
        <Note>Duplicate CN detection is enforced per CA — you cannot create two active or pending certificates with the same Common Name under the same CA.</Note>
      </Section>

      <Section title="Submitting a CSR">
        <P>If you generated a key pair yourself (e.g., with OpenSSL) and have a Certificate Signing Request (CSR):</P>
        <ol className="list-decimal list-inside space-y-1 mb-3">
          <Li>Click <strong>Submit CSR</strong> on the Certificates page.</Li>
          <Li>Paste the CSR content (starts with <Code>-----BEGIN CERTIFICATE REQUEST-----</Code>) or upload the file.</Li>
          <Li>Select the <strong>Issuing CA</strong> and set the validity period.</Li>
          <Li>Click <strong>Submit CSR</strong>.</Li>
        </ol>
        <Note>When you submit a CSR, your private key stays with you — only the public key is sent to Certifactory. This is the most secure method.</Note>
      </Section>

      <Section title="Generating a CSR with OpenSSL">
        <P>Generate a private key and CSR:</P>
        <CodeBlock>{`openssl req -new -newkey rsa:2048 -nodes \\
  -keyout server.key -out server.csr \\
  -subj "/CN=myserver.example.com/O=My Organization/C=US"`}</CodeBlock>
        <P>View the CSR contents to verify:</P>
        <CodeBlock>{`openssl req -in server.csr -text -noout`}</CodeBlock>
        <P>Copy the contents of <Code>server.csr</Code> and paste them into Certifactory's Submit CSR form. Keep <Code>server.key</Code> safe — you'll need it when installing the certificate.</P>
      </Section>

      <Section title="Viewing & Downloading Certificates">
        <P>On the certificate detail page:</P>
        <ul className="list-disc list-inside space-y-1 mb-3">
          <Li><strong>PEM</strong> — Standard text format. Used by Apache, Nginx, and most Linux applications.</Li>
          <Li><strong>DER</strong> — Binary format. Used by some Java applications.</Li>
          <Li><strong>PKCS12</strong> — Bundled format containing both the certificate and private key. You'll be prompted for a passphrase.</Li>
          <Li><strong>View PEM</strong> — View the certificate or CSR PEM directly in a modal with a copy-to-clipboard button.</Li>
        </ul>
        <P>If the certificate was created through Certifactory (not via CSR), you can also download the <strong>Private Key</strong> as a PEM file.</P>
        <Note>Private keys submitted via CSR are never stored in Certifactory — only the certificate is available for download.</Note>
      </Section>

      <Section title="Revoking a Certificate">
        <ol className="list-decimal list-inside space-y-1 mb-3">
          <Li>Go to the certificate detail page.</Li>
          <Li>Click <strong>Revoke</strong>.</Li>
          <Li>Select a reason (Key Compromise, Superseded, Cessation of Operation, etc.).</Li>
          <Li>Confirm the revocation.</Li>
        </ol>
        <P>Revoked certificates are added to the CA's CRL and will show as revoked in OCSP responses.</P>
      </Section>

      <Section title="Renewing a Certificate">
        <P>Click <strong>Renew</strong> on an active certificate's detail page. This creates a new certificate with the same subject and SANs but a fresh validity period. The old certificate remains active until you revoke it.</P>
      </Section>

      <Section title="Importing Certificates">
        <ol className="list-decimal list-inside space-y-1 mb-3">
          <Li>Click <strong>Import</strong> on the Certificates page.</Li>
          <Li>Upload the certificate file (PEM, DER, or PKCS12).</Li>
          <Li>Optionally upload the private key.</Li>
          <Li>Certifactory will auto-detect the issuing CA.</Li>
        </ol>
      </Section>
    </div>
  )
}

function ApprovalGuide() {
  return (
    <div>
      <H2>Approval Workflow</H2>
      <P>When a CA has <strong>Auto-Approve</strong> disabled, certificate requests require manual approval before they are signed.</P>

      <Section title="How It Works" defaultOpen>
        <ol className="list-decimal list-inside space-y-1 mb-3">
          <Li>A user creates a certificate request.</Li>
          <Li>The request enters a <strong>Pending</strong> state — the certificate is not yet signed.</Li>
          <Li>An Operator or Admin reviews the request on the <strong>Pending Requests</strong> page or the certificate detail page.</Li>
          <Li>They click <strong>Approve</strong> to sign and issue the certificate, or <strong>Deny</strong> to reject it.</Li>
          <Li>Pending certificates can also be <strong>Deleted</strong> to remove them entirely.</Li>
        </ol>
      </Section>

      <Section title="Self-Approval Permission">
        <P>The <strong>Self-Approve</strong> permission controls whether a user can approve certificates they themselves requested. This is managed per-user on the <strong>Users</strong> page:</P>
        <ul className="list-disc list-inside space-y-1 mb-3">
          <Li>Users with <strong>Self-Approve enabled</strong> can request and approve their own certificates.</Li>
          <Li>Users with <strong>Self-Approve disabled</strong> must have a different user approve their requests.</Li>
          <Li>Existing admin users have Self-Approve enabled by default. New users have it disabled.</Li>
        </ul>
        <P>Any user can <strong>deny</strong> their own requests (withdrawing them), regardless of this setting.</P>
        <Note>This applies to both UI and API token access. Use it to enforce four-eyes approval for entry-level technicians while allowing senior admins to self-serve.</Note>
      </Section>

      <Section title="When to Use Approval Workflow">
        <ul className="list-disc list-inside space-y-1 mb-3">
          <Li><strong>Production CAs:</strong> Always require approval to maintain control over which certificates are issued.</Li>
          <Li><strong>Lab/Dev CAs:</strong> Auto-approve is fine for development environments where speed matters more than oversight.</Li>
        </ul>
      </Section>
    </div>
  )
}

function UsersGuide() {
  return (
    <div>
      <H2>Users & Roles</H2>

      <Section title="Roles" defaultOpen>
        <div className="overflow-x-auto mb-4">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700">
                <th className="text-left py-2 pr-4 font-medium text-gray-500 dark:text-gray-400">Role</th>
                <th className="text-left py-2 pr-4 font-medium text-gray-500 dark:text-gray-400">Can Do</th>
                <th className="text-left py-2 font-medium text-gray-500 dark:text-gray-400">Cannot Do</th>
              </tr>
            </thead>
            <tbody className="text-gray-700 dark:text-gray-300">
              <tr className="border-b border-gray-100 dark:border-gray-800">
                <td className="py-2 pr-4 font-medium">Admin</td>
                <td className="py-2 pr-4">Everything — manage users, CAs, certificates, settings, MCP configuration</td>
                <td className="py-2">—</td>
              </tr>
              <tr className="border-b border-gray-100 dark:border-gray-800">
                <td className="py-2 pr-4 font-medium">Operator</td>
                <td className="py-2 pr-4">Create/manage CAs, issue/approve/deny/revoke certificates, view audit logs</td>
                <td className="py-2">Manage users, change settings</td>
              </tr>
              <tr className="border-b border-gray-100 dark:border-gray-800">
                <td className="py-2 pr-4 font-medium">Requester</td>
                <td className="py-2 pr-4">Request certificates, submit CSRs, import certificates, view own certificates</td>
                <td className="py-2">Manage CAs, approve/deny requests, view others' certificates</td>
              </tr>
              <tr>
                <td className="py-2 pr-4 font-medium">Auditor</td>
                <td className="py-2 pr-4">View CAs, certificates, and full audit logs (read-only)</td>
                <td className="py-2">Create, modify, or delete anything</td>
              </tr>
            </tbody>
          </table>
        </div>
      </Section>

      <Section title="Managing Users (Admin Only)">
        <P>Go to <strong>Users</strong> in the sidebar to:</P>
        <ul className="list-disc list-inside space-y-1 mb-3">
          <Li><strong>Create User:</strong> Click "Create User", enter username, email, password, and select a role.</Li>
          <Li><strong>Change Role:</strong> Use the role dropdown directly in the users table row.</Li>
          <Li><strong>Self-Approve:</strong> Toggle whether this user can approve certificates they requested.</Li>
          <Li><strong>Reset Password:</strong> Click "Reset Password" to set a new password for a user.</Li>
          <Li><strong>Deactivate:</strong> Click "Deactivate" to disable a user's account. Their audit history is preserved.</Li>
        </ul>
      </Section>

      <Section title="API Tokens">
        <P>Users can create API tokens for programmatic access from their <strong>Profile</strong> page. Tokens:</P>
        <ul className="list-disc list-inside space-y-1 mb-3">
          <Li>Have the same permissions as the user who created them</Li>
          <Li>Are long-lived (no expiration) — revoke them when no longer needed</Li>
          <Li>Are shown only once at creation — copy and store them securely</Li>
          <Li>Start with <Code>cf_</Code> and are used as Bearer tokens in API requests</Li>
          <Li>Are also used for MCP server authentication</Li>
        </ul>
      </Section>
    </div>
  )
}

function SettingsGuide() {
  return (
    <div>
      <H2>Settings</H2>
      <P>The <strong>Settings</strong> page (Admin only) lets you configure system-wide defaults. Changes take effect immediately for new operations.</P>

      <Section title="Security" defaultOpen>
        <ul className="list-disc list-inside space-y-1 mb-3">
          <Li><strong>Session Timeout</strong> — Minutes of inactivity before access tokens expire (5–1440).</Li>
          <Li><strong>Refresh Token Lifetime</strong> — Days before refresh tokens expire (1–90).</Li>
          <Li><strong>Minimum Password Length</strong> — Minimum characters required for new passwords (4–128).</Li>
          <Li><strong>Require Uppercase / Number / Special Character</strong> — Enforce password complexity rules.</Li>
        </ul>
        <Note>Password policy changes only apply to new passwords — existing passwords are not validated retroactively.</Note>
      </Section>

      <Section title="Certificates">
        <ul className="list-disc list-inside space-y-1 mb-3">
          <Li><strong>Default Certificate Validity</strong> — Default validity period in days for new certificates (1–3650).</Li>
          <Li><strong>Default CA Auto-Approve</strong> — Whether new CAs default to auto-approve. Can be overridden per CA.</Li>
        </ul>
      </Section>

      <Section title="Maintenance">
        <ul className="list-disc list-inside space-y-1 mb-3">
          <Li><strong>Audit Log Retention</strong> — Days to keep audit log entries before automatic cleanup (30–3650).</Li>
          <Li><strong>CRL Regeneration Interval</strong> — Minutes between automatic CRL regeneration cycles (5–1440).</Li>
        </ul>
      </Section>

      <Section title="MCP Server">
        <P>Configure AI agent access to your PKI server via the Model Context Protocol:</P>
        <ul className="list-disc list-inside space-y-1 mb-3">
          <Li><strong>MCP Server Enabled</strong> — Global kill switch. When disabled, all MCP tool calls are rejected.</Li>
          <Li><strong>MCP Allow Approval</strong> — Whether AI agents can approve or deny certificate requests via MCP. Disabled by default for security.</Li>
        </ul>
        <P>Per-CA MCP settings (MCP access enabled, allowed operations) are configured on each CA's <strong>Settings</strong> tab.</P>
      </Section>

      <Section title="TLS Certificate">
        <P>Configure the server certificate used by the Certifactory proxy for HTTPS:</P>
        <ul className="list-disc list-inside space-y-1 mb-3">
          <Li><strong>Upload</strong> — Paste a PEM certificate and private key to use an externally-issued certificate.</Li>
          <Li><strong>Issue from CA</strong> — Select one of your managed CAs and issue a server certificate directly. Enter the common name and SANs for your Certifactory hostname.</Li>
        </ul>
        <P>The current certificate details (subject, issuer, expiry) are displayed at the top of the card. After updating, restart the proxy container to apply the new certificate.</P>
        <Note>Certificates issued from a managed CA are auto-approved regardless of the CA's auto-approve setting.</Note>
      </Section>
    </div>
  )
}

function MCPGuide() {
  return (
    <div>
      <H2>MCP Server</H2>
      <P>Certifactory includes a built-in MCP (Model Context Protocol) server that allows AI agents like Claude to interact with your PKI infrastructure programmatically.</P>

      <Section title="Overview" defaultOpen>
        <P>The MCP server is accessible at <Code>/mcp</Code> via Streamable HTTP transport. It provides 12 tools for reading PKI state, issuing certificates, and managing approvals.</P>
        <P>Authentication uses the same API tokens (<Code>cf_</Code> prefix) that you create from your Profile page. Each tool call requires a <Code>token</Code> parameter.</P>
      </Section>

      <Section title="Available Tools">
        <div className="overflow-x-auto mb-4">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700">
                <th className="text-left py-2 pr-4 font-medium text-gray-500 dark:text-gray-400">Tool</th>
                <th className="text-left py-2 pr-4 font-medium text-gray-500 dark:text-gray-400">Description</th>
                <th className="text-left py-2 font-medium text-gray-500 dark:text-gray-400">Type</th>
              </tr>
            </thead>
            <tbody className="text-gray-700 dark:text-gray-300">
              {[
                ['list_cas', 'List CAs with optional status filter', 'Read'],
                ['get_ca', 'Get CA details by ID or name', 'Read'],
                ['get_ca_chain', 'Get full PEM certificate chain', 'Read'],
                ['list_certificates', 'Search/filter/sort certificates', 'Read'],
                ['get_certificate', 'Get certificate details by ID', 'Read'],
                ['get_crl_info', 'Get CRL status for a CA', 'Read'],
                ['check_certificate_status', 'Check revocation status', 'Read'],
                ['create_certificate', 'Issue a new certificate', 'Write'],
                ['submit_csr', 'Submit a CSR for signing', 'Write'],
                ['approve_certificate', 'Approve a pending cert', 'Write'],
                ['deny_certificate', 'Deny a pending cert', 'Write'],
                ['download_certificate', 'Download cert/key (PEM/DER/PKCS12)', 'Read'],
              ].map(([tool, desc, type]) => (
                <tr key={tool} className="border-b border-gray-100 dark:border-gray-800">
                  <td className="py-1.5 pr-4 font-mono text-xs">{tool}</td>
                  <td className="py-1.5 pr-4">{desc}</td>
                  <td className="py-1.5">{type}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section title="Configuration">
        <P>MCP access is controlled at three levels:</P>
        <ol className="list-decimal list-inside space-y-1 mb-3">
          <Li><strong>Global</strong> — Enable/disable the entire MCP server and approval tools from <strong>Settings</strong>.</Li>
          <Li><strong>Per-CA</strong> — Enable/disable MCP access and restrict operations on each CA's <strong>Settings</strong> tab.</Li>
          <Li><strong>Per-User</strong> — The API token inherits the user's role and <strong>Self-Approve</strong> permission.</Li>
        </ol>
      </Section>

      <Section title="Security Guards">
        <ul className="list-disc list-inside space-y-1 mb-3">
          <Li><strong>Self-approval guard:</strong> An agent cannot approve a certificate it requested (controlled by the user's Self-Approve permission).</Li>
          <Li><strong>RBAC enforcement:</strong> Each tool checks the API token user's role. Requesters can only see their own certificates.</Li>
          <Li><strong>Per-CA access control:</strong> Write operations (issue, download) check the CA's MCP allowed operations list.</Li>
        </ul>
      </Section>

      <Section title="Connecting from Claude Desktop">
        <P>Add this to your Claude Desktop MCP configuration:</P>
        <CodeBlock>{`{
  "mcpServers": {
    "certifactory": {
      "url": "https://your-server/mcp/",
      "headers": {
        "Authorization": "Bearer cf_your_api_token_here"
      }
    }
  }
}`}</CodeBlock>
      </Section>
    </div>
  )
}

function APIGuide() {
  return (
    <div>
      <H2>API Reference</H2>
      <P>Certifactory provides a complete REST API. For interactive documentation with try-it-out functionality, visit <a href="/docs" className="underline text-gray-900 dark:text-gray-100">/docs</a> (Swagger UI).</P>

      <Section title="Authentication" defaultOpen>
        <P><strong>JWT Token</strong> — Login and get a token:</P>
        <CodeBlock>{`curl -X POST https://your-server/api/v1/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{"username": "admin", "password": "admin"}'`}</CodeBlock>
        <P>Use the token in subsequent requests:</P>
        <CodeBlock>{`curl https://your-server/api/v1/cas \\
  -H "Authorization: Bearer eyJ..."`}</CodeBlock>
        <P>Refresh an expired access token:</P>
        <CodeBlock>{`curl -X POST https://your-server/api/v1/auth/refresh \\
  -H "Content-Type: application/json" \\
  -d '{"refresh_token": "eyJ..."}'`}</CodeBlock>
        <P><strong>API Token</strong> — Create from the Profile page, then use it:</P>
        <CodeBlock>{`curl https://your-server/api/v1/cas \\
  -H "Authorization: Bearer cf_a1b2c3d4..."`}</CodeBlock>
      </Section>

      <Section title="Certificate Authorities">
        <P>List all CAs:</P>
        <CodeBlock>{`curl https://your-server/api/v1/cas \\
  -H "Authorization: Bearer <token>"`}</CodeBlock>
        <P>Create a Root CA:</P>
        <CodeBlock>{`curl -X POST https://your-server/api/v1/cas \\
  -H "Authorization: Bearer <token>" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "My Root CA",
    "subject": {"CN": "My Root CA", "O": "My Org", "C": "US"},
    "key_algorithm": "RSA",
    "key_size": 2048,
    "validity_days": 3650,
    "auto_approve": true
  }'`}</CodeBlock>
        <P>Create an Intermediate CA:</P>
        <CodeBlock>{`curl -X POST https://your-server/api/v1/cas/<root_ca_id>/intermediate \\
  -H "Authorization: Bearer <token>" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "My Intermediate CA",
    "subject": {"CN": "My Intermediate CA", "O": "My Org", "C": "US"},
    "key_algorithm": "RSA",
    "key_size": 2048,
    "validity_days": 1825
  }'`}</CodeBlock>
        <P>Get CA certificate chain:</P>
        <CodeBlock>{`curl https://your-server/api/v1/cas/<ca_id>/chain \\
  -H "Authorization: Bearer <token>"`}</CodeBlock>
      </Section>

      <Section title="Certificates">
        <P>Request a new certificate:</P>
        <CodeBlock>{`curl -X POST https://your-server/api/v1/certificates \\
  -H "Authorization: Bearer <token>" \\
  -H "Content-Type: application/json" \\
  -d '{
    "ca_id": "<ca_id>",
    "subject": {"CN": "webserver.example.com"},
    "san": [
      {"type": "DNS", "value": "webserver.example.com"},
      {"type": "IP", "value": "192.168.1.100"}
    ],
    "type": "server",
    "key_algorithm": "RSA",
    "key_size": 2048,
    "validity_days": 365
  }'`}</CodeBlock>
        <P>Submit a CSR:</P>
        <CodeBlock>{`curl -X POST https://your-server/api/v1/certificates/csr \\
  -H "Authorization: Bearer <token>" \\
  -H "Content-Type: application/json" \\
  -d '{
    "ca_id": "<ca_id>",
    "csr_pem": "-----BEGIN CERTIFICATE REQUEST-----\\nMIIC...",
    "type": "server",
    "validity_days": 365
  }'`}</CodeBlock>
        <P>Download certificate (PEM):</P>
        <CodeBlock>{`curl https://your-server/api/v1/certificates/<id>/download?format=pem \\
  -H "Authorization: Bearer <token>" -o cert.pem`}</CodeBlock>
        <P>Download private key:</P>
        <CodeBlock>{`curl "https://your-server/api/v1/certificates/<id>/download?key_only=true" \\
  -H "Authorization: Bearer <token>" -o private_key.pem`}</CodeBlock>
        <P>Approve a pending certificate:</P>
        <CodeBlock>{`curl -X POST https://your-server/api/v1/certificates/<id>/approve \\
  -H "Authorization: Bearer <token>"`}</CodeBlock>
        <P>Revoke a certificate:</P>
        <CodeBlock>{`curl -X POST https://your-server/api/v1/certificates/<id>/revoke \\
  -H "Authorization: Bearer <token>" \\
  -H "Content-Type: application/json" \\
  -d '{"reason": "key_compromise"}'`}</CodeBlock>
      </Section>

      <Section title="CRL & OCSP">
        <P>Download CRL (no auth required):</P>
        <CodeBlock>{`curl https://your-server/api/v1/cas/<ca_id>/crl -o crl.pem`}</CodeBlock>
        <P>Force CRL regeneration:</P>
        <CodeBlock>{`curl -X POST https://your-server/api/v1/cas/<ca_id>/crl/generate \\
  -H "Authorization: Bearer <token>"`}</CodeBlock>
        <P>OCSP query:</P>
        <CodeBlock>{`openssl ocsp -issuer ca.pem -cert server.pem \\
  -url https://your-server/api/v1/ocsp/<ca_id> -resp_text`}</CodeBlock>
      </Section>

      <Section title="Templates">
        <P>List templates for a CA:</P>
        <CodeBlock>{`curl https://your-server/api/v1/cas/<ca_id>/templates \\
  -H "Authorization: Bearer <token>"`}</CodeBlock>
        <P>Create a template (admin only):</P>
        <CodeBlock>{`curl -X POST https://your-server/api/v1/cas/<ca_id>/templates \\
  -H "Authorization: Bearer <token>" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "Web Server",
    "type": "server",
    "key_algorithm": "RSA",
    "key_size": 2048,
    "validity_days": 365,
    "subject_defaults": {"O": "My Org", "C": "US"}
  }'`}</CodeBlock>
      </Section>

      <Section title="Settings">
        <P>Get all settings (admin only):</P>
        <CodeBlock>{`curl https://your-server/api/v1/settings \\
  -H "Authorization: Bearer <token>"`}</CodeBlock>
        <P>Update settings:</P>
        <CodeBlock>{`curl -X PUT https://your-server/api/v1/settings \\
  -H "Authorization: Bearer <token>" \\
  -H "Content-Type: application/json" \\
  -d '{"session_timeout_minutes": 60, "mcp_enabled": true}'`}</CodeBlock>
      </Section>

      <Section title="TLS Certificate">
        <P>Get current TLS certificate info:</P>
        <CodeBlock>{`curl https://your-server/api/v1/tls \\
  -H "Authorization: Bearer <token>"`}</CodeBlock>
        <P>Upload a TLS certificate:</P>
        <CodeBlock>{`curl -X POST https://your-server/api/v1/tls/upload \\
  -H "Authorization: Bearer <token>" \\
  -H "Content-Type: application/json" \\
  -d '{
    "certificate_pem": "-----BEGIN CERTIFICATE-----\\n...",
    "private_key_pem": "-----BEGIN PRIVATE KEY-----\\n..."
  }'`}</CodeBlock>
        <P>Issue TLS certificate from a managed CA:</P>
        <CodeBlock>{`curl -X POST https://your-server/api/v1/tls/issue \\
  -H "Authorization: Bearer <token>" \\
  -H "Content-Type: application/json" \\
  -d '{
    "ca_id": "<ca_id>",
    "common_name": "certifactory.example.com",
    "validity_days": 365
  }'`}</CodeBlock>
      </Section>

      <Section title="Users & Tokens">
        <P>Create a user (admin only):</P>
        <CodeBlock>{`curl -X POST https://your-server/api/v1/users \\
  -H "Authorization: Bearer <token>" \\
  -H "Content-Type: application/json" \\
  -d '{
    "username": "operator1",
    "email": "op1@example.com",
    "password": "securepassword",
    "role": "operator"
  }'`}</CodeBlock>
        <P>Create an API token:</P>
        <CodeBlock>{`curl -X POST https://your-server/api/v1/tokens \\
  -H "Authorization: Bearer <token>" \\
  -H "Content-Type: application/json" \\
  -d '{"name": "CI Pipeline"}'`}</CodeBlock>
      </Section>
    </div>
  )
}

function Glossary() {
  return (
    <div>
      <H2>Glossary</H2>
      <dl className="space-y-3 text-sm">
        {[
          ['CA (Certificate Authority)', 'A trusted entity that issues and signs digital certificates. A CA vouches for the identity of the certificate holder.'],
          ['Root CA', 'The top-level CA in a certificate chain. It is self-signed (it trusts itself). All trust in a PKI chain flows from the Root CA.'],
          ['Intermediate CA', 'A CA that is signed by a Root CA (or another Intermediate). Used to add a layer of security — if compromised, the Root CA is unaffected.'],
          ['CSR (Certificate Signing Request)', 'A message sent to a CA to request a signed certificate. Contains the public key and identity information. The private key is NOT included.'],
          ['SAN (Subject Alternative Name)', 'Additional identities (hostnames, IP addresses, emails) that a certificate covers. Modern browsers require SANs — the Common Name alone is not sufficient.'],
          ['PEM', 'A text-based file format for certificates and keys. Starts with "-----BEGIN CERTIFICATE-----". The most common format on Linux.'],
          ['DER', 'A binary file format for certificates. Same data as PEM but not human-readable. Used by some Java and Windows applications.'],
          ['PKCS12 / PFX', 'A file format that bundles a certificate with its private key in a single password-protected file. Common on Windows and in Java keystores.'],
          ['CRL (Certificate Revocation List)', 'A list published by a CA containing the serial numbers of certificates that have been revoked before their expiration date.'],
          ['OCSP (Online Certificate Status Protocol)', 'A protocol for checking whether a specific certificate has been revoked, in real time. Faster than downloading a full CRL.'],
          ['Key Usage', 'Certificate extension that defines what operations the key can be used for (e.g., digital signatures, key encipherment).'],
          ['Extended Key Usage (EKU)', 'Specifies the purpose of the certificate: TLS Web Server Auth, TLS Web Client Auth, Code Signing, Email Protection, etc.'],
          ['MCP (Model Context Protocol)', 'A protocol for AI agents to interact with external tools and services. Certifactory\'s MCP server lets agents manage certificates programmatically.'],
        ].map(([term, desc]) => (
          <div key={term}>
            <dt className="font-semibold text-gray-900 dark:text-gray-100">{term}</dt>
            <dd className="text-gray-700 dark:text-gray-300 mt-0.5">{desc}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}

const tabs = [
  { key: 'start', label: 'Getting Started', content: <GettingStarted /> },
  { key: 'authorities', label: 'Authorities', content: <AuthoritiesGuide /> },
  { key: 'certificates', label: 'Certificates', content: <CertificatesGuide /> },
  { key: 'approval', label: 'Approval', content: <ApprovalGuide /> },
  { key: 'users', label: 'Users & Roles', content: <UsersGuide /> },
  { key: 'settings', label: 'Settings', content: <SettingsGuide /> },
  { key: 'mcp', label: 'MCP Server', content: <MCPGuide /> },
  { key: 'api', label: 'API Reference', content: <APIGuide /> },
  { key: 'glossary', label: 'Glossary', content: <Glossary /> },
]

export default function Docs() {
  const [active, setActive] = useState('start')
  const activeTab = tabs.find((t) => t.key === active)

  return (
    <div className="flex flex-col h-full -m-6">
      <div className="px-6 pt-6 pb-0 flex-shrink-0">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4">Documentation</h1>
        <div className="flex border-b border-gray-200 dark:border-gray-800 overflow-x-auto">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActive(tab.key)}
              className={`px-4 py-2 text-sm font-medium whitespace-nowrap transition-colors ${
                active === tab.key
                  ? 'border-b-2 border-gray-900 dark:border-gray-100 text-gray-900 dark:text-gray-100'
                  : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>
      <div className="flex-1 overflow-y-auto px-6 py-6">
        <div className="max-w-3xl">
          {activeTab?.content}
        </div>
      </div>
    </div>
  )
}
