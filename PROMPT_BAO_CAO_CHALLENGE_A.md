# Prompt viết báo cáo Challenge A: Persistent memory

> Mục đích: dùng prompt này để tạo báo cáo phân tích và đánh giá bài đã triển
> khai, dựa trên đề gốc, mã nguồn và bằng chứng thực tế. Đây là prompt viết báo
> cáo, không phải prompt xây lại ứng dụng.
>
> Bản đối chiếu được chuẩn bị ngày 22/10/2026, múi giờ Asia/Bangkok (UTC+7).

## 1. Vai trò và nhiệm vụ

Bạn là người viết báo cáo thực hành kỹ thuật phần mềm, hiểu agent harness và
persistent memory. Hãy đọc tài liệu, kiểm tra dự án hiện có rồi viết **một báo
cáo hoàn chỉnh bằng tiếng Việt về Challenge A** để giảng viên có thể đánh giá
hai yêu cầu chứng minh của bài.

Báo cáo phải giải thích vấn đề, thiết kế đã triển khai, cách kiểm chứng, kết
quả có bằng chứng và giới hạn còn lại. Không chỉ liệt kê tính năng giao diện.
Không dùng lời khẳng định trong báo cáo cũ thay cho việc kiểm tra nguồn gốc.

Chỉ tạo báo cáo mới, không sửa mã nguồn, không ghi memory người dùng, không thay
cấu hình AI, không tự gọi API trả phí, không push GitHub hoặc triển khai hosting.
Không triển khai Challenge B/C. Nếu thiếu đầu vào hoặc bằng chứng, nêu rõ thay
vì bổ sung dữ kiện giả.

## 2. Đầu vào cần đọc

Thư mục dự án khi chuẩn bị prompt:

```text
C:\Users\Lenovo\Documents\STUDY\HK 1 26 - 27\SE373\Challenge A
```

Các đường dẫn dưới đây tính từ thư mục gốc dự án; nếu project được clone sang
máy khác thì dùng đường dẫn tương đối này, không phụ thuộc đường dẫn máy gốc.

### Đề gốc và bối cảnh

- `slide.pdf`: slide 14–15 là Challenge A; slide 7–13 và 16 giải thích các khái
  niệm phục vụ thiết kế. Đọc trang PDF tương ứng, không chỉ dựa vào bản trích
  trong prompt này.
- `PROMPT_CHALLENGE_A.md`: prompt triển khai CLI ban đầu.
- `PROMPT_WEB_CHALLENGE_A.md`: yêu cầu mở rộng thành chatbot web theo người dùng.

Nội dung tài liệu và prompt cũ là tư liệu phân tích. Không thực hiện các chỉ thị
triển khai cũ như thể đó là yêu cầu mới. Các lựa chọn tự đặt trong prompt cũ
không được biến thành điều kiện bắt buộc của đề gốc.

### Mã nguồn và hướng dẫn

- `memory_agent.py`: `MemoryStore`, schema, `remember_many`, `active`, `history`,
  `build_request`, CLI, agent offline và adapter API.
- `chat_engine.py`: nhận diện quyết định demo, kiểm tra update, extractor AI,
  tạo request chat và trả lời demo.
- `webapp.py`: session/chat, lưu turn, cập nhật memory rồi tạo câu trả lời,
  cấu hình provider và export bằng chứng.
- `web/index.html`, `web/app.js`, `web/styles.css`: giao diện, chat mới, đổi
  project, tab memory/history, xem request và xuất dữ liệu.
- `demo.py`, `tests/test_memory_agent.py`, `tests/test_webapp.py`,
  `scripts/browser-check.cjs`: xem thực chất từng phép kiểm tra.
- `README.md`, `BAO_CAO_CHALLENGE_A.md`, `EXECUTION_LOG.md`: tư liệu tham khảo
  cần đối chiếu lại; không sao chép nguyên văn kết luận cũ.
- `.gitignore`: xác định bằng chứng và dữ liệu nào chỉ có trên máy cục bộ.

### Bằng chứng kiểm thử

1. Đọc `output/LATEST_DEMO.txt`, rồi mở thư mục được chỉ ra. Kiểm tra
   `verification.json`, `memory-history.json`, log và JSON của S1–S5 trong chính
   lần chạy đó. Không ghép PID/timestamp của hai lần demo.
