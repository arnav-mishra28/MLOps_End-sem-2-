from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class DifficultyLevel(str, Enum):
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            for member in cls:
                if member.value.lower() == value.lower():
                    return member
        return None


class VivaStartRequest(BaseModel):
    student_name: str = Field(..., min_length=1, max_length=100, description="Full name of the student")
    subject: str = Field(..., min_length=1, max_length=100, description="Technical subject for the viva")
    difficulty_level: DifficultyLevel = Field(default=DifficultyLevel.MEDIUM, description="Difficulty: Easy, Medium, Hard")

    @field_validator("student_name", "subject")
    @classmethod
    def not_empty_or_whitespace(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Field cannot be empty or only whitespace")
        return trimmed


class VivaStartResponse(BaseModel):
    session_id: str
    student_name: str
    subject: str
    difficulty_level: str
    question_number: int
    total_questions: int
    question: str
    message: str


class VivaAnswerRequest(BaseModel):
    session_id: str = Field(..., min_length=1, description="Unique session ID of the viva")
    answer: str = Field(..., min_length=1, description="Student's answer to the current question")

    @field_validator("session_id", "answer")
    @classmethod
    def not_empty_or_whitespace(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Field cannot be empty or only whitespace")
        return trimmed


class PerformanceReport(BaseModel):
    student_name: str
    subject: str
    difficulty_level: str
    scores: List[float] = Field(..., description="Individual scores for each question out of 10")
    average_marks: float = Field(..., description="Average score across all questions")
    overall_assessment: str = Field(..., description="Comprehensive qualitative assessment of student performance")
    areas_for_improvement: List[str] = Field(..., description="Specific areas and topics recommended for improvement")


class VivaAnswerResponse(BaseModel):
    session_id: str
    question_number: int
    score: float
    feedback: str
    is_completed: bool
    next_question: Optional[str] = None
    report: Optional[PerformanceReport] = None


class QuestionAnswerRound(BaseModel):
    question_number: int
    question: str
    student_answer: Optional[str] = None
    score: Optional[float] = None
    feedback: Optional[str] = None
    timestamp: Optional[str] = None


class VivaSessionDetail(BaseModel):
    session_id: str
    student_name: str
    subject: str
    difficulty_level: str
    created_at: str
    current_question_index: int
    is_completed: bool
    history: List[QuestionAnswerRound]
    report: Optional[PerformanceReport] = None
