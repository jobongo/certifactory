import Card, { CardBody } from '../components/ui/Card'

function Section({ title, children }) {
  return (
    <Card className="mb-6">
      <CardBody>
        <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100 mb-3">{title}</h2>
        <div className="text-sm text-gray-700 dark:text-gray-300 space-y-2">{children}</div>
      </CardBody>
    </Card>
  )
}

function Code({ children }) {
  return <code className="px-1.5 py-0.5 bg-gray-100 dark:bg-surface-4 rounded text-xs font-mono">{children}</code>
}

export default function Docs() {
  return (
    <div className="max-w-3xl">
      <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-1">Documentation</h1>
      <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">Guide to using Certifactory</p>

      <Section title="Getting Started">
        <p>Certifactory is a PKI certificate management platform for creating and managing Certificate Authorities, issuing certificates, and handling the full certificate lifecycle.</p>
        <p>After logging in, you'll see the <strong>Dashboard</strong> with an overview of your PKI infrastructure — active CAs, certificates, pending requests, and expiring certificates.</p>
      </Section>

      <Section title="User Roles">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700">
                <th className="text-left py-2 pr-4 font-medium text-gray-500 dark:text-gray-400">Role</th>
                <th className="text-left py-2 font-medium text-gray-500 dark:text-gray-400">Permissions</th>
              </tr>
            </thead>
            <tbody className="text-gray-700 dark:text-gray-300">
              <tr className="border-b border-gray-100 dark:border-gray-800">
                <td className="py-2 pr-4 font-medium">Admin</td>
                <td className="py-2">Full access. Manage users, CAs, certificates, audit logs. Reset passwords. Enable/disable CAs.</td>
              </tr>
              <tr className="border-b border-gray-100 dark:border-gray-800">
                <td className="py-2 pr-4 font-medium">Operator</td>
                <td className="py-2">Create and manage CAs. Issue, approve, deny, and revoke certificates. View audit logs.</td>
              </tr>
              <tr className="border-b border-gray-100 dark:border-gray-800">
                <td className="py-2 pr-4 font-medium">Requester</td>
                <td className="py-2">Request certificates, submit CSRs, and import certificates. Can only view their own certificates.</td>
              </tr>
              <tr>
                <td className="py-2 pr-4 font-medium">Auditor</td>
                <td className="py-2">Read-only access to CAs, certificates, and audit logs. Cannot create or modify anything.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </Section>

      <Section title="Managing Certificate Authorities">
        <p><strong>Create a Root CA:</strong> Go to <strong>Authorities</strong> and click <strong>Create Root CA</strong>. Fill in the CA name, subject fields (Common Name is required), key algorithm, and validity period.</p>
        <p><strong>Create an Intermediate CA:</strong> Navigate to a Root CA's detail page and click <strong>Create Intermediate</strong>. The intermediate CA will be signed by the parent.</p>
        <p><strong>Import a CA:</strong> Click <strong>Import CA</strong> on the Authorities page. Upload a PEM/DER certificate and private key, or a PKCS12 file. The parent CA is auto-detected.</p>
        <p><strong>Disable/Enable:</strong> Admins can disable a CA to prevent it from issuing new certificates. Existing certificates remain valid.</p>
        <p><strong>Auto-Approve:</strong> When enabled on a CA, certificate requests are issued immediately without operator approval.</p>
      </Section>

      <Section title="Issuing Certificates">
        <p><strong>Create Certificate:</strong> Go to <strong>Certificates</strong> and click <strong>New Certificate</strong>. Select the issuing CA, fill in the subject and SANs, choose the type (Server, Client, Custom), and submit.</p>
        <p><strong>Advanced Options:</strong> Toggle "Show Advanced" to set Key Usage, Extended Key Usage, and custom X.509 extensions.</p>
        <p><strong>Submit CSR:</strong> If you already have a Certificate Signing Request, click <strong>Submit CSR</strong>. Paste the PEM content or upload the file, select the issuing CA, and submit.</p>
        <p><strong>Import Certificate:</strong> Click <strong>Import</strong> to import an existing certificate from PEM, DER, or PKCS12. The issuing CA is auto-detected.</p>
      </Section>

      <Section title="Approval Workflow">
        <p>When a CA has <strong>Auto-Approve</strong> disabled, certificate requests enter a <strong>Pending</strong> state.</p>
        <p>Operators and admins can review pending requests on the <strong>Pending Requests</strong> page and approve or deny each one.</p>
        <p>Approved certificates are signed immediately. Denied requests are marked and cannot be resubmitted.</p>
      </Section>

      <Section title="Certificate Lifecycle">
        <p><strong>Download:</strong> Active certificates can be downloaded in PEM, DER, or PKCS12 format from the certificate detail page. PKCS12 exports prompt for a passphrase.</p>
        <p><strong>Revoke:</strong> Operators and admins can revoke an active certificate with a reason (Key Compromise, Superseded, etc.). Revoked certificates appear in the CA's CRL.</p>
        <p><strong>Renew:</strong> Creates a new certificate with the same subject and SANs but a fresh validity period. The old certificate remains active until revoked.</p>
        <p><strong>Expiration:</strong> The dashboard shows certificates expiring within 30 days. Expired certificates are automatically marked by the background scheduler.</p>
      </Section>

      <Section title="CRL & OCSP">
        <p><strong>CRL (Certificate Revocation List):</strong> CRLs are regenerated automatically by the background scheduler based on each CA's configured interval (default: 24 hours). You can also force regeneration from the API.</p>
        <p><strong>OCSP:</strong> The built-in OCSP responder is available at <Code>/api/v1/ocsp/{'<ca_id>'}</Code>. It supports both HTTP GET and POST per RFC 6960. Each CA can be configured to sign OCSP responses with its own key or a dedicated OCSP signing certificate.</p>
      </Section>

      <Section title="API Access">
        <p>Certifactory provides a full REST API. All endpoints are under <Code>/api/v1/</Code>.</p>
        <p><strong>Authentication:</strong> Send <Code>POST /api/v1/auth/login</Code> with <Code>{`{"username": "...", "password": "..."}`}</Code> to receive a JWT token. Include it in subsequent requests as <Code>Authorization: Bearer {'<token>'}</Code>.</p>
        <p><strong>Interactive docs:</strong> The FastAPI auto-generated API documentation is available at <Code>/docs</Code> (Swagger UI) and <Code>/redoc</Code> (ReDoc).</p>
        <div className="mt-3">
          <p className="font-medium text-gray-900 dark:text-gray-100 mb-1">Key endpoints:</p>
          <ul className="list-none space-y-1 text-xs font-mono text-gray-600 dark:text-gray-400">
            <li>POST /api/v1/auth/login — authenticate</li>
            <li>GET /api/v1/cas — list CAs</li>
            <li>POST /api/v1/cas — create root CA</li>
            <li>POST /api/v1/cas/:id/intermediate — create intermediate CA</li>
            <li>GET /api/v1/certificates — list certificates</li>
            <li>POST /api/v1/certificates — request certificate</li>
            <li>POST /api/v1/certificates/csr — submit CSR</li>
            <li>POST /api/v1/certificates/:id/approve — approve pending</li>
            <li>POST /api/v1/certificates/:id/revoke — revoke certificate</li>
            <li>GET /api/v1/certificates/:id/download?format=pem — download</li>
            <li>GET /api/v1/cas/:id/crl — download CRL</li>
            <li>POST /api/v1/ocsp/:ca_id — OCSP responder</li>
          </ul>
        </div>
      </Section>

      <Section title="User Management">
        <p>Admins can manage users from the <strong>Users</strong> page:</p>
        <ul className="list-disc list-inside space-y-1">
          <li><strong>Create User:</strong> Click "Create User" and set username, email, password, and role.</li>
          <li><strong>Change Role:</strong> Use the role dropdown directly in the users table.</li>
          <li><strong>Reset Password:</strong> Click "Reset Password" to set a new password for a user.</li>
          <li><strong>Deactivate:</strong> Soft-deletes the user. They can no longer log in but their audit history is preserved.</li>
        </ul>
      </Section>

      <Section title="Profile & Preferences">
        <p>Access your profile from the user menu in the top-right corner.</p>
        <ul className="list-disc list-inside space-y-1">
          <li><strong>Theme:</strong> Toggle between light and dark mode. Your preference is saved locally.</li>
          <li><strong>Change Password:</strong> Enter your current password and set a new one.</li>
        </ul>
      </Section>
    </div>
  )
}
