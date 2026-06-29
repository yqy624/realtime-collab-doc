package com.collab.config;

import com.collab.util.JwtUtil;
import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.server.ServerHttpRequest;
import org.springframework.http.server.ServerHttpResponse;
import org.springframework.messaging.Message;
import org.springframework.messaging.MessageChannel;
import org.springframework.messaging.simp.config.ChannelRegistration;
import org.springframework.messaging.simp.config.MessageBrokerRegistry;
import org.springframework.messaging.simp.stomp.StompCommand;
import org.springframework.messaging.simp.stomp.StompHeaderAccessor;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.web.socket.WebSocketHandler;
import org.springframework.web.socket.config.annotation.EnableWebSocketMessageBroker;
import org.springframework.web.socket.config.annotation.StompEndpointRegistry;
import org.springframework.web.socket.config.annotation.WebSocketMessageBrokerConfigurer;
import org.springframework.web.socket.server.HandshakeInterceptor;
import org.springframework.web.socket.server.support.DefaultHandshakeHandler;
import org.springframework.web.util.UriComponentsBuilder;

import java.security.Principal;
import java.util.Collections;
import java.util.Map;

@Configuration
@EnableWebSocketMessageBroker
@RequiredArgsConstructor
public class WebSocketConfig implements WebSocketMessageBrokerConfigurer {

    private final JwtUtil jwtUtil;

    @Override
    public void configureMessageBroker(MessageBrokerRegistry registry) {
        registry.enableSimpleBroker("/topic", "/queue");
        registry.setApplicationDestinationPrefixes("/app");
        registry.setUserDestinationPrefix("/user");
    }

    @Override
    public void registerStompEndpoints(StompEndpointRegistry registry) {
        registry.addEndpoint("/ws")
                .setAllowedOriginPatterns("*")
                .addInterceptors(new HandshakeInterceptor() {
                    @Override
                    public boolean beforeHandshake(ServerHttpRequest request, ServerHttpResponse response,
                                                   WebSocketHandler wsHandler, Map<String, Object> attributes) {
                        String token = UriComponentsBuilder.fromUri(request.getURI())
                                .build()
                                .getQueryParams()
                                .getFirst("token");
                        if (token != null && !token.isBlank()) {
                            attributes.put("token", token);
                        }
                        return true;
                    }

                    @Override
                    public void afterHandshake(ServerHttpRequest request, ServerHttpResponse response,
                                               WebSocketHandler wsHandler, Exception exception) {
                    }
                })
                .setHandshakeHandler(new DefaultHandshakeHandler() {
                    @Override
                    protected Principal determineUser(ServerHttpRequest request, WebSocketHandler wsHandler,
                                                      Map<String, Object> attributes) {
                        Object username = attributes.get("username");
                        if (username instanceof String value && !value.isBlank()) {
                            return () -> value;
                        }
                        return super.determineUser(request, wsHandler, attributes);
                    }
                });
    }

    @Override
    public void configureClientInboundChannel(ChannelRegistration registration) {
        registration.interceptors(new org.springframework.messaging.support.ChannelInterceptor() {
            @Override
            public Message<?> preSend(Message<?> message, MessageChannel channel) {
                StompHeaderAccessor accessor = StompHeaderAccessor.wrap(message);
                StompCommand command = accessor.getCommand();
                if (command == null) {
                    return message;
                }

                if (command == StompCommand.CONNECT) {
                    String token = resolveToken(accessor);
                    if (token == null || !jwtUtil.isTokenValid(token)) {
                        throw new IllegalArgumentException("WebSocket authentication failed");
                    }

                    Integer userId = jwtUtil.extractUserId(token);
                    String username = jwtUtil.extractUsername(token);
                    accessor.getSessionAttributes().put("token", token);
                    accessor.getSessionAttributes().put("userId", userId);
                    accessor.getSessionAttributes().put("username", username);
                    accessor.setUser(new UsernamePasswordAuthenticationToken(username, null, Collections.emptyList()));
                }

                if ((command == StompCommand.SEND || command == StompCommand.SUBSCRIBE)
                        && (accessor.getSessionAttributes() == null || accessor.getSessionAttributes().get("userId") == null)) {
                    throw new IllegalArgumentException("WebSocket session is not authenticated");
                }
                return message;
            }
        });
    }

    private String resolveToken(StompHeaderAccessor accessor) {
        String authHeader = firstHeader(accessor, "Authorization");
        if (authHeader == null) {
            authHeader = firstHeader(accessor, "authorization");
        }
        if (authHeader != null && authHeader.startsWith("Bearer ")) {
            return authHeader.substring(7);
        }
        if (authHeader != null && !authHeader.isBlank()) {
            return authHeader;
        }

        String tokenHeader = firstHeader(accessor, "token");
        if (tokenHeader != null && !tokenHeader.isBlank()) {
            return tokenHeader;
        }

        Object token = accessor.getSessionAttributes() == null ? null : accessor.getSessionAttributes().get("token");
        if (token instanceof String value && !value.isBlank()) {
            return value;
        }
        return null;
    }

    private String firstHeader(StompHeaderAccessor accessor, String name) {
        return accessor.getFirstNativeHeader(name);
    }
}
