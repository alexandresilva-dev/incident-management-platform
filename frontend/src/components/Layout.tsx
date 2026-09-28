import { NavLink, Outlet } from 'react-router'
import { useAuth } from '../auth/useAuth.ts'

export default function Layout() {
  const { user, logout } = useAuth()

  return (
    <>
      <header className="topbar">
        <div className="container topbar__inner">
          <span className="brand">Incident Management</span>
          <nav className="nav">
            <NavLink to="/" end>Dashboard</NavLink>
            <NavLink to="/incidents">Incidents</NavLink>
          </nav>
          <div className="topbar__user">
            <span className="muted" title={user?.email}>{user?.full_name}</span>
            <button className="btn btn--small" onClick={logout}>Sign out</button>
          </div>
        </div>
      </header>
      <main className="container page">
        <Outlet />
      </main>
    </>
  )
}
