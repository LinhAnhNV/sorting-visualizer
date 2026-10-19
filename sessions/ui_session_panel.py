import session_manager

test = session_manager.SessionManager("Nhu")
test.load()
test.delete(5)
test.save()