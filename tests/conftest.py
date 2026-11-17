import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.services.session_store import session_store


@pytest.fixture(autouse=True)
def clean_session_store():
    """Resets in-memory session store before each test execution."""
    session_store.clear()
    yield
    session_store.clear()


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


@pytest.fixture
def mock_llm():
    """
    Mocks the LLM service to guarantee fast, deterministic, offline execution
    without incurring API calls or requiring network keys.
    """
    with patch("app.routers.viva.llm_service") as mock_service:
        # Default mock implementations
        mock_service.generate_first_question.return_value = (
            "Explain the difference between supervised and unsupervised learning."
        )

        def mock_eval_and_next(student_name, subject, difficulty, current_question_num, current_question, student_answer, conversation_history):
            if current_question_num == 1:
                return 8.5, "Good explanation with accurate core concepts.", "What is cross-validation and why is it used?"
            elif current_question_num == 2:
                return 9.0, "Excellent understanding of model evaluation techniques.", "Explain the vanishing gradient problem in deep neural networks."
            else:
                return 9.5, "Outstanding breakdown of backpropagation and activation functions.", None

        mock_service.evaluate_answer_and_generate_next.side_effect = mock_eval_and_next

        mock_service.generate_performance_report.return_value = {
            "student_name": "Test Student",
            "subject": "Machine Learning",
            "difficulty_level": "Medium",
            "scores": [8.5, 9.0, 9.5],
            "average_marks": 9.0,
            "overall_assessment": "The candidate demonstrated excellent theoretical knowledge and clear communication throughout the viva.",
            "areas_for_improvement": [
                "Explore deeper mathematical formulations of optimization algorithms",
                "Review advanced regularization techniques in Transformer models"
            ]
        }

        yield mock_service
