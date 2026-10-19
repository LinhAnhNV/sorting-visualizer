import json
from datetime import datetime

#Kiểm tra dữ liệu
def _is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)

#Session
class Session:
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

class SessionManager:
    def __init__(self, username):
        self.username = username
        self.sessions = []

    def load(self):
        with open("data/sessions.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        for sessions in data["users"]:
            if sessions["username"] == self.username:
                for session_data in sessions["sessions"]:
                    session = Session(
                        session_id=session_data["session_id"],
                        username=self.username,
                        algorithm=session_data["algorithm"],
                        values=session_data["values"],
                        swaps=session_data["swaps"],
                        comparisons=session_data["comparisons"],
                        note=session_data.get("note", "")
                    )
                    self.sessions.append(session)

    def save(self):
        with open("data/sessions.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        user_found = False
        for user in data["users"]:
            if user["username"] == self.username:
                user_found = True
                user["sessions"] = [session.to_dict() for session in self.sessions]
                break

        if not user_found:
            new_user = {
                "username": self.username,
                "sessions": [session.to_dict() for session in self.sessions]
            }
            data["users"].append(new_user)

        with open("data/sessions.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def add(self, algorithm, values, swaps, comparisons, note=""):
        session_id = len(self.sessions) + 1
        new_session = Session(session_id, self.username, algorithm, values, swaps, comparisons, note)
        self.sessions.append(new_session)

    def delete(self, session_id):
        self.sessions = [session for session in self.sessions if session.session_id != session_id]