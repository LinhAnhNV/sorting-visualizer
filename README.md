# Sorting Visualizer

Đồ án học phần **Lập trình Python** — Bộ môn KHDL & TTNT, HUIT.
Đề tài 28: Hệ thống trực quan hóa thuật toán sắp xếp.

## Mô tả

Ứng dụng Tkinter minh họa quá trình chạy của các thuật toán sắp xếp (Bubble, Insertion, Quick) theo từng bước trên Canvas, kèm quản lý phiên mô phỏng, thống kê hiệu năng, tài khoản người dùng có phân quyền và tích hợp API lấy dữ liệu ngẫu nhiên.

## Thành viên nhóm

| Tên | Vai trò |
|---|---|
| Nguyễn Văn Linh Anh (A) | Core thuật toán + Trực quan hóa (Canvas) |
| Nguyễn Trần Anh Khoa (B) | Quản lý phiên mô phỏng + Thống kê |
| Trương Phạm Gia Nghi (C) | Tài khoản + Regex + Crawl/API |

## Cấu trúc thư mục

sorting-visualizer/
├── main.py # Điểm khởi động, ráp 3 module vào main window
├── config.py # Hằng số dùng chung (đường dẫn, màu sắc, font)
├── algorithms/ # Module A — lớp thuật toán sắp xếp + UI Canvas
├── sessions/ # Module B — CRUD phiên, thống kê hiệu năng
├── accounts/ # Module C — tài khoản, Regex, API
├── data/ # File dữ liệu JSON (không commit dữ liệu thật)
├── utils/ # Tiện ích dùng chung (sys module...)
└── tests/ # Test case từng module

## Yêu cầu môi trường

- Python 3.11 hoặc 3.14
- Xem thư viện phụ thuộc trong `requirements.txt`

## Cài đặt

```bash
git clone https://github.com/LinhAnhNV/sorting-visualizer.git
cd sorting-visualizer
pip install -r requirements.txt
```

## Chạy ứng dụng

```bash
python main.py
```

## Quy tắc làm việc nhóm

- Mỗi thành viên làm việc trên 1 nhánh riêng (`feature/algorithms`, `feature/sessions`, `feature/accounts`), không sửa code trong thư mục module của người khác.
- Merge vào `main` sau khi đã test riêng phần của mình.

## Tiến độ

- [x] Tuần 4: Khởi tạo cấu trúc thư mục, thiết kế sơ đồ lớp
- [ ] Tuần 6-9: Code chức năng từng module
- [ ] Tuần 11-12: Tích hợp UI
- [ ] Tuần 13-15: Kiểm thử, đóng gói, báo cáo