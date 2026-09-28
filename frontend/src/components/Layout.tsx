import { NavLink, Outlet } from 'react-router'

export default function Layout() {
  return (
    <>
      <header className="topbar">
        <div className="container topbar__inner">
          <span className="brand">Incident Management</span>
          <nav className="nav">
            <NavLink to="/" end>Dashboard</NavLink>
            <NavLink to="/incidents">Incidents</NavLink>
          </nav>
        </div>
      </header>
      <main className="container page">
        <Outlet />
      </main>
    </>
  )
}
