package com.collab.repository;

import com.collab.model.entity.OperationLog;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface OperationLogRepository extends JpaRepository<OperationLog, Long> {
    List<OperationLog> findByDocumentIdAndRevisionGreaterThanOrderByRevisionAsc(Integer documentId, Integer revision);
}
