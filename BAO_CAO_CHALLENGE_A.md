# Báo cáo Challenge A: Persistent memory

## Bổ sung: bản web chatbot theo yêu cầu tiếp theo

Đã triển khai ứng dụng **Memory Chat**, chạy tại [localhost](http://127.0.0.1:8765).
Chạy lại bằng `python -X utf8 webapp.py` hoặc `start-web.ps1`. Mã nguồn và dữ liệu
nằm trong cùng workspace. Web không cần pip/npm; frontend HTML/CSS/JS, backend
Python standard library, dùng lại `MemoryStore` SQLite.

Giao diện có chat, lịch sử cuộc trò chuyện, chat mới, chọn/tạo project, bộ nhớ
active, lịch sử quy ước bị thay thế, xem request thực tế và xuất bằng chứng JSON.
Chat và memory tồn tại sau reload hoặc restart; hai project có bộ nhớ riêng.

Yêu cầu mới cho phép quyết định trong tin nhắn thông thường, thay cho ràng buộc
`--remember` của prompt CLI ban đầu. Prompt mới là `PROMPT_WEB_CHALLENGE_A.md`,
đã được tạo, đọc lại và thực hiện trong cùng phiên agent.

### Luồng AI và cập nhật memory

Ở chế độ OpenAI, harness gọi model trích các quyết định rõ ràng trong **chính tin
nhắn mới**, trả JSON theo schema với key/value/evidence. Harness kiểm tra key,
giá trị, bằng chứng nguyên văn và ghi quyết định vào SQLite. Sau đó retrieve
memory mới, ghép history của **riêng chat hiện tại**, rồi gọi model trả lời.
Không tự động ghi lời assistant hoặc history của chat khác vào memory.

Chat mới có history rỗng, nhưng memory vẫn được retrieve theo project. Quy ước
đổi vẫn dùng cơ chế version/active/superseded nguyên tử của bản CLI. JWT cũ có
trong lịch sử audit nhưng không được inject vào memory block mới. Transcript cũ
không được mang sang chat mới. Trong chat cũ, instructions quy định memory active
hiện tại có ưu tiên hơn quy ước cũ còn nằm trong history.

API key được nhập trong **Cài đặt AI**, chỉ giữ ở RAM phía server; không lưu DB,
file hoặc localStorage và không trả key về client. Nút kết nối thực hiện một
request thử trước khi áp dụng cấu hình. DB web là `data/web-chat.sqlite3`, tách
khỏi DB CLI và bằng chứng trước đó. Đây là ứng dụng localhost cho một người dùng,
chưa phải dịch vụ nhiều tài khoản trên Internet.

### Kết quả kiểm chứng bản web

- **28/28 test đạt**: 16 test ban đầu và 12 test web, qua HTTP server thật trong
  thư mục thử nghiệm. Đã kiểm tra natural decision, chat/session mới, cookie thay
  JWT, cô lập project, reload/restart, idempotency, lỗi API và giữ key ngoài DB.
  Log: `output/web-tests.log`.
- **13/13 kiểm tra trình duyệt đạt**: Edge headless, server/database/profile riêng.
  Có kiểm tra gửi Enter, Shift+Enter, lưu bốn quy ước, chat mới nhớ quy ước, đổi
  cookie và chat mới không inject JWT, xem lịch sử, xuất file, tải lại chat,
  project riêng, UI cấu hình AI và viewport điện thoại không tràn ngang.
- Không có lỗi JavaScript trong trình duyệt. Đã xem ảnh desktop, lịch sử và
  mobile để kiểm tra trực quan.
- Bằng chứng: `output/web-qa/verification.json`, `browser-export.json` và sáu ảnh
  `01-welcome.png` đến `06-ai-settings.png`.

Công cụ điều khiển cửa sổ Windows không kết nối được native pipe dù đã thử lại
và reset. Kiểm tra giao diện được hoàn tất bằng Playwright/Edge headless trong
phiên riêng. Server kiểm thử đã dừng; server dùng thật ở cổng 8765 được giữ chạy.

Các bài test API vẫn dùng mock, **không có kết quả gọi LLM thật trong bằng chứng
bàn giao**. Hiện chưa có API key từ môi trường khi triển khai; web có chế độ demo
ghi nhãn rõ. Để hỏi đáp tự do như chatbot AI, người dùng kết nối key trong Cài
đặt. Demo nhận diện một tập quyết định công nghệ theo quy tắc; không được coi là
LLM hoặc khẳng định hiểu mọi câu tiếng Việt. Trích quyết định bằng model cũng
cần đánh giá thực tế, evidence check không bảo đảm mọi suy luận đều đúng.

Phần dưới giữ nguyên phân tích và bằng chứng **bản CLI ban đầu**.

## 1. Phân tích yêu cầu trong slide

Nguồn đề: `slide.pdf`, slide 14–15. Khái niệm dùng để thiết kế lấy từ slide 7–13
và so sánh lựa chọn lưu trữ ở slide 16. Chỉ triển khai Challenge A.

Mục tiêu là agent nhớ quy ước dự án qua nhiều session và cập nhật khi quy ước
thay đổi. Slide 14 yêu cầu hai chứng minh:

1. Session mới vẫn dùng đúng quy ước đã thống nhất trước đó.
2. Sau khi đổi quy ước, các session tiếp theo dùng quy ước mới.

Đề cho phép dùng lại agent sẵn có và nêu timebox 30 phút. Slide 15 gợi ý lựa chọn
nơi lưu, người ghi, thời điểm nạp, cách xử lý quy ước cũ và in memory đã inject.
Đây là các lựa chọn thiết kế và gợi ý kiểm chứng; đề không bắt buộc database hay
nhà cung cấp model cụ thể. Bài chọn SQLite trong thư viện chuẩn để tập trung vào
hai chứng minh, không cần cài đặt dịch vụ.

## 2. Quyết định thiết kế

| Câu hỏi | Cách thực hiện | Lý do |
| --- | --- | --- |
| Lưu ở đâu? | File SQLite, bảng `conventions` | Persist qua process; hỗ trợ transaction và unique index |
| Ai ghi? | Harness nhận `--remember key=value` có `--source` | Chỉ ghi quyết định rõ ràng; không suy diễn từ hội thoại |
| Khi nào nạp? | Mỗi lần mở session, sau khi áp dụng quyết định của session đó | Session luôn có snapshot quy ước hiện hành lúc retrieve |
| Đọc gì? | Chỉ các bản active của đúng project | Cô lập project và không dùng quy ước đã lỗi thời |
| Khi thay đổi? | Supersede bản cũ, thêm version mới trong một transaction | Không để hai quy ước mâu thuẫn cùng active; giữ lịch sử |
| Chứng minh nạp thật? | In memory block và lưu chính request agent nhận | Phân biệt dữ liệu trên đĩa với dữ liệu thực sự vào context |

Mỗi quy ước lưu key, value, version, status, source, created_session, created_at,
superseded_at và superseded_by. Khi ghi cùng giá trị, không thêm version mới.
Lỗi trong batch được rollback, bao gồm việc đánh dấu superseded.

System prompt mô tả cách dùng memory nhưng không chứa sẵn TypeScript, PostgreSQL
hay quyết định authentication. Request mới chỉ có instructions, memory active và
task hiện tại. Log phiên trước chỉ nằm ở file bằng chứng. Source được giữ trong
DB để truy vết, không đưa vào context vì câu nguồn có thể nhắc lại quy ước cũ.

## 3. Prompt và cách thực hiện

Đã tạo `PROMPT_CHALLENGE_A.md` trước khi triển khai, sau đó đọc lại bằng terminal
và thực hiện trực tiếp trong phiên agent hiện tại. Prompt quy định phạm vi A,
thiết kế, kịch bản chứng minh và tiêu chí kiểm thử. File Markdown là đặc tả cho
agent, không được giả làm script thực thi.

SHA-256 của prompt:

```text
3a8beb570a71b62bd979b903aa30a2e7fbef62ef583d00f86a36a0311f92abec
```

Lệnh demo và test đã được chạy thật. Nhật ký là `EXECUTION_LOG.md`; hash trên
cũng được lưu trong `verification.json` của lần demo.

## 4. Hai chứng minh bằng thực thi

Lần demo bàn giao: **21/10/2026, khoảng 09:17:35–09:17:37, UTC+7**.
Timestamp kỹ thuật trong JSON và tên thư mục dùng UTC.

Thư mục bằng chứng: `output/demo/20261021T021735Z-83c61c69/`.

| Session | PID | Hành động | Kết quả đã quan sát |
| --- | --- | --- | --- |
| S1 | 2904 | Ghi TypeScript, PostgreSQL, JWT và REST `/api/v1`; JSON snake_case | Bốn quyết định được lưu version 1 |
| S2 | 14464 | Task mới về endpoint hồ sơ; không nhắc stack/auth | Memory inject và response vẫn chứa đủ bốn quy ước |
| S3 | 26384 | Đổi authentication thành session cookie | JWT v1 thành superseded, cookie v2 thành active |
| S4 | 7156 | Task mới về đăng xuất | Memory inject và response dùng cookie; request không chứa JWT |
| S5 | 17940 | Task mới về middleware đăng nhập | Tiếp tục dùng cookie, các quy ước khác được giữ nguyên |

Các session có UUID khác nhau và được chạy bằng `subprocess.run`, mỗi lần là một
Python process mở lại cùng file SQLite. Không truyền transcript cũ vào process
mới. PID và session ID nằm trong từng artifact và `verification.json`.

**Chứng minh 1:** đọc `s2-cold-start.log` hoặc JSON bên trong `s2-cold-start/`.
Task chỉ là “Đề xuất kế hoạch triển khai endpoint lấy hồ sơ người dùng.” Phần
`PROJECT_MEMORY_JSON` vẫn có TypeScript, PostgreSQL, JWT và quy ước API. Trong
response, `conventions_used` khớp đủ bốn quy ước; plan chọn xác minh bearer token
theo JWT.

**Chứng minh 2:** đọc `s4-cold-start.log`, `s5-cold-start.log` và
`memory-history.json`. S4/S5 inject `authentication=session cookie`, version 2.
Response chọn tra session phía server từ cookie. JWT không có trong request
hiện tại, nhưng vẫn tồn tại trong lịch sử với status superseded.

Trích lịch sử authentication thực tế:

| Value | Version | Status | Nguồn | Quan hệ |
| --- | --- | --- | --- | --- |
| JWT | 1 | superseded | Demo user S1: thống nhất stack và API | id=3, superseded_by=5 |
| session cookie | 2 | active | Demo user S3: chuyển từ JWT sang session cookie | id=5 |

JWT được tạo lúc `2026-10-21T02:17:35.728788+00:00`, thay thế lúc
`2026-10-21T02:17:36.500080+00:00`. Bản cookie có created_at bằng thời điểm thay
thế, có source và created_session riêng. Đây là cập nhật có lịch sử, không phải
append hai quy định cùng có hiệu lực hoặc xóa sạch dấu vết JWT.

## 5. Kết quả kiểm thử

`python -X utf8 demo.py` hoàn tất với **15/15 kiểm tra đạt**. Chi tiết nằm trong
`verification.json`: session/process độc lập, S2 nhớ quy ước, S4/S5 dùng quy ước
mới, không inject JWT cũ, không truyền history và bảo toàn metadata.

`python -X utf8 -m unittest discover -s tests -v` hoàn tất với **16/16 test đạt**.
Log cuối: `output/tests.log`. Nhóm kiểm tra gồm:

- Cold start qua subprocess, thay đổi JWT sang cookie và không rò quy ước cũ.
- Nguồn, session, thời điểm, liên kết phiên bản; ghi trùng không tạo version.
- Cô lập project; quay lại giá trị cũ tạo version 3.
- Rollback khi giả lập lỗi ghi sau khi đã retire bản cũ; unique index chặn hai
  phiên bản active; batch không hợp lệ không ghi dở dang.
- Memory rỗng không bịa stack; stack khác như Go/MariaDB lấy từ context.
- Thiếu cấu hình API lỗi trước khi ghi DB; API lỗi được ghi artifact failed.
- HTTP mock kiểm tra payload và output_text, response incomplete/refusal và
  lỗi HTTP 401. Các test này không gọi model thật.

Lần kiểm thử đầu gặp giới hạn truy cập thư mục tạm của sandbox Windows. Đã xác
minh ngoài sandbox sau khi được cho phép, sau đó đặt thư mục tạm của test dưới
`tmp/tests/` trong workspace. Lần kiểm thử bàn giao chạy thành công trong sandbox.

## 6. Mức độ chứng minh và hạn chế

Kết quả hiện tại chứng minh persistent memory của harness và hành vi của agent
offline theo quy tắc. Nó không phải bằng chứng LLM thực sự tuân thủ quy ước.
Môi trường chưa có API key/model nên chưa chạy phần OpenAI end-to-end. Bài có
adapter để sử dụng cùng cơ chế inject với LLM thật; hướng dẫn trong README.

Offline planner minh họa áp dụng stack/authentication, không hiểu task tự do hay
sinh ứng dụng hoàn chỉnh. Memory chỉ thay đổi qua quyết định có cấu trúc. LLM
adapter nhận chỉ dẫn xử lý mâu thuẫn, nhưng chỉ dẫn đó chưa được kiểm chứng bằng
model thật. Trong API demo, assertion kiểm chứng request, còn response phải được
đọc để đánh giá tuân thủ; không đánh đồng API trả 200 với đáp ứng đúng đề.

Các quy ước được nạp theo project khi bắt đầu session; nếu process khác cập nhật
giữa một lần gọi model đang chạy, lần gọi đó dùng snapshot đã inject. Session
tiếp theo sẽ retrieve bản mới. Với số lượng quy ước nhỏ của Challenge A, cách này
đủ đơn giản và có thể kiểm tra trực tiếp. Không triển khai Challenge B/C.
