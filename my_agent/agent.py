import asyncio
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import FunctionTool
from google.genai import types
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from time import gmtime, strftime


class Chapter(BaseModel):
    """Represents a chapter from a textbook with metadata for scheduling."""
    name: str = Field(description="Chapter title or number")
    page_count: int = Field(
        description="Estimated number of pages in this chapter")
    topics: List[str] = Field(description="Key topics covered in this chapter")
    estimated_complexity: str = Field(
        description="Complexity level: 'low', 'medium', or 'high'"
    )


class TopicList(BaseModel):
    """Structured extraction of course information from uploaded textbooks."""
    course_name: str = Field(description="Name of the course")
    total_pages: int = Field(
        description="Total number of pages in the textbook")
    chapters: List[Chapter] = Field(
        description="List of chapters with details")
    exam_topics: Optional[List[str]] = Field(
        default=None,
        description="Key topics likely to appear on the exam"
    )


class StudyDay(BaseModel):
    """Represents one day in the study schedule."""
    day: int = Field(description="Day number in the schedule (1, 2, 3, ...)")
    date: Optional[str] = Field(
        default=None,
        description="Actual date (YYYY-MM-DD format) if available"
    )
    course: str = Field(description="Course name")
    chapter: str = Field(description="Chapter or topic to study")
    task: str = Field(description="Specific study task description")
    estimated_hours: float = Field(
        description="Estimated hours to spend (max 4 per day, 0 for break days)"
    )


class FullPlan(BaseModel):
    """Complete study plan spanning multiple days."""
    plan: List[StudyDay] = Field(description="Day-by-day study schedule")
    total_study_days: int = Field(
        description="Total number of study days (excluding breaks)")
    total_hours: float = Field(description="Total estimated study hours")


MODEL = "gemini-3-flash-preview"

# Tool to save markdown file as downloadable artifact
async def save_study_plan(markdown_content: str, tool_context) -> str:
    """Saves the study plan as a downloadable markdown file.

    Args:
        markdown_content: The markdown text to save
        tool_context: The tool context (injected by ADK)

    Returns:
        Confirmation message with filename
    """
    # Create filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"study_plan_{timestamp}.md"

    try:
        # Create artifact with markdown content
        artifact = types.Part.from_bytes(
            data=markdown_content.encode('utf-8'),
            mime_type="text/markdown"
        )

        # Save artifact directly through tool_context
        version = await tool_context.save_artifact(
            filename=filename,
            artifact=artifact,
            custom_metadata={"type": "study_schedule", "format": "markdown"}
        )

        return f"✓ Study plan saved as '{filename}' (version {version}). You can download it from the web interface."

    except Exception as e:
        return f"Error saving file: {str(e)}. However, the study plan is shown above."

save_plan_tool = FunctionTool(save_study_plan)

extractor = LlmAgent(
    name="ExtractorAgent",
    model=MODEL,
    instruction="""You are analyzing uploaded course textbook PDF files to help create a study schedule.

**Your Task:**
1. If PDF files are uploaded, carefully analyze each textbook to extract:
   - Course name and subject area
   - Complete chapter structure (chapter titles/numbers)
   - Estimated page count for each chapter
   - Key topics and concepts within each chapter
   - Overall complexity assessment for each chapter (low/medium/high based on:
     * Density of mathematical equations
     * Number of diagrams and technical content
     * Abstract vs. concrete concepts
     * Prerequisite knowledge required)

2. If no PDFs are uploaded but the user provides course descriptions, extract:
   - Course name
   - Chapter/topic list from the text description
   - Make reasonable estimates for page counts (assume 30-50 pages per chapter)
   - Estimate complexity based on course level and topic names

**Page Count Estimation:**
- Carefully count or estimate pages per chapter from the table of contents
- If exact counts unavailable, estimate based on section density
- Total pages should sum to approximate textbook length

**Output Requirements:**
- Provide structured data about ALL chapters/sections to be covered
- Be thorough - the scheduler needs this information to create a realistic timeline
- If multiple textbooks are uploaded, analyze ALL of them

**Important:**
- If files are uploaded, actually read and analyze their content
- Don't make up information - base everything on the actual documents
- If you cannot determine something, use reasonable defaults""",
    output_key="topics",
    output_schema=TopicList,
)

scheduler = LlmAgent(
    name="SchedulerAgent",
    model=MODEL,
    instruction="""You are creating a realistic, day-by-day study schedule for a student preparing for midterm exams.

**Input Data:**
You will receive {topics} containing:
- Course information with chapters
- Page counts and complexity levels
- Total material to cover

**Scheduling Strategy:**
1. **Time Estimation Rules:**
   - Low complexity: ~15-20 minutes per 10 pages
   - Medium complexity: ~25-35 minutes per 10 pages
   - High complexity: ~40-60 minutes per 10 pages
   - Add buffer time for problem sets and review

2. **Daily Constraints (MUST FOLLOW):**
   - Maximum 4 hours of focused study per day
   - Minimum 0.5 hours per study session (or 0 for break)
   - All estimated_hours must be ≤ 4.0
   - All estimated_hours must be ≥ 0.0

3. **Break Management:**
   - Include at least one break day (0 hours) per week
   - Consider lighter days (1-2 hours) periodically
   - Build in review days near the exam

4. **Task Allocation:**
   - Prioritize complex material earlier in the schedule
   - Group related chapters together
   - Include review sessions for each completed section
   - Leave final 1-2 days for comprehensive review

5. **Day Numbering:**
   - Start with day=1 and increment sequentially
   - Days should represent consecutive calendar days

**Output Requirements:**
- Create a complete day-by-day plan from today until the midterm
- Include specific tasks (e.g., "Study Chapter 3: Linear Transformations, complete exercises")
- Ensure total study time covers all material reasonably
- Balance workload across available days
- Calculate total_study_days (days with study hours > 0) and total_hours

**Example Day:**
Day 3: Study Chapters 2-3 on Proofs and Induction, review exercises (3.5 hours)

**Critical:**
- NEVER exceed 4 hours per day
- ALWAYS include at least one break per week
- Make the plan realistic and achievable""",
    output_key="raw_schedule",
    output_schema=FullPlan
)

formatter = LlmAgent(
    name="FormatterAgent",
    model=MODEL,
    instruction=f"The time is {strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime())}." + """Convert the study schedule {raw_schedule} into a well-formatted Markdown table.

**Your Task:**
1. Create a markdown table with columns: Day | Date | Course | Chapter | Task | Hours
2. Use proper Markdown table syntax with | separators
3. Include a header row with column names and a separator row with dashes
4. After creating the table, call save_study_plan to make it downloadable
5. ALWAYS output the complete markdown table in your final response

**Example Format:**
```markdown
# Study Schedule

| Day | Date | Course | Chapter | Task | Hours |
|-----|------|--------|---------|------|-------|
| 1 | 2026-02-09 | Math 135 | Chapter 1-2 | Introduction to proofs | 3.5 |
| 2 | 2026-02-10 | Math 135 | Chapter 3 | Mathematical induction | 4.0 |
| 3 | 2026-02-11 | - | - | Break day | 0.0 |
```

**Important:**
- First, call save_study_plan with the markdown content
- Then, output the complete markdown table as your response""",
    tools=[save_plan_tool]
)

study_pipeline = SequentialAgent(
    name="ExamPlannerPipeline",
    sub_agents=[extractor, scheduler, formatter]
)


root_agent = study_pipeline
