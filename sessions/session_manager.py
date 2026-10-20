import json
import os
import re
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


#Kiểm tra dữ liệu
def _is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def _validate(algorithm, values, swaps, comparisons):
    if not isinstance(algorithm, str) or not algorithm.strip():
        raise ValueError("algorithm phải là chuỗi không rỗng")
    if not isinstance(values, list) or not all(_is_int(v) for v in values):
        raise ValueError("values phải là list các số nguyên")
    if not _is_int(swaps) or swaps < 0:
        raise ValueError("swaps phải là số nguyên >= 0")
    if not _is_int(comparisons) or comparisons < 0:
        raise ValueError("comparisons phải là số nguyên >= 0")


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
        self.username = username
        self.data_file = data_file
        self.sessions = []

    # ---------- Đọc / ghi file ----------
    def _read_file(self):
        """Đọc toàn bộ file JSON. File chưa có hoặc rỗng -> dữ liệu rỗng."""
        if not os.path.exists(self.data_file):
            return {"users": []}
        with open(self.data_file, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if not content:
            return {"users": []}
        data = json.loads(content)  # JSON hỏng sẽ báo lỗi, không âm thầm ghi đè mất dữ liệu
        if not isinstance(data, dict):
            data = {}
        if not isinstance(data.get("users"), list):
            data["users"] = []
        return data

    def _write_file(self, data):
        """Ghi qua file tạm rồi thay thế, tránh hỏng file nếu bị lỗi giữa chừng."""
        folder = os.path.dirname(self.data_file)
        if folder:
            os.makedirs(folder, exist_ok=True)
        tmp_path = self.data_file + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        os.replace(tmp_path, self.data_file)

    def _next_session_id(self):
        """Tạo id dạng SES001, SES002... không trùng với bất kỳ session nào trong file."""
        ids = [session.session_id for session in self.sessions]
        for user in self._read_file()["users"]:
            ids.extend(s.get("session_id") for s in user.get("sessions", []))

        numbers = []
        for sid in ids:
            match = re.search(r"\d+", str(sid))
            if match:
                numbers.append(int(match.group()))
        return f"SES{max(numbers, default=0) + 1:03d}"

    # ---------- Chức năng chính ----------
    def load(self):
        self.sessions = []  # tránh bị nhân đôi khi gọi load() nhiều lần
        data = self._read_file()

        for user in data["users"]:
            if user.get("username") == self.username:
                for session_data in user.get("sessions", []):
                    session = Session(
                        session_id=session_data["session_id"],
                        username=self.username,
                        algorithm=session_data["algorithm"],
                        values=session_data["values"],
                        swaps=session_data["swaps"],
                        comparisons=session_data["comparisons"],
                        note=session_data.get("note", ""),
                        create_at=session_data.get("create_at"),
                        sorted_values=session_data.get("sorted_values")
                    )
                    self.sessions.append(session)
                break

    def save(self):
        data = self._read_file()

        user_found = False
        for user in data["users"]:
            if user.get("username") == self.username:
                user_found = True
                user["sessions"] = [session.to_dict() for session in self.sessions]
                break

        if not user_found:
            new_user = {
                "username": self.username,
                "sessions": [session.to_dict() for session in self.sessions]
            }
            data["users"].append(new_user)

        self._write_file(data)

    def add(self, algorithm, values, swaps, comparisons, note="", sorted_values=None):
        _validate(algorithm, values, swaps, comparisons)
        session_id = self._next_session_id()
        new_session = Session(session_id, self.username, algorithm, values, swaps,
                              comparisons, note, sorted_values=sorted_values)
        self.sessions.append(new_session)
        return new_session

    def get(self, session_id):
        for session in self.sessions:
            if session.session_id == session_id:
                return session
        return None

    def filter_by_algorithm(self, algorithm=None):
        """Trả về các session của một thuật toán. algorithm rỗng/None -> trả về tất cả."""
        if not algorithm:
            return list(self.sessions)
        return [session for session in self.sessions
                if session.algorithm.casefold() == algorithm.casefold()]

    def delete(self, session_id):
        before = len(self.sessions)
        self.sessions = [session for session in self.sessions if session.session_id != session_id]
        return len(self.sessions) < before