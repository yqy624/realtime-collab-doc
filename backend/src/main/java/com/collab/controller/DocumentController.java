package com.collab.controller;

import com.collab.model.dto.SnapshotDTO;
import com.collab.model.dto.ApiResponse;
import com.collab.model.dto.ChatMessageDTO;
import com.collab.model.dto.DocumentDTO;
import com.collab.model.entity.ChatMessage;
import com.collab.model.entity.Document;
import com.collab.model.entity.User;
import com.collab.repository.ChatMessageRepository;
import com.collab.repository.UserRepository;
import com.collab.service.DocumentService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestAttribute;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/documents")
@RequiredArgsConstructor
public class DocumentController {

    private final DocumentService documentService;
    private final ChatMessageRepository chatMessageRepository;
    private final UserRepository userRepository;

    @GetMapping
    public ResponseEntity<ApiResponse<List<DocumentDTO>>> getDocuments(@RequestAttribute("userId") Integer userId) {
        return ResponseEntity.ok(ApiResponse.success(documentService.getDocumentsForUser(userId)));
    }

    @PostMapping
    public ResponseEntity<ApiResponse<DocumentDTO>> createDocument(@RequestBody DocumentDTO request,
                                                                   @RequestAttribute("userId") Integer userId) {
        return ResponseEntity.ok(ApiResponse.success(documentService.createDocument(request, userId)));
    }

    @GetMapping("/{id}")
    public ResponseEntity<ApiResponse<DocumentDTO>> getDocument(@PathVariable Integer id,
                                                                @RequestAttribute("userId") Integer userId) {
        return ResponseEntity.ok(ApiResponse.success(documentService.getDocument(id, userId)));
    }

    @PutMapping("/{id}")
    public ResponseEntity<ApiResponse<DocumentDTO>> updateDocument(@PathVariable Integer id,
                                                                   @RequestBody DocumentDTO request,
                                                                   @RequestAttribute("userId") Integer userId) {
        return ResponseEntity.ok(ApiResponse.success(documentService.updateDocument(id, request, userId)));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<ApiResponse<Void>> deleteDocument(@PathVariable Integer id,
                                                            @RequestAttribute("userId") Integer userId) {
        documentService.deleteDocument(id, userId);
        return ResponseEntity.ok(ApiResponse.success(null));
    }

    @GetMapping("/{id}/messages")
    public ResponseEntity<ApiResponse<List<ChatMessageDTO>>> getMessages(@PathVariable Integer id,
                                                                         @RequestAttribute("userId") Integer userId) {
        documentService.findAccessibleDocument(id, userId);
        List<ChatMessageDTO> messages = chatMessageRepository.findByDocumentIdOrderByCreatedAtAsc(id).stream()
                .map(this::toMessageDto)
                .toList();
        return ResponseEntity.ok(ApiResponse.success(messages));
    }

    @PostMapping("/{id}/save")
    public ResponseEntity<ApiResponse<SnapshotDTO>> saveDocument(@PathVariable Integer id,
                                                                 @RequestBody(required = false) DocumentDTO request,
                                                                 @RequestAttribute("userId") Integer userId) {
        return ResponseEntity.ok(ApiResponse.success(documentService.saveSnapshot(id, request, userId)));
    }

    @GetMapping("/{id}/snapshots")
    public ResponseEntity<ApiResponse<List<SnapshotDTO>>> getSnapshots(@PathVariable Integer id,
                                                                       @RequestAttribute("userId") Integer userId) {
        return ResponseEntity.ok(ApiResponse.success(documentService.getSnapshots(id, userId)));
    }

    @PostMapping("/{id}/snapshots/{snapshotId}/restore")
    public ResponseEntity<ApiResponse<DocumentDTO>> restoreSnapshot(@PathVariable Integer id,
                                                                    @PathVariable Long snapshotId,
                                                                    @RequestAttribute("userId") Integer userId) {
        Document document = documentService.restoreSnapshot(snapshotId, userId);
        return ResponseEntity.ok(ApiResponse.success(documentService.toDto(document)));
    }

    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<ApiResponse<Void>> handleIllegalArgument(IllegalArgumentException ex) {
        return ResponseEntity.badRequest().body(ApiResponse.failure(ex.getMessage()));
    }

    private ChatMessageDTO toMessageDto(ChatMessage entity) {
        User user = userRepository.findById(entity.getSenderId()).orElse(null);
        return ChatMessageDTO.builder()
                .id(entity.getId())
                .documentId(entity.getDocumentId())
                .senderId(entity.getSenderId())
                .senderName(user == null ? "Unknown" : user.getUsername())
                .senderAvatar(user == null ? "" : user.getAvatarUrl())
                .message(entity.getMessage())
                .messageType(entity.getMessageType())
                .createdAt(entity.getCreatedAt())
                .build();
    }
}
