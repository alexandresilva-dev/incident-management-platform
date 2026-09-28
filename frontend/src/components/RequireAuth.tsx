import { Navigate, Outlet, useLocation } from 'react-router'
import { useAuth } from '../auth/useAuth.ts'
import { Loading } from './StateViews.tsx'

/** Só deixa passar utilizadores autenticados; os outros vão para o login e voltam depois. */
export default function RequireAuth() {
  const { status } = useAuth()
  const location = useLocation()

  if (status === 'loading') return <Loading label="Checking your session…" />
  if (status === 'anonymous') {
    return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />
  }
  return <Outlet />
}
