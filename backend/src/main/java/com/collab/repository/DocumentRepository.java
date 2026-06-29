package com.collab.repository;

import com.collab.model.entity.Document;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface DocumentRepository extends JpaRepository<Document, Integer> {
    List<Document> findByCreatorIdOrderByUpdatedAtDesc(Integer creatorId);
    List<Document> findByIsPublicTrueOrderByUpdatedAtDesc();
}
