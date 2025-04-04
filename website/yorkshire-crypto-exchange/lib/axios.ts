// lib/axios.ts
import axios from 'axios'
import { getCookie } from '@/lib/cookies'

const instance = axios.create({
  baseURL: "http://localhost:8000",
  withCredentials: true, // This enables cookies to be sent with requests
});

// Add the token from cookie to every request header
instance.interceptors.request.use((config) => {
  const token = getCookie('jwt_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default instance;