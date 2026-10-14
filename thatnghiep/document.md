# Sloppy Slop (Canary) — Tài liệu kỹ thuật

*File: `bleeding_edge__7_.html` · Phiên bản tài liệu: tiếng Việt (bản tiếng Anh sẽ bổ sung sau)*

## 1. Tổng quan

**Sloppy Slop** là một ứng dụng web ôn tập (revision app) chạy hoàn toàn phía trình duyệt, đóng gói trong **một file HTML duy nhất** (\~278 KB, \~4.800 dòng). Không cần server, không cần build: mở file là dùng được. Bản này mang nhãn **Canary** (bản thử nghiệm, nên có thể chứa tính năng chưa ổn định).

Ý tưởng chính: giáo viên (hoặc học sinh) đưa tài liệu Word cho một AI, AI trả về một file JSON gọi là **Study Pack** (`*.studypack.json`). Người học nạp file này vào Sloppy Slop để có ngay:

- Ghi chú theo chủ đề (notes) và thuật ngữ chính (key terms)
- Flashcard với cơ chế lặp lại ngắt quãng (3 hộp)
- Bài quiz luyện tập với 6 dạng câu hỏi
- Chế độ thi thử (exam) có đồng hồ, đánh dấu câu, lưu tiến độ giữa chừng
- Theo dõi tiến độ, streak, hạn ôn thi, đồng hồ Pomodoro

Giao diện hỗ trợ **tiếng Việt và tiếng Anh**, giao diện **sáng / tối / theo hệ thống**, và hoạt động như PWA (cài lên màn hình chính iOS/Android, dùng offline).

## 2. Cấu trúc file

File gồm các khối chính theo thứ tự:

- **`<head>`**: meta PWA (apple-mobile-web-app-\*, viewport-fit=cover), `manifest` nhúng dạng data URI (tên "Sloppy Slop", `display: standalone`, màu nền `#0C1222`), icon `favicon-canary.png`.
- **`<style>` (dòng \~4–1099)**: toàn bộ CSS, dùng biến CSS cho theme (`--bg`, `--surface`, `--ink`, `--accent`, `--mark`, `--good`, `--warn`, `--bad`…). Có khối *WebKit / iOS 16 compatibility fixes* để sửa lỗi chữ đè nhau trên Safari cũ (class `.prog`, `.big`).
- **Nền trời động (`#sky`)**: SVG mặt trời + mây ban ngày, trăng lưỡi liềm + sao nhấp nháy ban đêm. Tạm dừng khi tab bị ẩn để tiết kiệm pin.
- **Thanh trên (`<header class="top">`)**: logo/tên gói (bấm để đóng mở sidebar), popup Debug, nút chọn ngôn ngữ VI/EN, chọn theme, đồng hồ tập trung.
- **`#app`**: vùng nội dung, được JS render lại bằng `innerHTML` mỗi khi trạng thái đổi.
- **Các thẻ `<script>` dữ liệu**:
  - `#promptText` (`text/plain`): prompt gửi cho AI để chuyển tài liệu Word thành Study Pack.
  - `#sampleEn`, `#sampleVi` (`application/json`): gói ví dụ tiếng Anh và tiếng Việt, dùng khi chưa nạp gói nào.
- **`<script>` chính**: logic ứng dụng (từ điển i18n, chuẩn hóa dữ liệu, trạng thái, render, sự kiện).
- **`<script>` cuối**: đăng ký Service Worker `sw.js` và yêu cầu cache trang hiện tại để mở offline.

> Lưu ý: `sw.js` và `favicon-canary.png` là file ngoài, **không nằm trong file này**. Nếu thiếu, ứng dụng vẫn chạy nhưng không có offline/icon.

## 3. Định dạng Study Pack (JSON)

Một Study Pack là một đối tượng JSON:

