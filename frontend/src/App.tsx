import { BrowserRouter, Navigate, Route, Routes } from 'react-router'
import Layout from './components/Layout.tsx'
import IncidentsPage from './pages/IncidentsPage.tsx'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Navigate to="/incidents" replace />} />
          <Route path="incidents" element={<IncidentsPage />} />
          <Route path="*" element={<p className="empty">Page not found.</p>} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
