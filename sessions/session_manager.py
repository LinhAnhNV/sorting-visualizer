class Session:
    def __init__(self, session_id, algorithm):
        self.session_id = session_id
        self.algorithm = algorithm
        self.comparisons = 0
        self.swaps = 0

class SessionManager:
    def __init__(self):
        self.sessions = []