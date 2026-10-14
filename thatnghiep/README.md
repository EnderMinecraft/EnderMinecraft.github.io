# Sloppy Slop

Ứng dụng web ôn tập chạy hoàn toàn trên trình duyệt, đóng gói trong **một file HTML duy nhất** (`index.html`). Không cần server, không cần build, không gửi dữ liệu đi đâu cả.

Bạn đưa tài liệu Word cho AI, nhận về một file JSON gọi là **Study Pack** (`*.studypack.json`), nạp vào Sloppy Slop và có ngay ghi chú, flashcard, quiz và thi thử.


## Tính năng

- **Ghi chú** theo chủ đề, bảng thuật ngữ, đánh dấu "đã đọc"
- **Flashcard** vuốt trái/phải, lặp lại ngắt quãng theo 3 hộp
- **Quiz** với 6 dạng câu hỏi: `mcq`, `truefalse`, `short`, `tfs`, `cloze`, `match`
- **Thi thử**: đồng hồ đếm ngược, đánh dấu câu cần xem lại, tự lưu và tiếp tục bài đang làm dở
- **Theo dõi tiến độ**: phần trăm sẵn sàng ôn thi, heatmap streak 7/30 ngày, hạn ôn thi
- **Đồng hồ Pomodoro** (25/5, 45/10, 15/3, 50/15 hoặc tùy chỉnh)
- Giao diện **Tiếng Việt / English**, theme **sáng / tối / theo hệ thống**, rung phản hồi trên di động
- **PWA**: cài lên màn hình chính, dùng offline (cần `sw.js`)

## Bắt đầu nhanh

1. Mở `index.html` bằng trình duyệt (hoặc đặt lên một web server tĩnh bất kỳ).
2. Chưa nạp gói nào thì app dùng gói ví dụ (theo ngôn ngữ giao diện).
3. Tạo Study Pack của riêng bạn:
   - Vào trang **Dành cho giáo viên**, sao chép prompt.
   - Gửi prompt kèm tài liệu Word cho AI, nhận lại file `*.studypack.json`.
4. Vào trang nạp file: kéo-thả file (có thể nhiều file cùng lúc) hoặc dán JSON trực tiếp.
5. Học theo thứ tự: Ghi chú, Flashcard, Quiz, Thi thử.

Tài liệu dài sẽ được AI tách thành nhiều file `name-part1.studypack.json`, `name-part2.studypack.json`... App tự gộp khi nạp cùng lúc.

## Định dạng Study Pack

```json
{
  "format": "studypack",
  "version": 1,
  "title": "Cells and Energy",
  "subject": "Biology",
  "level": "Grade 10",
  "language": "en",
  "topics": [
    {
      "id": "t1",
      "title": "Cell structure",
      "summary": "Tóm tắt tối đa 40 từ.",
      "notes": [
        { "heading": "Parts of the cell", "points": ["The **nucleus** contains DNA."] }
      ],
      "key_terms": [{ "term": "Nucleus", "definition": "..." }],
      "flashcards": [{ "front": "...", "back": "..." }],
      "questions": [
        { "type": "mcq", "prompt": "...", "options": ["A", "B", "C", "D"], "answer": 1, "explanation": "..." }
      ]
    }
  ]
}
```

Các dạng câu hỏi:

| Dạng | Trường chính |
|---|---|
| `mcq` | `prompt`, `options` (2-6), `answer` (chỉ số từ 0), `explanation`, tùy chọn `context`/`source` |
| `truefalse` | `prompt`, `answer` (boolean) |
| `short` | `prompt`, `answer` (đáp án mẫu, người học tự chấm) |
| `tfs` | `quote`, `items` (đúng 4 mệnh đề `{text, answer}`) |
| `cloze` | `prompt` có đúng một `____`, `answers[]` |
| `match` | `pairs` (4-5 cặp `{left, right}`, tối đa 8 được giữ lại) |