- `format`: luôn là `"studypack"`; `version`: luôn là `1`
- `title`, `subject`, `level`, `language` (chuỗi, có thể rỗng; `language` là mã như `vi`, `en`)
- `id` (tuỳ chọn): định danh gói. Nếu có, tiến độ gắn với `id` nên đổi tên gói không mất tiến độ
- `topics`: mảng chủ đề, mỗi chủ đề gồm:
  - `id` (`t1`, `t2`…), `title`, `summary` (≤ 40 từ)
  - `notes`: mảng `{heading, points[]}`; mỗi point là một câu, có thể bôi nổi bật bằng `**từ khoá**` (hiển thị như bút dạ quang vàng)
  - `key_terms`: mảng `{term, definition}`
  - `flashcards`: mảng `{front, back}`
  - `questions`: mảng câu hỏi (xem mục dưới)

### Các dạng câu hỏi

| Dạng | Trường chính | Cách chấm |
| --- | --- | --- |
| `mcq` | `prompt`, `options` (2–6), `answer` (chỉ số bắt đầu từ 0), `explanation`, tuỳ chọn `context`/`source` | Đúng/sai |
| `truefalse` | `prompt`, `answer` (boolean) | Đúng/sai |
| `short` | `prompt`, `answer` (đáp án mẫu) | Tự chấm: người học xem đáp án mẫu rồi chọn "đã làm được / chưa" |
| `tfs` | `quote`, `items` (đúng 4 mệnh đề `{text, answer}`) | Điểm theo số mệnh đề đúng: 0→0, 1→0,1, 2→0,25, 3→0,5, 4→1 |
| `cloze` | `prompt` có đúng một `____`, `answers[]` | So khớp chuẩn hoá; chấp nhận cả khi gõ thiếu dấu tiếng Việt (tính là "loose") |
| `match` | `pairs` (4–5 cặp `{left, right}`) | Điểm = số cặp đúng / tổng số cặp |

## 4. Nạp dữ liệu và chuẩn hoá

Các hàm lõi (có xuất `module.exports` để test bằng Node):

- **`spParse(text)`**: bỏ BOM, tự tách JSON ra khỏi code fence Markdown hoặc văn bản thừa quanh `{ ... }`. Lỗi → trả về thông báo `badjson`.
- **`spNormalise(data)`**: kiểm tra và làm sạch gói. Dữ liệu hỏng **không làm hỏng cả gói**: phần lỗi bị bỏ và ghi thành cảnh báo (warning) để hiển thị cho người dùng. Một số quy tắc đáng chú ý:
  - Chủ đề không có `title` bị bỏ; `id` trùng sẽ được đổi thành `id-2`, `id-3`…
  - Chấp nhận tên trường thay thế: `terms` thay `key_terms`, `cards` thay `flashcards`; trong `tfs` chấp nhận `t`/`a` thay `text`/`answer`.
  - `mcq` cần ≥ 2 lựa chọn và `answer` là số nguyên hợp lệ; `truefalse` chấp nhận chuỗi "true"/"false".
  - `tfs` cần ≥ 4 mệnh đề (thừa thì cắt còn 4); `match` cần ≥ 2 cặp, **tối đa 8 cặp** (thừa bị cắt), không cho trùng vế trái/phải.
  - Không có mục nào dùng được (notes + cards + questions = 0) thì báo lỗi `noitems`.
- **`spMerge(packs)`**: gộp nhiều file (ví dụ `name-part1`, `name-part2`) thành một gói; tự đặt lại `id` chủ đề bị trùng.
- **`spHash(s)`**: băm chuỗi (kiểu djb2) để tạo khoá lưu tiến độ.

Cách nạp: kéo-thả/chọn file (nhiều file cùng lúc), dán trực tiếp JSON vào ô văn bản, hoặc dùng gói ví dụ. Có danh sách **Bộ ôn tập gần đây** (mở, sửa, đổi tên, xoá).

## 5. Các màn hình và tính năng

