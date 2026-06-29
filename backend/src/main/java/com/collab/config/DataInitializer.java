package com.collab.config;

import com.collab.model.entity.ChatMessage;
import com.collab.model.entity.Document;
import com.collab.model.entity.User;
import com.collab.repository.ChatMessageRepository;
import com.collab.repository.DocumentRepository;
import com.collab.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.boot.CommandLineRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.crypto.password.PasswordEncoder;

@Configuration
@RequiredArgsConstructor
public class DataInitializer {

    private final UserRepository userRepository;
    private final DocumentRepository documentRepository;
    private final ChatMessageRepository chatMessageRepository;
    private final PasswordEncoder passwordEncoder;

    @Bean
    public CommandLineRunner initUsers() {
        return args -> {
            User admin = createUserIfMissing("admin", "admin@example.com", "Admin", "0D8ABC");
            createUserIfMissing("user1", "user1@example.com", "User1", "8E44AD");
            createUserIfMissing("user2", "user2@example.com", "User2", "16A085");
            createDefaultDocument(admin);
        };
    }

    private User createUserIfMissing(String username, String email, String avatarName, String color) {
        return userRepository.findByUsername(username).orElseGet(() -> userRepository.save(User.builder()
                .username(username)
                .email(email)
                .passwordHash(passwordEncoder.encode("password123"))
                .avatarUrl("https://ui-avatars.com/api/?name=" + avatarName + "&background=" + color + "&color=fff")
                .build()));
    }

    private void createDefaultDocument(User admin) {
        if (documentRepository.findByCreatorIdOrderByUpdatedAtDesc(admin.getId()).stream()
                .anyMatch(document -> "欢迎使用实时协作文档系统".equals(document.getTitle()))) {
            return;
        }

        Document document = documentRepository.save(Document.builder()
                .title("欢迎使用实时协作文档系统")
                .content("这是一个公开示例文档。\n\n你可以打开两个账号同时编辑，体验实时协作、在线状态、光标同步和聊天功能。")
                .creatorId(admin.getId())
                .isPublic(true)
                .revision(0)
                .build());

        chatMessageRepository.save(ChatMessage.builder()
                .documentId(document.getId())
                .senderId(admin.getId())
                .message("欢迎来到协作空间，试试发送 @user1 消息。")
                .messageType("TEXT")
                .build());
    }
}
