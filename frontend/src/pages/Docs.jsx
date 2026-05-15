import { useState } from 'react'

function Code({ children }) {
  return <code className="px-1.5 py-0.5 bg-gray-100 dark:bg-surface-4 rounded text-xs font-mono text-gray-800 dark:text-gray-200">{children}</code>
}

function CodeBlock({ children }) {
  return (
    <pre className="bg-gray-100 dark:bg-surface-4 rounded-lg p-4 text-xs font-mono text-gray-800 dark:text-gray-200 overflow-x-auto whitespace-pre">
      {children}
    </pre>
  )
}

function H2({ children }) {
  return <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100 mt-6 mb-3 first:mt-0">{children}</h2>
}

function H3({ children }) {
  return <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mt-4 mb-2">{children}</h3>
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
      <P>Certifactory is a platform for managing your organization's digital certificates. It lets you create Certificate Authorities (CAs), issue SSL/TLS certificates, track their lifecycle, and handle revocation — all from a web interface or REST API.</P>

      <H3>Logging In</H3>
      <P>Open Certifactory in your browser and enter your username and password. If this is your first time, ask your administrator for credentials. The default admin account is <Code>admin</Code> / <Code>admin</Code> — change this password immediately after first login.</P>

      <H3>Navigating the Interface</H3>
      <P>The left sidebar contains the main navigation:</P>
      <ul className="list-disc list-inside space-y-1 mb-3">
        <Li><strong>Dashboard</strong> — Overview of your PKI: active CAs, certificates, pending requests, and expiring certificates.</Li>
        <Li><strong>Authorities</strong> — Manage Certificate Authorities (Root CAs and Intermediate CAs).</Li>
        <Li><strong>Certificates</strong> — View, create, and manage certificates.</Li>
        <Li><strong>Pending Requests</strong> — Review and approve or deny certificate requests (Operators and Admins only).</Li>
        <Li><strong>Audit Log</strong> — See a record of every action taken in the system.</Li>
        <Li><strong>Users</strong> — Manage user accounts (Admins only).</Li>
      </ul>

      <H3>Your Profile</H3>
      <P>Click your name in the top-right corner and select <strong>Profile</strong> to:</P>
      <ul className="list-disc list-inside space-y-1 mb-3">
        <Li>View your account information</Li>
        <Li>Switch between light and dark mode</Li>
        <Li>Change your password</Li>
        <Li>Create and manage API tokens for automated access</Li>
      </ul>

      <H3>What is a Certificate Authority (CA)?</H3>
      <P>A Certificate Authority is a trusted entity that issues digital certificates. Think of it like a notary — it vouches that a certificate belongs to who it claims. In Certifactory, you can create your own CAs to issue certificates for your servers, applications, and users.</P>

      <H3>What is a Certificate?</H3>
      <P>A digital certificate is an electronic document that proves the identity of a server, device, or person. When you visit a website with HTTPS, your browser checks the site's certificate to make sure it's legitimate. Certifactory helps you create and manage these certificates.</P>
    </div>
  )
}

