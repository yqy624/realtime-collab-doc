import { defineStore } from "pinia";

export interface DocumentItem {
  id: number;
  title: string;
  content: string;
  creatorId: number;
  creatorName?: string;
  isPublic: boolean;
  workspaceId?: number | null;
  folderId?: number | null;
  contentFormat?: string;
  permission?: string;
  revision: number;
  createdAt: string;
  updatedAt: string;
  deletedAt?: string | null;
  deletedBy?: number | null;
  deleteReason?: string;
}

export const useDocumentStore = defineStore("document", {
  state: () => ({
    documents: [] as DocumentItem[],
    currentDocument: null as DocumentItem | null,
    loadingError: ""
  }),
  actions: {
    setDocuments(items: DocumentItem[]) {
      this.documents = items;
    },
    setCurrentDocument(item: DocumentItem | null) {
      this.currentDocument = item;
    },
    setLoadingError(message: string) {
      this.loadingError = message;
    }
  }
});