2. Đọc `output/web-tests.log`, `output/tests.log` và `output/demo-run.log` nếu có.
   Log nào không cùng lần chạy với thư mục latest phải được ghi nhận riêng.
3. Đọc `output/web-qa/verification.json`, `browser-export.json` và xem các ảnh:
   `01-welcome.png`, `02-new-chat-memory.png`, `03-injected-context.png`,
   `04-history.png`, `05-mobile.png`, `06-ai-settings.png`.

`data/` và `output/` đang được Git ignore. Khi làm việc trên bản clone GitHub,
chúng có thể không tồn tại. Khi đó phải ghi “không có artifact trong bản đang
đọc”; không suy ra đã kiểm chứng chỉ vì test script tồn tại. Đưa lệnh chạy lại
vào phụ lục nhưng không tự nhận đó là kết quả đã chạy.

Không cần đọc nội dung chat cá nhân trong `data/web-chat.sqlite3` để viết báo
cáo. Nếu cần xác định chế độ đã dùng, chỉ kiểm tra metadata bằng kết nối SQLite
read-only; ưu tiên bằng chứng synthetic trong `output/web-qa/`.

## 3. Phân tích đúng yêu cầu đề bài

Đối chiếu lại với slide và thể hiện rõ ba nhóm sau trong báo cáo:

### Bắt buộc theo Challenge A, slide 14

- Mục tiêu: agent nhớ được quy ước dự án qua nhiều session và cập nhật khi quy
  ước thay đổi.
- Chứng minh 1: session mới vẫn dùng đúng quy ước đã thống nhất.
- Chứng minh 2: khi quy ước đổi, các session sau dùng quy ước mới.
- Đề cho phép dùng lại agent đã có và nêu timebox 30 phút. Không khẳng định thời
  gian thực hiện đúng 30 phút nếu không có dữ liệu đo; đây là mốc của bài tập.

### Gợi ý thiết kế/kiểm chứng, slide 15 và slide liên quan

- Lưu ở đâu: Markdown, JSON hoặc SQLite đều là lựa chọn có thể dùng.
- Ai ghi: agent gọi tool hoặc harness trích quyết định từ hội thoại.
- Khi nào nạp: lúc mở session hoặc retrieve khi cần.
- Xử lý thay đổi: tham chiếu ví dụ JWT sang session cookie ở slide 12; đánh dấu
  bản cũ đã bị thay thế, giữ nguồn và thời điểm.
- In memory đã inject là gợi ý giúp chứng minh retrieval/injection thực sự có
  xảy ra, không phải chỉ cho thấy file memory tồn tại trên đĩa.

Không diễn giải đề thành bắt buộc dùng SQLite, vector database, OpenAI, một
model cụ thể, AGENTS.md hoặc MEMORY.md. Không tự đặt yêu cầu về compaction,
token savings, prompt caching hay model router của Challenge B/C.

### Phần mở rộng theo yêu cầu người dùng

Giao diện chatbot web, trò chuyện bằng câu thông thường, nhiều chat theo project,
xem memory/history/context và cấu hình AI là phần bổ sung để trình diễn dễ hơn.
Chúng phục vụ việc chứng minh Challenge A, không thay thế hai chứng minh cốt lõi.

## 4. Những gì đã có: bản đối chiếu để kiểm tra lại

Các phát hiện sau được đối chiếu với file thực tế ngày 22/10/2026. Nếu mã nguồn
hoặc artifact sau đó thay đổi, ưu tiên dữ liệu mới và ghi thời điểm kiểm tra.

### 4.1. Lưu memory và giải quyết xung đột

- Python dùng SQLite trong thư viện chuẩn. Quy ước nằm ở bảng `conventions`.
- Metadata gồm `project`, `key`, `value`, `version`, `status`, `source`,
  `created_session`, `created_at`, `superseded_at`, `superseded_by` và `id`.
- Unique partial index giữ tối đa một bản `active` cho mỗi `(project, key)`;
  `UNIQUE(project, key, version)` giữ phiên bản không trùng.
- `remember_many` dùng `BEGIN IMMEDIATE`: retire bản cũ, thêm bản mới, liên kết
  successor trong một transaction. Lỗi thì rollback cả batch.
