package com.collab.util;

import org.springframework.stereotype.Component;

import java.util.Collections;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

@Component
public class WebSocketSessionManager {

    private final Map<Integer, Set<String>> documentUsers = new ConcurrentHashMap<>();

    public Set<String> join(Integer documentId, String username) {
        documentUsers.computeIfAbsent(documentId, ignored -> ConcurrentHashMap.newKeySet()).add(username);
        return getOnlineUsers(documentId);
    }

    public Set<String> leave(Integer documentId, String username) {
        Set<String> users = documentUsers.get(documentId);
        if (users != null) {
            users.remove(username);
            if (users.isEmpty()) {
                documentUsers.remove(documentId);
            }
        }
        return getOnlineUsers(documentId);
    }

    public Set<String> getOnlineUsers(Integer documentId) {
        return Collections.unmodifiableSet(documentUsers.getOrDefault(documentId, Collections.emptySet()));
    }
}
