import { BrowserRouter, Routes, Route } from 'react-router-dom'
import AppLayout from './components/layout/AppLayout'
import ProtectedRoute from './components/shared/ProtectedRoute'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import CAList from './pages/cas/CAList'
import CADetail from './pages/cas/CADetail'
import CertificateList from './pages/certificates/CertificateList'
import CertificateDetail from './pages/certificates/CertificateDetail'
import PendingRequests from './pages/PendingRequests'
import AuditLog from './pages/AuditLog'
import Users from './pages/Users'
import Profile from './pages/Profile'
import Settings from './pages/Settings'
import Docs from './pages/Docs'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/cas" element={<ProtectedRoute roles={['admin', 'operator', 'auditor']}><CAList /></ProtectedRoute>} />
          <Route path="/cas/:id" element={<ProtectedRoute roles={['admin', 'operator', 'auditor']}><CADetail /></ProtectedRoute>} />
          <Route path="/certificates" element={<ProtectedRoute roles={['admin', 'operator', 'auditor']}><CertificateList /></ProtectedRoute>} />
          <Route path="/certificates/:id" element={<CertificateDetail />} />
          <Route path="/pending" element={<ProtectedRoute roles={['admin', 'operator']}><PendingRequests /></ProtectedRoute>} />
          <Route path="/audit" element={<ProtectedRoute roles={['admin', 'auditor', 'operator']}><AuditLog /></ProtectedRoute>} />
          <Route path="/users" element={<ProtectedRoute roles={['admin']}><Users /></ProtectedRoute>} />
          <Route path="/settings" element={<ProtectedRoute roles={['admin']}><Settings /></ProtectedRoute>} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/guide" element={<Docs />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
