# Nhật ký thực hiện prompt Challenge A

## Bổ sung bản chatbot web

Yêu cầu tiếp theo của người dùng: chạy trên web, giao diện chatbot, trò chuyện
bình thường và tiếp tục đáp ứng Challenge A.

- Đã tạo và đọc lại `PROMPT_WEB_CHALLENGE_A.md`, sau đó trực tiếp triển khai.
- SHA-256 prompt web:
  `1538d65ba5d7e4e026c426acdaab977ae3f13ba213ef734893e59a2de583b172`.
- Dùng lại `MemoryStore`; thêm `chat_engine.py`, `webapp.py`, `web/`,
  `start-web.ps1` và `tests/test_webapp.py`.
- API key chỉ lưu RAM; cấu hình qua UI có kiểm tra kết nối. Chưa gọi LLM thật
  trong phần kiểm chứng vì không có key từ môi trường khi triển khai.
- `node --check web/app.js` và Python compile check thành công.
- Unit/integration test: **28/28 đạt**, log `output/web-tests.log`. Test HTTP
  phải chạy ngoài sandbox vì Windows sandbox chặn socket localhost.
- Browser QA: **13/13 đạt** qua Playwright và Edge headless, log/bằng chứng tại
  `output/web-qa/`. Server/DB/profile thử nghiệm riêng, đã dừng khi kết thúc QA.
- Đã xem screenshot `01-welcome.png`, `04-history.png`, `05-mobile.png`;
  không thấy lỗi bố cục, không tràn ngang trên mobile, không có lỗi JavaScript.
- Công cụ Windows Computer Use không kết nối native pipe sau retry/reset;
  dùng browser QA riêng để hoàn tất kiểm chứng giao diện.
- Đã khởi động server người dùng bằng `start-web.ps1`, lắng nghe
  `http://127.0.0.1:8765`, giữ chạy sau bàn giao. PID/log nằm trong `output/`.
- Đã mở URL bằng công cụ trình duyệt của app, cập nhật README và báo cáo bản web.

Kịch bản đã kiểm chứng bằng UI: chốt bốn quy ước bằng tin nhắn; mở chat mới và
nhớ lại; chuyển JWT sang cookie; mở chat mới dùng cookie; xem context không có
JWT cũ; xem lịch sử superseded; tải JSON bằng chứng; reload giữ chat; project mới
có memory rỗng; Enter gửi và Shift+Enter xuống dòng.

Browser QA đầu tiên chờ trạng thái visible của thẻ HTML option nên timeout;
đã sửa điều kiện sang attached và chạy lại thành công. Log cũ được giữ ở
`output/web-qa/previous-attempt-diagnostic.txt`, kết quả hiện hành là
`output/web-qa/verification.json`. Tệp cấu hình AI được kiểm thử HTTP bằng mock,
không đánh đồng mock hoặc chế độ demo với kết quả model thật.

Phần dưới là nhật ký bản CLI ban đầu.

Ngày thực hiện: 21/10/2026 (UTC+7).

## Prompt đầu vào

- File: `PROMPT_CHALLENGE_A.md`.
- SHA-256: `3a8beb570a71b62bd979b903aa30a2e7fbef62ef583d00f86a36a0311f92abec`.
- Cách thực hiện: agent trong chat tạo file, đọc lại bằng `Get-Content`, tính hash
  bằng `Get-FileHash`, rồi trực tiếp triển khai theo đặc tả trong file đó.
- Markdown là prompt cho agent, không phải mã PowerShell. Không có engine giả
  được dùng để tuyên bố đã thực thi một prompt bất kỳ.

## Các bước đã hoàn tất

1. Đọc toàn bộ text của PDF 52 trang để xác định phạm vi; xem ảnh slide 12,
   14 và 15 để đối chiếu yêu cầu và cách xử lý memory lỗi thời.
2. Tạo prompt riêng cho Challenge A, đọc lại, đối chiếu hash trước khi viết code.
3. Tạo `memory_agent.py`: SQLite memory có phiên bản và lịch sử; retrieve/inject
   quy ước active; CLI mở session mới; agent offline và adapter API tùy chọn.
4. Tạo `demo.py`: năm process độc lập, database riêng cho mỗi lần demo, log và
   request/response artifact, lịch sử memory và assertion tự động.
5. Tạo 16 test kiểm tra persistence, thay thế quy ước, metadata, transaction,
   project isolation và HTTP contract của adapter API.
6. Chạy test. Lần đầu sandbox Windows chặn thư mục tạm; chạy lại ngoài sandbox
   sau khi được cho phép để xác minh. Điều chỉnh test sử dụng thư mục tạm dưới
   workspace; lần kiểm thử cuối trong sandbox đạt đủ 16 test.
7. Chạy demo offline thành công, lưu bằng chứng của cả năm session/process.
8. Viết `README.md`, `BAO_CAO_CHALLENGE_A.md` và nhật ký này, phân biệt rõ chứng
   minh harness/offline với kiểm chứng LLM thật chưa thực hiện.

## Lệnh đã chạy và kết quả bàn giao

```powershell
Get-Content -LiteralPath 'PROMPT_CHALLENGE_A.md'
Get-FileHash -LiteralPath 'PROMPT_CHALLENGE_A.md' -Algorithm SHA256
python -X utf8 demo.py
python -X utf8 -m unittest discover -s tests -v
```

Lệnh demo/test được gọi qua Python subprocess để thu stdout/stderr và lưu log.
Không thay thế kết quả thực thi bằng nội dung tự viết.

| Kiểm tra | Kết quả | Bằng chứng |
| --- | --- | --- |
| Năm session/process độc lập | Đạt | `output/demo/20261021T021735Z-83c61c69/verification.json` |
| S2 nhớ quy ước ban đầu | Đạt | `s2-cold-start.log` trong thư mục demo trên |
| S4/S5 dùng session cookie | Đạt | `s4-cold-start.log`, `s5-cold-start.log` |
| JWT cũ có lịch sử superseded | Đạt | `memory-history.json` |
| Assertion demo offline | 15/15 đạt | `verification.json`, `output/demo-run.log` |
| Unit/integration/HTTP mock tests | 16/16 đạt | `output/tests.log` |
| Gọi LLM thật | Chưa chạy | Không có `OPENAI_API_KEY` và `OPENAI_MODEL` |

Demo bắt đầu khoảng 09:17:35 ngày 21/10/2026 (UTC+7). Timestamp trong file JSON
dùng UTC. Thư mục bằng chứng được tạo riêng, không ghi đè database người dùng.

API adapter tham khảo [OpenAI Docs](https://developers.openai.com/api/docs/guides/text).
Không có API key nào được đọc từ file credential, ghi vào mã nguồn hoặc log.
Test HTTP dùng secret giả và mock, không phải request đến model thật.

## Đối chiếu tiêu chí prompt

Các yêu cầu 1–5 được thể hiện trong báo cáo, SQLite store và request artifact;
yêu cầu 6 có hai adapter với giới hạn ghi rõ; yêu cầu 7–8 có demo và test đã chạy;
yêu cầu 9–10 có README và báo cáo. Prompt hash trong verification trùng file đầu
vào. Không triển khai Challenge B hoặc C.
