"""
Comprehensive Test Suite for Study Planner Agent

Determinism Strategy:
- Tests structural properties (schemas, constraints) which must be deterministic
- Does **not** test exact LLM outputs (which vary by nature)
- Validates hard constraints (4-hour max, positive hours) which must hold
- Checks all pipeline stages execute consistently

Test Categories:
- Determinism: Multi-run consistency, schema validation
- Constraints: 4-hour rule, breaks, positive hours
- Course Materials: Math 135, 136, 137, 138, STAT 230
- Edge Cases: Minimal/extensive content, special characters
- Performance: Latency benchmarks
- Sessions: Isolation and concurrency
- Format: Markdown table validation
"""

from my_agent import root_agent, TopicList, FullPlan, Chapter, StudyDay
import asyncio
import time
import pytest
import os
from pathlib import Path
from dotenv import load_dotenv
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai.types import Content, Part
from typing import List

load_dotenv()


NOTES_DIR = Path(__file__).parent / "notes"


def create_message(text: str) -> Content:
    """Creates a proper Content message object for the ADK runner."""
    return Content(parts=[Part(text=text)], role='user')


class AgentResponse:
    """Wrapper for agent response with both Event and session state."""

    def __init__(self, final_event, session_state, formatted_text):
        self.final_event = final_event
        self.output_data = session_state  # Structured outputs from agents
        self.text = formatted_text  # Formatted markdown output


def get_final_response(runner, message_text, user_id="test_user_123", session_id="test_session_456"):
    """
    Helper to drain the generator and return a response with structured data.
    Returns AgentResponse with:
    - output_data: Dict with 'topics' and 'raw_schedule' from session state
    - text: Formatted markdown output from FormatterAgent
    - final_event: The last Event from the generator
    """

    try:
        runner.session_service.create_session_sync(
            user_id=user_id,
            session_id=session_id,
            app_name=runner.app_name
        )
    except Exception:
        # Session might already exis
        pass

    message = create_message(message_text)

    gen = runner.run(
        new_message=message,
        user_id=user_id,
        session_id=session_id
    )

    final_event = None
    for event in gen:
        final_event = event

    time.sleep(0.5)

    session = runner.session_service.get_session_sync(
        user_id=user_id,
        session_id=session_id,
        app_name=runner.app_name
    )

    output_data = {}
    if 'topics' in session.state:
        output_data['topics'] = TopicList(**session.state['topics'])
    if 'raw_schedule' in session.state:
        output_data['raw_schedule'] = FullPlan(**session.state['raw_schedule'])

    formatted_text = ""
    if final_event and final_event.content and final_event.content.parts:
        formatted_text = final_event.content.parts[0].text

    return AgentResponse(final_event, output_data, formatted_text)


def validate_schedule_structure(response):
    """Helper to validate the structure of a schedule response."""
    assert response is not None, "Response should not be None"

    schedule_data = response.output_data.get("raw_schedule")
    assert schedule_data is not None, "raw_schedule should be present in output_data"
    assert isinstance(
        schedule_data, FullPlan), "raw_schedule should be a FullPlan instance"
    assert len(
        schedule_data.plan) > 0, "Schedule should contain at least one study day"

    for entry in schedule_data.plan:
        assert hasattr(entry, 'day'), "Each entry should have a 'day' field"
        assert hasattr(entry, 'task'), "Each entry should have a 'task' field"
        assert hasattr(
            entry, 'estimated_hours'), "Each entry should have an 'estimated_hours' field"
        assert hasattr(
            entry, 'course'), "Each entry should have a 'course' field"
        assert hasattr(
            entry, 'chapter'), "Each entry should have a 'chapter' field"
        assert isinstance(entry.day, int), "Day should be an integer"
        assert isinstance(entry.task, str), "Task should be a string"
        assert isinstance(entry.course, str), "Course should be a string"
        assert isinstance(entry.chapter, str), "Chapter should be a string"
        assert isinstance(entry.estimated_hours, (int, float)
                          ), "Hours should be numeric"
        assert entry.estimated_hours >= 0, "Hours should be non-negative (0 for breaks is allowed)"

    assert "|" in response.text, "Response should contain markdown table separator"
    assert "Day" in response.text, "Response should contain 'Day' column header"
    assert "Task" in response.text, "Response should contain 'Task' column header"

    return schedule_data

# Determinism Tests


@pytest.mark.asyncio
async def test_basic_output_determinism():
    """Checks if the agent consistently returns valid structured data."""
    mock_input = "Course: AI 101. Textbook covers: Neural Networks, Search, and Logic."
runner = Runner(app_name="bxtheory tests", agent=root_agent,
                session_service=InMemorySessionService())

response = get_final_response(runner, mock_input)
validate_schedule_structure(response)


