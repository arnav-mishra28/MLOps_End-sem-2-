from fastapi import APIRouter, HTTPException, status
from typing import List, Dict, Any
from app.config import settings
from app.models.schemas import (
    VivaStartRequest,
    VivaStartResponse,
    VivaAnswerRequest,
    VivaAnswerResponse,
    VivaSessionDetail,
    PerformanceReport,
)
from app.services.session_store import session_store
from app.services.llm_service import llm_service

router = APIRouter(prefix="/api/viva", tags=["Viva Interview System"])


@router.post(
    "/start",
    response_model=VivaStartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new Viva Examination Session",
    description="Accepts student details, initializes a unique viva session, and generates Question 1 using LLM."
)
def start_viva(payload: VivaStartRequest):
    # Generate the first technical question
    first_question = llm_service.generate_first_question(
        student_name=payload.student_name,
        subject=payload.subject,
        difficulty=payload.difficulty_level.value
    )

    # Persist session in store
    session_data = session_store.create_session(
        student_name=payload.student_name,
        subject=payload.subject,
        difficulty_level=payload.difficulty_level.value,
        first_question=first_question
    )

    return VivaStartResponse(
        session_id=session_data["session_id"],
        student_name=session_data["student_name"],
        subject=session_data["subject"],
        difficulty_level=session_data["difficulty_level"],
        question_number=1,
        total_questions=settings.TOTAL_QUESTIONS,
        question=first_question,
        message=f"Welcome {payload.student_name}! Your {payload.difficulty_level.value}-level viva on '{payload.subject}' has started. Please answer Question 1."
    )


@router.post(
    "/submit-answer",
    response_model=VivaAnswerResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit answer for evaluation and get feedback / next question",
    description="Evaluates answer with score (out of 10) and feedback. Returns next question or final performance report at Question 3."
)
def submit_answer(payload: VivaAnswerRequest):
    session = session_store.get_session(payload.session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Viva session with ID '{payload.session_id}' does not exist."
        )

    if session["is_completed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This viva examination session has already been completed. No further answers can be submitted."
        )

    curr_q_index = session["current_question_index"]
    
    # Locate the active question in history
    active_round = next((r for r in session["history"] if r["question_number"] == curr_q_index), None)
    if not active_round:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Corrupted session state: Question {curr_q_index} not found in history."
        )

    current_question_text = active_round["question"]

    # Evaluate answer and generate next question (or None if Q3)
    score, feedback, next_question = llm_service.evaluate_answer_and_generate_next(
        student_name=session["student_name"],
        subject=session["subject"],
        difficulty=session["difficulty_level"],
        current_question_num=curr_q_index,
        current_question=current_question_text,
        student_answer=payload.answer,
        conversation_history=session["history"]
    )

    # Record evaluation and potentially next question in store
    updated_session = session_store.record_answer_and_eval(
        session_id=payload.session_id,
        answer=payload.answer,
        score=score,
        feedback=feedback,
        next_question=next_question
    )

    # Check if exactly 3 questions have been completed
    if curr_q_index >= settings.TOTAL_QUESTIONS:
        # Generate comprehensive final performance report
        report_data = llm_service.generate_performance_report(
            student_name=session["student_name"],
            subject=session["subject"],
            difficulty=session["difficulty_level"],
            history=updated_session["history"]
        )

        # Mark session complete
        session_store.complete_session(payload.session_id, report_data)

        perf_report = PerformanceReport(**report_data)
        return VivaAnswerResponse(
            session_id=payload.session_id,
            question_number=curr_q_index,
            score=score,
            feedback=feedback,
            is_completed=True,
            next_question=None,
            report=perf_report
        )

    return VivaAnswerResponse(
        session_id=payload.session_id,
        question_number=curr_q_index,
        score=score,
        feedback=feedback,
        is_completed=False,
        next_question=next_question,
        report=None
    )


@router.get(
    "/session/{session_id}",
    response_model=VivaSessionDetail,
    status_code=status.HTTP_200_OK,
    summary="Retrieve session history and progress",
    description="Returns full conversation history, scores, current question, and final performance report if completed."
)
def get_session_detail(session_id: str):
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Viva session with ID '{session_id}' not found."
        )
    return session


@router.get(
    "/sessions",
    response_model=List[VivaSessionDetail],
    status_code=status.HTTP_200_OK,
    summary="List all viva sessions",
    description="Returns all registered viva sessions."
)
def list_all_sessions():
    return session_store.list_sessions()