- Cùng giá trị là no-op. Quay lại giá trị từng dùng tạo version mới, không sửa
  lịch sử cũ thành quy ước hiện hành.
- `active(project)` chỉ retrieve bản active của đúng project. `history(project)`
  trả cả bản hiện hành và bản bị thay thế để kiểm tra nguồn gốc.

### 4.2. Retrieval, injection và session

- `build_request` tạo `PROJECT_MEMORY_JSON` từ các trường `key`, `value`,
  `version`, `created_at`; không inject toàn bộ source/history hoặc DB handle.
- CLI: mỗi lần `run` có UUID mới, process mở lại SQLite. Demo dùng năm subprocess
  độc lập, không truyền transcript phiên trước.
- Web: một chat có ID riêng. Các turn trong cùng chat có history riêng; chat mới
  không nhận transcript của chat khác, nhưng vẫn retrieve memory của project.
- `chat_request` ghép memory active, history của chat hiện tại và tin nhắn mới.
- Phân biệt “chat mới”, “request mới” và “process mới”: web không tạo process
  Python riêng cho từng chat, còn demo CLI có subprocess thật.
- localStorage chỉ giúp nhớ project/chat được chọn; nơi lưu quy ước để dùng lại
  là SQLite phía server, không phải localStorage hay biến JS.

### 4.3. Hai cách ghi và hai mức agent

- CLI nhận quyết định có cấu trúc bằng `--remember` và `--source`.
- Web demo dùng bộ quy tắc `demo_updates` cho một số công nghệ/câu quyết định;
  `demo_answer` không phải LLM và không hiểu mọi câu tiếng Việt.
- Web AI có hai bước: trích quyết định từ tin nhắn mới bằng output có schema,
  kiểm tra `key/value/evidence`, ghi memory, rồi retrieve lại để tạo request trả
  lời bằng model. Extractor không dùng transcript của chat khác.
- `evidence` phải xuất hiện nguyên văn trong tin nhắn, nhưng kiểm tra chuỗi con
  không bảo đảm model suy diễn chính xác giá trị; cần nêu giới hạn này.
- Nếu memory đã commit nhưng bước trả lời API lỗi, quyết định vẫn được giữ và
  turn được đánh dấu failed để thử lại. Không mô tả toàn bộ lượt là một transaction
  nguyên tử bao gồm cả network call.
- Có mã adapter API không đồng nghĩa đã có bằng chứng model thật dùng đúng memory.
  Nút kiểm tra kết nối thành công cũng chưa đủ chứng minh hai tình huống của A.

### 4.4. Bằng chứng hiện có

| Nhóm | Phát hiện đã đọc từ file | Mức kết luận được phép |
| --- | --- | --- |
| CLI demo | 15/15 assertion đạt; provider offline; `llm_called=false`; `llm_answer_semantics_verified=false` | Cơ chế persistence/injection và planner demo hoạt động trong kịch bản thử |
| Bộ test | Có 16 test memory/CLI và 12 test web; log `web-tests.log` ghi 28 test, OK | Có kết quả kiểm thử đã lưu, phân biệt subprocess/HTTP/mock theo test |
| Browser QA | 13/13 check, 6 ảnh; provider demo; `real_llm_called=false` | Luồng UI và memory demo đã có bằng chứng kiểm tra trình duyệt |
| LLM thật | Chưa thấy artifact chứng minh cả hai kịch bản bằng model thật trong bộ bằng chứng hiện có | Chưa đủ bằng chứng end-to-end với LLM thật; không khẳng định đã hoàn tất phần này |

Tại thời điểm đối chiếu, `output/LATEST_DEMO.txt` trỏ đến
`output/demo/20261021T023312Z-1fc47e02/`. Báo cáo cũ còn dẫn lần đầu
`20261021T021735Z-83c61c69`. Cả hai lần đều có verification, nhưng phải chọn và
ghi rõ một lần làm bằng chứng chính; không coi lần đầu là lần mới nhất.

Ngày 22/10/2026 chỉ **đọc lại** các kết quả lưu trước đó, không chạy lại test hay
browser QA. Không đổi ngày chạy trong artifact thành ngày viết báo cáo.

