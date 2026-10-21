# Challenge A: Chatbot web có bộ nhớ dự án

## Chạy giao diện chatbot

Ứng dụng web đã có giao diện chat tiếng Việt, nhiều cuộc trò chuyện, bộ nhớ theo
project, lịch sử thay thế và xem context thực sự nạp cho mỗi lượt.

```powershell
python -X utf8 webapp.py
```

Mở [Memory Chat](http://127.0.0.1:8765) trong trình duyệt. Hoặc chạy server ẩn:

```powershell
.\start-web.ps1
```

Không cần pip/npm để sử dụng. Server lắng nghe trên localhost; đây là ứng dụng
web chạy trên máy bạn. Đổi cổng nếu cần: `python -X utf8 webapp.py --port 8766`.

### Trò chuyện như bình thường

Vào **Cài đặt AI → AI thật**, nhập OpenAI API key, chọn model rồi bấm
**Kiểm tra kết nối & lưu**. Khi kết nối thành công bạn có thể hỏi đáp, yêu cầu
giải thích, viết code và trao đổi tiếp trong cùng chat. Có thể cấu hình bằng
`OPENAI_API_KEY` và `OPENAI_MODEL` trước khi khởi động server thay cho nhập qua UI.
Default model của bản web là `gpt-5-mini`, có thể thay trong Cài đặt.

API key chỉ giữ trong RAM của server. Không ghi key vào database, file, request
trace hay localStorage. Khi khởi động lại server, cần nhập lại key trừ khi đã
cấu hình từ môi trường. Các lượt chat thật dùng hạn mức API của tài khoản bạn.

Khi chưa có key, ứng dụng hiển thị **Demo · không dùng LLM**. Demo hỗ trợ các
quyết định công nghệ quen thuộc và tra cứu memory bằng quy tắc; không phải chatbot
AI đầy đủ. Không tự fallback sang demo nếu lời gọi API thật thất bại.

### Chứng minh Challenge A trực tiếp bằng giao diện

1. Nhắn: “Dự án dùng TypeScript, PostgreSQL và JWT. Chúng ta chọn API REST
   /api/v1 với JSON snake_case.” Kiểm tra bốn quy ước ở **Bộ nhớ dự án**.
2. Bấm **Cuộc trò chuyện mới**, hỏi: “Bạn đang nhớ quy ước nào của dự án?”
   Chat mới có history rỗng nhưng vẫn dùng memory vừa lưu.
3. Nhắn: “Chuyển authentication từ JWT sang session cookie.” Bản mới thành
   active, JWT cũ thành superseded và có thể xem ở tab **Lịch sử**.
4. Tạo chat mới lần nữa, yêu cầu lập kế hoạch middleware đăng nhập. Câu trả lời
   dùng cookie. Bấm **Xem ngữ cảnh** để thấy memory thật đã inject; request của
   chat mới không mang theo JWT hoặc transcript chat trước.
5. Tải lại trang hoặc khởi động lại server: chat và memory vẫn còn. Tạo project
   khác để kiểm tra memory được cô lập.

Nút **Xuất bằng chứng Challenge A** tải JSON gồm memory, lịch sử và request/response
của các chat trong project hiện tại. Tệp có nội dung chat bạn đã nhập; không có
API key. Bằng chứng cũ của CLI vẫn giữ nguyên.

### Cơ chế web

AI thật xử lý hai bước cho mỗi tin nhắn: dùng [Structured Outputs của OpenAI](https://developers.openai.com/api/docs/guides/structured-outputs)
để trích quyết định rõ ràng từ tin nhắn mới, kiểm tra trích dẫn nguyên văn, rồi
ghi SQLite; sau đó retrieve memory active và gọi model trả lời. Câu hỏi, giả định
hoặc lời assistant không được coi là quyết định. Đây là bước harness trích memory
thay cho tham số `--remember` của CLI theo yêu cầu bổ sung của người dùng.

History hội thoại được lưu riêng, chỉ history của chính chat đó được đưa vào
request. Nguồn quyết định và quy ước superseded không được đưa vào memory block.
Khi quay lại chat cũ, history cũ vẫn có thể nhắc quy ước cũ; instructions xác định
memory active hiện tại là quy ước được áp dụng. Chat mới có context sạch.

DB mặc định: `data/web-chat.sqlite3`. Bản CLI dùng DB khác, không bị thay đổi.
Turn ID chống gửi trùng; lỗi API có thể thử lại cùng tin nhắn. Nếu một quyết định
đã lưu nhưng bước trả lời lỗi, quyết định vẫn còn, trạng thái lượt là failed.

### Kiểm thử bản web

```powershell
python -X utf8 -m unittest discover -s tests -v
```

Bộ test gồm bản CLI và HTTP integration của web. Log lần chạy bàn giao:
**28/28 test đạt**, `output/web-tests.log`. Kiểm tra trình duyệt đạt **13/13**,
bằng chứng ở `output/web-qa/verification.json`, ảnh và JSON xuất từ UI trong
cùng thư mục. Trong sandbox Windows, test socket localhost có thể cần
quyền chạy ngoài sandbox; chạy terminal Python bình thường trên máy thì không
cần thay đổi ứng dụng.

`scripts/browser-check.cjs` là công cụ QA phát triển tùy chọn, cần Playwright và
trình duyệt Edge/Chrome. Không phải dependency của ứng dụng. Nó chạy trên server,
DB và profile thử nghiệm riêng; không sửa chat ở server đang dùng.

Mã mới: `webapp.py`, `chat_engine.py`, thư mục `web/`, `start-web.ps1`,
`tests/test_webapp.py`. Prompt mở rộng: `PROMPT_WEB_CHALLENGE_A.md`.

## Bản CLI và demo gốc

Harness giúp agent nhớ quy ước dự án giữa các session độc lập và dùng quy ước mới
khi quyết định thay đổi. Bài chỉ triển khai Challenge A ở slide 14–15 của `slide.pdf`.

Kết quả bàn giao bản CLI ban đầu: **5 session/process độc lập, 15/15 kiểm tra demo, 16/16 unit/integration
tests đạt**. Kết quả hiện có là **agent offline theo quy tắc**, không phải kết quả
LLM. Adapter LLM thật đã có và được kiểm thử bằng mock HTTP; chưa gọi API thật vì
môi trường không có `OPENAI_API_KEY` và `OPENAI_MODEL`.

## Chạy nhanh trên PowerShell

Cần Python 3.10+ có SQLite. Không cần pip, dịch vụ database hoặc mạng cho demo.
Mở terminal trong thư mục chứa README này:

```powershell
python -X utf8 demo.py
python -X utf8 -m unittest discover -s tests -v
```

Mỗi lần demo tạo một thư mục `output/demo/<timestamp>-<id>/` riêng với database,
5 log, 5 JSON request/response, `memory-history.json` và `verification.json`.
`output/LATEST_DEMO.txt` trỏ đến lần chạy gần nhất. Demo không dùng hoặc xóa DB
của các lệnh CLI thủ công.

Xem bằng chứng lần chạy mới nhất:

```powershell
$demoPath = Get-Content .\output\LATEST_DEMO.txt
Get-Content (Join-Path $demoPath 'verification.json')
Get-Content (Join-Path $demoPath 's2-cold-start.log')
Get-Content (Join-Path $demoPath 's4-cold-start.log')
Get-Content (Join-Path $demoPath 'memory-history.json')
```

## Thử thủ công bằng các session mới

Mỗi lệnh `run` tạo UUID mới, mở lại SQLite, retrieve quy ước active rồi inject
vào context. Hai lệnh liên tiếp không chia sẻ biến Python hoặc transcript.

```powershell
# Session 1: quyết định rõ ràng do người dùng cung cấp
python -X utf8 memory_agent.py run --project my-project `
  --task 'Ghi nhận quyết định dự án.' `
  --remember 'language=TypeScript' `
  --remember 'database=PostgreSQL' `
  --remember 'authentication=JWT' `
  --remember 'api_style=REST /api/v1; snake_case JSON' `
  --source 'Người dùng thống nhất stack ban đầu'

# Session 2: không nhắc lại stack hoặc authentication
python -X utf8 memory_agent.py run --project my-project `
  --task 'Đề xuất kế hoạch triển khai endpoint hồ sơ.'

# Session 3: thay thế quy ước cũ
python -X utf8 memory_agent.py run --project my-project `
  --task 'Ghi nhận thay đổi authentication.' `
  --remember 'authentication=session cookie' `
  --source 'Người dùng xác nhận chuyển sang session cookie'

# Session 4: dùng quy ước mới
python -X utf8 memory_agent.py run --project my-project `
  --task 'Đề xuất kế hoạch triển khai endpoint đăng xuất.'

# Xem cả quyết định cũ và mới
python -X utf8 memory_agent.py history --project my-project
```

CLI mặc định dùng `data/memory.sqlite3`, ghi request/response vào `output/sessions/`.
Có thể chỉ định `--db` và `--artifacts`. Dùng cùng đường dẫn DB và cùng project
để chia sẻ memory; project khác không đọc quy ước của nhau.

## Thiết kế và chính sách memory

```text
Người dùng --remember key=value + --source
       -> harness ghi/thay thế quyết định trong transaction SQLite
       -> retrieve WHERE project=? AND status='active'
       -> build_request: system instructions + memory JSON + task hiện tại
       -> in memory đã inject
       -> offline planner hoặc LLM adapter
       -> lưu request/response, session ID, PID và trạng thái
```

| Thành phần | Trong bài này |
| --- | --- |
| State | UUID session, PID, thời điểm bắt đầu/kết thúc, trạng thái chạy |
| History | Log và JSON của từng session, không đưa lại vào request sau |
| Memory | Quy ước có chọn lọc trong bảng `conventions` của SQLite |
| Context | System prompt, các quy ước active được retrieve, task hiện tại |

Harness ghi memory từ quyết định có cấu trúc `--remember`; không tự trích toàn bộ
hội thoại. Task và output agent không được tự động biến thành quy ước. `--source`
ghi nguồn để kiểm tra lại, không phải cơ chế xác thực người dùng.

Mỗi project/key có tối đa một bản active, được SQLite bảo đảm bằng unique partial
index. Khi thay đổi: khóa ghi bằng `BEGIN IMMEDIATE`, đánh dấu bản cũ superseded,
thêm version mới active, liên kết `superseded_by`, rồi commit cả batch. Nếu lỗi,
rollback toàn bộ batch. Ghi lại đúng cùng giá trị không thêm version. Quay lại
giá trị cũ tạo version mới thay vì kích hoạt lại bản lịch sử.

Nguồn, session tạo, thời điểm và bản bị thay thế nằm trong DB và history export.
Context chỉ chứa key, value, version, created_at của quy ước active. Nguồn quyết
định có thể nhắc lại giá trị cũ, nên không inject trường nguồn vào context.

Offline planner chỉ nhận request đã tạo, không nhận DB. Stack không được hardcode
trong system prompt: test dùng Rust/SQLite và Go/MariaDB để kiểm tra điểm này.
Các nhánh JWT/cookie minh họa hành vi theo giá trị memory, không phải lựa chọn
authentication mặc định.

## Chạy với LLM thật (tùy chọn)

Adapter dùng [OpenAI Responses API](https://developers.openai.com/api/docs/guides/text).
Mỗi request độc lập gửi `instructions`, memory và task; `store=false`, không có
`previous_response_id` hoặc `conversation`. Model được chọn qua `OPENAI_MODEL`.
Không có key/model thì báo lỗi, không tự chuyển sang offline.

Sau khi cấu hình biến môi trường `OPENAI_API_KEY` và `OPENAI_MODEL` trong phiên
PowerShell hiện tại, chạy:

```powershell
# Gọi model một lần trên memory của project thủ công
python -X utf8 memory_agent.py run --provider openai --project my-project `
  --task 'Đề xuất kế hoạch triển khai endpoint đăng xuất theo quy ước dự án.'

# Chạy kịch bản 5 session với model thật (5 API requests)
python -X utf8 demo.py --provider openai
```

Không đặt API key vào source, prompt, tham số CLI hoặc file bằng chứng. Request
artifact không chứa header Authorization. Chế độ API có phí theo tài khoản/model.
Trong chế độ API, demo tự kiểm tra persistence và memory injection; cần đọc thêm
response của model ở S2/S4/S5 để xác nhận model thực sự tuân thủ quy ước. Trường
`llm_answer_semantics_verified` giữ `false` vì không có bộ chấm ngữ nghĩa tự động.

Nếu quyết định đã commit nhưng API lỗi, memory vẫn giữ quyết định rõ ràng của
người dùng; artifact ghi `status=failed`. Thiếu cấu hình API được phát hiện trước
khi ghi DB.

## File bàn giao và phạm vi kiểm chứng

| File | Vai trò |
| --- | --- |
| `PROMPT_CHALLENGE_A.md` | Prompt được tạo, đọc lại và thực hiện bởi agent trong chat |
| `memory_agent.py` | SQLite store, context injection, CLI và hai agent adapter |
| `demo.py` | Kịch bản 5 process và 15 assertion offline |
| `tests/test_memory_agent.py` | 16 test về persistence, lịch sử, rollback, cô lập và HTTP contract |
| `BAO_CAO_CHALLENGE_A.md` | Phân tích đề và đối chiếu bằng chứng thực thi |
| `EXECUTION_LOG.md` | Nhật ký thực hiện prompt, hash và lệnh đã chạy |
| `output/tests.log` | Kết quả kiểm thử cuối cùng đã chạy |
| `output/demo-run.log` | Console của lần demo bàn giao |

Markdown prompt được agent đọc và thực hiện như đặc tả; nó không phải script
PowerShell. Nhật ký và hash prompt trong `verification.json` giúp đối chiếu prompt
đã dùng. Muốn chạy lại phần chứng minh chỉ cần `python -X utf8 demo.py`.

Đây là bản thực hành nhỏ. Offline planner không hiểu task tự do, không tự phát
hiện xung đột ngôn ngữ tự nhiên và không sinh ứng dụng hoàn chỉnh. LLM thật chưa
được kiểm chứng end-to-end. Bài dùng key chuẩn hóa, nạp tất cả quy ước active của
một project nhỏ; chưa có tìm kiếm ngữ nghĩa, phân quyền nhiều người dùng hoặc
chính sách xóa memory. Không triển khai các phần Challenge B/C.