### 5.1 Tổng quan (overview)

- Vòng/phần trăm **"sẵn sàng ôn thi"** của cả gói và danh sách chủ đề kèm thanh tiến độ.
- **Heatmap streak** chuyển được giữa 7 ngày và 30 ngày.
- **Hạn ôn thi (deadline)**: đặt ngày, lưu theo từng gói.
- Nút nhanh vào chế độ tập trung, nút đặt lại tiến độ (có bước xác nhận).

Cách tính độ sẵn sàng của một chủ đề: trung bình cộng của các thành phần *có tồn tại* — (1) đã đánh dấu đọc xong ghi chú (0 hoặc 1), (2) tỉ lệ flashcard "đã thuộc", (3) điểm quiz cao nhất (0–100%). Độ sẵn sàng của cả gói là trung bình các chủ đề.

### 5.2 Học theo chủ đề (study)

Chọn một chủ đề (hoặc "tất cả") rồi chuyển giữa ba tab:

- **Notes**: ghi chú theo mục, bảng thuật ngữ (`<dl>`), nút "đã đọc" để tính tiến độ.
- **Cards**: flashcard, vuốt phải = đã nhớ, vuốt trái = ôn lại (hỗ trợ cảm ứng, chuột, bút nhờ Pointer Events), có nút "quay lại thẻ trước" (lưu tối đa 100 thao tác), tuỳ chọn xáo trộn và bỏ qua thẻ đã thuộc. Xong bộ thẻ sẽ bắn pháo giấy.
- **Quiz**: chọn số câu, giới hạn thời gian mỗi câu, xáo trộn; xong có màn kết quả với danh sách câu sai và nút làm lại riêng các câu sai.

### 5.3 Flashcard — hệ thống 3 hộp (Leitner đơn giản)

Mỗi thẻ có trạng thái `{box: 1..3}`.

- Trả lời **đúng**: lên 1 hộp (tối đa Hộp 3).
- Trả lời **sai**: rớt về Hộp 1 và thẻ được đẩy xuống cuối hàng đợi để gặp lại ngay trong phiên.
- Thẻ được coi là "đã thuộc" khi `box >= 2`.
- Tương thích ngược: trạng thái cũ dạng boolean `true` được hiểu là Hộp 3.

### 5.4 Thi thử (exam)

- Cấu hình mặc định: phạm vi `all`, chế độ `full`, **45 phút**, dạng `truefalse` **tắt** mặc định.
- Chọn phạm vi (chủ đề), chế độ đầy đủ hoặc rút gọn, và dạng câu hỏi nào được đưa vào đề. Mỗi dạng được chọn và có sẵn sẽ có **ít nhất một câu**, phần còn lại lấy ngẫu nhiên; trong mỗi dạng thì xáo trộn, còn thứ tự dạng được cố định (mcq, đúng/sai … short).
- Trong khi làm bài: điều hướng trước/sau, bảng nhảy tới câu bất kỳ, **đánh dấu câu cần xem lại**, đồng hồ đếm ngược, xác nhận trước khi nộp.
- **Tự lưu và tiếp tục**: trạng thái bài đang làm lưu ở `sp:run:<khoá gói>`; lần sau mở lại sẽ có nút "tiếp tục". Nộp bài hoặc thoát thì xoá bản lưu.
- Kết quả: số câu đúng / đúng một phần / sai / bỏ qua / chờ chấm; xem lại từng câu với bộ lọc "tất cả / chỉ câu sai". Câu `short` do người học tự chấm.

### 5.5 Trang "Dành cho giáo viên" (teach)

- Hiển thị **prompt** để sao chép, kèm đường dẫn nhanh tới các công cụ AI.
- Bảng giải thích cấu trúc file (trường – kiểu – ý nghĩa).
- Prompt yêu cầu AI: giữ ≥ 90% thông tin của tài liệu trong ghi chú; chuyển 100% câu hỏi có sẵn (trừ câu cần hình ảnh); **không bịa** thông tin ngoài tài liệu; trả về file (không dán vào khung chat); tài liệu dài (> \~20 trang hoặc \~8.000 từ) thì tách nhiều file `name-partN.studypack.json`.

