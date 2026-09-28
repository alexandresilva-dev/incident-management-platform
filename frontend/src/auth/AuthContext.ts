import { createContext } from 'react'
import type { User } from '../api/types.ts'

export interface AuthState {
  status: 'loading' | 'authenticated' | 'anonymous'
  user: User | null
}

export interface AuthContextValue extends AuthState {
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}

export const AuthContext = createContext<AuthContextValue | null>(null)
