"""Session History, Sliding-Window Truncation, Summarization, and Token Budgeting (Week 5).

Maintains multi-turn context within strict token budgets. Compresses older turns
into an executive summary when context limits are approached, while preserving
recent turns verbatim.
"""
from __future__ import annotations

import math
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def estimate_token_count(text: str) -> int:
    """Accurate token estimator based on whitespace/subword boundaries.

    Approximately 1 token ~= 0.75 words ~= 4 characters for English text.
    """
    if not text:
        return 0
    words = len(text.split())
    chars = len(text)
    # Average between word-based and character-based token estimates
    est = math.ceil(max(words * 1.33, chars / 4.0))
    return max(1, est)


@dataclass
class ConversationTurn:
    role: str  # "user", "assistant", "system", "summary"
    content: str
    tokens: int = 0
    timestamp: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.tokens:
            self.tokens = estimate_token_count(self.content)
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class SessionState:
    session_id: str
    user_id: str
    turns: List[ConversationTurn] = field(default_factory=list)
    summary: Optional[str] = None
    max_history_tokens: int = 1500
    total_lifetime_tokens: int = 0
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at


class TokenBudgetManager:
    """Manages token budgeting, thresholding, and allocation per request."""

    def __init__(
        self,
        max_prompt_budget: int = 2048,
        max_completion_budget: int = 512,
    ):
        self.max_prompt_budget = max_prompt_budget
        self.max_completion_budget = max_completion_budget

    def evaluate_budget(
        self,
        system_prompt: str,
        history_text: str,
        user_query: str,
        retrieved_context: str = "",
    ) -> Dict[str, Any]:
        """Calculates token breakdown and checks against hard budget limits."""
        sys_tokens = estimate_token_count(system_prompt)
        hist_tokens = estimate_token_count(history_text)
        query_tokens = estimate_token_count(user_query)
        ctx_tokens = estimate_token_count(retrieved_context)

        total_prompt_tokens = sys_tokens + hist_tokens + query_tokens + ctx_tokens
        remaining_budget = max(0, self.max_prompt_budget - total_prompt_tokens)
        is_within_budget = total_prompt_tokens <= self.max_prompt_budget

        return {
            "is_within_budget": is_within_budget,
            "total_prompt_tokens": total_prompt_tokens,
            "system_tokens": sys_tokens,
            "history_tokens": hist_tokens,
            "query_tokens": query_tokens,
            "context_tokens": ctx_tokens,
            "max_prompt_budget": self.max_prompt_budget,
            "remaining_budget": remaining_budget,
            "max_completion_budget": self.max_completion_budget,
        }


class SessionManager:
    """Thread-safe multi-session history manager with sliding window & summarization."""

    def __init__(self, max_history_tokens: int = 1200, recent_turns_to_keep: int = 4):
        self.max_history_tokens = max_history_tokens
        self.recent_turns_to_keep = recent_turns_to_keep
        self._sessions: Dict[str, SessionState] = {}
        self._lock = threading.Lock()

    def get_or_create_session(self, session_id: str, user_id: str = "anonymous") -> SessionState:
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = SessionState(
                    session_id=session_id,
                    user_id=user_id,
                    max_history_tokens=self.max_history_tokens,
                )
            return self._sessions[session_id]

    def add_turn(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ConversationTurn:
        """Appends turn and triggers sliding truncation or summarization if over budget."""
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                session = SessionState(session_id=session_id, user_id="anonymous", max_history_tokens=self.max_history_tokens)
                self._sessions[session_id] = session

            turn = ConversationTurn(role=role, content=content, metadata=metadata or {})
            session.turns.append(turn)
            session.total_lifetime_tokens += turn.tokens
            session.updated_at = datetime.now(timezone.utc).isoformat()

            # Enforce history token constraints
            self._prune_or_summarize_session(session)
            return turn

    def _prune_or_summarize_session(self, session: SessionState) -> None:
        """Compresses older turns when total active turn tokens exceed max_history_tokens."""
        total_tokens = sum(t.tokens for t in session.turns)
        if total_tokens <= session.max_history_tokens or len(session.turns) <= self.recent_turns_to_keep:
            return

        # Split turns: older turns to summarize vs recent turns to preserve verbatim
        older_turns = session.turns[:-self.recent_turns_to_keep]
        recent_turns = session.turns[-self.recent_turns_to_keep:]

        # Create structured executive summary of older turns
        summarized_points = []
        for t in older_turns:
            preview = t.content[:80].replace("\n", " ").strip()
            summarized_points.append(f"{t.role.upper()}: {preview}...")

        summary_text = (
            f"[Previous Context Summary: {len(older_turns)} earlier turns condensed - "
            f"{'; '.join(summarized_points[:3])}]"
        )
        session.summary = summary_text
        session.turns = recent_turns

    def get_context_for_prompt(self, session_id: str) -> str:
        """Builds formatted history string containing optional summary + recent turns."""
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return ""

            parts = []
            if session.summary:
                parts.append(session.summary)

            for t in session.turns:
                parts.append(f"{t.role.capitalize()}: {t.content}")

            return "\n\n".join(parts)

    def clear_session(self, session_id: str) -> bool:
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False


# Singleton instance
_global_session_manager: Optional[SessionManager] = None

def get_session_manager() -> SessionManager:
    global _global_session_manager
    if _global_session_manager is None:
        _global_session_manager = SessionManager()
    return _global_session_manager

