-- Default users are initialized in DataInitializer to ensure passwords are encoded correctly.
INSERT INTO documents (title, content, creator_id, is_public, revision, created_at, updated_at)
SELECT '欢迎使用实时协作文档系统', '这是一个公开示例文档。\n\n你可以打开两个账号同时编辑，体验实时协作、在线状态、光标同步和聊天功能。', u.id, TRUE, 0, NOW(), NOW()
FROM users u
WHERE u.username = 'admin'
  AND NOT EXISTS (
    SELECT 1 FROM documents d WHERE d.title = '欢迎使用实时协作文档系统'
  );

INSERT INTO chat_messages (document_id, sender_id, message, message_type, created_at)
SELECT d.id, u.id, '欢迎来到协作空间，试试发送 @user1 消息。', 'TEXT', NOW()
FROM documents d
JOIN users u ON u.username = 'admin'
WHERE d.title = '欢迎使用实时协作文档系统'
  AND NOT EXISTS (
    SELECT 1 FROM chat_messages c WHERE c.document_id = d.id AND c.message = '欢迎来到协作空间，试试发送 @user1 消息。'
  );
