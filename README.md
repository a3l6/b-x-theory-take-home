# Exam Study Planner 

## Overview

This project uses Google's Agent Development Kit (ADK) to orchestrate three AI agents that collaborate to create realistic study plans:

1. **ExtractorAgent** - Analyzes uploaded PDF textbooks to extract course structure, chapters, topics, page counts, and complexity levels
2. **SchedulerAgent** - Creates a day-by-day study schedule based on textbook analysis, respecting realistic time constraints
3. **FormatterAgent** - Produces a well-formatted Markdown table with your complete study plan

## Requirements

- Python 3.9+
- Google API Key (free via [AI Studio](https://makersuite.google.com/app/apikey))
- Course textbooks in PDF format

## Installation

### 1. Clone the repository

```bash
cd my_agent
```

### 2. Create and activate virtual environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up API key

Create a `.env` file in the project root:

```bash
echo 'GOOGLE_API_KEY=your_api_key_here' > .env
```

Get your free API key from [Google AI Studio](https://makersuite.google.com/app/apikey).

## Usage

### Running the Agent

Start the interactive web interface:

```bash
adk web --port 8080
```

Then open your browser to: **http://localhost:8080**

### Creating a Study Plan

1. **Upload your textbooks**
   - Click the file upload button in the web interface
   - Select your course PDF textbooks (e.g., Math_135.pdf, STAT_230.pdf)
   - You can upload multiple files for different courses
   - For testing, see notes folder

2. **Request your study plan**
   - Type a message like:
     - "I have 3 midterms in 2 weeks. Create a study plan for me."
     - "Generate a day-by-day study schedule for the uploaded textbooks."
     - "I need to study these courses. Math 135 on Feb 20, STAT 230 on Feb 22."

3. **Review and download**
   - The agent will analyze your textbooks and create a detailed schedule
   - Download the Markdown table output
   - Adjust as needed based on your preferences

### Example Session

```
You: [Upload Math_135.pdf and STAT_230.pdf]

You: "I have midterms for both these courses in 2 weeks. Create a study plan."

Agent: [ExtractorAgent analyzes PDFs]
"I've analyzed your textbooks:
- Math 135: 10 chapters, 234 pages, high complexity
- STAT 230: 6 chapters, 187 pages, medium complexity"

[SchedulerAgent creates timeline]
"I've created a 14-day schedule with balanced daily study..."

[FormatterAgent outputs table]
| Day | Date | Course | Chapter | Task | Hours |
|-----|------|--------|---------|------|-------|
| 1 | 2026-02-09 | Math 135 | Ch 1-2 | Logic & Proofs | 3.5 |
```

## Architecture

### Agent Pipeline

```
User Input + PDF Files
        ↓
   ExtractorAgent
   - Analyzes PDFs
   - Extracts chapters, topics, page counts
   - Assesses complexity
        ↓
   SchedulerAgent
   - Calculates study time per chapter
   - Creates day-by-day schedule
   - Respects constraints (4hr/day max, breaks)
        ↓
   FormatterAgent
   - Formats as Markdown table
   - Adds summary statistics
        ↓
   Final Study Plan (Markdown)
```

### Data Models

**Chapter** - Individual chapter with metadata
```python
{
    "name": "Chapter 3: Mathematical Induction",
    "page_count": 28,
    "topics": ["Base case", "Inductive step", "Strong induction"],
    "estimated_complexity": "high"
}
```

**TopicList** - Complete course structure
```python
{
    "course_name": "Math 135",
    "total_pages": 234,
    "chapters": [Chapter, Chapter, ...],
    "exam_topics": ["Proofs", "Induction", "Sets"]
}
```

**StudyDay** - Single day in schedule
```python
{
    "day": 1,
    "date": "2026-02-09",
    "course": "Math 135",
    "chapter": "Chapter 1-2",
    "task": "Study logic and basic proofs",
    "estimated_hours": 3.5
}
```

**FullPlan** - Complete schedule
```python
{
    "plan": [StudyDay, StudyDay, ...],
    "total_study_days": 12,
    "total_hours": 42.0
}
```

## Scheduling Rules

The SchedulerAgent follows these constraints:

- **Maximum 4 hours per day**
- **At least 1 break day per week**
- **Complexity-based time allocation:**
  - Low complexity: 15-20 min per 10 pages
  - Medium complexity: 25-35 min per 10 pages
  - High complexity: 40-60 min per 10 pages
- **Prioritization:** Complex material scheduled earlier
- **Review sessions:** Built into the schedule

## Testing
### Running Tests

```bash
# All tests
pytest test_agents.py -v

# Specific test category
pytest test_agents.py -k "constraint" -v
```

**Note:** Update your API key in `.env` before running tests.

## Sample Output

```markdown
# Study Schedule

| Day | Date | Course | Chapter | Task | Hours |
|-----|------|--------|---------|------|-------|
| 1 | 2026-02-09 | Math 135 | Ch 1-2 | Introduction to Logic and Proofs | 3.5 |
| 2 | 2026-02-10 | Math 135 | Ch 3 | Mathematical Induction + exercises | 4.0 |
| 3 | 2026-02-11 | Math 135 | Ch 4 | Sets and Functions | 3.0 |
| 4 | 2026-02-12 | STAT 230 | Ch 1-2 | Probability Basics | 3.5 |
| 5 | 2026-02-13 | - | - | Break Day | 0.0 |
| 6 | 2026-02-14 | STAT 230 | Ch 3 | Discrete Random Variables | 4.0 |
```

## Troubleshooting

### Agent not processing PDFs
Ensure you're uploading files through the web interface. See [[Installation]]

## Technical Details

- **Framework:** Google Agent Development Kit (ADK)
- **LLM:** Gemini 2.0 Flash Experimental
- **Language:** Python 3.9+
- **Testing:** pytest, pytest-asyncio
- **Data Validation:** Pydantic

## Contributing

This is a take-home project for b(x) Theory's AI Engineer internship position. The code is provided for educational purposes.


## Contact

For questions about this implementation, please refer to the submission guidelines in the take-home instructions.

---
