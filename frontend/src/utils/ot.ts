export interface TextOperation {
  type: "INSERT" | "DELETE" | "FULL_SYNC";
  position: number;
  length?: number;
  content?: string;
  revision?: number;
  clientId?: string;
  requestId?: string;
}
