import axios from "axios";
import { apiBaseUrl } from "./config";

const documentApi = axios.create({
  baseURL: `${apiBaseUrl}/documents`
});

// 统一附加 JWT
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

// ===== 分享 =====
export const getShareInfo = (id: number) => documentApi.get(`/${id}/share/info`);
export const createShareLink = (id: number) => documentApi.post(`/${id}/share`);
export const updateSharePermission = (id: number, permission: "view" | "edit") =>
  documentApi.put(`/${id}/share`, { permission });
export const revokeShare = (id: number) => documentApi.delete(`/${id}/share`);
export const shareToUser = (id: number, username: string, permission: "view" | "edit") =>
  documentApi.post(`/${id}/share/users`, { username, permission });
export const removeShareUser = (id: number, targetUserId: number) =>
  documentApi.delete(`/${id}/share/users/${targetUserId}`);
// 分享链接访问（后端路由不带 /documents 前缀）
export const accessShareToken = (token: string) => axios.get(`${apiBaseUrl}/share/${token}`);
