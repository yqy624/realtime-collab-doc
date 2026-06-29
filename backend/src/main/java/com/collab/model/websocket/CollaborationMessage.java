package com.collab.model.websocket;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.Set;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CollaborationMessage {
    private MessageType type;
    private Integer documentId;
    private Integer userId;
    private String username;
    private String avatarUrl;
    private Operation operation;
    private String chatMessage;
    private String content;
    private Integer revision;
    private Integer cursorPosition;
    private Set<String> onlineUsers;
    private LocalDateTime timestamp;

    public enum MessageType {
        JOIN, LEAVE, EDIT, CURSOR, CHAT, SYNC, PRESENCE, ERROR
    }
}
