"""
Instruction templates and prompt constants for the Exam Study Planner agents.

This module contains reusable prompt templates and configuration constants
that can be used to customize agent behavior.
"""

TIME_PER_10_PAGES = {
    "low": 17.5,      # minutes (15-20 range)
    "medium": 30.0,   # minutes (25-35 range)
    "high": 50.0,     # minutes (40-60 range)
}

MAX_DAILY_HOURS = 4.0
MIN_SESSION_HOURS = 0.5
BREAK_DAYS_PER_WEEK = 1

COMPLEXITY_INDICATORS = {
    "high": [
        "Heavy mathematical notation",
        "Abstract theoretical concepts",
        "Dense technical content",
        "Requires extensive prerequisite knowledge",
        "Many proofs or derivations"
    ],
    "medium": [
        "Moderate technical content",
        "Mix of theory and application",
        "Some mathematical notation",
        "Standard college-level difficulty"
    ],
    "low": [
        "Primarily descriptive content",
        "Concrete examples and applications",
        "Minimal prerequisites",
        "Introductory material"
    ]
}

EXTRACTOR_INSTRUCTION_CONCISE = """Analyze uploaded PDF textbooks and extract:
1. Course name
2. Chapter structure (titles, page counts)
3. Key topics per chapter
4. Complexity assessment (low/medium/high)

Base complexity on: math density, abstraction level, prerequisite requirements.
If no PDFs uploaded, extract from text descriptions with reasonable estimates."""

SCHEDULER_INSTRUCTION_FLEXIBLE = """Create a study schedule using {topics}.

Time allocation: 15-20 min/10 pages (low), 25-35 min/10 pages (medium), 40-60 min/10 pages (high).
Max 4 hours/day. Include 1+ break days per week.
Prioritize complex material early. Include review sessions.
Output realistic day-by-day plan."""

FORMATTER_INSTRUCTION_CSV = """Convert {raw_schedule} into CSV format.

Format:
Day,Date,Course,Chapter,Task,Hours
1,2026-02-09,Math 135,Chapter 1-2,Study logic and proofs,3.5
2,2026-02-10,Math 135,Chapter 3,Mathematical induction,4.0

Include summary statistics as comments at the end."""

EXAMPLE_USER_PROMPTS = [
    "I have 3 midterms in 2 weeks. Create a study plan.",
    "Generate a day-by-day schedule for these textbooks. Math 135 exam is Feb 20, STAT 230 is Feb 22.",
    "I need to study these courses. Schedule 3 hours per day maximum.",
    "Create a study plan with extra review time for the harder chapters.",
]

VALIDATION_RULES = {
    "max_hours_per_day": 4.0,
    "min_hours_per_session": 0.5,
    "max_hours_per_session": 4.0,
    "min_breaks_per_week": 1,
    "sequential_day_numbers": True,
    "positive_hours": True,
}

RECOMMENDED_MODELS = [
    "gemini-2.0-flash-exp",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
]

ERROR_MESSAGES = {
    "no_files": "Please upload your course textbook PDF files to begin analysis.",
    "invalid_pdf": "Unable to read PDF file. Please ensure the file is not corrupted.",
    "no_chapters": "Could not extract chapter structure from textbook. Please describe your course content.",
    "timeline_too_short": "The timeline is too aggressive. Consider extending your study period or reducing scope.",
    "constraint_violation": "Schedule violates constraints (4-hour max per day). Please report this bug.",
}

SUCCESS_MESSAGES = {
    "extraction_complete": "Successfully analyzed {num_files} textbook(s) covering {num_chapters} chapters.",
    "schedule_created": "Created {num_days}-day study plan with {total_hours} total hours.",
    "ready_to_download": "Your study plan is ready! Download the Markdown table above.",
}
