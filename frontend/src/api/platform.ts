import axios from "axios";
import { apiBaseUrl } from "./config";

const platformApi = axios.create({
  baseURL: apiBaseUrl
});

platformApi.interceptors.request.use((config) => {
  const token = sessionStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export interface WorkspaceItem {
  id: number;
  name: string;
  description: string;
  ownerId: number;
  role: "owner" | "admin" | "member" | "viewer";
  documentCount: number;
  memberCount: number;
  createdAt?: string;
  updatedAt?: string;
}

export interface FolderItem {
  id: number;
  workspaceId: number;
  parentId?: number | null;
  name: string;
  creatorId: number;
  sortOrder: number;
  createdAt?: string;
  updatedAt?: string;
}

export interface WorkspaceMemberItem {
  id: number;
  workspaceId: number;
  userId: number;
  username: string;
  avatarUrl: string;
  role: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface AuditLogItem {
  id: number;
  actorId: number;
  action: string;
  targetType: string;
  targetId?: number | null;
  workspaceId?: number | null;
  documentId?: number | null;
  before: Record<string, unknown>;
  after: Record<string, unknown>;
  metadata: Record<string, unknown>;
  createdAt?: string;
}

export const listWorkspaces = () =>
  platformApi.get<{ success: boolean; data: WorkspaceItem[] }>("/workspaces");

export const createWorkspace = (payload: { name: string; description?: string }) =>
  platformApi.post<{ success: boolean; data: WorkspaceItem }>("/workspaces", payload);

export const listWorkspaceMembers = (workspaceId: number) =>
  platformApi.get<{ success: boolean; data: WorkspaceMemberItem[] }>(
    `/workspaces/${workspaceId}/members`
  );

export const upsertWorkspaceMember = (
  workspaceId: number,
  payload: { username: string; role: string }
) =>
  platformApi.post<{ success: boolean; data: WorkspaceMemberItem }>(
    `/workspaces/${workspaceId}/members`,
    payload
  );

export const listFolders = (workspaceId: number) =>
  platformApi.get<{ success: boolean; data: FolderItem[] }>(
    `/workspaces/${workspaceId}/folders`
  );

export const createFolder = (
  workspaceId: number,
  payload: { name: string; parentId?: number | null }
) =>
  platformApi.post<{ success: boolean; data: FolderItem }>(
    `/workspaces/${workspaceId}/folders`,
    payload
  );

export const listWorkspaceAuditLogs = (workspaceId: number, limit = 100) =>
  platformApi.get<{ success: boolean; data: AuditLogItem[] }>(
    `/audit/workspaces/${workspaceId}/logs`,
    { params: { limit } }
  );
