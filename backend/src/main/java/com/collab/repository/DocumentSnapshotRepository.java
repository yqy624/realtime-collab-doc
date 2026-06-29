package com.collab.repository;

import com.collab.model.entity.DocumentSnapshot;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface DocumentSnapshotRepository extends JpaRepository<DocumentSnapshot, Long> {
    List<DocumentSnapshot> findByDocumentIdOrderByCreatedAtDesc(Integer documentId);
}
