"""Bản giả lập tối thiểu của tkinter để kiểm thử LOGIC giao diện khi không có màn hình.

Không thay thế được việc chạy thật trên Tk (không kiểm tra bố cục/hiển thị), nhưng đủ để
chạy toàn bộ code của App / ControlPanel / CanvasView / BenchmarkWindow và bắt các lỗi như
gõ sai tên hàm, sai luồng trạng thái, sai logic cập nhật. Các phương thức Tk "vô hại"
(pack, grid, bind ...) nằm trong danh sách trắng; truy cập tên khác sẽ báo AttributeError.
"""
import itertools
import sys
import types

SCHEDULE = []          # [(id, fn)] các callback đăng ký bằng after()
_ids = itertools.count(1)

HARMLESS = {
    "pack", "grid", "place", "columnconfigure", "rowconfigure",
    "protocol", "title", "geometry", "minsize", "lift", "focus_force", "mainloop",
    "theme_use", "heading", "column", "add", "pack_propagate", "winfo_toplevel", "set", "bind_all", "unbind_all",
}


def run_pending(limit=200000):
    """Chạy lần lượt các callback after() cho tới khi hết (mô phỏng mainloop)."""
    n = 0
    while SCHEDULE and n < limit:
        _id, fn = SCHEDULE.pop(0)
        fn()
        n += 1
    return n


def run_n(count):
    n = 0
    while SCHEDULE and n < count:
        _id, fn = SCHEDULE.pop(0)
        fn()
        n += 1
    return n


class TclError(Exception):
    pass


class Variable:
    def __init__(self, master=None, value=None, **_):
        self._v = value

    def get(self):
        return self._v

    def set(self, v):
        self._v = v


class StringVar(Variable):
    def __init__(self, master=None, value="", **kw):
        super().__init__(master, value, **kw)


class IntVar(Variable):
    def __init__(self, master=None, value=0, **kw):
        super().__init__(master, value, **kw)


class DoubleVar(Variable):
    def __init__(self, master=None, value=0.0, **kw):
        super().__init__(master, value, **kw)


class BooleanVar(Variable):
    def __init__(self, master=None, value=False, **kw):
        super().__init__(master, value, **kw)


class Widget:
    def __init__(self, master=None, *args, **kw):
        self.master = master
        self.kw = dict(kw)
        self._command = kw.get("command")
        self._disabled = False
        self._destroyed = False
        self._bindings = {}
        self._items = {}

    def __getattr__(self, name):
        if name in HARMLESS:
            return lambda *a, **k: None
        raise AttributeError(f"fake tkinter: '{type(self).__name__}' không có '{name}'")

    def configure(self, **kw):
        self.kw.update(kw)

    config = configure

    def yview(self, *args):
        return None

    # các hàm hay dùng ----------------------------------------------------
    def winfo_width(self):
        return 800

    def winfo_height(self):
        return 500

    def winfo_reqwidth(self):
        return 300

    def winfo_screenheight(self):
        return 1080

    def winfo_exists(self):
        return 0 if self._destroyed else 1

    def destroy(self):
        self._destroyed = True

    def state(self, flags):
        for f in flags:
            if f == "disabled":
                self._disabled = True
            elif f == "!disabled":
                self._disabled = False

    def invoke(self):
        """Giả lập người dùng bấm nút."""
        if not self._disabled and self._command:
            self._command()

    def bind(self, seq, fn=None, add=None):
        self._bindings[seq] = fn

    def event(self, seq, *args):
        fn = self._bindings.get(seq)
        if fn:
            fn(*args)

    def after(self, ms, fn=None, *args):
        i = next(_ids)
        SCHEDULE.append((i, (lambda: fn(*args))))
        return i

    def after_cancel(self, ident):
        SCHEDULE[:] = [(i, f) for (i, f) in SCHEDULE if i != ident]

    def __setitem__(self, key, value):
        self.kw[key] = value

    def __getitem__(self, key):
        return self.kw[key]


class Tk(Widget):
    pass


class Toplevel(Widget):
    pass


class Frame(Widget):
    pass