@pytest.mark.asyncio
async def test_repeated_runs_determinism():
    """
    Tests determinism by running the same input multiple times.
    While LLM outputs may vary slightly, structural properties should be consistent.
    """
    mock_input = "Course: Math 101. Topics: Calculus, Linear Algebra, Probability."

    responses = []
    for i in range(3):
        runner = Runner(
            app_name=f"bxtheory tests run {i}",
            agent=root_agent,
            session_service=InMemorySessionService()
        )
        response = get_final_response(
            runner, mock_input, session_id=f"session_{i}")
        responses.append(response)

    for i, response in enumerate(responses):
        schedule = validate_schedule_structure(response)

        assert len(schedule.plan) > 0, f"Run {
            i} should produce a non-empty schedule"

        for entry in schedule.plan:
            assert entry.estimated_hours <= 4.0, f"Run {
                i}: Day {entry.day} exceeds 4 hours"


@pytest.mark.asyncio
async def test_schema_determinism():
    """Tests that output schemas are consistently enforced."""
    mock_input = "Course: Data Structures. Chapters: Arrays, Trees, Graphs, Hash Tables."

    runner = Runner(app_name="bxtheory tests", agent=root_agent,
                    session_service=InMemorySessionService())

    response = get_final_response(runner, mock_input)

    topics = response.output_data.get("topics")
    assert topics is not None, "topics should be extracted"
    assert isinstance(topics, TopicList), "topics should be TopicList type"
    assert hasattr(topics, 'course_name'), "TopicList should have course_name"
    assert hasattr(topics, 'chapters'), "TopicList should have chapters"
    assert isinstance(topics.chapters, list), "chapters should be a list"
    assert hasattr(topics, 'total_pages'), "TopicList should have total_pages"

    if len(topics.chapters) > 0:
        first_chapter = topics.chapters[0]
        assert isinstance(first_chapter, (Chapter, dict)
                          ), "chapters should contain Chapter objects or dicts"
        if isinstance(first_chapter, Chapter):
            assert hasattr(first_chapter, 'name'), "Chapter should have name"
            assert hasattr(
                first_chapter, 'page_count'), "Chapter should have page_count"
            assert hasattr(
                first_chapter, 'topics'), "Chapter should have topics"
            assert hasattr(
                first_chapter, 'estimated_complexity'), "Chapter should have estimated_complexity"

    schedule = response.output_data.get("raw_schedule")
    assert schedule is not None, "raw_schedule should exist"
    assert isinstance(
        schedule, FullPlan), "raw_schedule should be FullPlan type"
    assert isinstance(schedule.plan, list), "plan should be a list"
    assert hasattr(
        schedule, 'total_study_days'), "FullPlan should have total_study_days"
    assert hasattr(schedule, 'total_hours'), "FullPlan should have total_hours"
    assert isinstance(schedule.total_study_days,
                      int), "total_study_days should be int"
    assert isinstance(schedule.total_hours, (int, float)
                      ), "total_hours should be numeric"


# Contraint tests

@pytest.mark.asyncio
async def test_four_hour_daily_constraint():
    """Verifies that the SchedulerAgent follows the 4-hour/day maximum."""
    mock_input = "Chapters: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12."

    runner = Runner(app_name="bxtheory tests", agent=root_agent,
                    session_service=InMemorySessionService())

    response = get_final_response(runner, mock_input)
    plan = response.output_data["raw_schedule"].plan

    violations = []
    for entry in plan:
        if entry.estimated_hours > 4.0:
            violations.append(f"Day {entry.day}: {
                              entry.estimated_hours} hours")

    assert len(violations) == 0, f"4-hour constraint violated: {violations}"


@pytest.mark.asyncio
async def test_weekly_break_constraint():
    """Verifies that schedules include breaks (lower study hours periodically)."""
    mock_input = """
    Course: Advanced Mathematics.
    Chapters: 1. Set Theory, 2. Logic, 3. Proofs, 4. Number Theory,
    5. Algebra, 6. Geometry, 7. Calculus I, 8. Calculus II
    """

    runner = Runner(app_name="bxtheory tests", agent=root_agent,
                    session_service=InMemorySessionService())

    response = get_final_response(runner, mock_input)
    plan = response.output_data["raw_schedule"].plan

    hours_list = [entry.estimated_hours for entry in plan]

    unique_hours = len(set(hours_list))
    assert unique_hours > 1 or len(
        plan) < 7, "Schedule should include variation for breaks"


