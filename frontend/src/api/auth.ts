import axios from "axios";
import { apiBaseUrl } from "./config";

const authApi = axios.create({
  baseURL: `${apiBaseUrl}/auth`
});

export interface AuthPayload {
  username: string;
  password: string;
  email?: string;
}

export const registerApi = (payload: AuthPayload) => authApi.post("/register", payload);
export const loginApi = (payload: AuthPayload) => authApi.post("/login", payload);
