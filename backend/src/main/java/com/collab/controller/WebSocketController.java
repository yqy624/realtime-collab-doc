package com.collab.controller;

import com.collab.model.dto.ChatMessageDTO;
import com.collab.model.entity.ChatMessage;
import com.collab.model.entity.Document;
import com.collab.model.entity.OperationLog;
import com.collab.model.entity.User;
import com.collab.model.websocket.CollaborationMessage;
import com.collab.model.websocket.Operation;
import com.collab.repository.ChatMessageRepository;
import com.collab.repository.OperationLogRepository;
import com.collab.repository.UserRepository;
import com.collab.service.DocumentService;
import com.collab.service.OTService;
import com.collab.util.WebSocketSessionManager;
import lombok.RequiredArgsConstructor;
import org.springframework.messaging.handler.annotation.MessageExceptionHandler;
import org.springframework.messaging.handler.annotation.MessageMapping;
import org.springframework.messaging.handler.annotation.Payload;
import org.springframework.messaging.simp.SimpMessageHeaderAccessor;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Controller;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.Set;

@Controller
@RequiredArgsConstructor
public class WebSocketController {

    private final SimpMessagingTemplate messagingTemplate;
    private final DocumentService documentService;
    private final OTService otService;
    private final WebSocketSessionManager sessionManager;
    private final ChatMessageRepository chatMessageRepository;
    private final OperationLogRepository operationLogRepository;
    private final UserRepository userRepository;

    @MessageMapping("/collaboration")
    public void handleMessage(@Payload CollaborationMessage message, SimpMessageHeaderAccessor accessor) {
        if (message.getDocumentId() == null) {
            return;
        }

        User user = resolveUser(accessor);
        if (user == null) {
            throw new IllegalArgumentException("未授权的 WebSocket 连接");
        }

        try {
            switch (message.getType()) {
                case JOIN -> handleJoin(message, user);
                case LEAVE -> handleLeave(message, user);
                case EDIT -> handleEdit(message, user);
                case CHAT -> handleChat(message, user);
                case CURSOR -> handleCursor(message, user);
                default -> {
                }
            }
        } catch (IllegalArgumentException ex) {
            sendUserError(user.getUsername(), message.getDocumentId(), ex.getMessage());
        }
    }

    @MessageExceptionHandler(IllegalArgumentException.class)
    public void handleWebSocketError(IllegalArgumentException ex, SimpMessageHeaderAccessor accessor) {
        String username = accessor.getUser() == null ? null : accessor.getUser().getName();
        Object documentId = accessor.getSessionAttributes() == null ? null : accessor.getSessionAttributes().get("documentId");
        if (username != null) {
            sendUserError(username, documentId instanceof Integer value ? value : null, ex.getMessage());
        }
    }

    private void handleJoin(CollaborationMessage message, User user) {
        Set<String> users = sessionManager.join(message.getDocumentId(), user.getUsername());
        messagingTemplate.convertAndSend("/topic/presence/" + message.getDocumentId(),
                CollaborationMessage.builder()
                        .type(CollaborationMessage.MessageType.PRESENCE)
                        .documentId(message.getDocumentId())
                        .onlineUsers(users)
                        .timestamp(LocalDateTime.now())
                        .build());

        Document document = documentService.findEntity(message.getDocumentId());
        messagingTemplate.convertAndSend("/topic/document/" + message.getDocumentId(),
                CollaborationMessage.builder()
                        .type(CollaborationMessage.MessageType.SYNC)
                        .documentId(document.getId())
                        .content(document.getContent())
                        .revision(document.getRevision())
                        .timestamp(LocalDateTime.now())
                        .build());
    }

    private void handleLeave(CollaborationMessage message, User user) {
        Set<String> users = sessionManager.leave(message.getDocumentId(), user.getUsername());
        messagingTemplate.convertAndSend("/topic/presence/" + message.getDocumentId(),
                CollaborationMessage.builder()
                        .type(CollaborationMessage.MessageType.PRESENCE)
                        .documentId(message.getDocumentId())
                        .onlineUsers(users)
                        .timestamp(LocalDateTime.now())
                        .build());
    }