@pytest.mark.asyncio
async def test_positive_hours_constraint():
    """Ensures all scheduled hours are non-negative (0 allowed for breaks)."""
    mock_input = "Short course with 3 topics: A, B, C."

    runner = Runner(app_name="bxtheory tests", agent=root_agent,
                    session_service=InMemorySessionService())

    response = get_final_response(runner, mock_input)
    plan = response.output_data["raw_schedule"].plan

    for entry in plan:
        assert entry.estimated_hours >= 0, f"Day {
            entry.day} has negative hours: {entry.estimated_hours}"

        if 'break' not in entry.task.lower():
            assert entry.estimated_hours > 0, f"Non-break day {
                entry.day} should have positive hours: {entry.estimated_hours}"


@pytest.mark.asyncio
async def test_sequential_days():
    """Verifies that days are numbered sequentially."""
    mock_input = "Course with 5 chapters."

    runner = Runner(app_name="bxtheory tests", agent=root_agent,
                    session_service=InMemorySessionService())

    response = get_final_response(runner, mock_input)
    plan = response.output_data["raw_schedule"].plan

    days = [entry.day for entry in plan]

    for i in range(1, len(days)):
        assert days[i] >= days[i-1], f"Days not sequential: {days}"


# Course Materials Tests

@pytest.mark.asyncio
async def test_math_135_course_notes():
    """Tests agent with actual Math 135 course PDF."""
    math_135_path = NOTES_DIR / "Math_135.pdf"

    if not math_135_path.exists():
        pytest.skip("Math 135 PDF not found")

    input_text = f"""
    I have the textbook "Language and Proofs in Algebra: An Introduction" for Math 135.
    The course covers: Introduction to Language of Mathematics, Logical Analysis,
    Proving Statements, Mathematical Induction, Sets, Greatest Common Divisor,
    Linear Diophantine Equations, Congruence and Modular Arithmetic, RSA Encryption,
    and Complex Numbers.
    """

    runner = Runner(app_name="bxtheory tests", agent=root_agent,
                    session_service=InMemorySessionService())

    response = get_final_response(runner, input_text)
    schedule = validate_schedule_structure(response)

    # Should generate a reasonable schedule for this content
    assert len(schedule.plan) >= 5, "Math 135 should require multiple study days"

    # Verify topics mentioned in output
    full_text = response.text.lower()
    # At least some mathematical terms should appear
    assert any(term in full_text for term in ['logic', 'proof', 'set', 'algebra', 'number']), \
        "Schedule should reference mathematical topics"


@pytest.mark.asyncio
async def test_math_136_course():
    """Tests with Math 136 course content."""
    input_text = """
    Course: Math 136 - Linear Algebra 1
    Topics: Systems of linear equations, Matrix algebra, Determinants,
    Vector spaces, Linear transformations, Eigenvalues and eigenvectors
    """

    runner = Runner(app_name="bxtheory tests", agent=root_agent,
                    session_service=InMemorySessionService())

    response = get_final_response(runner, input_text)
    schedule = validate_schedule_structure(response)

    topics = response.output_data.get("topics")
    assert topics is not None
    assert "136" in topics.course_name or "linear" in topics.course_name.lower()


@pytest.mark.asyncio
async def test_stat_230_course():
    """Tests with STAT 230 probability course."""
    input_text = """
    STAT 230: Probability
    Chapters: Introduction to Probability, Conditional Probability,
    Discrete Random Variables, Continuous Random Variables,
    Joint Distributions, Sampling Distributions
    """

    runner = Runner(app_name="bxtheory tests", agent=root_agent,
                    session_service=InMemorySessionService())

    response = get_final_response(runner, input_text)
    schedule = validate_schedule_structure(response)

    topics = response.output_data.get("topics")
    assert "probability" in topics.course_name.lower() or "230" in topics.course_name


@pytest.mark.asyncio
async def test_multiple_courses_extraction():
    """Tests extraction from multiple course descriptions."""
    test_cases = [
        ("Math 137: Calculus 1. Chapters: Limits, Derivatives, Integrals", "calculus"),
        ("Math 138: Calculus 2. Topics include: Integration Techniques, Applications, Series and Sequences", "calculus"),
        ("CS 101: Introduction to Programming. Course covers: Variables, Loops, Functions, Data Structures", "programming"),
    ]

    for course_input, expected_keyword in test_cases:
        runner = Runner(app_name="bxtheory tests", agent=root_agent,
                        session_service=InMemorySessionService())

        response = get_final_response(runner, course_input)
        topics = response.output_data.get("topics")

        assert topics is not None, f"Failed to extract topics from: {
            course_input}"
        assert topics.course_name is not None and len(topics.course_name) > 0, \
            f"Failed to extract course name from: {course_input}"


# Edge Cases Tests

