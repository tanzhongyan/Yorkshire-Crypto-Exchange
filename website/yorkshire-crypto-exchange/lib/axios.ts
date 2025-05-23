// lib/axios.ts
import axios from "axios";
import { getCookie } from "@/lib/cookies";
const API_GATEWAY_URL = process.env.NEXT_PUBLIC_API_GATEWAY_URL;

const instance = axios.create({
  baseURL: API_GATEWAY_URL,
  withCredentials: true, // This enables cookies to be sent with requests
});

// Add the token from cookie to every request header
instance.interceptors.request.use(
  (config) => {
    const token = getCookie("jwt_token");
    if (token) {
      // Make sure we format the token correctly with Bearer prefix
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    // Handle request errors
    return Promise.reject(error);
  },
);

// Add response interceptor to handle 401 errors
instance.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      console.log(
        "Authentication error - may need to refresh token or redirect to login",
      );
      // Optionally redirect to login page if token is invalid
      // window.location.href = '/login';
    }
    return Promise.reject(error);
  },
);

export default instance;
