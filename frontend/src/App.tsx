import { BrowserRouter, Navigate, Route, Routes } from 'react-router'
import Layout from './components/Layout.tsx'
import IncidentDetailPage from './pages/IncidentDetailPage.tsx'
import IncidentsPage from './pages/IncidentsPage.tsx'
import NewIncidentPage from './pages/NewIncidentPage.tsx'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Navigate to="/incidents" replace />} />
          <Route path="incidents" element={<IncidentsPage />} />
          <Route path="incidents/new" element={<NewIncidentPage />} />
          <Route path="incidents/:id" element={<IncidentDetailPage />} />
          <Route path="*" element={<p className="empty">Page not found.</p>} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
