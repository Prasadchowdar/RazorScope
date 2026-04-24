import axios, { type AxiosInstance } from "axios";

const BASE = (window as any).__ENV__?.VITE_API_BASE
  ?? import.meta.env.VITE_API_BASE
  ?? "";

export function createBearerClient(accessToken: string): AxiosInstance {
  return axios.create({
    baseURL: BASE,
    headers: { Authorization: `Bearer ${accessToken}` },
    withCredentials: true,
  });
}

export function createApiKeyClient(apiKey: string): AxiosInstance {
  return axios.create({
    baseURL: BASE,
    headers: { "X-Api-Key": apiKey },
  });
}
