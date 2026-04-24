import axios from "axios";

const BASE = (window as any).__ENV__?.VITE_API_BASE
  ?? import.meta.env.VITE_API_BASE
  ?? "";

export interface AuthResponse {
  access_token: string;
  token_type: string;
  merchant_id: string;
  user_id: string;
  name: string;
  email: string;
}

export interface RegisterResponse extends AuthResponse {
  api_key: string;
  webhook_secret: string;
  webhook_url: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  company_name: string;
  name: string;
  email: string;
  password: string;
  razorpay_key_id?: string;
}

export async function login(req: LoginRequest): Promise<AuthResponse> {
  const { data } = await axios.post(`${BASE}/api/v1/auth/login`, req, {
    withCredentials: true,
  });
  return data;
}

export async function register(req: RegisterRequest): Promise<RegisterResponse> {
  const { data } = await axios.post(`${BASE}/api/v1/auth/register`, req, {
    withCredentials: true,
  });
  return data;
}

export async function refreshAccessToken(): Promise<string> {
  const { data } = await axios.post(
    `${BASE}/api/v1/auth/refresh`,
    {},
    { withCredentials: true },
  );
  return data.access_token;
}

export async function logout(): Promise<void> {
  await axios.post(`${BASE}/api/v1/auth/logout`, {}, { withCredentials: true });
}
