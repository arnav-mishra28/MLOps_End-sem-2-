let currentSessionId = null;
let currentQuestionNum = 1;
let totalQuestions = 3;
let currentQuestionText = "";
let studentData = {};

function selectSubject(name) {
  document.getElementById("subject").value = name;
}

// Live word count for answer textarea
const answerText = document.getElementById("answer-text");
if (answerText) {
  answerText.addEventListener("input", () => {
    const text = answerText.value.trim();
    const words = text ? text.split(/\s+/).length : 0;
    document.getElementById("ans-word-count").textContent = words;
  });
}

// Handle viva start
document.getElementById("start-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const name = document.getElementById("student-name").value.trim();
  const subject = document.getElementById("subject").value.trim();
  const difficulty = document.getElementById("difficulty").value;

  const errorDiv = document.getElementById("setup-error");
  errorDiv.classList.add("hidden");

  const startBtn = document.getElementById("start-btn");
  const spinner = document.getElementById("start-spinner");
  startBtn.disabled = true;
  spinner.classList.remove("hidden");

  try {
    const res = await fetch("/api/viva/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        student_name: name,
        subject: subject,
        difficulty_level: difficulty,
      }),
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Failed to start viva session");
    }

    currentSessionId = data.session_id;
    currentQuestionNum = data.question_number;
    totalQuestions = data.total_questions || 3;
    currentQuestionText = data.question;
    studentData = { name, subject, difficulty };

    // Update Meta info
    document.getElementById("meta-student-name").textContent = name;
    document.getElementById("meta-subject").textContent = subject;
    const diffBadge = document.getElementById("meta-difficulty-badge");
    diffBadge.textContent = difficulty;
    diffBadge.className = `difficulty-badge diff-${difficulty.toLowerCase()}`;
    document.getElementById("meta-session-id").textContent = currentSessionId.slice(0, 8) + "...";

    // Set first question
    updateQuestionDisplay(currentQuestionNum, currentQuestionText);

    // Switch screen
    document.getElementById("setup-screen").classList.add("hidden");
    document.getElementById("exam-screen").classList.remove("hidden");
    document.getElementById("history-container").innerHTML = "";
    document.getElementById("answer-text").value = "";
    document.getElementById("ans-word-count").textContent = "0";
  } catch (err) {
    errorDiv.textContent = err.message;
    errorDiv.classList.remove("hidden");
  } finally {
    startBtn.disabled = false;
    spinner.classList.add("hidden");
  }
});

function updateQuestionDisplay(qNum, qText) {
  document.getElementById("active-q-badge").textContent = `Question ${qNum} of ${totalQuestions}`;
  document.getElementById("active-question-text").textContent = qText;

  // Update progress bar
  const percent = Math.round((qNum / totalQuestions) * 100);
  document.getElementById("progress-text").textContent = `Question ${qNum} of ${totalQuestions}`;
  document.getElementById("progress-percent").textContent = `${percent}%`;
  document.getElementById("progress-bar-fill").style.width = `${percent}%`;
}

// Handle answer submission
document.getElementById("answer-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const answer = document.getElementById("answer-text").value.trim();
  const errorDiv = document.getElementById("answer-error");
  errorDiv.classList.add("hidden");

  if (!answer) {
    errorDiv.textContent = "Please provide an answer before submitting.";
    errorDiv.classList.remove("hidden");
    return;
  }

  const submitBtn = document.getElementById("submit-answer-btn");
  const spinner = document.getElementById("answer-spinner");
  submitBtn.disabled = true;
  spinner.classList.remove("hidden");

  try {
    const res = await fetch("/api/viva/submit-answer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: currentSessionId,
        answer: answer,
      }),
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Failed to submit answer.");
    }

    // Add evaluated round to history display
    addHistoryItem(currentQuestionNum, currentQuestionText, answer, data.score, data.feedback);

    if (data.is_completed && data.report) {
      // Completed! Show report screen
      showReportScreen(data.report);
    } else {
      // Advance to next question
      currentQuestionNum = data.question_number + 1;
      currentQuestionText = data.next_question;
      updateQuestionDisplay(currentQuestionNum, currentQuestionText);
      document.getElementById("answer-text").value = "";
      document.getElementById("ans-word-count").textContent = "0";
      document.getElementById("answer-text").focus();
    }
  } catch (err) {
    errorDiv.textContent = err.message;
    errorDiv.classList.remove("hidden");
  } finally {
    submitBtn.disabled = false;
    spinner.classList.add("hidden");
  }
});

function addHistoryItem(qNum, qText, answer, score, feedback) {
  const container = document.getElementById("history-container");
  const item = document.createElement("div");
  item.className = "history-item";

  const pillClass = score === 0 ? "score-pill score-zero" : (score < 6 ? "score-pill score-low" : "score-pill");

  item.innerHTML = `
    <div class="history-q"><strong>Q${qNum}:</strong> ${escapeHtml(qText)}</div>
    <div class="history-a"><strong>Your Answer:</strong> ${escapeHtml(answer)}</div>
    <div class="eval-box">
      <span class="${pillClass}">Score: ${score}/10</span>
      <span class="eval-feedback">${escapeHtml(feedback)}</span>
    </div>
  `;
  container.appendChild(item);
}

function showReportScreen(report) {
  document.getElementById("exam-screen").classList.add("hidden");
  document.getElementById("report-screen").classList.remove("hidden");

  document.getElementById("report-student-name").textContent = report.student_name;
  document.getElementById("report-subject").textContent = report.subject;
  document.getElementById("report-difficulty").textContent = report.difficulty_level;

  const scores = report.scores || [];
  document.getElementById("report-q1-score").textContent = scores[0] !== undefined ? `${scores[0]}/10` : "--";
  document.getElementById("report-q2-score").textContent = scores[1] !== undefined ? `${scores[1]}/10` : "--";
  document.getElementById("report-q3-score").textContent = scores[2] !== undefined ? `${scores[2]}/10` : "--";
  document.getElementById("report-avg-score").textContent = `${report.average_marks} / 10`;

  document.getElementById("report-assessment-text").textContent = report.overall_assessment;

  const list = document.getElementById("report-improvements-list");
  list.innerHTML = "";
  (report.areas_for_improvement || []).forEach((area) => {
    const li = document.createElement("li");
    li.textContent = area;
    list.appendChild(li);
  });
}

function resetViva() {
  currentSessionId = null;
  currentQuestionNum = 1;
  currentQuestionText = "";
  document.getElementById("report-screen").classList.add("hidden");
  document.getElementById("exam-screen").classList.add("hidden");
  document.getElementById("setup-screen").classList.remove("hidden");
  document.getElementById("start-form").reset();
  document.getElementById("setup-error").classList.add("hidden");
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
