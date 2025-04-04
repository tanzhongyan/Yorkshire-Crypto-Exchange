// components/AuthProvider.tsx
"use client"

import React, { createContext, useContext, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { jwtDecode } from 'jwt-decode'
import { setCookie, getCookie, removeCookie } from '@/lib/cookies'

type AuthContextType = {
  token: string | null;
  isAuthenticated: boolean;
  login: (token: string) => void;
  logout: () => void;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [token, setToken] = useState<string | null>(null);
  const router = useRouter();

  const login = (newToken: string, expirySeconds = 604800) => {
    setCookie('jwt_token', newToken, expirySeconds);
    setCookie('userId', getUserIdFromToken(newToken) || '', expirySeconds);
    setToken(newToken);
  };

  const logout = () => {
    removeCookie('jwt_token');
    removeCookie('userId');
    setToken(null);
    router.push('/login');
  };

  // Extract userId from token
  const getUserIdFromToken = (token: string): string | null => {
    try {
      const decoded: any = jwtDecode(token);
      return decoded.userId || decoded.sub || null;
    } catch (e) {
      return null;
    }
  };

  // Function to validate token
  const validateToken = (token: string) => {
    try {
      const payload: any = jwtDecode(token);
      return payload.exp * 1000 > Date.now();
    } catch (e) {
      return false;
    }
  };

  useEffect(() => {
    // Initial token check
    const storedToken = getCookie('jwt_token');
    
    if (storedToken) {
      if (validateToken(storedToken)) {
        setToken(storedToken);
      } else {
        logout();
      }
    }
  }, [router]);

  const isAuthenticated = !!token;

  return (
    <AuthContext.Provider value={{ token, isAuthenticated, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}