function AuthoritiesGuide() {
  return (
    <div>
      <H2>Certificate Authorities</H2>
      <P>Certificate Authorities (CAs) are the foundation of your PKI. They sign and issue certificates. Certifactory supports a flexible hierarchy — you can have a simple single CA or a multi-tier structure.</P>

      <H3>Creating a Root CA</H3>
      <P>A Root CA is the top-level authority in your certificate chain. To create one:</P>
      <ol className="list-decimal list-inside space-y-1 mb-3">
        <Li>Go to <strong>Authorities</strong> in the sidebar.</Li>
        <Li>Click <strong>Create Root CA</strong>.</Li>
        <Li>Enter a <strong>CA Name</strong> (e.g., "My Organization Root CA").</Li>
        <Li>Fill in the <strong>Common Name</strong> (CN) — this identifies the CA (e.g., "My Org Root CA").</Li>
        <Li>Optionally fill in Organization, Country, etc.</Li>
        <Li>Choose a <strong>Key Algorithm</strong> — RSA 2048 is a safe default. Use RSA 4096 or EC P-256 for higher security.</Li>
        <Li>Set the <strong>Validity</strong> — Root CAs typically last 10-20 years (3650-7300 days).</Li>
        <Li>Click <strong>Create CA</strong>.</Li>
      </ol>
      <Note>The Root CA's private key is encrypted and stored securely. Keep your Certifactory master key safe — it protects all stored private keys.</Note>

      <H3>Creating an Intermediate CA</H3>
      <P>Intermediate CAs sit between the Root CA and end-entity certificates. This is a best practice for production environments because if an intermediate is compromised, the root remains safe.</P>
      <ol className="list-decimal list-inside space-y-1 mb-3">
        <Li>Go to the Root CA's detail page (click it in the list).</Li>
        <Li>Click <strong>Create Intermediate</strong>.</Li>
        <Li>Fill in the details (same as Root CA, but validity is usually shorter — e.g., 5 years / 1825 days).</Li>
        <Li>The intermediate will be automatically signed by the parent CA.</Li>
      </ol>

      <H3>Importing an Existing CA</H3>
      <P>If you already have a CA certificate and private key, you can import them:</P>
      <ol className="list-decimal list-inside space-y-1 mb-3">
        <Li>Click <strong>Import CA</strong> on the Authorities page.</Li>
        <Li>Choose the format — PEM/DER (separate cert and key files) or PKCS12/PFX (single bundled file).</Li>
        <Li>Upload the files and enter a name.</Li>
        <Li>Certifactory will automatically detect the parent CA if it exists in the system.</Li>
      </ol>
      <Note>A private key is required when importing a CA — without it, the CA cannot sign new certificates.</Note>

      <H3>CA Settings</H3>
      <ul className="list-disc list-inside space-y-1 mb-3">
        <Li><strong>Auto-Approve:</strong> When enabled, certificate requests are signed immediately. When disabled, requests go to the Pending queue for operator review. Use auto-approve for lab/dev environments and disable it for production.</Li>
        <Li><strong>OCSP Signing Mode:</strong> Choose whether OCSP responses are signed by the CA key directly or by a dedicated OCSP signing certificate.</Li>
        <Li><strong>Disable/Enable:</strong> Disabling a CA prevents it from issuing new certificates. Existing certificates remain valid.</Li>
      </ul>

      <H3>Downloading CA Certificates</H3>
      <P>On the CA detail page, you can download:</P>
      <ul className="list-disc list-inside space-y-1 mb-3">
        <Li><strong>Certificate PEM</strong> — The CA certificate file. Distribute this to systems that need to trust certificates issued by this CA.</Li>
        <Li><strong>Full Chain</strong> — The CA certificate plus all parent certificates. Use this when a client needs the complete chain of trust.</Li>
      </ul>
    </div>
  )
}

