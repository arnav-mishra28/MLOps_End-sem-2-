import threading
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List


class SessionStore:
    def __init__(self):
        self._lock = threading.Lock()
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def create_session(
        self,
        student_name: str,
        subject: str,
        difficulty_level: str,
        first_question: str
    ) -> Dict[str, Any]:
        with self._lock:
            session_id = str(uuid.uuid4())
            now_iso = datetime.now(timezone.utc).isoformat()
            
            session_data: Dict[str, Any] = {
                "session_id": session_id,
                "student_name": student_name,
                "subject": subject,
                "difficulty_level": difficulty_level,
                "created_at": now_iso,
                "current_question_index": 1,
                "is_completed": False,
                "history": [
                    {
                        "question_number": 1,
                        "question": first_question,
                        "student_answer": None,
                        "score": None,
                        "feedback": None,
                        "timestamp": now_iso,
                    }
                ],
                "scores": [],
                "report": None,
            }
            self._sessions[session_id] = session_data
            return session_data

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            # Return shallow copy
            return dict(session)

    def record_answer_and_eval(
        self,
        session_id: str,
        answer: str,
        score: float,
        feedback: str,
        next_question: Optional[str] = None
    ) -> Dict[str, Any]:
        with self._lock:
            if session_id not in self._sessions:
                raise KeyError(f"Session '{session_id}' not found.")
            
            session = self._sessions[session_id]
            curr_idx = session["current_question_index"]
            now_iso = datetime.now(timezone.utc).isoformat()

            # Update current question record in history
            for q_round in session["history"]:
                if q_round["question_number"] == curr_idx:
                    q_round["student_answer"] = answer
                    q_round["score"] = score
                    q_round["feedback"] = feedback
                    q_round["timestamp"] = now_iso
                    break

            session["scores"].append(score)

            # If next question is provided, advance to next question
            if next_question:
                next_idx = curr_idx + 1
                session["current_question_index"] = next_idx
                session["history"].append({
                    "question_number": next_idx,
                    "question": next_question,
                    "student_answer": None,
                    "score": None,
                    "feedback": None,
                    "timestamp": now_iso,
                })

            return dict(session)

    def complete_session(
        self,
        session_id: str,
        report: Dict[str, Any]
    ) -> Dict[str, Any]:
        with self._lock:
            if session_id not in self._sessions:
                raise KeyError(f"Session '{session_id}' not found.")
            session = self._sessions[session_id]
            session["is_completed"] = True
            session["report"] = report
            return dict(session)

    def list_sessions(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [dict(s) for s in self._sessions.values()]

    def clear(self):
        """Helper for test suites to reset in-memory state."""
        with self._lock:
            self._sessions.clear()


# Global singleton store instance
session_store = SessionStore()
