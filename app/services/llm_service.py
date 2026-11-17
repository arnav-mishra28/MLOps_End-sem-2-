import json
import logging
import re
from typing import List, Dict, Any, Tuple, Optional
from app.config import settings

logger = logging.getLogger("viva_llm_service")

# Curated technical knowledge bank for intelligent offline / fallback mode
SUBJECT_QUESTION_BANK = {
    "python": {
        "Easy": [
            "Explain the difference between mutable and immutable data types in Python, giving examples of each.",
            "How does memory management work in Python, and what role does reference counting play?",
            "What are list comprehensions in Python, and how do they differ from generator expressions in terms of performance?"
        ],
        "Medium": [
            "Explain Python's Global Interpreter Lock (GIL) and its implications on CPU-bound multi-threaded programs.",
            "How do Python decorators work internally, and how would you implement a decorator that accepts custom arguments?",
            "Discuss the method resolution order (MRO) in Python multiple inheritance and how the C3 linearization algorithm resolves it."
        ],
        "Hard": [
            "Explain Python's async/await event loop architecture and compare its coroutine scheduling with OS-level threading.",
            "How does CPython optimize dictionary lookups using hash tables, perturb algorithms, and compact dict memory layouts?",
            "Explain custom metaclasses in Python: when would you use `__new__` versus `__init__` in a metaclass, and how does `__init_subclass__` serve as an alternative?"
        ]
    },
    "machine learning": {
        "Easy": [
            "What is the difference between supervised, unsupervised, and reinforcement learning? Give an example of each.",
            "Explain the bias-variance tradeoff in machine learning and how it affects model generalization.",
            "What is cross-validation, and why is k-fold cross-validation preferred over a simple train-test split?"
        ],
        "Medium": [
            "Explain how the Gradient Descent optimization algorithm updates weights, and compare Batch, Stochastic, and Mini-batch GD.",
            "Describe the mathematical intuition behind Support Vector Machines (SVM) and the kernel trick.",
            "What is the vanishing gradient problem in deep neural networks, and how do modern activation functions (like ReLU) and skip connections mitigate it?"
        ],
        "Hard": [
            "Detail the Multi-Head Self-Attention mechanism in Transformer architectures with its mathematical formulation.",
            "Explain techniques for combating catastrophic forgetting in continual learning or fine-tuning large language models (e.g., LoRA, EWC).",
            "How does Contrastive Representation Learning (such as SimCLR or CLIP) optimize the InfoNCE loss function without labelled classification targets?"
        ]
    },
    "operating systems": {
        "Easy": [
            "What is the difference between a process and a thread, and how are resources shared between them?",
            "Explain the four necessary conditions for a deadlock to occur in an operating system.",
            "What is virtual memory, and what happens during a page fault?"
        ],
        "Medium": [
            "Compare preemptive and non-preemptive CPU scheduling algorithms, focusing on Round Robin and Multi-Level Feedback Queues.",
            "Explain the difference between mutexes, semaphores, and spinlocks, including busy-waiting behavior.",
            "How does the Linux Virtual File System (VFS) abstract different physical file systems using inodes and dentries?"
        ],
        "Hard": [
            "Describe the page table translation process with TLBs (Translation Lookaside Buffers) and multi-level or inverted page tables.",
            "Explain how the Linux CFS (Completely Fair Scheduler) utilizes red-black trees and virtual runtime (`vruntime`) for scheduling.",
            "Discuss cache coherence protocols like MESI/MOESI in multi-core systems and their interaction with memory consistency models."
        ]
    },
    "mlops": {
        "Easy": [
            "What is MLOps, and how does it bridge the gap between Machine Learning engineering and DevOps?",
            "What is the role of data version control (e.g., DVC), and why isn't standard Git sufficient for datasets?",
            "Explain the concept of concept drift and data drift in production ML models."
        ],
        "Medium": [
            "How would you design a CI/CD pipeline for machine learning that includes automated model training, validation gates, and artifact registry pushing?",
            "Explain model registry workflows (e.g., MLflow, Weights & Biases) and the transition from candidate to production stages.",
            "Describe techniques for serving ML models with low latency, comparing REST vs. gRPC, and batch inference vs. real-time streaming inference."
        ],
        "Hard": [
            "Design an end-to-end continuous training (CT) architecture with automated feature stores, drift detection alerts, shadow/canary deployments, and rollback strategies.",
            "How do you profile, optimize, and deploy large-scale LLMs in production using tensor parallelism, pipeline parallelism, and vLLM/TGI inference engines?",
            "Explain how you ensure reproducibility and governance across heterogeneous distributed GPU clusters using Kubernetes (Kubeflow), container runtimes, and Ray."
        ]
    }
}