function CertificatesGuide() {
  return (
    <div>
      <H2>Certificates</H2>

      <H3>Creating a Certificate</H3>
      <P>To create a new certificate (the server generates the key pair for you):</P>
      <ol className="list-decimal list-inside space-y-1 mb-3">
        <Li>Go to <strong>Certificates</strong> and click <strong>New Certificate</strong>.</Li>
        <Li>Select the <strong>Issuing CA</strong> that will sign this certificate.</Li>
        <Li>Enter the <strong>Common Name</strong> — usually the server's hostname (e.g., <Code>webserver.example.com</Code>).</Li>
        <Li>Add <strong>Subject Alternative Names (SANs)</strong> — these are additional hostnames or IPs the certificate covers. Click "Add SAN" for each one. For example, add <Code>DNS: www.example.com</Code> and <Code>DNS: example.com</Code>.</Li>
        <Li>Choose the <strong>Type</strong>: Server (for web servers, APIs), Client (for mutual TLS), or Custom.</Li>
        <Li>Set the <strong>Validity</strong> in days (e.g., 365 for one year).</Li>
        <Li>Click <strong>Create Certificate</strong>.</Li>
      </ol>
      <P>If the CA has auto-approve enabled, the certificate is issued immediately. Otherwise, it enters the Pending queue.</P>

      <H3>Submitting a CSR</H3>
      <P>If you generated a key pair yourself (e.g., with OpenSSL) and have a Certificate Signing Request (CSR), you can submit it for signing:</P>
      <ol className="list-decimal list-inside space-y-1 mb-3">
        <Li>Click <strong>Submit CSR</strong> on the Certificates page.</Li>
        <Li>Paste the CSR content (starts with <Code>-----BEGIN CERTIFICATE REQUEST-----</Code>) or upload the file.</Li>
        <Li>Select the <strong>Issuing CA</strong>.</Li>
        <Li>Set the validity period.</Li>
        <Li>Click <strong>Submit CSR</strong>.</Li>
      </ol>
      <Note>When you submit a CSR, your private key stays with you — only the public key is sent to Certifactory. This is the most secure method.</Note>

      <H3>How to Generate a CSR with OpenSSL</H3>
      <P>If you need to generate a CSR on your server, run:</P>
      <CodeBlock>{`# Generate a private key and CSR
openssl req -new -newkey rsa:2048 -nodes \\
  -keyout server.key -out server.csr \\
  -subj "/CN=myserver.example.com/O=My Organization/C=US"

# View the CSR contents to verify
openssl req -in server.csr -text -noout`}</CodeBlock>
      <P>Copy the contents of <Code>server.csr</Code> and paste them into Certifactory's Submit CSR form. Keep <Code>server.key</Code> safe — you'll need it when installing the certificate.</P>

      <H3>Downloading Certificates</H3>
      <P>Go to the certificate detail page and use the download buttons:</P>
      <ul className="list-disc list-inside space-y-1 mb-3">
        <Li><strong>PEM</strong> — Standard text format. Used by Apache, Nginx, and most Linux applications.</Li>
        <Li><strong>DER</strong> — Binary format. Used by some Java applications.</Li>
        <Li><strong>PKCS12</strong> — Bundled format containing both the certificate and private key. Used by Windows (IIS), Java keystores, and browsers. You'll be prompted for a passphrase to protect the file.</Li>
      </ul>

      <H3>Revoking a Certificate</H3>
      <P>If a certificate's private key has been compromised or the certificate is no longer needed:</P>
      <ol className="list-decimal list-inside space-y-1 mb-3">
        <Li>Go to the certificate detail page.</Li>
        <Li>Click <strong>Revoke</strong>.</Li>
        <Li>Select a reason (Key Compromise, Superseded, Cessation of Operation, etc.).</Li>
        <Li>Confirm the revocation.</Li>
      </ol>
      <P>Revoked certificates are added to the CA's Certificate Revocation List (CRL) and will show as revoked in OCSP responses.</P>

      <H3>Renewing a Certificate</H3>
      <P>Click <strong>Renew</strong> on an active certificate's detail page. This creates a new certificate with the same subject and SANs but a fresh validity period. The old certificate remains active until you revoke it.</P>

      <H3>Importing Certificates</H3>
      <P>To import an existing certificate:</P>
      <ol className="list-decimal list-inside space-y-1 mb-3">
        <Li>Click <strong>Import</strong> on the Certificates page.</Li>
        <Li>Upload the certificate file (PEM, DER, or PKCS12).</Li>
        <Li>Optionally upload the private key.</Li>
        <Li>Certifactory will auto-detect the issuing CA. If it can't find a match, select the CA manually.</Li>
      </ol>
    </div>
  )
}

function ApprovalGuide() {
  return (
    <div>
      <H2>Approval Workflow</H2>
      <P>When a CA has <strong>Auto-Approve</strong> disabled, certificate requests require manual approval before they are signed.</P>

      <H3>How It Works</H3>
      <ol className="list-decimal list-inside space-y-1 mb-3">
        <Li>A user (Requester, Operator, or Admin) creates a certificate request.</Li>
        <Li>The request enters a <strong>Pending</strong> state — the certificate is not yet signed.</Li>
        <Li>An Operator or Admin reviews the request on the <strong>Pending Requests</strong> page.</Li>
        <Li>They click <strong>Approve</strong> to sign and issue the certificate, or <strong>Deny</strong> to reject it.</Li>
      </ol>

      <H3>Reviewing Requests</H3>
      <P>Each pending request shows:</P>
      <ul className="list-disc list-inside space-y-1 mb-3">
        <Li>The subject (who/what the certificate is for)</Li>
        <Li>Subject Alternative Names (additional hostnames/IPs)</Li>
        <Li>Who requested it and when</Li>
        <Li>The certificate type (Server, Client, Custom)</Li>
      </ul>
      <P>Review these details carefully before approving. Make sure the requester is authorized to get a certificate for the listed domains/IPs.</P>

      <H3>When to Use Approval Workflow</H3>
      <ul className="list-disc list-inside space-y-1 mb-3">
        <Li><strong>Production CAs:</strong> Always require approval to maintain control over which certificates are issued.</Li>
        <Li><strong>Lab/Dev CAs:</strong> Auto-approve is fine for development environments where speed matters more than oversight.</Li>
      </ul>
    </div>
  )
}