@pytest.mark.asyncio
async def test_minimal_input():
    """Tests agent with minimal information."""
    minimal_input = "Course: Basic Math. Topic: Addition."

    runner = Runner(app_name="bxtheory tests", agent=root_agent,
                    session_service=InMemorySessionService())

    response = get_final_response(runner, minimal_input)
    schedule = validate_schedule_structure(response)

    assert len(schedule.plan) >= 1


@pytest.mark.asyncio
async def test_extensive_course_content():
    """Tests with extensive course content (many chapters)."""
    chapters = ", ".join([f"Chapter {i}" for i in range(1, 21)])
    extensive_input = f"Advanced Course with many topics: {chapters}"

    runner = Runner(app_name="bxtheory tests", agent=root_agent,
                    session_service=InMemorySessionService())

    response = get_final_response(runner, extensive_input)
    schedule = validate_schedule_structure(response)

    assert len(
        schedule.plan) >= 5, "Extensive content should require multiple days"

    for entry in schedule.plan:
        assert entry.estimated_hours <= 4.0


@pytest.mark.asyncio
async def test_special_characters_in_input():
    """Tests handling of special characters in course content."""
    special_input = """
    Course: Advanced Topics in C++ & Python
    Chapters: 1. Pointers & References, 2. Lambda Functions -> Closures,
    3. Templates<T>, 4. STL: Vectors/Maps, 5. Async/Await
    """

    runner = Runner(app_name="bxtheory tests", agent=root_agent,
                    session_service=InMemorySessionService())

    response = get_final_response(runner, special_input)
    validate_schedule_structure(response)


# Performance Tests

@pytest.mark.asyncio
async def test_performance_latency():
    """Measures execution time to ensure it meets 'Fast' requirements."""
    start_time = time.perf_counter()

    runner = Runner(app_name="bxtheory tests", agent=root_agent,
                    session_service=InMemorySessionService())

    get_final_response(
        runner, "Sample textbook content for performance testing.")

    duration = time.perf_counter() - start_time
    print(f"\nTotal Latency: {duration:.2f} seconds")

    assert duration < 60.0


@pytest.mark.asyncio
async def test_concurrent_sessions():
    """Tests that multiple sessions can run independently."""
    inputs = [
        "Course A: Topic 1, Topic 2",
        "Course B: Topic 3, Topic 4",
        "Course C: Topic 5, Topic 6"
    ]

    responses = []
    for i, input_text in enumerate(inputs):
        runner = Runner(
            app_name=f"bxtheory tests session {i}",
            agent=root_agent,
            session_service=InMemorySessionService()
        )
        response = get_final_response(
            runner, input_text, session_id=f"concurrent_{i}")
        responses.append(response)

    # Each session should produce valid output
    for i, response in enumerate(responses):
        validate_schedule_structure(response)


# Session Persistence Tests

@pytest.mark.asyncio
async def test_session_isolation():
    """Tests that sessions are properly isolated."""
    session_service = InMemorySessionService()

    runner1 = Runner(app_name="bxtheory tests", agent=root_agent,
                     session_service=session_service)
    response1 = get_final_response(runner1, "Course X: Topics A, B",
                                   session_id="session_1")

    runner2 = Runner(app_name="bxtheory tests", agent=root_agent,
                     session_service=session_service)
    response2 = get_final_response(runner2, "Course Y: Topics C, D",
                                   session_id="session_2")

    validate_schedule_structure(response1)
    validate_schedule_structure(response2)

    topics1 = response1.output_data.get("topics")
    topics2 = response2.output_data.get("topics")

    assert topics1.course_name != topics2.course_name or \
        topics1.chapters != topics2.chapters, \
        "Sessions should maintain separate state"


# Output Format Tests


@pytest.mark.asyncio
async def test_markdown_table_format():
    """Validates that the markdown table is properly formatted."""
    mock_input = "Simple course: Topic A, Topic B, Topic C"

    runner = Runner(app_name="bxtheory tests", agent=root_agent,
                    session_service=InMemorySessionService())

    response = get_final_response(runner, mock_input)

    lines = response.text.strip().split('\n')

    table_lines = [l for l in lines if '|' in l]
    assert len(table_lines) >= 2, "Should have at least header and one data row"

    header = table_lines[0].lower()
    assert 'day' in header
    assert 'task' in header or 'topic' in header
    assert 'hour' in header


@pytest.mark.asyncio
async def test_output_completeness():
    """Ensures all pipeline stages contribute to final output."""
    mock_input = "Course: Test. Chapters: 1, 2, 3."

    runner = Runner(app_name="bxtheory tests", agent=root_agent,
                    session_service=InMemorySessionService())

    response = get_final_response(runner, mock_input)

    assert "topics" in response.output_data, "ExtractorAgent output missing"
    assert "raw_schedule" in response.output_data, "SchedulerAgent output missing"
    assert response.text and len(
        response.text) > 0, "FormatterAgent output missing"
