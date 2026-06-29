package com.collab.repository;

import com.collab.model.entity.ChatMessage;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface ChatMessageRepository extends JpaRepository<ChatMessage, Long> {
    List<ChatMessage> findByDocumentIdOrderByCreatedAtAsc(Integer documentId);
}