function UsersGuide() {
  return (
    <div>
      <H2>Users & Roles</H2>

      <H3>Roles</H3>
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
              <td className="py-2 pr-4">Everything — manage users, CAs, certificates, audit logs, reset passwords, enable/disable CAs</td>
              <td className="py-2">—</td>
            </tr>
            <tr className="border-b border-gray-100 dark:border-gray-800">
              <td className="py-2 pr-4 font-medium">Operator</td>
              <td className="py-2 pr-4">Create/manage CAs, issue/approve/deny/revoke certificates, view audit logs</td>
              <td className="py-2">Manage users, reset passwords</td>
            </tr>
            <tr className="border-b border-gray-100 dark:border-gray-800">
              <td className="py-2 pr-4 font-medium">Requester</td>
              <td className="py-2 pr-4">Request certificates, submit CSRs, import certificates, view own certificates</td>
              <td className="py-2">Manage CAs, approve/deny requests, view other users' certificates, access audit logs</td>
            </tr>
            <tr>
              <td className="py-2 pr-4 font-medium">Auditor</td>
              <td className="py-2 pr-4">View CAs, certificates, and full audit logs (read-only)</td>
              <td className="py-2">Create, modify, or delete anything</td>
            </tr>
          </tbody>
        </table>
      </div>

      <H3>Managing Users (Admin Only)</H3>
      <P>Go to <strong>Users</strong> in the sidebar to:</P>
      <ul className="list-disc list-inside space-y-1 mb-3">
        <Li><strong>Create User:</strong> Click "Create User", enter username, email, password, and select a role.</Li>
        <Li><strong>Change Role:</strong> Use the role dropdown directly in the users table row.</Li>
        <Li><strong>Reset Password:</strong> Click "Reset Password" to set a new temporary password for a user.</Li>
        <Li><strong>Deactivate:</strong> Click "Deactivate" to disable a user's account. They can no longer log in, but their audit history is preserved.</Li>
      </ul>

      <H3>API Tokens</H3>
      <P>Users can create API tokens for programmatic access from their <strong>Profile</strong> page. Tokens:</P>
      <ul className="list-disc list-inside space-y-1 mb-3">
        <Li>Have the same permissions as the user who created them</Li>
        <Li>Are long-lived (no expiration) — revoke them when no longer needed</Li>
        <Li>Are shown only once at creation — copy and store them securely</Li>
        <Li>Start with <Code>cf_</Code> and are used as Bearer tokens in API requests</Li>
      </ul>
    </div>
  )
}

