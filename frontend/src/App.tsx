import { BrowserRouter, Route, Routes } from 'react-router'
import { AuthProvider } from './auth/AuthProvider.tsx'
import Layout from './components/Layout.tsx'
import RequireAuth from './components/RequireAuth.tsx'
import DashboardPage from './pages/DashboardPage.tsx'
import IncidentDetailPage from './pages/IncidentDetailPage.tsx'
import IncidentsPage from './pages/IncidentsPage.tsx'
import LoginPage from './pages/LoginPage.tsx'
import NewIncidentPage from './pages/NewIncidentPage.tsx'

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="login" element={<LoginPage />} />
          <Route element={<RequireAuth />}>
            <Route element={<Layout />}>
              <Route index element={<DashboardPage />} />
              <Route path="incidents" element={<IncidentsPage />} />
              <Route path="incidents/new" element={<NewIncidentPage />} />
              <Route path="incidents/:id" element={<IncidentDetailPage />} />
              <Route path="*" element={<p className="empty">Page not found.</p>} />
            </Route>
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
