package com.collab.model.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ChatMessageDTO {
    private Long id;
    private Integer documentId;
    private Integer senderId;
    private String senderName;
    private String senderAvatar;
    private String message;
    private String messageType;
    private LocalDateTime createdAt;
}
