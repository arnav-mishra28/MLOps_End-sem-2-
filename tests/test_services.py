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
    assert score >= 6.0
    assert "Accurately" in feedback or "Solid" in feedback or "detail" in feedback or "core concepts" in feedback
    assert next_q is not None

    # At question 3, next_q should be None
    score3, feedback3, next_q3 = service.evaluate_answer_and_generate_next(
        student_name="Student X",
        subject="Python",
        difficulty="Easy",
        current_question_num=3,
        current_question="What are list comprehensions in Python?",
        student_answer="List comprehensions provide a concise way to create lists using expressions in brackets.",
        conversation_history=[]
    )
    assert next_q3 is None
    assert score3 > 0.0

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


def test_llm_service_relevance_and_evasive_check():
    """Verify that unrelated or evasive answers receive 0.0 marks."""
    service = LLMService()
    service._gemini_client = None

    question = "Explain the difference between mutable and immutable data types in Python."
    subject = "Python"

    # 1. Evasive: "I don't know"
    is_rel, score, fb = service.check_relevance(question, subject, "I do not know")
    assert is_rel is False
    assert score == 0.0
    assert "0/10" in fb

    # 2. Evasive: "skip"
    is_rel, score, fb = service.check_relevance(question, subject, "please skip this question")
    assert is_rel is False
    assert score == 0.0

    # 3. Unrelated / Off-topic
    is_rel, score, fb = service.check_relevance(question, subject, "The quick brown fox jumps over the lazy dog.")
    assert is_rel is False
    assert score == 0.0
    assert "unrelated" in fb.lower()

    # 4. Relevant answer
    is_rel, score, fb = service.check_relevance(
        question, subject,
        "Mutable data types in Python such as lists and dicts can be modified after creation, while immutable types like tuples cannot."
    )
    assert is_rel is True
    assert score >= 7.0


def test_llm_service_zero_score_performance_report():
    """Verify that a candidate who provided unrelated answers receives an appropriate assessment."""
    service = LLMService()
    service._gemini_client = None

    report = service.generate_performance_report(
        student_name="Unprepared Student",
        subject="Python",
        difficulty="Easy",
        history=[
            {"question_number": 1, "score": 0.0},
            {"question_number": 2, "score": 0.0},
            {"question_number": 3, "score": 0.0},
        ]
    )
    assert report["average_marks"] == 0.0
    assert "did not successfully answer" in report["overall_assessment"] or "unrelated" in report["overall_assessment"]