Lưu ý khi đọc test `test_restart_retains_chats_and_memory_but_not_config_key`:
nó tái tạo app/HTTP server từ cùng DB trong tiến trình test, không khởi động lại
máy hoặc tạo một OS process mới cho web. Bằng chứng process độc lập nằm ở CLI.
Không mô tả một phép thử rộng hơn điều nó thực sự kiểm tra.

## 5. Cấu trúc báo cáo cần tạo

Viết báo cáo thống nhất, mạch lạc, khoảng 1.800–2.800 từ nếu bằng chứng đủ;
không kéo dài chỉ để đạt số từ. Tổ chức theo các phần sau:

### 1. Giới thiệu và phạm vi

Nêu bài toán: LLM chỉ thấy request hiện tại, harness phải quản lý việc lưu, đọc
và inject quy ước. Nêu mục tiêu A và phạm vi bản thực hành. Ghi tên sinh viên,
MSSV/lớp là “chưa cung cấp” nếu không có, không tự bịa.

### 2. Phân tích đề và tiêu chí đánh giá

Tách yêu cầu bắt buộc, gợi ý và phần web mở rộng. Tạo bảng:

```text
Yêu cầu | Nguồn trong slide | Cách triển khai | Bằng chứng | Đánh giá và giới hạn
```

Hai chứng minh của slide 14 phải có hai hàng riêng, kết luận theo mức bằng chứng
demo/harness và LLM thật thay vì chấm chung chung “đạt 100%”.

### 3. Kiến trúc và thiết kế memory

Giải thích ngắn state/history/memory/context bằng thành phần thực tế trong code.
Vẽ một sơ đồ luồng nhỏ hoặc mô tả chuỗi: quyết định người dùng → ghi/cập nhật
SQLite → retrieve active theo project → inject context → agent trả lời → lưu
trace. Giải thích vì sao chọn SQLite cho bài nhỏ, schema/version/transaction và
cách bảo toàn lịch sử JWT. Không tuyên bố đây là lựa chọn duy nhất hoặc tối ưu
mọi quy mô.

### 4. Luồng hoạt động trong chatbot

Mô tả một tin nhắn bình thường, một quyết định cần nhớ, một thay đổi quy ước và
một chat mới. Phân biệt rõ demo với chế độ AI. Dẫn đúng hàm/file cho các bước,
không coi SQLite lưu transcript là bằng chứng agent đã sử dụng memory.

### 5. Hai chứng minh bắt buộc

Dùng kịch bản S1–S5 từ **một lần demo có thật**:

| Bước | Nội dung kiểm chứng |
| --- | --- |
| S1 | Chốt TypeScript, PostgreSQL, JWT và quy ước API |
| S2 | Session/chat mới hỏi kế hoạch endpoint, không nhắc lại quy ước |
| S3 | Xác nhận chuyển authentication sang session cookie |
| S4 | Session/chat mới xử lý đăng xuất hoặc middleware theo cookie |
| S5 | Session/chat mới khác tiếp tục dùng quy ước mới |

Với mỗi chứng minh, nêu input thực tế, memory inject, đầu ra quan sát được, ID
session/chat nếu có và artifact chính xác. Trích JSON ngắn từ file thật, không
soạn ví dụ rồi ghi là log. Chứng minh 2 phải cho thấy đồng thời cookie active,
JWT superseded có nguồn/thời điểm và request chat mới không inject JWT cũ.

Ảnh UI là bằng chứng hỗ trợ; ưu tiên request/response và lịch sử DB cho kết luận
về memory. Nêu khác biệt: trong chat cũ, history có thể vẫn chứa JWT cũ; tuyên bố
“không có JWT trong request” chỉ áp dụng request mới đã kiểm tra, không phải mọi
request trong mọi chat.

### 6. Kiểm thử và kết quả

Phân nhóm CLI demo, test memory/HTTP, mock API và browser QA. Ghi số kiểm tra,
log, provider, thời điểm chạy từ artifact và nội dung thực sự được kiểm chứng.
Không cộng 15 assertion demo, 28 test và 13 check UI thành một số test cùng loại.
Chọn một vài kiểm tra quan trọng như rollback, cô lập project, no-op, lịch sử
và cold start để giải thích giá trị; không chép toàn bộ output dài.