class Canvas(Widget):
    def __init__(self, master=None, **kw):
        super().__init__(master, **kw)
        self.items = {}

    def _new(self, kind, coords, kw):
        i = next(_ids)
        self.items[i] = {"kind": kind, "coords": list(coords), **kw}
        return i

    def create_rectangle(self, *c, **kw):
        return self._new("rect", c, kw)

    def create_text(self, *c, **kw):
        return self._new("text", c, kw)

    def create_line(self, *c, **kw):
        return self._new("line", c, kw)

    def create_oval(self, *c, **kw):
        return self._new("oval", c, kw)

    def create_window(self, *c, **kw):
        return self._new("window", c, kw)

    def bbox(self, *what):
        return (0, 0, 300, 1000)

    def itemconfigure(self, item, **kw):
        self.items[item].update(kw)

    def yview(self, *args):
        """Không đối số: trả (đầu, cuối) của vùng nhìn thấy. Có đối số: lệnh cuộn từ Scrollbar."""
        if not args:
            return getattr(self, "_view", (0.0, 0.5))
        self.scrolled = getattr(self, "scrolled", []) + [args]

    def yview_scroll(self, n, what):
        self.scrolled = getattr(self, "scrolled", []) + [("scroll", n, what)]

    def coords(self, item, *c):
        self.items[item]["coords"] = list(c)

    def itemconfig(self, item, **kw):
        self.items[item].update(kw)

    def delete(self, *what):
        if "all" in what:
            self.items.clear()
        else:
            for w in what:
                self.items.pop(w, None)


class Treeview(Widget):
    def __init__(self, master=None, **kw):
        super().__init__(master, **kw)
        self.rows = {}

    def insert(self, parent, index, values=(), **kw):
        i = next(_ids)
        self.rows[i] = tuple(values)
        return i

    def get_children(self, *a):
        return tuple(self.rows)

    def delete(self, *ids):
        for i in ids:
            self.rows.pop(i, None)


class Style(Widget):
    def theme_use(self, name=None):
        return None

    def lookup(self, style, option, state=None, default=None):
        return "#dcdad5"


# --------------------------------------------------------------- messagebox / dialogs
class _MessageBox(types.ModuleType):
    def __init__(self):
        super().__init__("tkinter.messagebox")
        self.calls = []

    def showerror(self, title=None, message=None, **kw):
        self.calls.append(("error", title, message))

    def showinfo(self, title=None, message=None, **kw):
        self.calls.append(("info", title, message))


class _FileDialog(types.ModuleType):
    def __init__(self):
        super().__init__("tkinter.filedialog")
        self.open_result = ""
        self.save_result = ""

    def askopenfilename(self, **kw):
        return self.open_result

    def asksaveasfilename(self, **kw):
        return self.save_result


def build_modules():
    tk = types.ModuleType("tkinter")
    ttk = types.ModuleType("tkinter.ttk")
    messagebox, filedialog = _MessageBox(), _FileDialog()

    for name, obj in dict(Tk=Tk, Toplevel=Toplevel, Frame=Frame, Canvas=Canvas, TclError=TclError,
                          StringVar=StringVar, IntVar=IntVar, DoubleVar=DoubleVar,
                          BooleanVar=BooleanVar, Widget=Widget).items():
        setattr(tk, name, obj)
    for name in ("Frame", "LabelFrame", "Label", "Button", "Entry", "Combobox", "Spinbox",
                 "Scale", "Checkbutton", "Progressbar", "Notebook", "Scrollbar"):
        setattr(ttk, name, type(name, (Widget,), {}))
    ttk.Treeview = Treeview
    ttk.Style = Style
    tk.ttk, tk.messagebox, tk.filedialog = ttk, messagebox, filedialog
    return {"tkinter": tk, "tkinter.ttk": ttk, "tkinter.messagebox": messagebox,
            "tkinter.filedialog": filedialog}


def install():
    """Cài tkinter giả vào sys.modules; trả về hàm khôi phục."""
    saved = {k: sys.modules.get(k) for k in ("tkinter", "tkinter.ttk", "tkinter.messagebox",
                                              "tkinter.filedialog")}
    ui_saved = {k: v for k, v in sys.modules.items() if k == "ui" or k.startswith("ui.")}
    for k in ui_saved:
        del sys.modules[k]
    fake = build_modules()
    sys.modules.update(fake)
    SCHEDULE.clear()

    def restore():
        for k in [k for k in sys.modules if k.startswith("ui.")]:
            del sys.modules[k]
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v
        sys.modules.update(ui_saved)
        SCHEDULE.clear()

    return fake, restore