### 5.6 Đồng hồ tập trung (Pomodoro)

- Mặc định 25 phút tập trung / 5 phút nghỉ; preset 25/5, 45/10, 15/3, 50/15; tuỳ chỉnh tập trung 1–180 phút, nghỉ 1–60 phút.
- Các nút Bắt đầu, Đặt lại, Bỏ qua (chuyển tập trung ↔ nghỉ); phát tiếng bíp khi hết giờ.
- Dùng mốc thời gian thực (`endsAt`) nên vẫn chính xác khi tab ở nền.
- Thống kê số phiên và số phút theo ngày (`sp:timer:YYYY-M-D`).

### 5.7 Giao diện, đa ngôn ngữ, rung phản hồi

- **Ngôn ngữ**: VI/EN, tự nhận theo `navigator.language`, lưu ở `sp:lang`. Chuỗi giao diện nằm trong đối tượng `I18N`; hàm `tr(key, vars)` hỗ trợ biến `{n}` và dạng số ít/số nhiều.
- **Theme**: `light` / `dark` / `system` (lưu ở `sp:theme`), chuyển nền trời ngày–đêm tương ứng.
- **Haptic**: rung phản hồi trên iOS/Android khi trả lời đúng/sai, bật tắt bằng `sp:haptic`.
- **Sidebar**: thu gọn được trên desktop (`sp:rail`), dạng ngăn kéo (drawer) trên di động.
- **Popup Debug ("Runtime Inspector")**: hiện khoá gói, số chủ đề/thẻ, ngôn ngữ/chế độ, dung lượng localStorage, nút test haptic và làm mới.

## 6. Lưu trữ dữ liệu (localStorage)

Toàn bộ dữ liệu nằm trên thiết bị, không gửi đi đâu. Mọi thao tác đọc/ghi đều bọc `try/catch` nên ứng dụng vẫn chạy khi storage bị chặn (chỉ không nhớ được tiến độ).

| Khoá | Nội dung |
| --- | --- |
| `sp:pack` | Gói đang dùng (JSON) |
| `sp:prog:<key>` | Tiến độ: ghi chú đã đọc, hộp flashcard, điểm quiz cao nhất |
| `sp:run:<key>` | Bài thi đang làm dở |
| `sp:deadline:<key>` | Ngày hạn ôn thi (`YYYY-MM-DD`) |
| `sp:recent_packs` | Danh sách bộ ôn tập gần đây |
| `sp:timer:<ngày>` | Thống kê Pomodoro theo ngày |
| `sp:lang`, `sp:theme`, `sp:haptic`, `sp:rail` | Tuỳ chọn người dùng |

**Khoá gói (`<key>`)**: nếu gói có `id` thì `key = spHash("id:" + id)`; nếu không thì băm từ `title` + danh sách `id:title` của các chủ đề (công thức cũ). Gói ví dụ dùng khoá cố định `example`. Khi lần đầu nạp gói có `id`, tiến độ cũ lưu theo khoá kiểu cũ sẽ được **chuyển sang** khoá mới.

## 7. Kiến trúc mã nguồn (JavaScript)

Mã được viết kiểu ES5 + vài đoạn ES6, không dùng framework, không phụ thuộc thư viện ngoài (chỉ tải font Google: JetBrains Mono, Plus Jakarta Sans, Lora).

