Phần code khác truyền các dữ kiện cần thiết vào như sau:

1) USERNAME - phần đăng nhập gọi sau khi đăng nhập thành công:
    panel = SessionPanel(root, result_provider=ham_lay_ket_qua)   # tạo panel, lúc này chưa có user
    panel.pack(fill="both", expand=True)
    ...
    panel.set_user("Nhu")     # đăng nhập xong thì gọi (đổi user cũng gọi lại hàm này)
    panel.clear_user()        # đăng xuất thì gọi
   set_user trả về True nếu đọc dữ liệu thành công, False nếu lỗi file (đã báo bằng hộp thoại,
   panel giữ nguyên user cũ). Username rỗng / không phải chuỗi -> ValueError.
   Vai trò (admin/user) không truyền vào mà được đọc từ data/sessions.json (users[].role).

2) KẾT QUẢ SẮP XẾP - phần code sắp xếp cung cấp qua một hàm không nhận tham số:
    SessionPanel(root, result_provider=ham_lay_ket_qua)
    # hoặc gắn sau: panel.set_result_provider(ham_lay_ket_qua)
   `ham_lay_ket_qua()` trả về kết quả của lần sắp xếp gần nhất:
    {"values": [5, 2, 9],          # dãy đầu vào
     "sorted_values": [2, 5, 9],   # dãy sau khi sắp xếp
     "swaps": 2,                   # số lần hoán đổi
     "comparisons": 3}             # số lần so sánh
   hoặc trả về None nếu chưa có kết quả nào. Khi bấm "Thêm session", người dùng chỉ chọn
   thuật toán và nhập ghi chú; mã session (SE0001, SE0002...) do hệ thống tự sinh.

3) FILE DỮ LIỆU (tùy chọn): SessionPanel(root, data_file="duong/dan/sessions.json")

Không dùng giao diện thì gọi thẳng (username lấy từ lúc tạo SessionManager):
    manager = SessionManager(username); manager.load()
    manager.add_and_save(algorithm, values, sorted_values, swaps, comparisons, note)