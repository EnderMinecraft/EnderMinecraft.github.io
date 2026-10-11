# 📚 Revision Desk 

<p align="center">
  <b>A Web-native, single-file web dashboard for smart study management and AI-powered revision packs.</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/status-active-success.svg" alt="Status">
  <img src="https://img.shields.io/badge/platform-macOS%20native%20web-blue.svg" alt="Platform">
  <img src="https://img.shields.io/badge/dependencies-zero-orange.svg" alt="Zero Dependencies">
  <img src="https://img.shields.io/badge/lang-EN%20%2F%20VI-brightgreen" alt="Languages">
</p>

---

## 🚀 Feature Log & Changelog

### ✨ Core Architecture & Performance
* **Single-File Architecture:** Toàn bộ ứng dụng (HTML, CSS, JavaScript, nội dung mẫu i18n và tệp Prompt AI) được gói gọn trong một tệp duy nhất, mang lại hiệu năng cao và dễ dàng triển khai.
* **Zero Dependencies:** Xây dựng hoàn toàn bằng Vanilla JavaScript và CSS hiện đại, không phụ thuộc vào bất kỳ framework hoặc thư viện bên ngoài nào.
* **Local-First Persistence:** Mọi tiến trình học tập, trạng thái flashcard, bộ đếm thời gian và lịch sử tệp đều được lưu trữ bảo mật cục bộ thông qua trình duyệt (`localStorage`).

### 🤖 AI Study Pack Integration & Quick Launchers
* **AI Tool Launchers:** Tích hợp trực tiếp các nút chuyển hướng nhanh cho **ChatGPT**, **Claude** và **Gemini** ngay tại tab *Make a pack*.
* **Smart Prompt Encoding:** Tự động mã hóa hệ thống prompt tiêu chuẩn vào đường dẫn URL giúp người dùng mở nhanh trang AI với đầy đủ ngữ cảnh để chuyển đổi tài liệu Word/PDF thành tệp `.json` chuẩn xác.
* **System Prompt Generator:** Cung cấp sẵn một bộ quy tắc prompt khắt khe để đảm bảo cấu trúc dữ liệu JSON đầu ra luôn đồng nhất (gồm Notes, Key Terms, Flashcards và Questions đủ các cấp độ).

### 📂 Recent Files & Pack Management
* **Recent Packs Tracker:** Tự động theo dõi, lưu trữ và quản lý tối đa **5 tệp Study Pack gần nhất** (`.studypack.json`).
* **Full File Control:** Hỗ trợ đầy đủ các thao tác quản lý trực tiếp trên giao diện:
  * **Load:** Mở và tải gói ôn tập ngay lập tức.
  * **Edit:** Nạp nhanh nội dung JSON vào khung chỉnh sửa thủ công.
  * **Rename:** Đổi tên hiển thị bộ ôn tập theo ý muốn.
  * **Delete:** Xóa tệp khỏi lịch sử lưu trữ cục bộ.

### 🌌 Dynamic Celestial Sky & Theme Engine
* **Day/Night Orbital Cycle:** Hiệu ứng chuyển động quỹ đạo 180 độ mượt mà giữa Mặt Trời (Light Mode) và Mặt Trăng (Dark Mode).
* **Star-field Animation:** Tự động sinh ngẫu nhiên hàng loạt ngôi sao lấp lánh (`twinkling stars`) với kích thước và độ trễ động khi bật chế độ tối.
* **Multi-Theme Modes:** Hỗ trợ chuyển đổi linh hoạt giữa 3 chế độ: *Light*, *Dark*, và đồng bộ tự động theo *System (OS preference)*.

### 🧠 Advanced Study Modes
* **Leitner Flashcard System:** 
  * Hệ thống thẻ ghi nhớ thông minh phân loại theo không gian lặp lại (spaced repetition).
  * Hiệu ứng lật thẻ 3 dạng không gian 3D mượt mà (`perspective`).
  * Hiệu ứng pháo giấy (`confetti celebration`) chúc mừng khi hoàn thành toàn bộ bộ thẻ.
* **Comprehensive Quiz Engine:** 
  * Hỗ trợ 3 dạng câu hỏi: Trắc nghiệm (MCQ), Đúng/Sai (True/False), và Tự luận ngắn (Short answer).
  * Tích hợp đồng hồ đếm ngược từng câu hỏi, xáo trộn tùy chỉnh (shuffle options/questions) và danh sách xem lại câu trả lời sai.
* **Structured Notes & Key Terms:** Trình bày ghi chú theo định dạng trực quan với từ khóa được làm nổi bật (`marker-yellow underlines`).

### 🔥 Productivity & Diagnostics Tools
* **Focus Timer (Pomodoro):** Đồng hồ tập trung tích hợp vòng tròn tiến độ động (`SVG stroke-dashoffset`), âm thanh thông báo tùy chỉnh và bộ đếm thời gian nghỉ giải lao linh hoạt.
* **Study Streak & Heatmap:** Theo dõi chuỗi ngày học tập liên tục kết hợp biểu đồ bản đồ nhiệt hoạt động (`Activity Heatmap`) có thể chuyển đổi chế độ xem **7 ngày** hoặc **30 ngày**.
* **System Debug Popover:** Bảng chẩn đoán Runtime Inspector tích hợp ngay trên logo ứng dụng để kiểm tra nhanh `Pack Key`, thống kê chủ đề/thẻ, trạng thái ngôn ngữ/theme và dung lượng `localStorage` đang sử dụng.

### 💎 UI/UX Polish
* **Smooth Micro-Interactions:** Hiệu ứng tỏa sáng theo con trỏ chuột (`mouse-following radial glow`) trên các thẻ nội dung và hàng danh sách.
* **View Transitions:** Hiệu ứng chuyển cảnh trượt nhẹ (`fade & slide`) tinh tế giữa các tab và trang.
* **Bilingual Localization:** Hỗ trợ đa ngôn ngữ hoàn chỉnh gồm **Tiếng Anh (EN)** và **Tiếng Việt (VI)**.

---
