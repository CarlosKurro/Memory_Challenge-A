# Prompt mở rộng Challenge A thành chatbot web

Yêu cầu mới của người dùng: chạy trên web, giao diện chatbot, trò chuyện bình
thường và đáp ứng Challenge A. Đây là phần tiếp nối, thay thế ràng buộc chỉ ghi
qua CLI của bản đầu. Giữ nguyên kết quả và bằng chứng CLI trước đó.

1. Dùng lại Python/SQLite hiện có, xây web app localhost không cần cài package.
2. Có giao diện tiếng Việt: chat, lịch sử hội thoại, chat mới, đổi project, memory
   active, lịch sử thay thế và phần context đã inject vào từng lượt.
3. Lưu chat/message trên server để tải lại trang không mất cuộc trò chuyện.
   Chat mới có history rỗng nhưng vẫn retrieve memory của cùng project.
4. Người dùng nói quyết định bằng ngôn ngữ tự nhiên; harness trích quyết định
   rõ ràng từ chính tin nhắn mới, cập nhật memory trước khi tạo request trả lời.
   Không ghi câu hỏi, ví dụ giả định hay lời assistant thành quy ước.
5. Hỗ trợ LLM thật qua OpenAI Responses API với cấu hình ngay trong giao diện.
   API key chỉ giữ trong RAM phía server, không lưu DB/file/localStorage và không
   gửi key lại client. Model tùy chỉnh. Không cấu hình thì dùng demo có nhãn rõ.
6. Chế độ AI có hai bước: trích quyết định có cấu trúc kèm trích dẫn từ người
   dùng; sau đó retrieve memory mới và trả lời với history của riêng chat đó.
   Agent extractor không được đọc history từ chat khác để suy diễn memory.
7. Giao diện gọn, responsive, dễ dùng như ứng dụng chat; gửi Enter, xuống dòng
   Shift+Enter, hiển thị đang trả lời, xử lý lỗi và giữ tin nhắn có thể thử lại.
8. Kiểm thử thực chất HTTP: chat thông thường, lưu quyết định, mở chat mới,
   đổi JWT sang cookie, chat mới dùng cookie, project isolation, restart server,
   history và trace không chứa quy ước lỗi thời ở chat mới. Mock adapter riêng;
   không công bố đã gọi LLM thật nếu thiếu key.
9. Cập nhật README, báo cáo và log; khởi động server và mở URL cho người dùng.

Agent hiện tại đọc lại prompt này rồi trực tiếp triển khai trong workspace.
Không tạo chat Codex mới và không cần ủy quyền agent khác.