Ghi chú: `**từ khóa**` trong `notes` được tô như bút dạ quang. Trường `id` ở cấp gói (tùy chọn) giúp giữ tiến độ khi đổi tên gói.

Khi nạp, dữ liệu hỏng không làm hỏng cả gói: mục lỗi bị bỏ qua và app hiển thị cảnh báo. Ngoài ra app chấp nhận một số tên trường thay thế (`terms`, `cards`, `t`/`a` trong `tfs`) và tự bóc JSON ra khỏi code fence Markdown.

## Cách chấm điểm

- **tfs**: 0 đúng = 0, 1 = 0,1, 2 = 0,25, 3 = 0,5, 4 = 1 điểm
- **match**: số cặp đúng / tổng số cặp
- **cloze**: so khớp sau khi chuẩn hóa; chấp nhận cả khi gõ thiếu dấu tiếng Việt
- **Độ sẵn sàng của chủ đề**: trung bình của (đã đọc ghi chú, tỉ lệ thẻ đã thuộc, điểm quiz cao nhất), chỉ tính thành phần có tồn tại

## Dữ liệu lưu ở đâu

Tất cả nằm trong `localStorage` của trình duyệt:

| Khóa | Nội dung |
|---|---|
| `sp:pack` | Gói đang dùng |
| `sp:prog:<key>` | Tiến độ (ghi chú, hộp flashcard, điểm quiz) |
| `sp:run:<key>` | Bài thi đang làm dở |
| `sp:deadline:<key>` | Hạn ôn thi |
| `sp:recent_packs` | Bộ ôn tập gần đây |
| `sp:timer:<ngày>` | Thống kê Pomodoro |
| `sp:lang`, `sp:theme`, `sp:haptic`, `sp:rail` | Tùy chọn người dùng |

Xóa dữ liệu trình duyệt đồng nghĩa với mất tiến độ (chưa có xuất/nhập tiến độ).

## Cấu trúc file

- `<head>`: meta PWA, manifest nhúng dạng data URI, icon `favicon-canary.png`
- `<style>`: toàn bộ CSS, biến CSS cho theme, các bản vá tương thích WebKit/iOS 16
- `#sky`: nền trời động (mặt trời và mây ban ngày, trăng và sao ban đêm)
- `<header class="top">`: thanh trên (logo, popup Debug, ngôn ngữ, theme, đồng hồ)
- `#app`: vùng nội dung, JS render lại bằng `innerHTML`
- `<script>` dữ liệu: `#promptText` (prompt cho AI), `#sampleEn`, `#sampleVi` (gói ví dụ)
- `<script>` chính: logic ứng dụng; hàm lõi `spParse`, `spNormalise`, `spMerge`, `spHash` (có `module.exports` để test bằng Node)
- `<script>` cuối: đăng ký Service Worker `sw.js`

Không dùng framework hay thư viện ngoài, chỉ tải font Google (JetBrains Mono, Plus Jakarta Sans, Lora).

## Lưu ý và hạn chế

- Chỉ hiển thị văn bản, không có ảnh; câu hỏi cần hình sẽ bị bỏ khi tạo gói.
- `sw.js` và `favicon-canary.png` là file ngoài, cần đặt cùng thư mục. Mở bằng `file://` thường không đăng ký được Service Worker, nên không dùng được offline.
- Chế độ thi dùng `localStorage` trực tiếp (không qua `try/catch`), có thể lỗi nếu trình duyệt chặn lưu trữ.

## Hướng phát triển

- Xuất/nhập tiến độ học để đồng bộ giữa thiết bị
- Tách thành `index.html`, `app.js`, `i18n.js`, `core.js`, `styles.css` khi dự án lớn hơn
- Thêm kiểm thử tự động cho `spParse` / `spNormalise`
- Lịch nhắc ôn flashcard theo ngày (hiện chỉ có 3 hộp, chưa có lịch)