- **Trạng thái toàn cục `S`**: `pack`, `key`, `prog`, `view` (`overview`/study/`exam`/load/teacher), `scope`, `mode` (`notes`/`cards`/`quiz`), `exam`, `cards`, `quiz`, `qopts`, `copts`, `railOff`, `drawerOpen`, `streakView`…
- **Vòng lặp render**: `render()` dựng chuỗi HTML của sidebar + `<main>` rồi gán vào `#app`; các hàm `*HTML()` (`navHTML`, `overviewHTML`, `studyHTML`, `notesHTML`, `cardsHTML`, `quizHTML`, `renderExam`, `loadHTML`, `teacherHTML`…) trả về chuỗi.
- **Xử lý sự kiện tập trung**: mọi nút dùng thuộc tính `data-act="..."`, một hàm `act(name, el)` dạng switch xử lý tất cả hành động (event delegation).
- **An toàn XSS**: nội dung người dùng luôn đi qua `esc()`; chỉ `**...**` được đổi thành `<mark>` qua `rich()`.
- **Boot**: `boot()` → đọc ngôn ngữ → áp dụng chuỗi tĩnh → khởi tạo theme → nạp `sp:pack` nếu hợp lệ, nếu không thì dùng gói ví dụ theo ngôn ngữ → render.
- **Điều hướng**: hàm `go(where, id, mode)`.
- **Bố cục**: topbar cố định + sidebar chủ đề bên trái + một cột làm việc; có `safe-area-inset` cho tai thỏ iPhone.

## 8. Hướng dẫn sử dụng nhanh

1. Đưa tài liệu Word cho AI kèm prompt ở trang *Dành cho giáo viên* để nhận file `.studypack.json`.
2. Mở Sloppy Slop, vào trang nạp file, kéo-thả file (hoặc dán JSON). Nếu có cảnh báo, kiểm tra các mục bị bỏ.
3. Đọc ghi chú → đánh dấu đã đọc → luyện flashcard → làm quiz → thi thử.
4. Đặt hạn ôn thi và dùng đồng hồ tập trung để giữ nhịp.
5. Muốn cài như ứng dụng: dùng "Thêm vào Màn hình chính" (iOS) hoặc "Cài đặt ứng dụng" (Android/Chrome).

## 9. Hạn chế và lưu ý

- **Chỉ văn bản**: không hiển thị ảnh; câu hỏi cần hình sẽ bị bỏ khi tạo gói.
- Dữ liệu chỉ nằm trên một trình duyệt/thiết bị; xoá dữ liệu trình duyệt là mất tiến độ (chưa có xuất/nhập tiến độ trong file này).
- Offline phụ thuộc file `sw.js` đặt cùng thư mục; mở file trực tiếp kiểu `file://` thường không đăng ký được Service Worker.
- Một số chuỗi trong giao diện đang ghi cứng tiếng Việt (ví dụ "Bộ ôn tập gần đây", "Mở / Sửa / Đổi tên / Xóa", "Làm mới") thay vì đi qua `I18N`, nên chưa dịch được sang tiếng Anh.
- Phần phụ trợ gồm popup Debug và nhãn *Canary* là dành cho giai đoạn thử nghiệm; nên cân nhắc ẩn đi ở bản phát hành chính thức.
- Exam dùng `localStorage` trực tiếp (không qua hàm `store` có `try/catch`) nên có thể lỗi nếu trình duyệt chặn lưu trữ (ví dụ chế độ riêng tư nghiêm ngặt).

## 10. Gợi ý hướng phát triển

- Xuất/nhập tiến độ học (file hoặc mã) để đồng bộ giữa thiết bị.
- Đưa toàn bộ chuỗi giao diện còn ghi cứng vào `I18N`.
- Tách file thành `index.html`, `app.js`, `i18n.js`, `core.js`, `styles.css` nếu dự án lớn thêm (các comment trong mã đã nhắc tới `core.js` và `i18n.js`).
- Thêm kiểm thử tự động cho `spParse`/`spNormalise` (đã sẵn `module.exports`).
- Lặp lại ngắt quãng theo ngày (hiện chỉ có hộp 1–3, chưa có lịch nhắc theo ngày).
