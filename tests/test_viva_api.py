import pytest
from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    """Test system health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "app_name" in data
    assert "llm_mode" in data
    assert data["total_questions_per_viva"] == 3


def test_root_serves_html(client: TestClient):
    """Test that GET / returns the HTML user interface."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Autonomous Technical Viva System" in response.text


def test_start_viva_success(client: TestClient, mock_llm):
    """Test starting a viva session with valid parameters."""
    payload = {
        "student_name": "Arnav Mishra",
        "subject": "Machine Learning",
        "difficulty_level": "Medium"
    }
    response = client.post("/api/viva/start", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert "session_id" in data
    assert len(data["session_id"]) > 0
    assert data["student_name"] == "Arnav Mishra"
    assert data["subject"] == "Machine Learning"
    assert data["difficulty_level"] == "Medium"
    assert data["question_number"] == 1
    assert data["total_questions"] == 3
    assert data["question"] == "Explain the difference between supervised and unsupervised learning."

    # Verify mock LLM was called
    mock_llm.generate_first_question.assert_called_once_with(
        student_name="Arnav Mishra",
        subject="Machine Learning",
        difficulty="Medium"
    )


def test_start_viva_invalid_input_empty_name(client: TestClient):
    """Test validation failure when student name is empty or missing."""
    payload = {
        "student_name": "   ",
        "subject": "Operating Systems",
        "difficulty_level": "Easy"
    }
    response = client.post("/api/viva/start", json=payload)
    assert response.status_code == 422
    errors = response.json().get("detail", [])
    assert any("student_name" in str(err) for err in errors)


def test_start_viva_invalid_input_empty_subject(client: TestClient):
    """Test validation failure when subject is empty."""
    payload = {
        "student_name": "John Doe",
        "subject": "",
        "difficulty_level": "Hard"
    }
    response = client.post("/api/viva/start", json=payload)
    assert response.status_code == 422


def test_start_viva_invalid_difficulty(client: TestClient):
    """Test validation failure with unsupported difficulty level."""
    payload = {
        "student_name": "Alice Smith",
        "subject": "Python",
        "difficulty_level": "SuperHard"
    }
    response = client.post("/api/viva/start", json=payload)
    assert response.status_code == 422


def test_submit_answer_invalid_session_id(client: TestClient):
    """Test submitting an answer for a non-existent session ID."""
    payload = {
        "session_id": "non-existent-uuid-1234",
        "answer": "This is an answer to a question."
    }
    response = client.post("/api/viva/submit-answer", json=payload)
    assert response.status_code == 404
    assert "does not exist" in response.json()["detail"]


def test_submit_answer_empty_answer(client: TestClient):
    """Test submitting an empty or whitespace answer string."""
    payload = {
        "session_id": "some-session-id",
        "answer": "   "
    }
    response = client.post("/api/viva/submit-answer", json=payload)
    assert response.status_code == 422


def test_full_viva_lifecycle_exactly_three_questions(client: TestClient, mock_llm):
    """
    Test complete viva workflow:
    1. Start viva (Question 1)
    2. Submit Answer 1 -> Evaluation 1 + Question 2
    3. Submit Answer 2 -> Evaluation 2 + Question 3
    4. Submit Answer 3 -> Evaluation 3 + Final Performance Report with scores, average marks, assessment, improvement areas.
    """
    # 1. Start Session
    start_res = client.post("/api/viva/start", json={
        "student_name": "Test Student",
        "subject": "Machine Learning",
        "difficulty_level": "Medium"
    })
    assert start_res.status_code == 201
    session_id = start_res.json()["session_id"]
    assert start_res.json()["question_number"] == 1

    # 2. Submit Question 1 Answer
    ans1_res = client.post("/api/viva/submit-answer", json={
        "session_id": session_id,
        "answer": "Supervised learning uses labelled data whereas unsupervised learning finds patterns in unlabelled data."
    })
    assert ans1_res.status_code == 200
    ans1_data = ans1_res.json()
    assert ans1_data["question_number"] == 1
    assert ans1_data["score"] == 8.5
    assert ans1_data["is_completed"] is False
    assert ans1_data["next_question"] == "What is cross-validation and why is it used?"
    assert ans1_data["report"] is None

    # 3. Submit Question 2 Answer
    ans2_res = client.post("/api/viva/submit-answer", json={
        "session_id": session_id,
        "answer": "Cross validation splits data into k folds to ensure the model generalizes well and avoids overfitting."
    })
    assert ans2_res.status_code == 200
    ans2_data = ans2_res.json()
    assert ans2_data["question_number"] == 2
    assert ans2_data["score"] == 9.0
    assert ans2_data["is_completed"] is False
    assert ans2_data["next_question"] == "Explain the vanishing gradient problem in deep neural networks."
    assert ans2_data["report"] is None

    # 4. Submit Question 3 (Final Question) Answer
    ans3_res = client.post("/api/viva/submit-answer", json={
        "session_id": session_id,
        "answer": "Vanishing gradient occurs when gradients become exponentially small during backpropagation, solved by ReLU and residual connections."
    })
    assert ans3_res.status_code == 200
    ans3_data = ans3_res.json()
    assert ans3_data["question_number"] == 3
    assert ans3_data["score"] == 9.5
    assert ans3_data["is_completed"] is True
    assert ans3_data["next_question"] is None
    
    # Verify Performance Report is present and matches requirements
    report = ans3_data["report"]
    assert report is not None
    assert report["student_name"] == "Test Student"
    assert report["subject"] == "Machine Learning"
    assert report["difficulty_level"] == "Medium"
    assert report["scores"] == [8.5, 9.0, 9.5]
    assert report["average_marks"] == 9.0
    assert "overall_assessment" in report
    assert len(report["overall_assessment"]) > 0
    assert isinstance(report["areas_for_improvement"], list)
    assert len(report["areas_for_improvement"]) >= 2

    # Verify session status via GET /session/{session_id}
    detail_res = client.get(f"/api/viva/session/{session_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["is_completed"] is True
    assert len(detail["history"]) == 3
    assert detail["report"] is not None


def test_cannot_submit_answer_after_completion(client: TestClient, mock_llm):
    """Test that submitting an answer to an already completed viva is rejected."""
    # Start and complete 3 questions
    start_res = client.post("/api/viva/start", json={
        "student_name": "Test Student",
        "subject": "Machine Learning",
        "difficulty_level": "Medium"
    })
    session_id = start_res.json()["session_id"]

    for i in range(1, 4):
        client.post("/api/viva/submit-answer", json={
            "session_id": session_id,
            "answer": f"Answer for question {i}."
        })

    # Attempt 4th submission
    extra_res = client.post("/api/viva/submit-answer", json={
        "session_id": session_id,
        "answer": "Another answer."
    })
    assert extra_res.status_code == 400
    assert "already been completed" in extra_res.json()["detail"]


def test_get_session_not_found(client: TestClient):
    """Test fetching non-existent session ID returns 404."""
    response = client.get("/api/viva/session/unknown-session-id")
    assert response.status_code == 404


def test_list_all_sessions(client: TestClient, mock_llm):
    """Test listing all viva sessions."""
    client.post("/api/viva/start", json={
        "student_name": "Student A",
        "subject": "MLOps",
        "difficulty_level": "Hard"
    })
    client.post("/api/viva/start", json={
        "student_name": "Student B",
        "subject": "Python",
        "difficulty_level": "Easy"
    })

    response = client.get("/api/viva/sessions")
    assert response.status_code == 200
    sessions = response.json()
    assert len(sessions) == 2
    student_names = [s["student_name"] for s in sessions]
    assert "Student A" in student_names
    assert "Student B" in student_names
