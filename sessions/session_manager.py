import json
import os
import re
import shutil
from datetime import datetime


def _find_data_file():
    """Tìm data/sessions.json: thư mục đang chạy -> cạnh file này -> thư mục cha của file này."""
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.abspath(os.path.join("data", "sessions.json")),
        os.path.join(here, "data", "sessions.json"),
        os.path.join(os.path.dirname(here), "data", "sessions.json"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return candidates[1]  # chưa có file nào -> mặc định tạo cạnh file này


DATA_FILE = _find_data_file()

# Vai trò người dùng
ROLE_ADMIN = "admin"
ROLE_USER = "user"
VALID_ROLES = (ROLE_ADMIN, ROLE_USER)

# Mã session do hệ thống tự sinh: "SE" + 4 chữ số (SE0001, SE0002...)
SESSION_ID_PREFIX = "SE"
SESSION_ID_DIGITS = 4
MAX_SESSION_NUMBER = 10 ** SESSION_ID_DIGITS - 1  # 9999


class SessionDataError(Exception):
    """Không đọc/ghi được file dữ liệu (không mở được, không có quyền, ổ đĩa lỗi...)."""


class CorruptDataError(SessionDataError):
    """File tồn tại nhưng sai định dạng JSON hoặc sai cấu trúc tổng thể."""


#Kiểm tra dữ liệu
def _is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def _is_int_list(x):
    return isinstance(x, list) and all(_is_int(v) for v in x)


def _is_sorted_permutation(values, sorted_values):
    """sorted_values phải gồm đúng các phần tử của values và đã có thứ tự (tăng hoặc giảm dần)."""
    if sorted(values) != sorted(sorted_values):
        return False
    pairs = list(zip(sorted_values, sorted_values[1:]))
    return all(a <= b for a, b in pairs) or all(a >= b for a, b in pairs)


def _validate(algorithm, values, sorted_values, swaps, comparisons):
    if not isinstance(algorithm, str) or not algorithm.strip():
        raise ValueError("algorithm phải là chuỗi không rỗng")
    if not _is_int_list(values):
        raise ValueError("values phải là list các số nguyên")
    if not _is_int_list(sorted_values):
        raise ValueError("sorted_values phải là list các số nguyên")
    if not _is_sorted_permutation(values, sorted_values):
        raise ValueError("sorted_values phải là dãy values đã được sắp xếp tăng hoặc giảm")
    if not _is_int(swaps) or swaps < 0:
        raise ValueError("swaps phải là số nguyên >= 0")
    if not _is_int(comparisons) or comparisons < 0:
        raise ValueError("comparisons phải là số nguyên >= 0")


def _parse_session(raw):
    """Kiểm tra và chuẩn hóa một session đọc từ file.
    Trả về dict tham số cho Session, hoặc raise ValueError kèm lý do."""
    if not isinstance(raw, dict):
        raise ValueError("không phải đối tượng JSON")

    session_id = raw.get("session_id")
    if isinstance(session_id, bool) or not isinstance(session_id, (str, int)) or session_id == "":
        raise ValueError("thiếu hoặc sai session_id")
    label = f"id {session_id}"

    algorithm = raw.get("algorithm")
    if not isinstance(algorithm, str) or not algorithm.strip():
        raise ValueError(f"{label}: thiếu hoặc sai algorithm")
    if not _is_int_list(raw.get("values")):
        raise ValueError(f"{label}: values phải là list số nguyên")
    for key in ("swaps", "comparisons"):
        if not _is_int(raw.get(key)) or raw[key] < 0:
            raise ValueError(f"{label}: {key} phải là số nguyên >= 0")

    # Các trường phụ: sai thì dùng giá trị mặc định thay vì bỏ cả session
    note = raw.get("note", "")
    note = "" if note is None else str(note)

    create_at = raw.get("create_at")
    try:
        datetime.fromisoformat(create_at)
    except (TypeError, ValueError):
        create_at = None

    sorted_values = raw.get("sorted_values")
    if not _is_int_list(sorted_values):
        sorted_values = None

    return {
        "session_id": session_id,
        "algorithm": algorithm,
        "values": raw["values"],
        "swaps": raw["swaps"],
        "comparisons": raw["comparisons"],
        "note": note,
        "create_at": create_at,
        "sorted_values": sorted_values,
    }


#Session
class Session:
    def __init__(self, session_id, username, algorithm, values, swaps, comparisons,
                 note="", create_at=None, sorted_values=None):
        self.session_id = session_id
        self.username = username
        self.algorithm = algorithm
        self.values = list(values)
        self.swaps = swaps
        self.comparisons = comparisons
        # Giữ nguyên thời gian tạo cũ khi load từ file, chỉ lấy giờ hiện tại khi tạo mới
        self.create_at = create_at or datetime.now().isoformat(timespec='seconds')
        self.note = note
        # Nếu chưa có kết quả sắp xếp thì tự tính từ values
        self.sorted_values = list(sorted_values) if sorted_values is not None else sorted(self.values)

    def to_dict(self):
        return {
            "session_id": self.session_id,
            "username": self.username,
            "algorithm": self.algorithm,
            "values": self.values,
            "swaps": self.swaps,
            "comparisons": self.comparisons,
            "create_at": self.create_at,
            "note": self.note,
            "sorted_values": self.sorted_values
        }


class SessionManager:
    def __init__(self, username, data_file=DATA_FILE):
        if not isinstance(username, str) or not username.strip():
            raise ValueError("username không được để trống")
        self.username = username.strip()
        self.data_file = data_file
        self.role = ROLE_USER  # được cập nhật từ file trong load()
        self.sessions = []
        self.warnings = []     # cảnh báo của lần load() gần nhất (bản ghi lỗi bị bỏ qua...)
        self._skipped_raw = [] # bản ghi lỗi của user này: không hiển thị nhưng vẫn giữ nguyên trong file

    @property
    def is_admin(self):
        return self.role == ROLE_ADMIN

    # ---------- Đọc / ghi file ----------
    def _read_file(self):
        """Đọc toàn bộ file JSON.
        - File chưa có hoặc rỗng -> dữ liệu rỗng.
        - Không mở được -> SessionDataError.
        - Sai JSON / sai cấu trúc -> CorruptDataError."""
        path = self.data_file
        if not os.path.exists(path):
            return {"users": []}

        try:
            with open(path, "r", encoding="utf-8-sig") as f:  # utf-8-sig: chấp nhận cả file có BOM
                content = f.read()
        except UnicodeDecodeError as e:
            raise CorruptDataError(f"File {path} không đọc được (không phải UTF-8).") from e
        except OSError as e:
            raise SessionDataError(f"Không mở được file {path}: {e.strerror or e}") from e

        if not content.strip():
            return {"users": []}

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise CorruptDataError(
                f"File {path} không phải JSON hợp lệ (dòng {e.lineno}, cột {e.colno}: {e.msg}).") from e

        if data == {}:
            return {"users": []}
        if not isinstance(data, dict) or not isinstance(data.get("users"), list):
            raise CorruptDataError(f'File {path} sai cấu trúc: cần có dạng {{"users": [...]}}.')
        return data

    def _write_file(self, data):
        """Ghi qua file tạm rồi thay thế, tránh hỏng file nếu bị lỗi giữa chừng."""
        tmp_path = self.data_file + ".tmp"
        try:
            folder = os.path.dirname(self.data_file)
            if folder:
                os.makedirs(folder, exist_ok=True)
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            os.replace(tmp_path, self.data_file)
        except OSError as e:
            try:
                os.remove(tmp_path)
            except OSError:
                pass
            raise SessionDataError(f"Không ghi được file {self.data_file}: {e.strerror or e}") from e

    def _backup(self):
        """Giữ bản sao của file trước khi ghi đè (sessions.json.bak). Lỗi sao lưu không chặn việc lưu."""
        if os.path.isfile(self.data_file):
            try:
                shutil.copy2(self.data_file, self.data_file + ".bak")
            except OSError:
                pass

    @staticmethod
    def _users(data):
        """Chỉ lấy các mục user hợp lệ (là đối tượng JSON), bỏ qua phần tử rác."""
        for user in data["users"]:
            if isinstance(user, dict):
                yield user

    def _next_session_id(self):
        """Sinh mã dạng SE0001, SE0002... không trùng với bất kỳ session nào (của mọi user) trong file."""
        ids = [session.session_id for session in self.sessions]
        for user in self._users(self._read_file()):
            raw_sessions = user.get("sessions", [])
            if isinstance(raw_sessions, list):
                ids.extend(s.get("session_id") for s in raw_sessions if isinstance(s, dict))

        used = set()
        for sid in ids:
            match = re.search(r"\d+", str(sid))
            if match:
                used.add(int(match.group()))

        number = max(used, default=0) + 1
        if number > MAX_SESSION_NUMBER:
            # Hết số ở cuối dãy thì tìm số trống nhỏ nhất (số của session đã xóa)
            number = next((n for n in range(1, MAX_SESSION_NUMBER + 1) if n not in used), None)
            if number is None:
                raise SessionDataError(
                    f"Đã dùng hết mã session (tối đa {SESSION_ID_PREFIX}{MAX_SESSION_NUMBER}).")
        return f"{SESSION_ID_PREFIX}{number:0{SESSION_ID_DIGITS}d}"

    @staticmethod
    def _build_sessions(username, user_data, warnings, skipped=None):
        """Dựng danh sách Session của một user. Bản ghi lỗi bị bỏ qua, ghi vào warnings
        và (nếu có) được gom vào danh sách skipped."""
        raw_sessions = user_data.get("sessions", [])
        if not isinstance(raw_sessions, list):
            warnings.append(f"User '{username}': mục 'sessions' không phải danh sách, đã bỏ qua.")
            return []

        sessions = []
        seen_ids = set()
        for index, raw in enumerate(raw_sessions, start=1):
            try:
                parsed = _parse_session(raw)
                if parsed["session_id"] in seen_ids:
                    raise ValueError(f"id {parsed['session_id']} bị trùng")
                seen_ids.add(parsed["session_id"])
                sessions.append(Session(username=username, **parsed))
            except ValueError as e:
                warnings.append(f"User '{username}': bỏ qua session thứ {index} ({e}).")
                if skipped is not None:
                    skipped.append(raw)
        return sessions

    # ---------- Chức năng chính ----------
    def load(self):
        """Đọc dữ liệu của user này. Nếu lỗi thì trạng thái cũ được giữ nguyên."""
        file_exists = os.path.exists(self.data_file)
        data = self._read_file()  # có thể raise SessionDataError / CorruptDataError

        warnings = []
        if not file_exists:
            warnings.append(f"Chưa có file dữ liệu: {self.data_file}. "
                            f"File sẽ được tạo khi lưu session đầu tiên.")

        sessions = []
        skipped = []
        role = ROLE_USER
        for user in self._users(data):
            if user.get("username") == self.username:
                raw_role = user.get("role", ROLE_USER)
                if raw_role in VALID_ROLES:
                    role = raw_role
                else:
                    warnings.append(f"Vai trò '{raw_role}' không hợp lệ, dùng '{ROLE_USER}'.")
                sessions = self._build_sessions(self.username, user, warnings, skipped)
                break

        self.sessions, self.role, self.warnings = sessions, role, warnings
        self._skipped_raw = skipped

    def all_sessions(self):
        """Session của tất cả người dùng. Chỉ admin mới được xem.
        Bản ghi lỗi của user khác được bỏ qua."""
        if not self.is_admin:
            raise PermissionError("Chỉ admin mới xem được session của tất cả người dùng.")

        result = []
        has_self = False
        for user in self._users(self._read_file()):
            name = user.get("username")
            if not isinstance(name, str) or not name:
                continue
            if name == self.username:
                if not has_self:
                    result.extend(self.sessions)  # dùng bản đang có trong bộ nhớ
                    has_self = True
            else:
                result.extend(self._build_sessions(name, user, []))
        if not has_self:
            result.extend(self.sessions)
        return result

    def save(self):
        data = self._read_file()  # file đang lỗi thì dừng ở đây, không ghi đè

        mine = None
        for user in self._users(data):
            if user.get("username") == self.username:
                mine = user
                break

        # Bản ghi lỗi chưa sửa được vẫn giữ nguyên trong file để người dùng tự chỉnh, không bị mất
        sessions = [session.to_dict() for session in self.sessions] + self._skipped_raw
        if mine is None:
            data["users"].append({
                "username": self.username,
                "role": self.role,
                "sessions": sessions
            })
        else:
            mine["sessions"] = sessions

        self._backup()
        self._write_file(data)

    def reset_data_file(self):
        """Dùng khi file bị lỗi: đổi tên file cũ thành *.corrupt-<thời gian> rồi tạo file mới rỗng.
        Trả về đường dẫn bản sao lưu (hoặc None nếu trước đó chưa có file)."""
        backup = None
        if os.path.isfile(self.data_file):
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            backup = f"{self.data_file}.corrupt-{stamp}"
            try:
                os.replace(self.data_file, backup)
            except OSError as e:
                raise SessionDataError(f"Không sao lưu được file lỗi: {e.strerror or e}") from e
        self._write_file({"users": []})
        self.sessions, self.role, self.warnings = [], ROLE_USER, []
        self._skipped_raw = []
        return backup

    def add(self, algorithm, values, sorted_values, swaps, comparisons, note=""):
        """Tạo session mới trong bộ nhớ (chưa ghi file) và trả về nó.
        - algorithm, note: người dùng nhập.
        - values (dãy đầu vào), sorted_values (dãy sau sắp xếp), swaps, comparisons: do phần code
          sắp xếp cung cấp.
        - session_id: hệ thống tự sinh (SE0001, SE0002...), không nhận từ bên ngoài.
        Dữ liệu sai thì raise ValueError."""
        _validate(algorithm, values, sorted_values, swaps, comparisons)
        note = "" if note is None else str(note).strip()
        session_id = self._next_session_id()
        new_session = Session(session_id, self.username, algorithm.strip(), values, swaps,
                              comparisons, note, sorted_values=sorted_values)
        self.sessions.append(new_session)
        return new_session

    def add_and_save(self, algorithm, values, sorted_values, swaps, comparisons, note=""):
        """Giống add() nhưng ghi file luôn. Ghi thất bại thì hoàn tác để bộ nhớ khớp với file."""
        session = self.add(algorithm, values, sorted_values, swaps, comparisons, note)
        try:
            self.save()
        except SessionDataError:
            self.sessions.remove(session)
            raise
        return session

    def get(self, session_id):
        for session in self.sessions:
            if session.session_id == session_id:
                return session
        return None

    def filter_by_algorithm(self, algorithm=None, sessions=None):
        """Lọc theo thuật toán trên `sessions` (mặc định: session của user này).
        algorithm rỗng/None -> trả về tất cả."""
        source = self.sessions if sessions is None else sessions
        if not algorithm:
            return list(source)
        return [session for session in source
                if session.algorithm.casefold() == algorithm.casefold()]

    def delete(self, session_id):
        before = len(self.sessions)
        self.sessions = [session for session in self.sessions if session.session_id != session_id]
        return len(self.sessions) < before