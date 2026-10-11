"""A conservative purchase ledger between full board observations.

The caller verifies observation identity/freshness before creating a batch and
records only confirmed one-star purchases. Counts here are shopping decisions,
never observations of where a unit is or whether an automatic merge occurred.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


def _valid_name(name: Any) -> bool:
    return isinstance(name, str) and bool(name.strip())


def _target_copies(goal: Any) -> int | None:
    return 3 ** (goal - 1) if type(goal) is int and 1 <= goal <= 3 else None


@dataclass
class ShoppingBatch:
    _copies: dict[str, int]
    _remaining_spaces: int
    _pending_names: set[str] = field(default_factory=set)
    _pending_count: int = 0

    @classmethod
    def from_observations(cls, observations: Mapping[str, Sequence[Any]]) -> ShoppingBatch | None:
        """Copy a complete board snapshot, rejecting any unknown identity/star.

        Slot states may be strings or enums exposing ``value``. The caller owns
        evidence validity; this module deliberately has no runtime dependencies.
        Only confirmed EMPTY bench slots contribute purchase space. Confirmed
        LOCKED slots have no character and provide no purchase space.
        """
        areas = ("on_field", "off_field", "in_hand")
        if not isinstance(observations, Mapping) or any(area not in observations for area in areas):
            return None
        copies: dict[str, int] = {}
        spaces = 0
        for area in areas:
            slots = observations[area]
            if not isinstance(slots, Sequence) or isinstance(slots, (str, bytes)):
                return None
            for observation in slots:
                state = getattr(observation, "state", None)
                state = getattr(state, "value", state)
                if isinstance(state, str):
                    state = state.lower()
                if state == "empty":
                    spaces += area == "in_hand"
                    continue
                if state == "locked":
                    continue
                if state != "known":
                    return None
                name = getattr(getattr(observation, "character", None), "name", None)
                count = _target_copies(getattr(observation, "stars", None))
                if not _valid_name(name) or count is None:
                    return None
                copies[name] = copies.get(name, 0) + count
        return cls(copies, spaces)

    @property
    def space_safe(self) -> bool:
        return self._remaining_spaces > 0

    @property
    def pending_names(self) -> set[str]:
        return set(self._pending_names)

    @property
    def pending_count(self) -> int:
        return self._pending_count

    def missing_goals(self, goals: Mapping[str, int]) -> dict[str, int]:
        """Return unmet targets even if safe purchase space has run out."""
        missing = {}
        for name, goal in goals.items():
            count = _target_copies(goal)
            if not _valid_name(name) or count is None:
                raise ValueError("Shopping goals require character names and stars from 1 to 3")
            if self._copies.get(name, 0) < count:
                missing[name] = goal
        return missing

    def can_buy(self, name: str, goal: int) -> bool:
        count = _target_copies(goal)
        return bool(self.space_safe and _valid_name(name) and count is not None
                    and self._copies.get(name, 0) < count)

    def record_purchase(self, name: str) -> None:
        """Record one confirmed one-star transaction, consuming one safe slot.

        Even a purchase expected to merge units consumes a slot. Only a new
        observation can confirm that space was freed and start another batch.
        """
        if not _valid_name(name):
            raise ValueError("A confirmed purchase requires a character name")
        if not self.space_safe:
            raise ValueError("No confirmed bench space remains in this batch")
        self._copies[name] = self._copies.get(name, 0) + 1
        self._remaining_spaces -= 1
        self._pending_names.add(name)
        self._pending_count += 1
