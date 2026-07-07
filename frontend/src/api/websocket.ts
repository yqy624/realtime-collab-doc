import { Client, type IMessage } from "@stomp/stompjs";
import { wsBaseUrl } from "./config";

export interface WsHandlers {
  onConnect?: () => void;
  onDocumentMessage?: (payload: unknown) => void;
  onPresenceMessage?: (payload: unknown) => void;
  onChatMessage?: (payload: unknown) => void;
  onMentionMessage?: (payload: unknown) => void;
  onErrorMessage?: (payload: unknown) => void;
  onDisconnect?: () => void;
  onWebSocketError?: (error: unknown) => void;
}

export class CollabSocket {
  private client: Client | null = null;
  private connected = false;
  private pendingPayloads: unknown[] = [];

  connect(documentId: number, handlers: WsHandlers) {
    const token = sessionStorage.getItem("token") ?? "";
    this.connected = false;
    this.pendingPayloads = [];
    this.client = new Client({
      brokerURL: `${wsBaseUrl}?token=${encodeURIComponent(token)}`,
      connectHeaders: {
        Authorization: `Bearer ${token}`,
        token
      },
      reconnectDelay: 3000,
      heartbeatIncoming: 5000,
      heartbeatOutgoing: 5000
    });

    this.client.onConnect = () => {
      this.connected = true;
      this.subscribe(`/topic/document/${documentId}`, handlers.onDocumentMessage);
      this.subscribe(`/topic/presence/${documentId}`, handlers.onPresenceMessage);
      this.subscribe(`/topic/chat/${documentId}`, handlers.onChatMessage);
      this.subscribe(`/user/queue/mentions`, handlers.onMentionMessage);
      this.subscribe(`/user/queue/errors`, handlers.onErrorMessage);
      handlers.onConnect?.();
      this.flushPendingPayloads();
    };

    this.client.onDisconnect = () => {
      this.connected = false;
      handlers.onDisconnect?.();
    };

    this.client.onWebSocketClose = () => {
      this.connected = false;
      handlers.onDisconnect?.();
    };

    this.client.onWebSocketError = (evt) => {
      handlers.onWebSocketError?.(evt);
    };

    this.client.activate();
  }

  disconnect() {
    this.pendingPayloads = [];
    this.connected = false;
    this.client?.deactivate();
    this.client = null;
  }

  send(payload: unknown) {
    if (!this.client) {
      return;
    }

    if (!this.connected) {
      this.pendingPayloads.push(payload);
      return;
    }

    this.client.publish({
      destination: "/app/collaboration",
      body: JSON.stringify(payload)
    });
  }

  private flushPendingPayloads() {
    if (!this.client || !this.connected || this.pendingPayloads.length === 0) {
      return;
    }

    for (const payload of this.pendingPayloads) {
      this.client.publish({
        destination: "/app/collaboration",
        body: JSON.stringify(payload)
      });
    }
    this.pendingPayloads = [];
  }

  private subscribe(destination: string, handler?: (payload: unknown) => void) {
    this.client?.subscribe(destination, (message: IMessage) => {
      handler?.(JSON.parse(message.body));
    });
  }
}