function APIGuide() {
  return (
    <div>
      <H2>API Reference</H2>
      <P>Certifactory provides a complete REST API. For interactive documentation with try-it-out functionality, visit <a href="/docs" className="underline text-gray-900 dark:text-gray-100">/docs</a> (Swagger UI).</P>

      <H3>Authentication</H3>
      <P>Two authentication methods are supported:</P>
      <P><strong>1. JWT Token</strong> (for interactive sessions):</P>
      <CodeBlock>{`# Login and get a token
curl -X POST https://your-server/api/v1/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{"username": "admin", "password": "admin"}'

# Response:
# {"access_token": "eyJ...", "refresh_token": "eyJ...", "token_type": "bearer"}

# Use the token in subsequent requests
curl https://your-server/api/v1/cas \\
  -H "Authorization: Bearer eyJ..."`}</CodeBlock>

      <P><strong>2. API Token</strong> (for scripts and automation):</P>
      <CodeBlock>{`# Create a token from the Profile page, then use it:
curl https://your-server/api/v1/cas \\
  -H "Authorization: Bearer cf_a1b2c3d4..."`}</CodeBlock>

      <H3>Certificate Authorities</H3>
      <CodeBlock>{`# List all CAs
curl https://your-server/api/v1/cas \\
  -H "Authorization: Bearer <token>"

# Create a Root CA
curl -X POST https://your-server/api/v1/cas \\
  -H "Authorization: Bearer <token>" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "My Root CA",
    "subject": {"CN": "My Root CA", "O": "My Org", "C": "US"},
    "key_algorithm": "RSA",
    "key_size": 2048,
    "validity_days": 3650,
    "auto_approve": true
  }'

# Create an Intermediate CA under a Root CA
curl -X POST https://your-server/api/v1/cas/<root_ca_id>/intermediate \\
  -H "Authorization: Bearer <token>" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "My Intermediate CA",
    "subject": {"CN": "My Intermediate CA", "O": "My Org", "C": "US"},
    "key_algorithm": "RSA",
    "key_size": 2048,
    "validity_days": 1825
  }'

# Get CA certificate chain
curl https://your-server/api/v1/cas/<ca_id>/chain \\
  -H "Authorization: Bearer <token>"`}</CodeBlock>

      <H3>Certificates</H3>
      <CodeBlock>{`# Request a new certificate
curl -X POST https://your-server/api/v1/certificates \\
  -H "Authorization: Bearer <token>" \\
  -H "Content-Type: application/json" \\
  -d '{
    "ca_id": "<ca_id>",
    "subject": {"CN": "webserver.example.com"},
    "san": [
      {"type": "DNS", "value": "webserver.example.com"},
      {"type": "DNS", "value": "www.example.com"},
      {"type": "IP", "value": "192.168.1.100"}
    ],
    "type": "server",
    "key_algorithm": "RSA",
    "key_size": 2048,
    "validity_days": 365
  }'

# Submit a CSR
curl -X POST https://your-server/api/v1/certificates/csr \\
  -H "Authorization: Bearer <token>" \\
  -H "Content-Type: application/json" \\
  -d '{
    "ca_id": "<ca_id>",
    "csr_pem": "-----BEGIN CERTIFICATE REQUEST-----\\nMIIC...",
    "type": "server",
    "validity_days": 365
  }'

# Download certificate (PEM format)
curl https://your-server/api/v1/certificates/<cert_id>/download?format=pem \\
  -H "Authorization: Bearer <token>" -o cert.pem

# Download certificate (PKCS12 format with passphrase)
curl "https://your-server/api/v1/certificates/<cert_id>/download?format=pkcs12&passphrase=mypassword" \\
  -H "Authorization: Bearer <token>" -o cert.p12

# Approve a pending certificate
curl -X POST https://your-server/api/v1/certificates/<cert_id>/approve \\
  -H "Authorization: Bearer <token>"

# Revoke a certificate
curl -X POST https://your-server/api/v1/certificates/<cert_id>/revoke \\
  -H "Authorization: Bearer <token>" \\
  -H "Content-Type: application/json" \\
  -d '{"reason": "key_compromise"}'`}</CodeBlock>

      <H3>CRL & OCSP</H3>
      <CodeBlock>{`# Download CRL for a CA (no auth required)
curl https://your-server/api/v1/cas/<ca_id>/crl -o crl.pem

# Force CRL regeneration
curl -X POST https://your-server/api/v1/cas/<ca_id>/crl/generate \\
  -H "Authorization: Bearer <token>"

# OCSP query (using OpenSSL)
openssl ocsp -issuer ca.pem -cert server.pem \\
  -url https://your-server/api/v1/ocsp/<ca_id> -resp_text`}</CodeBlock>

      <H3>Users & Tokens</H3>
      <CodeBlock>{`# Create a user (admin only)
curl -X POST https://your-server/api/v1/users \\
  -H "Authorization: Bearer <token>" \\
  -H "Content-Type: application/json" \\
  -d '{
    "username": "operator1",
    "email": "op1@example.com",
    "password": "securepassword",
    "role": "operator"
  }'

# Create an API token
curl -X POST https://your-server/api/v1/tokens \\
  -H "Authorization: Bearer <token>" \\
  -H "Content-Type: application/json" \\
  -d '{"name": "CI Pipeline"}'
# Response includes the token value — save it immediately

# List your API tokens
curl https://your-server/api/v1/tokens \\
  -H "Authorization: Bearer <token>"

# Revoke an API token
curl -X DELETE https://your-server/api/v1/tokens/<token_id> \\
  -H "Authorization: Bearer <token>"`}</CodeBlock>
    </div>
  )
}