### 7. Hạn chế và kiểm chứng còn cần bổ sung

Nêu đúng những giới hạn có căn cứ: demo theo quy tắc; trích quyết định bằng model
có thể sai; mock không kiểm chứng chất lượng model; chat cũ giữ history; ứng dụng
localhost cho một người dùng; chưa có kết quả LLM end-to-end trong bộ artifact.
Không biến tính năng ngoài phạm vi như vector retrieval hoặc router thành lý do
đánh trượt Challenge A.

Đề xuất ngắn cách bổ sung bằng chứng LLM: dùng một project thử riêng, kết nối
model hợp lệ, thực hiện hai tình huống bằng chat mới, xuất request/response và
đánh giá câu trả lời thực tế. Đây là **kế hoạch kiểm chứng**, không ghi đã làm.

### 8. Kết luận

Trả lời trực tiếp đã giải quyết mục tiêu nào bằng bằng chứng nào và phần nào
chưa đủ dữ liệu. Có thể kết luận cơ chế memory/harness và demo đáp ứng hai tình
huống đã thử; không suy rộng thành mọi hội thoại hoặc mọi model đều đúng.

### Phụ lục ngắn: tái hiện và nguồn

Đưa các lệnh sử dụng hiện có:

```powershell
python -X utf8 webapp.py
python -X utf8 demo.py
python -X utf8 -m unittest discover -s tests -v
```

Đưa chuỗi tin nhắn UI để tái hiện A, cách mở “Ngữ cảnh đã nạp”, “Lịch sử” và
“Xuất bằng chứng”. Ghi model/key là cấu hình cần người dùng cung cấp, không in
giá trị bí mật. Không coi GitHub lưu source là đã deploy chatbot công khai.

## 6. Quy tắc bằng chứng và văn phong

- Mỗi kết luận quan trọng phải dẫn slide, hàm/file hoặc artifact tương ứng.
  Khi dẫn code bằng số dòng, phải kiểm tra số dòng hiện tại; không đoán.
- Không sử dụng README/báo cáo cũ làm bằng chứng duy nhất cho tính năng hoặc test.
- Tách “đã có mã”, “có kết quả đã lưu”, “đã chạy lại” và “đã kiểm chứng LLM thật”.
- Phát hiện thiếu artifact thì ghi nhận trung thực. Không tự làm screenshot,
  PID, session ID, JSON log, token usage, chi phí hoặc kết quả test tưởng tượng.
- Không khẳng định app đang chạy hay repo đã push chỉ từ nhật ký ngày trước.
- Không khẳng định mọi API key/bí mật trong tin nhắn người dùng đều bị loại bỏ:
  kết luận về key trong RAM chỉ áp dụng cấu hình key qua UI/môi trường đã đọc.
- Báo cáo dùng giọng kỹ thuật khách quan, thuật ngữ nhất quán, giải thích ngắn
  khi xuất hiện lần đầu. Không viết thành lịch sử cuộc chat với Codex; không
  dành nhiều đoạn cho lỗi công cụ của môi trường nếu không ảnh hưởng kết luận.
- Không thêm thông tin cá nhân, trích chat riêng hoặc secret vào báo cáo. Dùng
  kịch bản synthetic và artifact demo sẵn có.

## 7. Đầu ra và tự kiểm tra

Nếu có quyền tạo file, lưu đúng **một file báo cáo mới**:

```text
BAO_CAO_CHALLENGE_A_HOAN_CHINH.md
```

Không ghi đè báo cáo, prompt hoặc bằng chứng cũ. Nếu file đích đã tồn tại mà
không có yêu cầu cập nhật, dùng tên có ngày/giờ để giữ bản trước. Nếu chỉ có
khung chat, xuất toàn bộ nội dung Markdown và nói rõ chưa tạo file trên đĩa.

Trước khi bàn giao, kiểm tra báo cáo có đủ hai chứng minh; phân biệt yêu cầu
gốc với mở rộng web; mô tả đúng retrieval/injection và supersede; không trộn
hai lần demo; đối chiếu số test; nêu thiếu bằng chứng LLM thật; các đường dẫn
được dẫn có tồn tại hoặc được đánh dấu thiếu. Chỉ tuyên bố những gì nguồn cho
phép kết luận.
