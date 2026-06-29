package com.collab.service;

import com.collab.model.dto.SnapshotDTO;
import com.collab.model.dto.DocumentDTO;
import com.collab.model.entity.Document;
import com.collab.model.entity.DocumentSnapshot;
import com.collab.model.entity.User;
import com.collab.repository.DocumentSnapshotRepository;
import com.collab.repository.DocumentRepository;
import com.collab.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Service
@RequiredArgsConstructor
public class DocumentService {

    private final DocumentRepository documentRepository;
    private final DocumentSnapshotRepository documentSnapshotRepository;
    private final UserRepository userRepository;

    public DocumentDTO createDocument(DocumentDTO request, Integer userId) {
        Document document = Document.builder()
                .title(request.getTitle())
                .content(request.getContent() == null ? "" : request.getContent())
                .creatorId(userId)
                .isPublic(request.getIsPublic() == null || request.getIsPublic())
                .revision(0)
                .build();
        return toDto(documentRepository.save(document));
    }

    public DocumentDTO updateDocument(Integer id, DocumentDTO request, Integer userId) {
        Document document = findOwnedDocument(id, userId);
        document.setTitle(request.getTitle() == null || request.getTitle().isBlank() ? document.getTitle() : request.getTitle());
        if (request.getContent() != null) {
            document.setContent(request.getContent());
        }
        if (request.getIsPublic() != null) {
            document.setIsPublic(request.getIsPublic());
        }
        if (request.getRevision() != null) {
            document.setRevision(request.getRevision());
        }
        return toDto(documentRepository.save(document));
    }

    public DocumentDTO getDocument(Integer id, Integer userId) {
        return toDto(findAccessibleDocument(id, userId));
    }

    public void deleteDocument(Integer id, Integer userId) {
        Document document = findOwnedDocument(id, userId);
        documentRepository.delete(document);
    }

    public List<DocumentDTO> getDocumentsForUser(Integer userId) {
        Map<Integer, DocumentDTO> merged = new LinkedHashMap<>();
        for (Document document : documentRepository.findByCreatorIdOrderByUpdatedAtDesc(userId)) {
            merged.put(document.getId(), toDto(document));
        }
        for (Document document : documentRepository.findByIsPublicTrueOrderByUpdatedAtDesc()) {
            merged.putIfAbsent(document.getId(), toDto(document));
        }
        return new ArrayList<>(merged.values());
    }

    public Document findEntity(Integer id) {
        return documentRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("Document not found"));
    }

    public Document findAccessibleDocument(Integer id, Integer userId) {
        Document document = findEntity(id);
        if (document.getCreatorId().equals(userId) || Boolean.TRUE.equals(document.getIsPublic())) {
            return document;
        }
        throw new IllegalArgumentException("No permission to access this document");
    }

    public Document save(Document document) {
        return documentRepository.save(document);
    }

    public DocumentDTO toDto(Document document) {
        return DocumentDTO.builder()
                .id(document.getId())
                .title(document.getTitle())
                .content(document.getContent())
                .creatorId(document.getCreatorId())
                .isPublic(document.getIsPublic())
                .revision(document.getRevision())
                .createdAt(document.getCreatedAt())
                .updatedAt(document.getUpdatedAt())
                .build();
    }

    public SnapshotDTO saveSnapshot(Integer documentId, Integer userId) {
        Document document = findAccessibleDocument(documentId, userId);
        DocumentSnapshot snapshot = DocumentSnapshot.builder()
                .documentId(document.getId())
                .title(document.getTitle())
                .content(document.getContent())
                .revision(document.getRevision())
                .userId(userId)
                .build();
        return toSnapshotDto(documentSnapshotRepository.save(snapshot));
    }

    public List<SnapshotDTO> getSnapshots(Integer documentId, Integer userId) {
        findAccessibleDocument(documentId, userId);
        return documentSnapshotRepository.findByDocumentIdOrderByCreatedAtDesc(documentId).stream()
                .map(this::toSnapshotDto)
                .toList();
    }

    public Document restoreSnapshot(Long snapshotId, Integer userId) {
        DocumentSnapshot snapshot = documentSnapshotRepository.findById(snapshotId)
                .orElseThrow(() -> new IllegalArgumentException("Snapshot not found"));
        Document document = findOwnedDocument(snapshot.getDocumentId(), userId);
        document.setTitle(snapshot.getTitle());
        document.setContent(snapshot.getContent());
        document.setRevision(snapshot.getRevision());
        return documentRepository.save(document);
    }

    private Document findOwnedDocument(Integer id, Integer userId) {
        Document document = findEntity(id);
        if (!document.getCreatorId().equals(userId)) {
            throw new IllegalArgumentException("No permission to operate on this document");
        }
        return document;
    }

    private SnapshotDTO toSnapshotDto(DocumentSnapshot snapshot) {
        User user = userRepository.findById(snapshot.getUserId()).orElse(null);
        return SnapshotDTO.builder()
                .id(snapshot.getId())
                .documentId(snapshot.getDocumentId())
                .title(snapshot.getTitle())
                .content(snapshot.getContent())
                .revision(snapshot.getRevision())
                .userId(snapshot.getUserId())
                .userName(user == null ? "Unknown" : user.getUsername())
                .createdAt(snapshot.getCreatedAt())
                .build();
    }
}