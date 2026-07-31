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
  private socket: WebSocket | null = null;
  private connected = false;
  private pendingPayloads: unknown[] = [];
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private handlers: WsHandlers = {};
  private documentId = 0;
  private shouldReconnect = false;

  connect(documentId: number, handlers: WsHandlers) {
    this.documentId = documentId;
    this.handlers = handlers;
    this.shouldReconnect = true;
    this.pendingPayloads = [];
    this.doConnect();
  }

  private doConnect() {
    const token = sessionStorage.getItem("token") ?? "";
    const url = `${wsBaseUrl}?token=${encodeURIComponent(token)}`;

    this.socket = new WebSocket(url);

    this.socket.onopen = () => {
      this.connected = true;
      this.handlers.onConnect?.();
      this.flushPendingPayloads();

      // Send JOIN after connecting
      this.send({
        type: "JOIN",
        documentId: this.documentId
      });
    };

    this.socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        this.routeMessage(payload);
      } catch {
        // ignore malformed messages
      }
    };

    this.socket.onclose = () => {
      this.connected = false;
      this.handlers.onDisconnect?.();
      this.scheduleReconnect();
    };

    this.socket.onerror = (evt) => {
      this.handlers.onWebSocketError?.(evt);
    };
  }

  private routeMessage(payload: any) {
    switch (payload.type) {
      case "SYNC":
      case "EDIT":
      case "CURSOR":
      case "ERROR":
        this.handlers.onDocumentMessage?.(payload);
        break;
      case "PRESENCE":
        this.handlers.onPresenceMessage?.(payload);
        break;
      case "CHAT":
        // Chat messages arrive as direct payload with sender info.
        this.handlers.onChatMessage?.(payload);
        break;
      default:
        this.handlers.onDocumentMessage?.(payload);
    }
  }

  disconnect() {
    this.shouldReconnect = false;
    this.pendingPayloads = [];
    this.connected = false;

    // Send LEAVE before closing
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({
        type: "LEAVE",
        documentId: this.documentId
      }));
    }

    this.socket?.close();
    this.socket = null;

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  send(payload: unknown) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      this.pendingPayloads.push(payload);
      return;
    }
    this.socket.send(JSON.stringify(payload));
  }

  private flushPendingPayloads() {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN || this.pendingPayloads.length === 0) {
      return;
    }
    for (const payload of this.pendingPayloads) {
      this.socket.send(JSON.stringify(payload));
    }
    this.pendingPayloads = [];
  }

  private scheduleReconnect() {
    if (!this.shouldReconnect) return;
    if (this.reconnectTimer) return;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      if (this.shouldReconnect) {
        this.doConnect();
      }
    }, 3000);
  }
}
