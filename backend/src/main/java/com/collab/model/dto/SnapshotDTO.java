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
public class SnapshotDTO {
    private Long id;
    private Integer documentId;
    private String title;
    private String content;
    private Integer revision;
    private Integer userId;
    private String userName;
    private LocalDateTime createdAt;
}
