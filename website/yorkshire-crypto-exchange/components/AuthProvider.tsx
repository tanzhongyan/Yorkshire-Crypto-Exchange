// components/AuthProvider.tsx
"use client"

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { jwtDecode } from 'jwt-decode'
import { setCookie, getCookie, removeCookie } from '@/lib/cookies'

type AuthContextType = {
  token: string | null;
  isAuthenticated: boolean;
  isInitializing: boolean; // Add this state
  login: (token: string) => void;
  logout: () => void;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [token, setToken] = useState<string | null>(null);
  const [isInitializing, setIsInitializing] = useState(true); // Add loading state
  const router = useRouter();

  const login = useCallback((newToken: string, expirySeconds = 604800) => {
    setCookie('jwt_token', newToken, expirySeconds);
    setCookie('userId', getUserIdFromToken(newToken) || '', expirySeconds);
    setToken(newToken);
  }, []);

  const logout = useCallback(() => {
    removeCookie('jwt_token');
    removeCookie('userId');
    setToken(null);
    router.push('/login');
  }, [router]);

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
    // Add a small delay to ensure cookies are loaded
    const checkToken = () => {
      const storedToken = getCookie('jwt_token');
      
      if (storedToken) {
        if (validateToken(storedToken)) {
          setToken(storedToken);
        }
      }
      setIsInitializing(false);
    };

    // Delay the check slightly to allow cookies to load
    setTimeout(checkToken, 100);
    
    // Can also implement a retry mechanism if needed
    // let attempts = 0;
    // const maxAttempts = 5;
    // const checkInterval = setInterval(() => {
    //   const storedToken = getCookie('jwt_token');
    //   attempts++;
    //   
    //   if (storedToken) {
    //     clearInterval(checkInterval);
    //     if (validateToken(storedToken)) {
    //       setToken(storedToken);
    //     }
    //     setIsInitializing(false);
    //   } else if (attempts >= maxAttempts) {
    //     clearInterval(checkInterval);
    //     setIsInitializing(false);
    //   }
    // }, 100);
    // 
    // return () => clearInterval(checkInterval);
    
  }, []); // No dependency on router

  const isAuthenticated = !!token;

  return (
    <AuthContext.Provider value={{ 
      token, 
      isAuthenticated, 
      isInitializing, // Expose loading state
      login, 
      logout 
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}