    private void handleEdit(CollaborationMessage message, User user) {
        if (message.getOperation() == null || message.getOperation().getType() == null) {
            throw new IllegalArgumentException("无效的编辑操作");
        }

        Document document = documentService.findEntity(message.getDocumentId());
        Operation transformed = transformAgainstPendingLogs(message.getDocumentId(), message.getOperation(), document.getRevision());
        document.setContent(otService.apply(document.getContent(), transformed));
        document.setRevision(document.getRevision() + 1);
        documentService.save(document);
        saveOperationLog(document.getId(), user.getId(), transformed, document.getRevision());

        messagingTemplate.convertAndSend("/topic/document/" + message.getDocumentId(),
                CollaborationMessage.builder()
                        .type(CollaborationMessage.MessageType.EDIT)
                        .documentId(document.getId())
                        .userId(user.getId())
                        .username(user.getUsername())
                        .avatarUrl(user.getAvatarUrl())
                        .content(document.getContent())
                        .revision(document.getRevision())
                        .operation(transformed)
                        .timestamp(LocalDateTime.now())
                        .build());
    }

    private void handleChat(CollaborationMessage message, User user) {
        String chatMessage = message.getChatMessage() == null ? "" : message.getChatMessage().trim();
        if (chatMessage.isEmpty()) {
            throw new IllegalArgumentException("消息不能为空");
        }

        ChatMessage saved = chatMessageRepository.save(ChatMessage.builder()
                .documentId(message.getDocumentId())
                .senderId(user.getId())
                .message(chatMessage)
                .messageType("TEXT")
                .build());

        messagingTemplate.convertAndSend("/topic/chat/" + message.getDocumentId(),
                ChatMessageDTO.builder()
                        .id(saved.getId())
                        .documentId(saved.getDocumentId())
                        .senderId(user.getId())
                        .senderName(user.getUsername())
                        .senderAvatar(user.getAvatarUrl())
                        .message(saved.getMessage())
                        .messageType(saved.getMessageType())
                        .createdAt(saved.getCreatedAt())
                        .build());
    }

    private void handleCursor(CollaborationMessage message, User user) {
        messagingTemplate.convertAndSend("/topic/document/" + message.getDocumentId(),
                CollaborationMessage.builder()
                        .type(CollaborationMessage.MessageType.CURSOR)
                        .documentId(message.getDocumentId())
                        .userId(user.getId())
                        .username(user.getUsername())
                        .avatarUrl(user.getAvatarUrl())
                        .cursorPosition(message.getCursorPosition())
                        .timestamp(LocalDateTime.now())
                        .build());
    }

    private User resolveUser(SimpMessageHeaderAccessor accessor) {
        if (accessor.getSessionAttributes() == null) {
            return null;
        }
        Object userId = accessor.getSessionAttributes().get("userId");
        if (!(userId instanceof Integer value)) {
            return null;
        }
        return userRepository.findById(value).orElse(null);
    }

    private Operation transformAgainstPendingLogs(Integer documentId, Operation incoming, Integer currentRevision) {
        int baseRevision = incoming.getRevision() == null ? 0 : incoming.getRevision();
        if (baseRevision > currentRevision) {
            throw new IllegalArgumentException("文档版本无效");
        }

        Operation transformed = incoming;
        List<OperationLog> logs = operationLogRepository.findByDocumentIdAndRevisionGreaterThanOrderByRevisionAsc(documentId, baseRevision);
        for (OperationLog log : logs) {
            transformed = otService.transform(transformed, Operation.builder()
                    .type(Operation.OperationType.valueOf(log.getOperationType().name()))
                    .position(log.getPosition())
                    .content(log.getContent())
                    .revision(log.getRevision())
                    .build());
        }
        transformed.setRevision(currentRevision);
        return transformed;
    }

    private void saveOperationLog(Integer documentId, Integer userId, Operation operation, Integer revision) {
        operationLogRepository.save(OperationLog.builder()
                .documentId(documentId)
                .userId(userId)
                .operationType(OperationLog.OperationType.valueOf(operation.getType().name()))
                .position(operation.getPosition() == null ? 0 : operation.getPosition())
                .content(operation.getType() == Operation.OperationType.DELETE && operation.getLength() != null
                        ? "#".repeat(Math.max(operation.getLength(), 0))
                        : operation.getContent())
                .revision(revision)
                .build());
    }

    private void sendUserError(String username, Integer documentId, String message) {
        messagingTemplate.convertAndSendToUser(username, "/queue/errors", Map.of("message", message));
        if (documentId != null) {
            messagingTemplate.convertAndSend("/topic/document/" + documentId,
                    CollaborationMessage.builder()
                            .type(CollaborationMessage.MessageType.ERROR)
                            .username(username)
                            .documentId(documentId)
                            .chatMessage(message)
                            .timestamp(LocalDateTime.now())
                            .build());
        }
    }
}
