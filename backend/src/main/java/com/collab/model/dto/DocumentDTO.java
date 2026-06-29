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
public class DocumentDTO {
    private Integer id;
    private String title;
    private String content;
    private Integer creatorId;
    private Boolean isPublic;
    private Integer revision;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
