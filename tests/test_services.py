import pytest
from app.services.session_store import SessionStore
from app.services.llm_service import LLMService


def test_session_store_lifecycle():
    store = SessionStore()
    
    # 1. Create session
    session = store.create_session(
        student_name="Candidate One",
        subject="MLOps",
        difficulty_level="Medium",
        first_question="What is model drift?"
    )
    s_id = session["session_id"]
    assert session["current_question_index"] == 1
    assert session["is_completed"] is False
    assert len(session["history"]) == 1

    # 2. Get session
    retrieved = store.get_session(s_id)
    assert retrieved is not None
    assert retrieved["student_name"] == "Candidate One"

    # 3. Record answer & next question
    updated = store.record_answer_and_eval(
        session_id=s_id,
        answer="Model drift is the decay in model accuracy over time.",
        score=8.5,
        feedback="Accurate definition.",
        next_question="How do you monitor model drift?"
    )
    assert updated["current_question_index"] == 2
    assert len(updated["scores"]) == 1
    assert updated["scores"][0] == 8.5
    assert len(updated["history"]) == 2

    # 4. Complete session
    report_data = {
        "student_name": "Candidate One",
        "subject": "MLOps",
        "difficulty_level": "Medium",
        "scores": [8.5],
        "average_marks": 8.5,
        "overall_assessment": "Good performance.",
        "areas_for_improvement": ["Review drift detection metrics"]
    }
    completed = store.complete_session(s_id, report_data)
    assert completed["is_completed"] is True
    assert completed["report"] == report_data


def test_session_store_non_existent():
    store = SessionStore()
    assert store.get_session("unknown") is None

    with pytest.raises(KeyError):
        store.record_answer_and_eval("unknown", "ans", 7.0, "fb")

    with pytest.raises(KeyError):
        store.complete_session("unknown", {})


def test_llm_service_offline_mode():
    service = LLMService()
    # Force offline mode for deterministic testing of fallback engine
    service._gemini_client = None

    q1 = service.generate_first_question("Student X", "Python", "Easy")
    assert isinstance(q1, str)
    assert len(q1) > 10

    score, feedback, next_q = service.evaluate_answer_and_generate_next(
        student_name="Student X",
        subject="Python",
        difficulty="Easy",
        current_question_num=1,
        current_question=q1,
        student_answer="Mutable objects can be modified after creation like lists, whereas immutable objects cannot be modified like tuples.",
        conversation_history=[]
    )
    assert 0.0 <= score <= 10.0
    assert len(feedback) > 0
    assert next_q is not None

    # At question 3, next_q should be None
    score3, feedback3, next_q3 = service.evaluate_answer_and_generate_next(
        student_name="Student X",
        subject="Python",
        difficulty="Easy",
        current_question_num=3,
        current_question="Q3 text",
        student_answer="Another good answer.",
        conversation_history=[]
    )
    assert next_q3 is None

    report = service.generate_performance_report(
        student_name="Student X",
        subject="Python",
        difficulty="Easy",
        history=[
            {"question_number": 1, "score": 8.0},
            {"question_number": 2, "score": 8.5},
            {"question_number": 3, "score": 9.0},
        ]
    )
    assert report["student_name"] == "Student X"
    assert report["scores"] == [8.0, 8.5, 9.0]
    assert report["average_marks"] == 8.5
    assert len(report["overall_assessment"]) > 0
    assert len(report["areas_for_improvement"]) > 0
