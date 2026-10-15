"""Automated tests for ConversationService and session state management.

Validates:
- Multi-turn conversation persistence within the same session.
- Strict isolation between separate session IDs (no data leakage).
- Sliding-window history truncation at MAX_HISTORY_TURNS limit.
- Concurrent turn additions under async tasks.
- Session clearance functionality.
"""

import asyncio
import uuid

import pytest

from app.services.conversation_service import ConversationService


@pytest.mark.asyncio
async def test_session_history_persistence() -> None:
    """Test that conversation history persists across sequential turns for a session."""
    service = ConversationService(max_history_turns=5)
    session_id = str(uuid.uuid4())

    # Initial state should be empty
    initial_history = await service.get_history(session_id)
    assert len(initial_history) == 0

    # Add turn 1
    await service.add_turn(session_id, "Hello, who are you?", "I am your AI assistant.")
    history_turn1 = await service.get_history(session_id)
    assert len(history_turn1) == 2
    assert history_turn1[0].content == "Hello, who are you?"
    assert history_turn1[1].content == "I am your AI assistant."

    # Add turn 2
    await service.add_turn(session_id, "What can you do?", "I can answer questions.")
    history_turn2 = await service.get_history(session_id)
    assert len(history_turn2) == 4
    assert history_turn2[2].content == "What can you do?"
    assert history_turn2[3].content == "I can answer questions."


@pytest.mark.asyncio
async def test_session_isolation() -> None:
    """Test that two different session IDs maintain completely isolated histories."""
    service = ConversationService(max_history_turns=5)
    session_a = str(uuid.uuid4())
    session_b = str(uuid.uuid4())

    # Add turn to session A
    await service.add_turn(session_a, "Question for Session A", "Answer for Session A")

    # Add turn to session B
    await service.add_turn(session_b, "Question for Session B", "Answer for Session B")

    history_a = await service.get_history(session_a)
    history_b = await service.get_history(session_b)

    assert len(history_a) == 2
    assert history_a[0].content == "Question for Session A"

    assert len(history_b) == 2
    assert history_b[0].content == "Question for Session B"

    # Cross-verify no overlap
    assert all("Session B" not in msg.content for msg in history_a)
    assert all("Session A" not in msg.content for msg in history_b)


@pytest.mark.asyncio
async def test_history_truncation_at_limit() -> None:
    """Test that history is trimmed to max_history_turns (sliding window)."""
    max_turns = 3
    service = ConversationService(max_history_turns=max_turns)
    session_id = str(uuid.uuid4())

    # Add 5 sequential turns (exceeding limit of 3)
    for i in range(1, 6):
        await service.add_turn(session_id, f"Question {i}", f"Answer {i}")

    history = await service.get_history(session_id)

    # 3 turns = 6 messages (3 Human + 3 AI)
    assert len(history) == max_turns * 2

    # Should retain the most recent turns (3, 4, 5) and drop (1, 2)
    assert history[0].content == "Question 3"
    assert history[1].content == "Answer 3"
    assert history[2].content == "Question 4"
    assert history[3].content == "Answer 4"
    assert history[4].content == "Question 5"
    assert history[5].content == "Answer 5"


@pytest.mark.asyncio
async def test_clear_session() -> None:
    """Test clearing session history resets state."""
    service = ConversationService(max_history_turns=5)
    session_id = str(uuid.uuid4())

    await service.add_turn(session_id, "User Q", "AI A")
    assert await service.get_turn_count(session_id) == 1

    cleared = await service.clear_session(session_id)
    assert cleared is True
    assert len(await service.get_history(session_id)) == 0
    assert await service.get_turn_count(session_id) == 0

    # Clearing again returns False
    assert await service.clear_session(session_id) == False


@pytest.mark.asyncio
async def test_concurrent_turns_safe_execution() -> None:
    """Test that concurrent turn additions to distinct sessions execute safely."""
    service = ConversationService(max_history_turns=10)

    async def worker(index: int) -> None:
        sid = f"00000000-0000-0000-0000-{index:012d}"
        for turn in range(3):
            await service.add_turn(sid, f"Q{turn} from worker {index}", f"A{turn}")

    # Launch 10 concurrent worker tasks
    tasks = [asyncio.create_task(worker(i)) for i in range(10)]
    await asyncio.gather(*tasks)

    assert await service.get_active_session_count() == 10
    for i in range(10):
        sid = f"00000000-0000-0000-0000-{i:012d}"
        history = await service.get_history(sid)
        assert len(history) == 6  # 3 turns * 2 messages