STOPWORDS = {
    'what', 'is', 'the', 'difference', 'between', 'how', 'does', 'explain', 'why',
    'and', 'or', 'in', 'to', 'for', 'a', 'an', 'of', 'with', 'at', 'by', 'from',
    'this', 'that', 'these', 'those', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'giving', 'examples', 'each', 'could',
    'would', 'should', 'can', 'about', 'such', 'into', 'which', 'their', 'there',
    'some', 'when', 'where', 'also', 'just', 'more', 'less', 'very', 'over', 'under'
}

EVASIVE_PATTERNS = [
    r'^(i\s+)?(do\s+not|don\'?t)\s+know',
    r'^no\s+idea',
    r'^(please\s+)?skip',
    r'^pass$',
    r'^idk$',
    r'^dunno$',
    r'^nothing$',
    r'^n/?a$',
    r'^no\s+answer',
    r'^not\s+sure',
    r'^i\s+have\s+no\s+(idea|clue)',
    r'^can\'?t\s+answer',
    r'^cannot\s+answer',
    r'^left\s+blank',
    r'^none$',
    r'^asdf',
    r'^qwerty',
    r'^[a-z]{1,4}$'
]


class LLMService:
    def __init__(self):
        self._gemini_client = None
        self._init_gemini_client()

    def _init_gemini_client(self):
        api_key = settings.GEMINI_API_KEY.strip() if settings.GEMINI_API_KEY else ""
        if api_key:
            try:
                from google import genai
                self._gemini_client = genai.Client(api_key=api_key)
                logger.info("Google GenAI client initialized successfully.")
            except Exception as e:
                logger.warning(f"Failed to initialize Google GenAI client: {e}. Falling back to offline viva examiner.")
                self._gemini_client = None
        else:
            logger.info("No GEMINI_API_KEY provided in .env. Operating in intelligent offline viva mode.")
            self._gemini_client = None

    @property
    def is_live_llm_available(self) -> bool:
        return self._gemini_client is not None

    def _clean_json_response(self, text: str) -> Dict[str, Any]:
        """Extract and parse JSON object from LLM response string."""
        cleaned = re.sub(r"^```json\s*", "", text.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"^```\s*$", "", cleaned.strip(), flags=re.MULTILINE)
        
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        match = re.search(r"(\{[\s\S]*\})", cleaned)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        raise ValueError(f"Could not parse valid JSON from text: {text[:200]}")

    def generate_first_question(self, student_name: str, subject: str, difficulty: str) -> str:
        """Generate the first technical viva question using LLM or offline examiner."""
        if self.is_live_llm_available:
            try:
                prompt = (
                    f"You are an experienced university professor conducting an oral technical viva examination.\n"
                    f"Student Name: {student_name}\n"
                    f"Subject: {subject}\n"
                    f"Difficulty Level: {difficulty}\n"
                    f"Task: Generate the very first technical viva question (Question 1 of 3) for this student.\n"
                    f"Guidelines:\n"
                    f"- The question must be appropriate for {difficulty} level.\n"
                    f"- Focus on core principles, architecture, or conceptual understanding in {subject}.\n"
                    f"- Return ONLY the question text directly without greetings, introductory remarks, or question numbering."
                )
                response = self._gemini_client.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=prompt
                )
                text = response.text.strip()
                if text:
                    return text
            except Exception as e:
                logger.error(f"Live LLM call failed in generate_first_question: {e}. Falling back to offline examiner.")

        return self._mock_first_question(subject, difficulty)

    def evaluate_answer_and_generate_next(
        self,
        student_name: str,
        subject: str,
        difficulty: str,
        current_question_num: int,
        current_question: str,
        student_answer: str,
        conversation_history: List[Dict[str, Any]]
    ) -> Tuple[float, str, Optional[str]]:
        """
        Evaluates the student's answer strictly based on its relevance to the current question.
        If the answer is unrelated, evasive, or off-topic, assigns a score of 0.0 with appropriate feedback.
        """
        is_last_question = (current_question_num >= settings.TOTAL_QUESTIONS)

        if self.is_live_llm_available:
            try:
                history_summary = []
                for h in conversation_history:
                    q_num = h.get("question_number")
                    q_text = h.get("question")
                    ans_text = h.get("student_answer") or "(Not yet answered)"
                    history_summary.append(f"Q{q_num}: {q_text}\nStudent Answer: {ans_text}")
                history_str = "\n\n".join(history_summary)

                next_q_instruction = (
                    "Since this was Question 3 of 3 (the final question), 'next_question' MUST be null."
                    if is_last_question else
                    f"Formulate Question {current_question_num + 1} of 3. The next question should logically follow up or deepen the examination based on the student's previous answers in {subject} at {difficulty} level."
                )

                prompt = (
                    f"You are an expert university examiner conducting an oral technical viva examination.\n"
                    f"Student Name: {student_name}\n"
                    f"Subject: {subject}\n"
                    f"Difficulty Level: {difficulty}\n\n"
                    f"Examination History so far:\n{history_str}\n\n"
                    f"Current Question ({current_question_num} of {settings.TOTAL_QUESTIONS}): {current_question}\n"
                    f"Student's Answer: {student_answer}\n\n"
                    f"STRICT EVALUATION CRITERIA (RELEVANCE FIRST):\n"
                    f"1. MANDATORY RELEVANCE CHECK:\n"
                    f"   - Check if the student's response is directly addressing the technical question asked above.\n"
                    f"   - If the student provided: empty answer, evasive phrases (e.g. 'I don't know', 'skip', 'idk', 'no clue', 'pass'), off-topic text, gibberish, or text completely unrelated to '{current_question}':\n"
                    f"     -> ASSIGN A SCORE OF 0.0 OUT OF 10.\n"
                    f"     -> In 'feedback', explicitly state that the answer is completely unrelated to the question or skipped.\n"
                    f"   - Do NOT give any partial marks for unrelated text, regardless of length.\n"
                    f"2. TECHNICAL MERIT (ONLY IF RELEVANT):\n"
                    f"   - If and only if the answer is relevant, evaluate technical accuracy, conceptual correctness, depth, and clarity.\n"
                    f"   - Assign an objective numerical score between 1.0 and 10.0.\n"
                    f"3. FEEDBACK:\n"
                    f"   - Provide concise, constructive feedback explaining what was correct, incorrect, or missing.\n"
                    f"4. {next_q_instruction}\n\n"
                    f"Respond ONLY with a valid JSON object in this exact schema (no markdown, no extra commentary):\n"
                    f"{{\n"
                    f'  "score": <float between 0.0 and 10.0>,\n'
                    f'  "feedback": "<concise technical feedback>",\n'
                    f'  "next_question": <string next question or null if question {settings.TOTAL_QUESTIONS}>\n'
                    f"}}"
                )

                response = self._gemini_client.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=prompt
                )
                parsed = self._clean_json_response(response.text)
                
                raw_score = float(parsed.get("score", 0.0))
                score = max(0.0, min(10.0, round(raw_score, 1)))
                feedback = str(parsed.get("feedback", "Evaluation completed.")).strip()
                next_q = parsed.get("next_question")
                if is_last_question or not next_q:
                    next_q = None
                else:
                    next_q = str(next_q).strip()

                return score, feedback, next_q
            except Exception as e:
                logger.error(f"Live LLM call failed in evaluate_answer_and_generate_next: {e}. Falling back to offline examiner.")

        return self._mock_evaluate_and_next(
            subject=subject,
            difficulty=difficulty,
            current_question_num=current_question_num,
            current_question=current_question,
            student_answer=student_answer
        )

    def generate_performance_report(
        self,
        student_name: str,
        subject: str,
        difficulty: str,
        history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate final performance report with scores, average marks, assessment, and improvement areas."""
        scores = [float(h["score"]) for h in history if h.get("score") is not None]
        avg_marks = round(sum(scores) / len(scores), 2) if scores else 0.0

        if self.is_live_llm_available:
            try:
                transcript_parts = []
                for h in history:
                    q_num = h.get("question_number")
                    q_txt = h.get("question")
                    ans_txt = h.get("student_answer")
                    sc = h.get("score")
                    fb = h.get("feedback")
                    transcript_parts.append(
                        f"Question {q_num}: {q_txt}\n"
                        f"Student Answer: {ans_txt}\n"
                        f"Score: {sc}/10\n"
                        f"Feedback: {fb}"
                    )
                full_transcript = "\n\n".join(transcript_parts)

                prompt = (
                    f"You are the Chief Academic Examiner for university viva examinations.\n"
                    f"Student Name: {student_name}\n"
                    f"Subject: {subject}\n"
                    f"Difficulty Level: {difficulty}\n"
                    f"Calculated Scores: {scores}\n"
                    f"Calculated Average Marks: {avg_marks}/10\n\n"
                    f"Complete Viva Transcript:\n{full_transcript}\n\n"
                    f"Task: Generate a final performance evaluation report.\n"
                    f"Provide:\n"
                    f"1. 'overall_assessment': A thoughtful, objective summary (3-5 sentences) summarizing the candidate's actual performance, technical depth, or lack of knowledge.\n"
                    f"2. 'areas_for_improvement': A list of 2 to 4 concrete, actionable topics/concepts the student must study.\n\n"
                    f"Respond ONLY with a valid JSON object in this exact schema:\n"
                    f"{{\n"
                    f'  "overall_assessment": "<assessment text>",\n'
                    f'  "areas_for_improvement": ["<area 1>", "<area 2>", "<area 3>"]\n'
                    f"}}"
                )

                response = self._gemini_client.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=prompt
                )
                parsed = self._clean_json_response(response.text)
                overall_assessment = str(parsed.get("overall_assessment", "")).strip()
                areas = parsed.get("areas_for_improvement", [])
                if isinstance(areas, list) and areas:
                    areas = [str(a).strip() for a in areas if str(a).strip()]
                else:
                    areas = [f"Review foundational principles of {subject}", "Practice answering specific technical questions directly"]

                if overall_assessment:
                    return {
                        "student_name": student_name,
                        "subject": subject,
                        "difficulty_level": difficulty,
                        "scores": scores,
                        "average_marks": avg_marks,
                        "overall_assessment": overall_assessment,
                        "areas_for_improvement": areas,
                    }
            except Exception as e:
                logger.error(f"Live LLM call failed in generate_performance_report: {e}. Falling back to offline examiner.")

        return self._mock_performance_report(
            student_name=student_name,
            subject=subject,
            difficulty=difficulty,
            scores=scores,
            avg_marks=avg_marks
        )

    # ------------------ Intelligent Offline / Fallback Mock Engine ------------------

    def check_relevance(self, question: str, subject: str, answer: str) -> Tuple[bool, float, str]:
        """
        Validates if the student's answer is relevant to the question and subject.
        Returns: (is_relevant, score, feedback)
        """
        clean = answer.strip().lower()

        # 1. Evasive / Empty / No-knowledge check
        for pat in EVASIVE_PATTERNS:
            if re.search(pat, clean):
                return False, 0.0, "No technical answer was provided (candidate skipped or indicated lack of knowledge). Score: 0/10."

        # 2. Extract technical keywords from question and subject
        q_words = set(re.findall(r'[a-zA-Z]{3,}', question.lower())) - STOPWORDS
        sub_words = set(re.findall(r'[a-zA-Z]{3,}', subject.lower())) - STOPWORDS
        target_keywords = q_words.union(sub_words)

        ans_words = set(re.findall(r'[a-zA-Z]{3,}', clean)) - STOPWORDS

        if not ans_words:
            return False, 0.0, "The answer contains no substantive content. Score: 0/10."

        # Direct overlap
        overlap = target_keywords.intersection(ans_words)

        # Stem / prefix matching (e.g. mutab -> mutable, mutability; optim -> optimize, optimization)
        stem_overlap = set()
        for kw in target_keywords:
            prefix = kw[:4]
            if any(w.startswith(prefix) for w in ans_words):
                stem_overlap.add(kw)

        effective_matches = overlap.union(stem_overlap)

        # If zero relevant keywords from the question or subject are present in the answer
        if not effective_matches:
            return False, 0.0, "The submitted answer is completely unrelated to the question asked. Score: 0/10."

        # Calculate score based on relevance coverage and explanation depth
        match_count = len(effective_matches)
        word_count = len(clean.split())

        if match_count >= 3 and word_count >= 30:
            score = 9.2
            fb = "Outstanding, highly detailed response directly answering the question with strong technical accuracy."
        elif match_count >= 2 and word_count >= 15:
            score = 8.0
            fb = "Solid explanation addressing the core concepts of the question accurately."
        elif match_count >= 1 and word_count >= 8:
            score = 6.5
            fb = "Partially answered the question, but could elaborate further with more depth and technical specifics."
        else:
            score = 4.0
            fb = "Mentioned relevant terms, but the answer lacks sufficient explanation and depth."

        return True, score, fb

    def _mock_first_question(self, subject: str, difficulty: str) -> str:
        key = subject.strip().lower()
        diff = difficulty.capitalize() if difficulty.capitalize() in ("Easy", "Medium", "Hard") else "Medium"
        for sub_key in SUBJECT_QUESTION_BANK:
            if sub_key in key or key in sub_key:
                return SUBJECT_QUESTION_BANK[sub_key][diff][0]
        
        return f"To start your viva on {subject} ({diff} level), could you define the foundational architecture, primary use cases, and key components of {subject}?"

    def _mock_evaluate_and_next(
        self,
        subject: str,
        difficulty: str,
        current_question_num: int,
        current_question: str,
        student_answer: str
    ) -> Tuple[float, str, Optional[str]]:
        # Evaluate relevance strictly
        is_relevant, score, feedback = self.check_relevance(
            question=current_question,
            subject=subject,
            answer=student_answer
        )

        # Check if next question is needed
        if current_question_num >= settings.TOTAL_QUESTIONS:
            return score, feedback, None

        next_q_num = current_question_num + 1
        key = subject.strip().lower()
        diff = difficulty.capitalize() if difficulty.capitalize() in ("Easy", "Medium", "Hard") else "Medium"
        
        next_question = None
        for sub_key in SUBJECT_QUESTION_BANK:
            if sub_key in key or key in sub_key:
                questions = SUBJECT_QUESTION_BANK[sub_key][diff]
                if next_q_num - 1 < len(questions):
                    next_question = questions[next_q_num - 1]
                break

        if not next_question:
            if next_q_num == 2:
                next_question = f"Building on your previous response about {subject}, how do error handling, scalability, and performance bottlenecks manifest in this context?"
            else:
                next_question = f"In an enterprise production deployment of {subject}, what best practices and design trade-offs would you implement to ensure resilience and maintainability?"

        return score, feedback, next_question

    def _mock_performance_report(
        self,
        student_name: str,
        subject: str,
        difficulty: str,
        scores: List[float],
        avg_marks: float
    ) -> Dict[str, Any]:
        if avg_marks >= 8.5:
            assessment = (
                f"{student_name} demonstrated exceptional technical proficiency and articulate communication during the viva in {subject} at {difficulty} level. "
                f"The answers exhibited deep conceptual clarity, accurate terminology, and strong systematic problem-solving aptitude."
            )
            improvements = [
                f"Explore cutting-edge industry standards and recent RFCs/benchmarks in {subject}",
                "Delve into advanced low-level internal optimizations and profiling techniques"
            ]
        elif avg_marks >= 6.0:
            assessment = (
                f"{student_name} showcased a solid grasp of core {subject} principles at {difficulty} level. "
                f"Concepts were clearly articulated with sound understanding, though deeper elaboration on edge cases and design trade-offs will enhance mastery."
            )
            improvements = [
                f"Strengthen understanding of underlying operational trade-offs and edge-case handling in {subject}",
                "Practice elaborating on real-world system architecture diagrams and production failure modes"
            ]
        elif avg_marks > 0.0:
            assessment = (
                f"{student_name} demonstrated foundational awareness in {subject}, but answers lacked sufficient technical depth and specificity. "
                f"Reviewing core theoretical frameworks and hands-on implementations will significantly build viva confidence and knowledge retention."
            )
            improvements = [
                f"Revisit fundamental definitions, core algorithms, and foundational mechanics of {subject}",
                "Conduct hands-on coding and lab exercises to reinforce practical conceptual linkages",
                "Practice structured answers (Definition -> Internal Mechanism -> Real-world Trade-offs)"
            ]
        else:
            assessment = (
                f"{student_name} did not successfully answer the examination questions or provided unrelated responses during the viva in {subject} at {difficulty} level. "
                f"A comprehensive review of the foundational syllabus and dedicated practice is required before retaking the examination."
            )
            improvements = [
                f"Study the core syllabus and fundamental concepts of {subject} thoroughly",
                "Focus on directly answering the technical questions asked during the examination",
                "Practice answering technical viva questions without skipping"
            ]

        return {
            "student_name": student_name,
            "subject": subject,
            "difficulty_level": difficulty,
            "scores": scores,
            "average_marks": avg_marks,
            "overall_assessment": assessment,
            "areas_for_improvement": improvements,
        }


# Singleton LLM service instance
llm_service = LLMService()
