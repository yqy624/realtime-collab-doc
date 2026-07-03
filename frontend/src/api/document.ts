import axios from "axios";
import { apiBaseUrl } from "./config";

const documentApi = axios.create({
  baseURL: `${apiBaseUrl}/documents`
});

documentApi.interceptors.request.use((config) => {
  const token = sessionStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export interface DocumentPayload {
  id?: number;
  title: string;
  content?: string;
  isPublic?: boolean;
  revision?: number;
}

export const listDocuments = () => documentApi.get("");
export const getDocument = (id: number) => documentApi.get(`/${id}`);
export const createDocument = (payload: DocumentPayload) => documentApi.post("", payload);
export const updateDocument = (id: number, payload: DocumentPayload) => documentApi.put(`/${id}`, payload);
export const deleteDocument = (id: number) => documentApi.delete(`/${id}`);
export const fetchMessages = (id: number) => documentApi.get(`/${id}/messages`);
export const saveDocument = (id: number, payload?: DocumentPayload) => documentApi.post(`/${id}/save`, payload ?? {});
export const getSnapshots = (id: number) => documentApi.get(`/${id}/snapshots`);
export const restoreSnapshot = (id: number, snapshotId: number) => documentApi.post(`/${id}/snapshots/${snapshotId}/restore`);
