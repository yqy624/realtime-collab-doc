package com.collab.service;

import com.collab.model.websocket.Operation;
import org.springframework.stereotype.Service;

@Service
public class OTService {

    public String apply(String original, Operation operation) {
        String content = original == null ? "" : original;
        if (operation == null || operation.getType() == null) {
            return content;
        }

        int position = Math.max(0, Math.min(operation.getPosition() == null ? 0 : operation.getPosition(), content.length()));

        return switch (operation.getType()) {
            case INSERT -> content.substring(0, position) + defaultValue(operation.getContent()) + content.substring(position);
            case DELETE -> {
                int length = operation.getLength() == null ? defaultValue(operation.getContent()).length() : operation.getLength();
                int end = Math.min(content.length(), position + Math.max(length, 0));
                yield content.substring(0, position) + content.substring(end);
            }
            case FULL_SYNC -> defaultValue(operation.getContent());
        };
    }

    public Operation transform(Operation incoming, Operation applied) {
        if (incoming == null || incoming.getType() == null || applied == null || applied.getType() == null) {
            return incoming;
        }

        Operation transformed = Operation.builder()
                .type(incoming.getType())
                .position(incoming.getPosition())
                .length(incoming.getLength())
                .content(incoming.getContent())
                .revision(incoming.getRevision())
                .clientId(incoming.getClientId())
                .build();

        int incomingPosition = safePosition(transformed.getPosition());
        int appliedPosition = safePosition(applied.getPosition());
        int appliedLength = operationLength(applied);

        if (applied.getType() == Operation.OperationType.INSERT) {
            if (incomingPosition > appliedPosition || sameInsertPosition(incoming, applied)) {
                transformed.setPosition(incomingPosition + appliedLength);
            }
            return transformed;
        }

        if (applied.getType() == Operation.OperationType.DELETE) {
            if (incomingPosition >= appliedPosition + appliedLength) {
                transformed.setPosition(Math.max(appliedPosition, incomingPosition - appliedLength));
                return transformed;
            }

            if (incomingPosition >= appliedPosition) {
                transformed.setPosition(appliedPosition);
                if (transformed.getType() == Operation.OperationType.DELETE) {
                    int overlap = Math.min(appliedPosition + appliedLength, incomingPosition + operationLength(incoming)) - incomingPosition;
                    transformed.setLength(Math.max(0, operationLength(incoming) - Math.max(overlap, 0)));
                }
            }
        }

        return transformed;
    }

    private boolean sameInsertPosition(Operation incoming, Operation applied) {
        return incoming.getType() == Operation.OperationType.INSERT
                && applied.getType() == Operation.OperationType.INSERT
                && safePosition(incoming.getPosition()) == safePosition(applied.getPosition())
                && compareClientId(incoming.getClientId(), applied.getClientId()) > 0;
    }

    private int compareClientId(String left, String right) {
        return defaultValue(left).compareTo(defaultValue(right));
    }

    private int operationLength(Operation operation) {
        if (operation == null) {
            return 0;
        }
        if (operation.getLength() != null) {
            return Math.max(0, operation.getLength());
        }
        return defaultValue(operation.getContent()).length();
    }

    private int safePosition(Integer position) {
        return Math.max(0, position == null ? 0 : position);
    }

    private String defaultValue(String value) {
        return value == null ? "" : value;
    }
}
