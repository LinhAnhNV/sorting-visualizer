# Hướng dẫn sử dụng

## 1. Cài đặt và khởi động

1. Cài Python 3.8 trở lên. Kiểm tra tkinter: `python -c "import tkinter"` (không báo lỗi là được;
   nếu thiếu trên Ubuntu/Debian: `sudo apt install python3-tk`).
2. Mở terminal tại thư mục dự án và chạy `python main.py`.

## 2. Giao diện

Cửa sổ chia hai phần: **bảng điều khiển** bên trái (ControlPanel; nếu màn hình thấp, kéo thanh cuộn bên phải bảng hoặc lăn chuột khi con trỏ nằm trên bảng để xem các mục phía dưới) và **Canvas** bên phải
(tiêu đề thuật toán, các cột dữ liệu, chú giải màu, dòng mô tả bước vừa thực hiện).

### Ý nghĩa màu

| Màu | Ý nghĩa |
|---|---|
| Xanh xám | Cột bình thường |
| Vàng | Hai cột đang được so sánh |
| Đỏ | Hai cột vừa hoán đổi |
| Cam | Vị trí vừa bị ghi đè (Merge Sort) |
| Tím | Phần tử chốt (Quick Sort) |
| Xanh lá | Toàn dãy đã sắp xếp xong |

## 3. Các bước thao tác

1. **Chuẩn bị dữ liệu** (mục 1 – Dữ liệu), chọn một trong ba cách:
   * Chọn *Số phần tử* (2–500) và *kịch bản* (Ngẫu nhiên, Đã sắp xếp, Đảo ngược, Gần như sắp xếp,
     Ít giá trị khác nhau) rồi bấm **Sinh dãy số**.
   * Gõ dãy vào ô nhập (ngăn cách bằng dấu phẩy, chấm phẩy hoặc khoảng trắng, ví dụ `9 4 7, 1; 8`)
     rồi bấm **Áp dụng dãy nhập**.
   * Bấm **Nạp file…** để mở file `.json` hoặc `.csv` (xem định dạng ở mục 5). Bấm **Lưu dãy…** để lưu
     dãy hiện tại (dãy gốc, trước khi sắp xếp).
2. **Chọn thuật toán** (mục 2). Phần mô tả và độ phức tạp hiện ngay bên dưới.
3. **Điều khiển** (mục 3):
   * **Chạy** – chạy tự động liên tục.
   * **Tạm dừng** / **Tiếp tục** – dừng và chạy tiếp đúng chỗ cũ.
   * **Từng bước** – mỗi lần bấm tiến đúng một bước (dùng khi đang Sẵn sàng hoặc Tạm dừng).
   * **Đặt lại** – đưa dãy về trạng thái ban đầu để chạy lại.
4. **Tốc độ** (mục 4): kéo thanh trượt; có hiệu lực ngay cả khi đang chạy.
5. **Thống kê** (mục 5) cập nhật theo thời gian thực: trạng thái, số lần so sánh, hoán đổi, ghi đè, tổng số bước.

> Thay đổi dữ liệu hoặc thuật toán trong lúc đang chạy sẽ dừng lần chạy hiện tại và đặt lại.

## 4. So sánh hiệu năng

Bấm **So sánh hiệu năng…** để mở cửa sổ riêng:

1. Nhập *Kích thước dãy* (ví dụ `100, 500, 1000, 2000`, tối đa 5000), chọn *Kịch bản* (hoặc *Tất cả kịch bản*),
   *Số lần lặp* (kết quả là trung bình) và tick các thuật toán cần so sánh.
2. Bấm **Chạy benchmark**. Tiến trình hiện ở thanh bên phải; có thể bấm **Dừng**. Cửa sổ không bị đơ
   vì phép đo chạy ở luồng nền.
3. Xem **Bảng kết quả** hoặc tab **Biểu đồ** (chọn đại lượng, kịch bản, bật *Thang log* để dễ so sánh khi
   chênh lệch rất lớn).
4. Khi chạy xong, kết quả **tự động lưu** vào `data/results/benchmark_<thời gian>.json`.
   Bấm **Xuất kết quả…** để lưu thêm ra `.json` hoặc `.csv` ở nơi khác.

> Lưu ý: thời gian (ms) phụ thuộc máy và bao gồm chi phí sinh bước hoạt hình (như nhau cho mọi thuật
> toán), nên dùng để so sánh *tương đối*. Số lần so sánh/hoán đổi là số liệu chính xác, không phụ thuộc máy.

## 5. Định dạng file dữ liệu

**JSON** – một danh sách, hoặc đối tượng có khoá `data`:

```json
{ "size": 5, "data": [9, 4, 7, 1, 8] }
```

**CSV** – mọi ô số đều được đọc; dòng đầu nếu không phải số được coi là tiêu đề:

```
value
9
4
7
```

Chỉ hỗ trợ số nguyên; tối đa 500 phần tử khi hoạt hình (5000 khi dùng benchmark).
File mẫu: `data/sample.json`, `data/sample.csv`, `data/sample_nearly_sorted.json`.

## 6. Chạy benchmark bằng dòng lệnh

```bash
python main.py --benchmark --sizes 100,500,1000 --scenario all --repeats 3 --out data/results/ketqua.csv
python main.py --benchmark --algorithms bubble,merge --scenario random
```

Tham số: `--sizes`, `--scenario` (`all|random|sorted|reversed|nearly_sorted|few_unique`),
`--algorithms` (`all` hoặc danh sách khoá `bubble,selection,insertion,merge,quick`), `--repeats`, `--out`.

## 7. Xử lý sự cố

| Hiện tượng | Cách xử lý |
|---|---|
| `No module named 'tkinter'` | Cài `python3-tk` (Linux) hoặc cài lại Python có tuỳ chọn tcl/tk. |
| Báo "Dãy nhập không hợp lệ" | Chỉ nhập số nguyên, tối thiểu 2 phần tử. |
| Không nạp được file | Kiểm tra đuôi `.json/.csv`, nội dung là số nguyên, tối đa 500 phần tử. |
| Hoạt hình quá chậm với dãy lớn | Kéo thanh tốc độ sang phải; mỗi tick sẽ xử lý tới 10 bước. |
| Benchmark lâu | Giảm kích thước (Bubble/Selection/Insertion là O(n²)) hoặc giảm số lần lặp. |
