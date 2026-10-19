from datetime import datetime

#Kiểm tra dữ liệu
def _is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)

#Session
class session:
    def __init__(self, session_id, username, algorithm, values, swaps, comparisons, note=""):
        self.session_id = session_id
        self.username = username
        self.algorithm = algorithm
        self.values = values
        self.swaps = swaps
        self.comparisons = comparisons
        self.create_at = datetime.now().isoformat(timespec='seconds')
        self.note = note

    def to_dict(self):
        return {
            "session_id": self.session_id,
            "username": self.username,
            "algorithm": self.algorithm,
            "values": self.values,
            "swaps": self.swaps,
            "comparisons": self.comparisons,
            "create_at": self.create_at,
            "note": self.note
        }