"use client"

import { useAuth } from './AuthProvider'
import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { getCookie } from '@/lib/cookies'

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth()
  const router = useRouter()
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    const storedToken = getCookie('jwt_token');
    if (!storedToken || !isAuthenticated) {
      router.replace('/login');
    } else {
      setChecking(false);
    }
  }, [isAuthenticated, router])

  if (checking) return null

  return children
}