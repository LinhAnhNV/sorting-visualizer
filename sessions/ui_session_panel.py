import os
import re
import sys
import tkinter as tk
from tkinter import ttk, messagebox

import session_manager
import stats

ALGORITHMS = ["Bubble Sort", "Selection Sort", "Insertion Sort"]
ALL = "Tất cả"  # lựa chọn "không lọc"


def parse_values(text):
    """'5, 2 9;1' -> [5, 2, 9, 1]. Để trống -> []. Sai định dạng -> ValueError."""
    text = text.strip()
    if not text:
        return []
    try:
        return [int(x) for x in re.split(r"[,;\s]+", text)]
    except ValueError:
        raise ValueError("Dãy số chỉ được gồm các số nguyên, cách nhau bằng dấu phẩy hoặc khoảng trắng.")


def parse_count(text, name):
    try:
        number = int(text.strip() or "0")
    except ValueError:
        raise ValueError(f"{name} phải là số nguyên.")
    if number < 0:
        raise ValueError(f"{name} phải >= 0.")
    return number


class AddSessionDialog(tk.Toplevel):
    """Hộp thoại nhập một session mới."""

    def __init__(self, master, manager, on_added):
        super().__init__(master)
        self.title("Thêm session")
        self.resizable(False, False)
        self.manager = manager
        self.on_added = on_added

        self.algorithm = tk.StringVar(value=ALGORITHMS[0])
        self.values = tk.StringVar()
        self.swaps = tk.StringVar(value="0")
        self.comparisons = tk.StringVar(value="0")
        self.note = tk.StringVar()

        form = ttk.Frame(self, padding=12)
        form.pack()
        rows = (
            ("Thuật toán", ttk.Combobox(form, textvariable=self.algorithm, values=ALGORITHMS,
                                        state="readonly", width=34)),
            ("Dãy số (vd: 5, 2, 9, 1)", ttk.Entry(form, textvariable=self.values, width=36)),
            ("Số lần swap", ttk.Entry(form, textvariable=self.swaps, width=36)),
            ("Số lần so sánh", ttk.Entry(form, textvariable=self.comparisons, width=36)),
            ("Ghi chú", ttk.Entry(form, textvariable=self.note, width=36)),
        )
        for i, (label, widget) in enumerate(rows):
            ttk.Label(form, text=label).grid(row=i, column=0, sticky="w", pady=4, padx=(0, 8))
            widget.grid(row=i, column=1, pady=4)

        buttons = ttk.Frame(form)
        buttons.grid(row=len(rows), column=0, columnspan=2, sticky="e", pady=(10, 0))
        ttk.Button(buttons, text="Lưu", command=self.submit).pack(side="left", padx=4)
        ttk.Button(buttons, text="Hủy", command=self.destroy).pack(side="left", padx=4)

        self.transient(master)
        self.grab_set()

    def submit(self):
        try:
            values = parse_values(self.values.get())
            swaps = parse_count(self.swaps.get(), "Số lần swap")
            comparisons = parse_count(self.comparisons.get(), "Số lần so sánh")
            self.manager.add(self.algorithm.get(), values, swaps, comparisons, self.note.get().strip())
            self.manager.save()
        except ValueError as e:
            messagebox.showerror("Dữ liệu chưa hợp lệ", str(e), parent=self)
            return
        self.on_added()
        self.destroy()