function Glossary() {
  return (
    <div>
      <H2>Glossary</H2>
      <dl className="space-y-3 text-sm">
        <div>
          <dt className="font-semibold text-gray-900 dark:text-gray-100">CA (Certificate Authority)</dt>
          <dd className="text-gray-700 dark:text-gray-300 mt-0.5">A trusted entity that issues and signs digital certificates. A CA vouches for the identity of the certificate holder.</dd>
        </div>
        <div>
          <dt className="font-semibold text-gray-900 dark:text-gray-100">Root CA</dt>
          <dd className="text-gray-700 dark:text-gray-300 mt-0.5">The top-level CA in a certificate chain. It is self-signed (it trusts itself). All trust in a PKI chain flows from the Root CA.</dd>
        </div>
        <div>
          <dt className="font-semibold text-gray-900 dark:text-gray-100">Intermediate CA</dt>
          <dd className="text-gray-700 dark:text-gray-300 mt-0.5">A CA that is signed by a Root CA (or another Intermediate). Used to add a layer of security — if compromised, the Root CA is unaffected.</dd>
        </div>
        <div>
          <dt className="font-semibold text-gray-900 dark:text-gray-100">CSR (Certificate Signing Request)</dt>
          <dd className="text-gray-700 dark:text-gray-300 mt-0.5">A message sent to a CA to request a signed certificate. Contains the public key and identity information. The private key is NOT included in the CSR — it stays on your server.</dd>
        </div>
        <div>
          <dt className="font-semibold text-gray-900 dark:text-gray-100">SAN (Subject Alternative Name)</dt>
          <dd className="text-gray-700 dark:text-gray-300 mt-0.5">Additional identities (hostnames, IP addresses, emails) that a certificate covers. Modern browsers require SANs — the Common Name alone is not sufficient.</dd>
        </div>
        <div>
          <dt className="font-semibold text-gray-900 dark:text-gray-100">PEM</dt>
          <dd className="text-gray-700 dark:text-gray-300 mt-0.5">A text-based file format for certificates and keys. Starts with "-----BEGIN CERTIFICATE-----". The most common format on Linux.</dd>
        </div>
        <div>
          <dt className="font-semibold text-gray-900 dark:text-gray-100">DER</dt>
          <dd className="text-gray-700 dark:text-gray-300 mt-0.5">A binary file format for certificates. Same data as PEM but not human-readable. Used by some Java and Windows applications.</dd>
        </div>
        <div>
          <dt className="font-semibold text-gray-900 dark:text-gray-100">PKCS12 / PFX</dt>
          <dd className="text-gray-700 dark:text-gray-300 mt-0.5">A file format that bundles a certificate with its private key (and optionally the CA chain) in a single password-protected file. Common on Windows and in Java keystores.</dd>
        </div>
        <div>
          <dt className="font-semibold text-gray-900 dark:text-gray-100">CRL (Certificate Revocation List)</dt>
          <dd className="text-gray-700 dark:text-gray-300 mt-0.5">A list published by a CA containing the serial numbers of certificates that have been revoked before their expiration date.</dd>
        </div>
        <div>
          <dt className="font-semibold text-gray-900 dark:text-gray-100">OCSP (Online Certificate Status Protocol)</dt>
          <dd className="text-gray-700 dark:text-gray-300 mt-0.5">A protocol for checking whether a specific certificate has been revoked, in real time. Faster and more efficient than downloading a full CRL.</dd>
        </div>
        <div>
          <dt className="font-semibold text-gray-900 dark:text-gray-100">Key Usage</dt>
          <dd className="text-gray-700 dark:text-gray-300 mt-0.5">Certificate extension that defines what operations the key can be used for (e.g., digital signatures, key encipherment, certificate signing).</dd>
        </div>
        <div>
          <dt className="font-semibold text-gray-900 dark:text-gray-100">Extended Key Usage (EKU)</dt>
          <dd className="text-gray-700 dark:text-gray-300 mt-0.5">Specifies the purpose of the certificate more precisely: TLS Web Server Authentication, TLS Web Client Authentication, Code Signing, Email Protection, etc.</dd>
        </div>
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
