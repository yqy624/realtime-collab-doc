package com.collab.model.websocket;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Operation {
    private OperationType type;
    private Integer position;
    private Integer length;
    private String content;
    private Integer revision;
    private String clientId;

    public enum OperationType {
        INSERT, DELETE, FULL_SYNC
    }
}