class SessionPanel(ttk.Frame):
    COLUMNS = (
        ("id", "ID", 80),
        ("algorithm", "Thuật toán", 130),
        ("size", "Số phần tử", 90),
        ("swaps", "Swaps", 70),
        ("comparisons", "So sánh", 80),
        ("time", "Thời gian", 150),
        ("note", "Ghi chú", 220),
    )

    def __init__(self, master, manager):
        super().__init__(master, padding=8)
        self.manager = manager
        self._build()
        self.refresh()

    def _build(self):
        # Thanh chọn user: người khác nhập tên của mình rồi bấm "Đổi user"
        user_bar = ttk.Frame(self)
        user_bar.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
        ttk.Label(user_bar, text="User:").pack(side="left")
        self.user_var = tk.StringVar(value=self.manager.username)
        user_entry = ttk.Entry(user_bar, textvariable=self.user_var, width=20)
        user_entry.pack(side="left", padx=6)
        user_entry.bind("<Return>", lambda _e: self.switch_user())
        ttk.Button(user_bar, text="Đổi user", command=self.switch_user).pack(side="left")

        # Lọc theo thuật toán
        ttk.Label(user_bar, text="Lọc thuật toán:").pack(side="left", padx=(24, 0))
        self.filter_var = tk.StringVar(value=ALL)
        self.filter_box = ttk.Combobox(user_bar, textvariable=self.filter_var,
                                       values=[ALL] + ALGORITHMS, state="readonly", width=16)
        self.filter_box.pack(side="left", padx=6)
        self.filter_box.bind("<<ComboboxSelected>>", lambda _e: self.refresh())

        # Bảng danh sách session
        self.tree = ttk.Treeview(self, columns=[c[0] for c in self.COLUMNS],
                                 show="headings", selectmode="browse", height=10)
        for key, title, width in self.COLUMNS:
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, anchor="w")
        scroll = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.grid(row=1, column=0, sticky="nsew")
        scroll.grid(row=1, column=1, sticky="ns")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # Chi tiết session đang chọn
        self.detail = tk.Text(self, height=4, state="disabled", wrap="word")
        self.detail.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        # Nút chức năng
        buttons = ttk.Frame(self)
        buttons.grid(row=3, column=0, columnspan=2, sticky="e", pady=8)
        ttk.Button(buttons, text="Thêm session", command=self.add_session).pack(side="left", padx=4)
        ttk.Button(buttons, text="Làm mới", command=self.reload).pack(side="left", padx=4)
        ttk.Button(buttons, text="Xóa session", command=self.delete_selected).pack(side="left", padx=4)

        # Thống kê
        self.stats_label = ttk.Label(self, justify="left")
        self.stats_label.grid(row=4, column=0, columnspan=2, sticky="w")

        # Cho biết đang đọc file nào, có bao nhiêu session
        self.status_label = ttk.Label(self, foreground="gray")
        self.status_label.grid(row=5, column=0, columnspan=2, sticky="w", pady=(6, 0))

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

    def _update_filter_options(self):
        """Danh sách lọc = các thuật toán có sẵn + thuật toán lạ xuất hiện trong dữ liệu."""
        extra = sorted({s.algorithm for s in self.manager.sessions} - set(ALGORITHMS))
        options = [ALL] + ALGORITHMS + extra
        self.filter_box.config(values=options)
        if self.filter_var.get() not in options:
            self.filter_var.set(ALL)

    def refresh(self):
        """Vẽ lại bảng và thống kê theo bộ lọc hiện tại."""
        self._update_filter_options()
        selected_algorithm = self.filter_var.get()
        shown = self.manager.filter_by_algorithm(None if selected_algorithm == ALL else selected_algorithm)

        self.tree.delete(*self.tree.get_children())
        for s in shown:
            self.tree.insert("", "end", iid=str(s.session_id), values=(
                s.session_id, s.algorithm, len(s.values), s.swaps,
                s.comparisons, s.create_at.replace("T", " "), s.note,
            ))
        self._set_detail("")
        self.stats_label.config(text=stats.format_report(shown))

        path = self.manager.data_file
        if os.path.exists(path):
            self.status_label.config(
                text=f"User '{self.manager.username}': hiển thị {len(shown)}/{len(self.manager.sessions)} session"
                     f" | File: {path}")
        else:
            self.status_label.config(text=f"Không tìm thấy file dữ liệu: {path}")

        self.winfo_toplevel().title(f"Lịch sử session - {self.manager.username}")

    def reload(self):
        """Đọc lại dữ liệu từ file rồi vẽ lại."""
        try:
            self.manager.load()
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không đọc được dữ liệu:\n{e}")
            return
        self.refresh()

    def switch_user(self):
        name = self.user_var.get().strip()
        if not name:
            messagebox.showinfo("Thông báo", "Hãy nhập tên user.")
            return
        new_manager = session_manager.SessionManager(name, data_file=self.manager.data_file)
        try:
            new_manager.load()
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không đọc được dữ liệu:\n{e}")
            return
        self.manager = new_manager
        self.refresh()

    def add_session(self):
        AddSessionDialog(self, self.manager, on_added=self.refresh)

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Thông báo", "Hãy chọn một session để xóa.")
            return
        session_id = self._find_id(selected[0])
        if not messagebox.askyesno("Xác nhận", f"Xóa session {session_id}?"):
            return
        if self.manager.delete(session_id):
            self.manager.save()
        self.refresh()

    # ---------- nội bộ ----------
    def _find_id(self, iid):
        # iid trong Treeview luôn là chuỗi, nên tìm lại id gốc của session
        for s in self.manager.sessions:
            if str(s.session_id) == iid:
                return s.session_id
        return iid

    def _on_select(self, _event):
        selected = self.tree.selection()
        if not selected:
            return
        s = self.manager.get(self._find_id(selected[0]))
        if s:
            self._set_detail(f"Dữ liệu gốc: {s.values}\nSau khi sắp xếp: {s.sorted_values}")

    def _set_detail(self, text):
        self.detail.config(state="normal")
        self.detail.delete("1.0", "end")
        self.detail.insert("1.0", text)
        self.detail.config(state="disabled")


if __name__ == "__main__":
    username = sys.argv[1] if len(sys.argv) > 1 else "Nhu"
    manager = session_manager.SessionManager(username)
    manager.load()

    root = tk.Tk()
    panel = SessionPanel(root, manager)
    panel.pack(fill="both", expand=True)
    root.mainloop()