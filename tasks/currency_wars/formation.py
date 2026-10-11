"""Pure, conservative formation planning; no game or GUI imports.

Callers own observations and must confirm each returned move before replanning.
KNOWN observations are evidence, UNKNOWN slots never become empty by inference.
Trait names and memberships come exclusively from the strategy configuration.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Callable, Mapping, Sequence

FIELD_AREAS = ("on_field", "off_field")
ALL_AREAS = FIELD_AREAS + ("in_hand",)
UNRELIABLE_EVIDENCE = {"pending_drag", "stale", "observation_error", "event_invalidated",
                       "layout_changed", "strategy_changed"}


@dataclass(frozen=True)
class FormationStage:
    name: str
    min_capacity: int
    on_field: tuple[str, ...]
    off_field: tuple[str, ...]
    requires_fielded: tuple[str, ...] = ()
    priority: tuple[str, ...] = ()
    requires_available: tuple[str, ...] = ()
    role_requirements: Mapping[str, "RoleRequirement"] = field(default_factory=dict)
    requires_stars: Mapping[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class RoleProvider:
    name: str
    areas: tuple[str, ...]
    min_stars: int = 1


@dataclass(frozen=True)
class RoleRequirement:
    minimum: int = 1
    candidates: tuple[str, ...] = ()
    interim_candidates: tuple[str, ...] = ()
    on_missing: str = "warn_continue"


@dataclass(frozen=True)
class RoleEvaluation:
    state: str
    minimum: int
    on_missing: str
    reason: str
    field_providers: tuple[str, ...] = ()
    bench_candidates: tuple[str, ...] = ()
    purchase_names: tuple[str, ...] = ()


@dataclass(frozen=True)
class UpgradeGate:
    from_level: int
    fielded: Mapping[str, int] = field(default_factory=dict)
    traits: Mapping[str, int] = field(default_factory=dict)
    prices: Mapping[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class AssignmentCandidate:
    name: str
    rank: int = 0
    min_stars: int = 1


@dataclass(frozen=True)
class AssignmentGroup:
    area: str
    candidates: tuple[AssignmentCandidate, ...]
    replace_from: tuple[str, ...]
    count: int = 1
    star_policy: str = "prefer_not_lower"
    keep_incumbent_on_tie: bool = True
    on_unavailable: str = "keep_current"


@dataclass(frozen=True)
class PositionRule:
    name: str
    area: str
    min_capacity: int = 0
    requires_assignment: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class EffectiveTargets:
    stage: FormationStage | None
    base_stage_name: str = ""
    assignments: Mapping[str, str] = field(default_factory=dict)
    purchase_targets: Mapping[str, int] = field(default_factory=dict)
    reserve_targets: Mapping[str, int] = field(default_factory=dict)
    gaps: tuple[str, ...] = ()
    npc_count: int = 0
    strategy_capacity: int | None = None


@dataclass(frozen=True)
class FormationConfig:
    traits: Mapping[str, frozenset[str]]
    preserve_traits: Mapping[str, int]
    protect_until_fielded: Mapping[str, str]
    stages: tuple[FormationStage, ...]
    upgrade_gate: UpgradeGate | None = None
    roles: Mapping[str, tuple[RoleProvider, ...]] = field(default_factory=dict)
    role_requirements: Mapping[str, RoleRequirement] = field(default_factory=dict)
    assignment_groups: Mapping[str, AssignmentGroup] = field(default_factory=dict)
    position_rules: tuple[PositionRule, ...] = ()
    purchase_targets: Mapping[str, int] = field(default_factory=dict)
    root_positions: Mapping[str, tuple[str, ...]] = field(default_factory=dict)


@dataclass(frozen=True)
class FormationDecision:
    allowed: bool
    reason: str = "allowed"
    before_traits: Mapping[str, int] = field(default_factory=dict)
    after_traits: Mapping[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class FormationMove:
    source_area: str
    source_index: int
    target_area: str
    target_index: int
    reason: str
    before_traits: Mapping[str, int] = field(default_factory=dict)
    after_traits: Mapping[str, int] = field(default_factory=dict)
    source_name: str | None = None
    target_name: str | None = None
    source_stars: int | None = None
    target_stars: int | None = None
    requires_completion: bool = False


def _state(observation: Any) -> str:
    state = getattr(observation, "state", None)
    return getattr(state, "value", state)


def confirmed_field_npc_count(observations: Mapping[str, Sequence[Any]]) -> int:
    """Count reliable NPC occupants per field slot, excluding unavailable slots."""
    count = 0
    for area in FIELD_AREAS:
        for observation in observations.get(area, ()):
            character = getattr(observation, "character", None)
            name = getattr(character, "name", None)
            if (_state(observation) == "known"
                    and getattr(observation, "evidence", "") not in UNRELIABLE_EVIDENCE
                    and not getattr(observation, "stale", False)
                    and getattr(observation, "occupied", None) is not False
                    and getattr(character, "is_npc", False)
                    and isinstance(name, str) and name.strip() and not name.strip().isdecimal()):
                count += 1
    return count


def strategy_population_capacity(observations: Mapping[str, Sequence[Any]],
                                 capacity: int | None, *,
                                 reserved_npc_count: int = 0) -> int | None:
    """Ordinary-character seats used by strategy population thresholds.

    ``capacity`` remains the total population shown by the game. Physical move
    planners must continue using that total, because NPCs also occupy it.
    A previously authenticated NPC reservation can survive missing field evidence.
    """
    if (type(capacity) is not int or capacity < 0
            or type(reserved_npc_count) is not int or reserved_npc_count < 0):
        return None
    return max(0, capacity - max(confirmed_field_npc_count(observations), reserved_npc_count))


def _name(observation: Any) -> str | None:
    if (_state(observation) != "known"
            or getattr(observation, "evidence", "") in UNRELIABLE_EVIDENCE
            or getattr(observation, "stale", False)):
        return None
    character = getattr(observation, "character", None)
    name = getattr(character, "name", None)
    if (not isinstance(name, str) or not name.strip() or name.strip().isdecimal()
            or getattr(character, "is_npc", False)):
        return None
    return name


def _movable(observation: Any) -> bool:
    return _name(observation) is not None and not getattr(observation.character, "is_locked", False)


def _empty(observation: Any) -> bool:
    return (_state(observation) == "empty"
            and getattr(observation, "evidence", "") not in UNRELIABLE_EVIDENCE)


def _counts_towards_population(observation: Any) -> bool:
    """Unknown occupants remain reserved; authenticated locked slots do not.

    An unavailable slot still fails both _empty and _movable, so planners
    cannot use it as a destination or a temporary bench position.
    """
    locked = (_state(observation) == "locked"
              and getattr(observation, "evidence", "") not in UNRELIABLE_EVIDENCE
              and not getattr(observation, "stale", False))
    return not (_empty(observation) or locked)


def _field_names(observations: Mapping[str, Sequence[Any]]) -> set[str]:
    return {name for area in FIELD_AREAS for obs in observations.get(area, ())
            if (name := _name(obs)) is not None}


def _role_maximum_coverage(providers: Sequence[RoleProvider]) -> int:
    """Maximum distinct providers assignable to four front and six back slots."""
    by_name = {provider.name: provider for provider in providers}
    assigned = {}

    def assign(name, visited):
        for area in by_name[name].areas:
            for index in range(4 if area == "on_field" else 6):
                slot = area, index
                if slot in visited:
                    continue
                visited.add(slot)
                previous = assigned.get(slot)
                if previous is None or assign(previous, visited):
                    assigned[slot] = name
                    return True
        return False

    return sum(assign(name, set()) for name in by_name)


def validate_formation_config(strategy: Mapping[str, Any],
                              lookup: Callable[[str], Any | None]) -> FormationConfig | None:
    """Validate optional ``strategy.formation`` atomically and canonicalize names.

    A stage lists unique on/off names, ordered priority, a population capacity
    threshold and optional reliable fielded requirements. Root on/off mappings
    continue to own purchase targets. Omitting formation preserves old behavior.
    """
    raw = strategy.get("formation")
    if raw is None:
        return None
    if not isinstance(raw, Mapping):
        raise ValueError("formation 必须为对象或 null")

    def name(value: Any) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("formation 角色名称必须为非空字符串")
        character = lookup("".join(value.split()))
        if character is None or getattr(character, "is_npc", False) or getattr(character, "is_locked", False):
            raise ValueError(f"formation 未知或不可操作角色：{value}")
        return character.name

    def names(value: Any, label: str) -> tuple[str, ...]:
        if not isinstance(value, (list, tuple)):
            raise ValueError(f"{label} 必须为角色列表")
        result = tuple(name(item) for item in value)
        if len(set(result)) != len(result):
            raise ValueError(f"{label} 不得重复角色或其别名")
        return result

    def integer(value: Any, label: str, minimum: int = 1, maximum: int = 99) -> int:
        if type(value) is not int or not minimum <= value <= maximum:
            raise ValueError(f"{label} 必须为 {minimum} 至 {maximum} 的整数")
        return value

    root_names = {name(n) for area in FIELD_AREAS for n in strategy.get(area, {})}
    role_raw = raw.get("roles", {})
    if not isinstance(role_raw, Mapping):
        raise ValueError("formation.roles 必须为职责到提供者列表的映射")
    roles = {}
    for role, providers in role_raw.items():
        if not isinstance(role, str) or not role.strip() or role != role.strip():
            raise ValueError("formation.roles 职责名称必须为非空字符串")
        if not isinstance(providers, (list, tuple)) or not providers:
            raise ValueError("formation.roles 提供者必须为非空列表")
        parsed, seen = [], set()
        for provider in providers:
            if not isinstance(provider, Mapping):
                raise ValueError("职责提供者必须为对象")
            canonical = name(provider.get("name"))
            if canonical in seen:
                raise ValueError("同一职责提供者不得重复角色或别名")
            seen.add(canonical)
            areas = provider.get("area", list(FIELD_AREAS))
            areas = [areas] if isinstance(areas, str) else areas
            if (not isinstance(areas, (list, tuple)) or not areas
                    or any(area not in FIELD_AREAS for area in areas)
                    or len(set(areas)) != len(areas)):
                raise ValueError("职责 area 只能为非空前后台区域列表")
            parsed.append(RoleProvider(canonical, tuple(areas), integer(
                provider.get("min_stars", 1), "role.min_stars", maximum=3)))
        roles[role] = tuple(parsed)

    def role_requirements(value, inherited=None):
        if not isinstance(value, Mapping):
            raise ValueError("role_requirements 必须为对象")
        result = dict(inherited or {})
        for role, item in value.items():
            if role not in roles or not isinstance(item, Mapping):
                raise ValueError("role_requirements 必须引用已定义职责并提供对象")
            prior = result.get(role)
            interim = names(item.get("interim_candidates",
                prior.interim_candidates if prior else ()), "role.interim_candidates")
            available = tuple(provider.name for provider in roles[role])
            candidates = names(item.get("candidates", prior.candidates if prior else
                tuple(n for n in available if n not in interim)), "role.candidates")
            if set(candidates) & set(interim) or not set(candidates + interim) <= set(available):
                raise ValueError("职责候选必须属于该职责且正式/过渡候选不得重复")
            minimum = integer(item.get("minimum", prior.minimum if prior else 1),
                              "role.minimum", maximum=10)
            if minimum > len(candidates + interim):
                raise ValueError("职责 minimum 不得超过不同候选角色数量")
            selected = set(candidates + interim)
            if minimum > _role_maximum_coverage(
                    tuple(provider for provider in roles[role] if provider.name in selected)):
                raise ValueError("职责 minimum 无法在前台4槽、后台6槽分配满足")
            policy = item.get("on_missing", prior.on_missing if prior else "warn_continue")
            if policy not in ("block", "warn_continue"):
                raise ValueError("职责 on_missing 必须为 block 或 warn_continue")
            result[role] = RoleRequirement(minimum, candidates, interim, policy)
        return result

    global_roles = role_requirements(raw.get("role_requirements", {}))
    role_names = {provider.name for providers in roles.values() for provider in providers}
    group_raw = raw.get("assignment_groups", {})
    if not isinstance(group_raw, Mapping):
        raise ValueError("formation.assignment_groups 必须为对象")
    groups, assigned_names = {}, set()
    for group_name, item in group_raw.items():
        if not isinstance(group_name, str) or not group_name.strip() or group_name != group_name.strip():
            raise ValueError("assignment_groups 名称必须为非空字符串")
        if not isinstance(item, Mapping) or not item.keys() <= {
                "area", "count", "candidates", "replace_from", "star_policy",
                "keep_incumbent_on_tie", "on_unavailable"}:
            raise ValueError("assignment_groups 包含未知配置")
        area = item.get("area")
        if area not in FIELD_AREAS or item.get("count", 1) != 1 or type(item.get("count", 1)) is not int:
            raise ValueError("assignment_groups 目前支持前台或后台一个席位(count=1)")
        candidates_raw = item.get("candidates")
        if not isinstance(candidates_raw, (list, tuple)) or not candidates_raw:
            raise ValueError("assignment_groups.candidates 必须为非空列表")
        candidates = []
        for candidate in candidates_raw:
            if not isinstance(candidate, Mapping) or not candidate.keys() <= {"name", "rank", "min_stars"}:
                raise ValueError("assignment_groups 候选配置无效")
            canonical = name(candidate.get("name"))
            if canonical not in root_names or canonical in {c.name for c in candidates}:
                raise ValueError("assignment_groups 候选须为不重复的采购目标")
            candidates.append(AssignmentCandidate(canonical,
                integer(candidate.get("rank", 0), "candidate.rank", 0, 100000),
                integer(candidate.get("min_stars", 1), "candidate.min_stars", 1, 3)))
        replacements = names(item.get("replace_from", [c.name for c in candidates]), "replace_from")
        if not replacements or not set(replacements) <= {c.name for c in candidates}:
            raise ValueError("replace_from 必须引用本组候选")
        if assigned_names & {c.name for c in candidates}:
            raise ValueError("同一候选不能分配到多个席位")
        assigned_names.update(c.name for c in candidates)
        if item.get("star_policy", "prefer_not_lower") != "prefer_not_lower":
            raise ValueError("assignment_groups.star_policy 仅支持 prefer_not_lower")
        if item.get("keep_incumbent_on_tie", True) is not True or item.get("on_unavailable", "keep_current") != "keep_current":
            raise ValueError("assignment_groups 必须在同条件或证据缺失时保留现任")
        groups[group_name] = AssignmentGroup(area, tuple(candidates), replacements)
    rules_raw = raw.get("position_rules", [])
    if not isinstance(rules_raw, (list, tuple)):
        raise ValueError("formation.position_rules 必须为列表")
    rules, rule_names = [], set()
    for item in rules_raw:
        if not isinstance(item, Mapping) or not item.keys() <= {"name", "area", "min_capacity", "requires_assignment"}:
            raise ValueError("position_rules 包含未知配置")
        canonical = name(item.get("name"))
        if canonical not in root_names or canonical in rule_names or canonical in assigned_names:
            raise ValueError("position_rules 不得重复、覆盖席位候选或引用非采购角色")
        rule_names.add(canonical)
        area = item.get("area")
        if area not in FIELD_AREAS:
            raise ValueError("position_rules.area 只能为前后台区域")
        required = item.get("requires_assignment", {})
        if not isinstance(required, Mapping):
            raise ValueError("requires_assignment 必须为席位到候选的映射")
        parsed = {}
        for group_name, candidate in required.items():
            canonical_candidate = name(candidate)
            if group_name not in groups or canonical_candidate not in {c.name for c in groups[group_name].candidates}:
                raise ValueError("requires_assignment 必须引用已定义席位候选")
            parsed[group_name] = canonical_candidate
        rules.append(PositionRule(canonical, area,
            integer(item.get("min_capacity", 0), "position_rules.min_capacity", 0, 10), parsed))
    trait_raw = raw.get("traits", {})
    if not isinstance(trait_raw, Mapping):
        raise ValueError("formation.traits 必须为角色到羁绊列表的映射")
    traits: dict[str, frozenset[str]] = {}
    for character, memberships in trait_raw.items():
        canonical = name(character)
        if (not isinstance(memberships, (list, tuple))
                or any(not isinstance(t, str) or not t.strip() for t in memberships)):
            raise ValueError("formation.traits 羁绊必须为非空字符串列表")
        if canonical in traits:
            raise ValueError("formation.traits 不得重复角色别名")
        traits[canonical] = frozenset(t.strip() for t in memberships)
    trait_names = set().union(*traits.values()) if traits else set()

    def requirements(value: Any, label: str, character_keys: bool = False,
                     maximum: int = 99) -> dict[str, int]:
        if not isinstance(value, Mapping):
            raise ValueError(f"{label} 必须为对象")
        result = {}
        for key, count in value.items():
            canonical = name(key) if character_keys else key
            if not character_keys and canonical not in trait_names:
                raise ValueError(f"{label} 引用了没有成员定义的羁绊：{canonical}")
            if canonical in result:
                raise ValueError(f"{label} 包含重复别名")
            result[canonical] = integer(count, label, maximum=maximum)
        return result

    preserve = requirements(raw.get("preserve_traits", {}), "preserve_traits")
    protection_raw = raw.get("protect_until_fielded", {})
    if not isinstance(protection_raw, Mapping):
        raise ValueError("protect_until_fielded 必须为对象")
    protection = {}
    for protected, successor in protection_raw.items():
        protected, successor = name(protected), name(successor)
        if protected == successor or protected in protection:
            raise ValueError("protect_until_fielded 不能自我依赖或重复")
        protection[protected] = successor
    for start in protection:
        seen, current = set(), start
        while current in protection:
            if current in seen:
                raise ValueError("protect_until_fielded 存在循环依赖")
            seen.add(current)
            current = protection[current]

    stage_raw = raw.get("stages")
    if not isinstance(stage_raw, (list, tuple)) or not stage_raw:
        raise ValueError("formation.stages 必须是非空列表")
    stages = []
    stage_names = set()
    previous_capacity = 0
    for index, item in enumerate(stage_raw):
        if not isinstance(item, Mapping) or not isinstance(item.get("name"), str) or not item["name"].strip():
            raise ValueError("每个 formation stage 必须有名称")
        stage_name = item["name"].strip()
        if stage_name in stage_names:
            raise ValueError("formation stage 名称不得重复")
        stage_names.add(stage_name)
        capacity = integer(item.get("min_capacity", 0), "min_capacity", minimum=0)
        if capacity < previous_capacity:
            raise ValueError("formation stages 必须按 min_capacity 递增排列")
        previous_capacity = capacity
        on = names(item.get("on_field", []), "stage.on_field")
        off = names(item.get("off_field", []), "stage.off_field")
        if not on or len(on) > 4 or set(on) & set(off):
            raise ValueError("stage 前台须有 1 至 4 人，前后台不得重复同名")
        if not set(on + off) <= root_names | role_names:
            raise ValueError("stage 角色必须已列入根购买目标或职责候选")
        required = names(item.get("requires_fielded", []), "requires_fielded")
        available = names(item.get("requires_available", []), "requires_available")
        required_stars = requirements(item.get("requires_stars", {}), "requires_stars", True, 3)
        if not set(required + available) <= root_names | role_names:
            raise ValueError("阶段前置角色必须来自购买目标或职责候选")
        if not set(required_stars) <= root_names | role_names:
            raise ValueError("requires_stars 角色必须来自购买目标或职责候选")
        if index == 0 and (capacity != 0 or required or available or required_stars):
            raise ValueError("首个阶段必须从 min_capacity=0 开始且无角色前置要求")
        stage_roles = role_requirements(item.get("role_requirements", {}), global_roles)
        priority = names(item.get("priority", []), "stage.priority")
        if not set(priority) <= set(on + off):
            raise ValueError("stage.priority 必须来自本阶段阵容")
        priority += tuple(n for n in on + off if n not in priority)
        stages.append(FormationStage(stage_name, capacity, on, off, required, priority,
                                     available, stage_roles, required_stars))

    gate_raw = raw.get("upgrade_gate")
    gate = None
    if gate_raw is not None:
        if not isinstance(gate_raw, Mapping):
            raise ValueError("upgrade_gate 必须为对象或 null")
        gate = UpgradeGate(
            integer(gate_raw.get("from_level"), "upgrade_gate.from_level"),
            requirements(gate_raw.get("fielded", {}), "upgrade_gate.fielded", True, 3),
            requirements(gate_raw.get("traits", {}), "upgrade_gate.traits"),
            requirements(gate_raw.get("prices", {}), "upgrade_gate.prices", True),
        )
    for group in groups.values():
        if not any(set(getattr(stage, group.area)) & set(group.replace_from) for stage in stages):
            raise ValueError("assignment_groups 必须在至少一个阶段拥有可替换席位")
        if any(len(set(getattr(stage, group.area)) & set(group.replace_from)) > group.count for stage in stages):
            raise ValueError("阶段中同组席位超过 count")
    purchase_targets = {name(n): integer(stars, "purchase target stars", 1, 3)
                        for area in FIELD_AREAS for n, stars in strategy.get(area, {}).items()}
    root_positions = {}
    for area in FIELD_AREAS:
        for value in strategy.get(area, {}):
            canonical = name(value)
            root_positions[canonical] = root_positions.get(canonical, ()) + (area,)
    return FormationConfig(traits, preserve, protection, tuple(stages), gate, roles, global_roles,
                           groups, tuple(rules), purchase_targets, root_positions)


def confirmed_trait_counts(config: FormationConfig | None,
                           observations: Mapping[str, Sequence[Any]]) -> dict[str, int]:
    """Count unique confirmed fielded names, never hand copies or fee variants."""
    counts: dict[str, int] = {}
    if config is not None:
        for name in _field_names(observations):
            for trait in config.traits.get(name, ()):
                counts[trait] = counts.get(trait, 0) + 1
    return counts


def _role_requirements(config, stage):
    if config is None:
        return {}
    return {**config.role_requirements, **(stage.role_requirements if stage else {})}


def _role_providers(config, role, requirement):
    providers = {provider.name: provider for provider in config.roles.get(role, ())}
    return tuple(providers[name] for name in requirement.candidates + requirement.interim_candidates)


def _qualified_role_names(providers, observations):
    return tuple(provider.name for provider in providers if any(
        _name(obs) == provider.name and type(getattr(obs, "stars", None)) is int
        and obs.stars >= provider.min_stars
        for area in provider.areas for obs in observations.get(area, ())))


def _possible_role_names(providers, observations):
    # A reliable identity with unread stars is not confirmed coverage, but it
    # also is not evidence that the last possible provider can safely retire.
    return tuple(provider.name for provider in providers if any(
        _name(obs) == provider.name and (type(getattr(obs, "stars", None)) is not int
                                        or obs.stars >= provider.min_stars)
        for area in provider.areas for obs in observations.get(area, ())))


def _role_purchase_targets(providers, requirement, observations, field_providers):
    if len(field_providers) >= requirement.minimum:
        return {}
    # Acquire or upgrade one held candidate first. Do not stock every fallback,
    # nor buy duplicates merely because its stars have not yet been reread.
    for provider in providers:
        if provider.name in field_providers:
            continue
        owned = [obs for area in ALL_AREAS for obs in observations.get(area, ())
                 if _name(obs) == provider.name and (area != "in_hand" or _movable(obs))]
        if owned:
            stars = [getattr(obs, "stars", None) for obs in owned]
            if any(type(value) is not int for value in stars) or max(stars) >= provider.min_stars:
                return {}
            return {provider.name: provider.min_stars}
    return {provider.name: provider.min_stars for provider in providers
            if provider.name not in field_providers}


def evaluate_role_requirements(config: FormationConfig | None, stage: FormationStage | None,
                               observations: Mapping[str, Sequence[Any]]) -> dict[str, RoleEvaluation]:
    """Evaluate confirmed coverage, never count bench cards or unknown stars.

    Names come only from configured providers. Unknown coverage may still have
    an actionable, reliably identified bench candidate; callers own recovery
    budgets and the requirement's block/warn_continue policy.
    """
    result = {}
    for role, requirement in _role_requirements(config, stage).items():
        providers = _role_providers(config, role, requirement)
        fielded = _qualified_role_names(providers, observations)
        bench = tuple(provider.name for provider in providers
                      if provider.name not in fielded and any(
                          _movable(obs) and _name(obs) == provider.name
                          for obs in observations.get("in_hand", ())))
        uncertain_names = {provider.name for provider in providers if any(
            _name(obs) == provider.name and type(getattr(obs, "stars", None)) is not int
            for area in provider.areas for obs in observations.get(area, ()))}
        areas = {area for provider in providers for area in provider.areas}
        unknown_slots = sum(_state(obs) == "unknown" or
                            getattr(obs, "evidence", "") in UNRELIABLE_EVIDENCE or
                            getattr(obs, "stale", False)
                            for area in areas for obs in observations.get(area, ()))
        if any(area not in observations for area in areas):
            unknown_slots += len(providers)
        possible_extra = min(len(providers) - len(fielded),
                             unknown_slots + len(uncertain_names - set(fielded)))
        if len(fielded) >= requirement.minimum:
            state, reason = "satisfied", "role_confirmed"
        elif len(fielded) + possible_extra >= requirement.minimum:
            state, reason = "unknown", "role_not_confirmed"
        else:
            state, reason = "missing", "role_missing"
        targets = _role_purchase_targets(providers, requirement, observations, fielded)
        result[role] = RoleEvaluation(state, requirement.minimum, requirement.on_missing,
                                      reason, fielded, bench, tuple(targets))
    return result


def role_purchase_targets(config: FormationConfig | None, stage: FormationStage | None,
                          observations: Mapping[str, Sequence[Any]]) -> dict[str, int]:
    """Only current coverage needs; confirmed goals and held unknown stars pause buying."""
    targets = {}
    for role, requirement in _role_requirements(config, stage).items():
        providers = _role_providers(config, role, requirement)
        fielded = _qualified_role_names(providers, observations)
        for name, stars in _role_purchase_targets(providers, requirement, observations, fielded).items():
            targets[name] = max(stars, targets.get(name, 0))
    return targets


def role_protected_names(config: FormationConfig | None, stage: FormationStage | None,
                         observations: Mapping[str, Sequence[Any]]) -> frozenset[str]:
    """Reserve only enough held candidates/materials to close a current role gap."""
    protected = set()
    for evaluation in evaluate_role_requirements(config, stage, observations).values():
        needed = max(0, evaluation.minimum - len(evaluation.field_providers))
        protected.update(evaluation.bench_candidates[:needed])
    return frozenset(protected)


def _select_base_stage(config: FormationConfig | None,
                       observations: Mapping[str, Sequence[Any]],
                       capacity: int | None) -> FormationStage | None:
    if config is None:
        return None
    selected = config.stages[0]
    fielded = _field_names(observations)
    available = {name for area in ALL_AREAS for obs in observations.get(area, ())
                 if (area != "in_hand" or _movable(obs)) and (name := _name(obs)) is not None}
    for stage in config.stages[1:]:
        if (type(capacity) is not int or capacity < stage.min_capacity
                or not set(stage.requires_fielded) <= fielded
                or not set(stage.requires_available) <= available
                or any(not any(_name(obs) == name and type(getattr(obs, "stars", None)) is int
                               and obs.stars >= stars for area in ALL_AREAS
                               for obs in observations.get(area, ()))
                       for name, stars in stage.requires_stars.items())):
            break
        selected = stage
    return selected


def resolve_effective_targets(config: FormationConfig | None,
                              observations: Mapping[str, Sequence[Any]],
                              capacity: int | None,
                              previous: EffectiveTargets | None = None) -> EffectiveTargets:
    """Resolve one shared target without converting intent into observations.

    A group owns one regional seat, not a global exclusion. Reliable stars
    choose its occupant; ties retain the incumbent. Historical intent only
    survives a missing observation while uncertainty remains, and emits a gap.
    Population thresholds use ordinary-character seats; callers pass the total
    game population, and NPC occupancy is subtracted once in this resolver.
    """
    # Losing sight of an authenticated NPC is not evidence that its population
    # seat became free. Release that reservation only after the field is reliable;
    # an unresolved bench does not prevent a confirmed NPC departure.
    field_uncertain = any(_state(obs) not in {"known", "empty", "locked"}
                          or getattr(obs, "evidence", "") in UNRELIABLE_EVIDENCE
                          or getattr(obs, "stale", False)
                          for area in FIELD_AREAS for obs in observations.get(area, ()))
    current_npcs = confirmed_field_npc_count(observations)
    npc_count = max(current_npcs, previous.npc_count if previous and field_uncertain else 0)
    strategy_capacity = strategy_population_capacity(observations, capacity,
        reserved_npc_count=npc_count)
    base = _select_base_stage(config, observations, strategy_capacity)
    if base is None:
        return EffectiveTargets(None, npc_count=npc_count, strategy_capacity=strategy_capacity)
    gaps = []
    if npc_count > current_npcs:
        gaps.append("npc_population_unknown")
    uncertain = any(_state(obs) == "unknown" or getattr(obs, "evidence", "") in UNRELIABLE_EVIDENCE
                    or getattr(obs, "stale", False)
                    for area in ALL_AREAS for obs in observations.get(area, ()))
    if previous is not None and previous.base_stage_name:
        prior = next((stage for stage in config.stages if stage.name == previous.base_stage_name), None)
        if (prior is not None and config.stages.index(prior) > config.stages.index(base)
                and type(strategy_capacity) is int and strategy_capacity >= prior.min_capacity and uncertain):
            base = prior
            gaps.append("stage_evidence_unknown:" + prior.name)
    regional = {area: list(getattr(base, area)) for area in FIELD_AREAS}
    assignments = {}
    priority = list(base.priority or base.on_field + base.off_field)
    for key, group in config.assignment_groups.items():
        anchors = [n for n in regional[group.area] if n in group.replace_from]
        if not anchors:
            continue
        candidates = {c.name: c for c in group.candidates}
        held = {name: [(area, obs) for area in ALL_AREAS for obs in observations.get(area, ())
                       if _movable(obs) and _name(obs) == name] for name in candidates}
        stars = {name: max((obs.stars for _, obs in entries
                           if type(getattr(obs, "stars", None)) is int), default=None)
                 for name, entries in held.items()}
        incumbents = [n for n, entries in held.items() if any(area == group.area for area, _ in entries)]
        old = previous.assignments.get(key) if previous else None
        incumbent = old if old in incumbents else next(iter(incumbents), None)
        selected = incumbent
        # Unknown incumbent stars must not be interpreted as a downgrade to 0.
        if incumbent and stars[incumbent] is None:
            gaps.append("assignment_stars_unknown:" + key + ":" + incumbent)
        else:
            eligible = [n for n, star in stars.items() if type(star) is int
                        and star >= candidates[n].min_stars
                        and (incumbent is None or star >= stars[incumbent])]
            if eligible:
                selected = max(eligible, key=lambda n: (
                    stars[n], candidates[n].rank, n == incumbent,
                    n == old, -list(candidates).index(n)))
            elif incumbent and stars[incumbent] < candidates[incumbent].min_stars:
                selected = None
        if selected is None and old in candidates and uncertain:
            selected = old
            gaps.append("assignment_identity_unknown:" + key + ":" + old)
        elif old in candidates and (not held[old] and uncertain or held[old] and stars[old] is None):
            # A readable fallback is not evidence that a temporarily hidden
            # selected card disappeared. Hold target intent and request recovery.
            selected = old
            gaps.append("assignment_evidence_unknown:" + key + ":" + old)
        if selected is None:
            # With no reliable candidate retain the stage's existing seat;
            # this is a target, never a claim that the card is actually held.
            selected = anchors[0]
        assignments[key] = selected
        anchor = anchors[0]
        regional[group.area] = [selected if n == anchor else n for n in regional[group.area]
                               if n not in group.replace_from or n == anchor]
        # The selected identity cannot be required in both areas. The other
        # group candidate may remain an explicit target of the opposite area.
        opposite = next(area for area in FIELD_AREAS if area != group.area)
        regional[opposite] = [n for n in regional[opposite] if n != selected]
        priority = [selected if n == anchor else n for n in priority
                    if n not in group.replace_from or n == anchor or n in regional[opposite]]
    for rule in config.position_rules:
        if (type(strategy_capacity) is not int or strategy_capacity < rule.min_capacity
                or any(assignments.get(key) != name for key, name in rule.requires_assignment.items())
                or not any(rule.name in names for names in regional.values())):
            continue
        # Assignment intent with missing evidence cannot trigger a new migration.
        if rule.requires_assignment and any(gap.startswith("assignment_") for gap in gaps):
            if not (previous and previous.stage and rule.name in getattr(previous.stage, rule.area)):
                continue
        elif any(not any(_name(obs) == name and type(getattr(obs, "stars", None)) is int
                         and obs.stars >= next(c.min_stars for c in config.assignment_groups[key].candidates
                                               if c.name == name)
                         for area in ALL_AREAS for obs in observations.get(area, ()))
                 for key, name in rule.requires_assignment.items()):
            continue
        other = next(area for area in FIELD_AREAS if area != rule.area)
        if rule.name in regional[rule.area]:
            continue
        if rule.area == "off_field" and not any(_name(o) and _name(o) != rule.name
                                                for o in observations.get("on_field", ())):
            continue
        if len(regional[rule.area]) >= (4 if rule.area == "on_field" else 6):
            gaps.append("position_capacity:" + rule.name + ":" + rule.area)
            continue
        regional[other] = [n for n in regional[other] if n != rule.name]
        regional[rule.area].append(rule.name)
    all_desired = regional["on_field"] + regional["off_field"]
    priority = list(dict.fromkeys(n for n in priority if n in all_desired))
    priority += [n for n in all_desired if n not in priority]
    stage = replace(base, on_field=tuple(regional["on_field"]), off_field=tuple(regional["off_field"]),
                    priority=tuple(priority))
    purchases = dict(config.purchase_targets)
    purchases.update({name: max(purchases.get(name, 0), stars)
                      for name, stars in role_purchase_targets(config, stage, observations).items()})
    return EffectiveTargets(stage, base.name, assignments, purchases, dict(purchases), tuple(gaps),
                            npc_count, strategy_capacity)


def select_formation_stage(config: FormationConfig | None,
                           observations: Mapping[str, Sequence[Any]],
                           capacity: int | None) -> FormationStage | None:
    """Compatibility entry point; all callers see the same effective target."""
    return resolve_effective_targets(config, observations, capacity).stage


def formation_change_allowed(config: FormationConfig | None,
                             before: Mapping[str, Sequence[Any]],
                             after: Mapping[str, Sequence[Any]],
                             stage: FormationStage | None = None) -> FormationDecision:
    if config is None:
        return FormationDecision(True, "formation_disabled")
    before_names, after_names = _field_names(before), _field_names(after)
    before_counts, after_counts = confirmed_trait_counts(config, before), confirmed_trait_counts(config, after)
    for protected, successor in config.protect_until_fielded.items():
        if protected in before_names and protected not in after_names and successor not in before_names:
            return FormationDecision(False, f"protect:{protected}:until:{successor}", before_counts, after_counts)
    for trait, threshold in config.preserve_traits.items():
        if before_counts.get(trait, 0) >= threshold and after_counts.get(trait, 0) < threshold:
            return FormationDecision(False, f"preserve:{trait}:{threshold}", before_counts, after_counts)
    for role, requirement in _role_requirements(config, stage).items():
        # A new stage may narrow its recruitment candidates. Existing effective
        # fallback providers still need protection until a replacement is seen.
        providers = config.roles[role]
        established = set(_qualified_role_names(providers, before))
        if established:
            remaining = established & set(_qualified_role_names(providers, after))
        else:
            established = set(_possible_role_names(providers, before))
            remaining = established & set(_possible_role_names(providers, after))
        if established and len(remaining) < min(requirement.minimum, len(established)):
            return FormationDecision(False, f"preserve_role:{role}:{requirement.minimum}",
                                     before_counts, after_counts)
    return FormationDecision(True, "allowed", before_counts, after_counts)


def stage_upgrade_allowed(config: FormationConfig | None,
                          observations: Mapping[str, Sequence[Any]],
                          level: int | None,
                          prices: Mapping[str, int] | None = None) -> FormationDecision:
    gate = config.upgrade_gate if config else None
    if gate is None:
        return FormationDecision(True, "upgrade_gate_disabled")
    if type(level) is not int:
        return FormationDecision(False, "unknown_level")
    if level < gate.from_level:
        return FormationDecision(True, "below_upgrade_gate")
    names = _field_names(observations)
    for name, stars in gate.fielded.items():
        evidence = [getattr(o, "stars", None) for area in FIELD_AREAS
                    for o in observations.get(area, ()) if _name(o) == name]
        if name not in names or not evidence or any(type(s) is not int or s < stars for s in evidence):
            return FormationDecision(False, f"core_stars:{name}:{stars}")
    for name, price in gate.prices.items():
        actual = (prices or {}).get(name)
        if name not in names or type(actual) is not int or actual < price:
            return FormationDecision(False, f"core_price:{name}:{price}")
    counts = confirmed_trait_counts(config, observations)
    for trait, count in gate.traits.items():
        if counts.get(trait, 0) < count:
            return FormationDecision(False, f"core_trait:{trait}:{count}")
    return FormationDecision(True, "core_confirmed")


def _configured_interim_targets(config, stage):
    """Root targets can retire unrelated starters without activating gated seats."""
    staged = set(stage.on_field + stage.off_field)
    assigned = {candidate.name for group in config.assignment_groups.values()
                for candidate in group.candidates}
    return set(config.purchase_targets) - staged - assigned


def _placement_areas(config, stage, observation):
    """Explicit stage/root placement owns positioning, including early fillers."""
    name = _name(observation)
    for area in FIELD_AREAS:
        if name in getattr(stage, area):
            return (area,)
    if name in config.root_positions:
        return config.root_positions[name]
    position = getattr(observation.character, "position", None)
    if position is None:
        position = getattr(observation.character, "positioning", None)
    position = getattr(position, "value", position)
    return tuple(area for area, value in (("on_field", 1), ("off_field", 2))
                 if position in (value, 3))


def _target_score(config, stage, snapshot, preferred_names=()):
    desired = {name: area for area in FIELD_AREAS for name in getattr(stage, area)}
    interim = _configured_interim_targets(config, stage)
    priority = stage.priority or stage.on_field + stage.off_field
    rank = {name: len(priority) - i for i, name in enumerate(priority)}
    result = 0
    for role, requirement in _role_requirements(config, stage).items():
        providers = _role_providers(config, role, requirement)
        qualified = _qualified_role_names(providers, snapshot)
        result += min(requirement.minimum, len(qualified)) * 100000
        staged = sum(provider.name not in qualified and any(
            _name(obs) == provider.name and type(getattr(obs, "stars", None)) is not int
            for area in provider.areas for obs in snapshot[area]) for provider in providers)
        result += min(max(0, requirement.minimum - len(qualified)), staged) * 50000
    counted = set()
    for area in FIELD_AREAS:
        for obs in snapshot[area]:
            name = _name(obs)
            if name is None or name in counted:
                continue
            counted.add(name)
            if name not in desired:
                result += (200 + (100 if area in _placement_areas(config, stage, obs) else 0)
                           if name in interim else -50)
                continue
            result += 1000 + rank.get(name, 0) * 10 + (100 if desired[name] == area else 0)
            if name in config.protect_until_fielded.values():
                result += 20000
            if name in preferred_names:
                result += 40000
            if any(group.area == area and name in group.replace_from
                   for group in config.assignment_groups.values()):
                stars = getattr(obs, "stars", None)
                if type(stars) is int:
                    result += min(stars, 3) * 100
    return result


def _assignment_copy_upgrade(config, source, target):
    return (_name(source) is not None and _name(source) == _name(target)
            and any(_name(source) in group.replace_from for group in config.assignment_groups.values())
            and type(getattr(source, "stars", None)) is int
            and type(getattr(target, "stars", None)) is int and source.stars > target.stars)


def _assignment_replacement_allowed(config, desired, source, target, snapshot):
    for group in config.assignment_groups.values():
        if _name(source) not in group.replace_from or desired.get(_name(source)) != group.area:
            continue
        if _empty(target) or _name(target) in group.replace_from:
            continue
        if _name(target) in desired or any(_name(o) in group.replace_from
                                          for o in snapshot[group.area]):
            return False
    return True


def _plan_greedy_formation_move(config: FormationConfig | None, stage: FormationStage | None,
                         observations: Mapping[str, Sequence[Any]], capacity: int | None,
                         preferred_names: Sequence[str] = (),
                         excluded_moves: Sequence[tuple[str, int, str, int]] = (),
                         include_interim_targets: bool = True) -> FormationMove | None:
    """Return one strictly improving, protected swap; never mutate observations.

    Stage targets retain priority over root-list fillers, which may replace
    unrelated starters. Configured placement overrides character defaults.
    """
    if config is None or stage is None:
        return None
    desired = {name: area for area in FIELD_AREAS for name in getattr(stage, area)}
    requirements = _role_requirements(config, stage)
    role_providers = {role: _role_providers(config, role, requirement)
                      for role, requirement in requirements.items()}
    role_areas = {}
    for providers in role_providers.values():
        for provider in providers:
            role_areas.setdefault(provider.name, set()).update(provider.areas)
    interim = _configured_interim_targets(config, stage) if include_interim_targets else set()
    active_names = set(desired) | set(role_areas) | interim
    excluded = set(excluded_moves)
    priority = stage.priority or stage.on_field + stage.off_field
    rank = {name: len(priority) - index for index, name in enumerate(priority)}
    successors = set(config.protect_until_fielded.values())
    preferred = set(preferred_names)
    before = {area: list(observations.get(area, ())) for area in ALL_AREAS}
    names = _field_names(before)

    def score(snapshot):
        return _target_score(config, stage, snapshot, preferred)

    def destination_allowed(observation, area):
        if area == "in_hand" or _empty(observation):
            return True
        name = _name(observation)
        if name in desired:
            return desired[name] == area
        if area in role_areas.get(name, ()):
            return True
        return area in _placement_areas(config, stage, observation)

    baseline = score(before)
    choices = []
    for source_area in ALL_AREAS:
        for si, source in enumerate(before[source_area]):
            if not _movable(source):
                continue
            source_name = _name(source)
            if source_area == "in_hand" and (source_name not in active_names or source_name in names
                    and not any(_assignment_copy_upgrade(config, source, o)
                                for area in FIELD_AREAS for o in before[area])):
                continue
            for target_area in ALL_AREAS:
                if source_area == "in_hand" and target_area == "in_hand":
                    continue
                for ti, target in enumerate(before[target_area]):
                    if source_area == target_area and si == ti:
                        continue
                    if (source_area, si, target_area, ti) in excluded:
                        continue
                    if not (_empty(target) or _movable(target)):
                        continue
                    if source_area == "in_hand" and not _assignment_replacement_allowed(
                            config, desired, source, target, before):
                        continue
                    if (source_area == "in_hand" and source_name not in desired
                            and source_name in role_areas and _name(target) in desired):
                        # A fallback role provider may replace a temporary unit,
                        # never evict an already acquired stage requirement.
                        continue
                    # The symmetric hand -> field action owns deployment events.
                    if target_area == "in_hand" and not _empty(target):
                        continue
                    if target_area == "in_hand":
                        def replacement_improves(area, index):
                            # Retiring an interim unit removes its score penalty,
                            # but that alone is not progress. The available next
                            # placement must improve on the original board, or
                            # surplus role candidates can repeatedly bench and
                            # redeploy the same effective provider.
                            replaced = {a: list(slots) for a, slots in before.items()}
                            replaced[source_area][si], replaced[target_area][ti] = target, source
                            replaced[source_area][si], replaced[area][index] = (
                                replaced[area][index], replaced[source_area][si])
                            return score(replaced) > baseline

                        ready_replacement = any(
                            _movable(o) and _name(o) in active_names and _name(o) not in names
                            and destination_allowed(o, source_area)
                            and ("in_hand", index, source_area, si) not in excluded
                            and replacement_improves("in_hand", index)
                            for index, o in enumerate(before["in_hand"]))
                        ready_relocation = any(
                            _movable(o) and desired.get(_name(o)) == source_area
                            and (area, index, source_area, si) not in excluded
                            and replacement_improves(area, index)
                            for area in FIELD_AREAS if area != source_area
                            for index, o in enumerate(before[area]))
                        # Keep useful interim occupants until a real next step exists.
                        if source_name in desired or not (ready_replacement or ready_relocation):
                            continue
                    if _name(target) == source_name and not (
                            source_area == "in_hand" and _assignment_copy_upgrade(config, source, target)):
                        continue
                    if source_area == "in_hand" and source_name in names and _name(target) != source_name:
                        continue
                    if (not destination_allowed(source, target_area)
                            or not destination_allowed(target, source_area)):
                        continue
                    # A second field copy is never an intentional formation move.
                    if target_area == "in_hand" and _name(target) in names:
                        continue
                    after = {area: list(slots) for area, slots in before.items()}
                    after[source_area][si], after[target_area][ti] = target, source
                    field_before = sum(_counts_towards_population(o) for a in FIELD_AREAS for o in before[a])
                    field_after = sum(_counts_towards_population(o) for a in FIELD_AREAS for o in after[a])
                    if field_after > field_before and (type(capacity) is not int or field_after > capacity):
                        continue
                    # Keep at least one confirmed front unit once established.
                    if any(_name(o) for o in before["on_field"]) and not any(_name(o) for o in after["on_field"]):
                        continue
                    decision = formation_change_allowed(config, before, after, stage=stage)
                    gain = score(after) - baseline
                    if not decision.allowed or gain <= 0:
                        continue
                    reason = "relocate" if source_area in FIELD_AREAS and target_area in FIELD_AREAS else (
                        "deploy" if source_area == "in_hand" else "bench")
                    if reason == "deploy" and source_name in role_areas and source_name not in desired:
                        reason = "deploy_role"
                    move = FormationMove(source_area, si, target_area, ti, reason,
                                         decision.before_traits, decision.after_traits)
                    choices.append((gain, source_name in preferred, -si, -ti, move))
    if choices:
        return max(choices, key=lambda item: item[:4])[-1]
    if not include_interim_targets:
        return None

    # Starting hands need not contain any member of the selected strategy.
    # Keep the strategy planner first, then fill positively observed empty slots
    # with temporary units that a later desired deployment can replace.
    field_count = sum(_counts_towards_population(o) for area in FIELD_AREAS for o in before[area])
    if type(capacity) is not int or field_count >= capacity:
        return None
    has_front = any(_name(o) for o in before["on_field"])
    inactive_assignments = {candidate.name for group in config.assignment_groups.values()
                            for candidate in group.candidates} - set(desired)
    for si, source in enumerate(before["in_hand"]):
        if (not _movable(source) or _name(source) in desired or _name(source) in names
                or _name(source) in inactive_assignments):
            continue
        for target_area in FIELD_AREAS:
            if (target_area not in _placement_areas(config, stage, source)
                    or (not has_front and target_area != "on_field")):
                continue
            if _name(source) in role_areas and target_area not in role_areas[_name(source)]:
                continue
            for ti, target in enumerate(before[target_area]):
                if not _empty(target):
                    continue
                if ("in_hand", si, target_area, ti) in excluded:
                    continue
                after = {area: list(slots) for area, slots in before.items()}
                after["in_hand"][si], after[target_area][ti] = target, source
                decision = formation_change_allowed(config, before, after, stage=stage)
                if decision.allowed:
                    return FormationMove("in_hand", si, target_area, ti, "deploy_interim",
                                         decision.before_traits, decision.after_traits)
    return None


def _identified_move(move, observations, *, requires_completion=False):
    source = observations[move.source_area][move.source_index]
    target = observations[move.target_area][move.target_index]
    return replace(move, source_name=_name(source), target_name=_name(target),
                   source_stars=getattr(source, "stars", None), target_stars=getattr(target, "stars", None),
                   requires_completion=requires_completion)


def _sequence_edges(config, stage, before, capacity, excluded_moves=(), include_interim_targets=True):
    """Enumerate legal physical steps, including bounded temporary bench moves."""
    desired = {name: area for area in FIELD_AREAS for name in getattr(stage, area)}
    role_areas = {}
    for role, requirement in _role_requirements(config, stage).items():
        for provider in _role_providers(config, role, requirement):
            role_areas.setdefault(provider.name, set()).update(provider.areas)
    active = set(desired) | set(role_areas)
    if include_interim_targets:
        active |= _configured_interim_targets(config, stage)
    field_names = _field_names(before)
    before_count = sum(_counts_towards_population(o) for area in FIELD_AREAS for o in before[area])

    def allowed(obs, area):
        if area == "in_hand" or _empty(obs):
            return True
        if _name(obs) in desired:
            return desired[_name(obs)] == area
        if area in role_areas.get(_name(obs), ()):
            return True
        return area in _placement_areas(config, stage, obs)

    for source_area in ALL_AREAS:
        for si, source in enumerate(before[source_area]):
            if not _movable(source):
                continue
            name = _name(source)
            if source_area == "in_hand" and name not in active:
                continue
            for target_area in ALL_AREAS:
                if source_area == target_area:
                    continue
                for ti, target in enumerate(before[target_area]):
                    if (source_area, si, target_area, ti) in excluded_moves:
                        continue
                    if not (_empty(target) or _movable(target)):
                        continue
                    if target_area == "in_hand" and not _empty(target):
                        continue
                    if source_area == "in_hand" and not _assignment_replacement_allowed(
                            config, desired, source, target, before):
                        continue
                    if source_area == "in_hand" and name in field_names and not _assignment_copy_upgrade(config, source, target):
                        continue
                    if source_area == "in_hand" and name in role_areas and name not in desired and _name(target) in desired:
                        continue
                    if _name(target) == name and not _assignment_copy_upgrade(config, source, target):
                        continue
                    if not allowed(source, target_area) or not allowed(target, source_area):
                        continue
                    after = {area: list(slots) for area, slots in before.items()}
                    after[source_area][si], after[target_area][ti] = target, source
                    after_count = sum(_counts_towards_population(o) for area in FIELD_AREAS for o in after[area])
                    if after_count > before_count and (type(capacity) is not int or after_count > capacity):
                        continue
                    if any(_name(o) for o in before["on_field"]) and not any(_name(o) for o in after["on_field"]):
                        continue
                    decision = formation_change_allowed(config, before, after, stage)
                    if not decision.allowed:
                        continue
                    move = FormationMove(source_area, si, target_area, ti, "planned_relocation",
                                         decision.before_traits, decision.after_traits)
                    yield _identified_move(move, before, requires_completion=True), after


def _board_key(snapshot):
    return tuple(tuple((_state(o), _name(o), getattr(o, "stars", None), _empty(o))
                       for o in snapshot[area]) for area in ALL_AREAS)


def _target_progress(config, stage, snapshot, preferred_names=()):
    # Merely removing an interim-unit penalty cannot justify the first leg of
    # a combination. Its terminal board must make actual target/role progress.
    desired = set(stage.on_field + stage.off_field)
    extras = _field_names(snapshot) - desired
    return _target_score(config, stage, snapshot, preferred_names) + 50 * len(extras)


def plan_formation_sequence(config: FormationConfig | None, stage: FormationStage | None,
                            observations: Mapping[str, Sequence[Any]], capacity: int | None,
                            preferred_names: Sequence[str] = (),
                            excluded_moves: Sequence[tuple[str, int, str, int]] = (),
                            max_moves: int = 3, *,
                            _include_interim_targets: bool = True) -> tuple[FormationMove, ...]:
    """Prefer one improving step, otherwise prove a legal two/three step path.

    Search is bounded to 64 boards per depth and 512 expanded boards. Callers
    retain the remaining steps, verify actual endpoints after every move and
    revalidate the remainder. A partially executed plan is not battle-ready.
    """
    if config is None or stage is None or max_moves < 1:
        return ()
    greedy = _plan_greedy_formation_move(config, stage, observations, capacity,
                                          preferred_names, excluded_moves, _include_interim_targets)
    if greedy is not None and _include_interim_targets:
        source = observations[greedy.source_area][greedy.source_index]
        staged = set(stage.on_field + stage.off_field)
        if (_name(source) in _configured_interim_targets(config, stage)
                and any(_movable(obs) and _name(obs) in staged - _field_names(observations)
                        for obs in observations.get("in_hand", ()))):
            # A one-step filler must not win over a two-step current-stage
            # deployment merely because its destination happens to be closer.
            primary_plan = plan_formation_sequence(config, stage, observations, capacity,
                preferred_names, excluded_moves, max_moves, _include_interim_targets=False)
            if primary_plan:
                # The unrestricted greedy candidate may differ, so validate
                # this proved stage-first choice through the sequence guards.
                return tuple(replace(move, requires_completion=True) for move in primary_plan)
    if greedy is not None:
        return (_identified_move(greedy, observations),)
    if max_moves < 2:
        return ()
    initial = {area: list(observations.get(area, ())) for area in ALL_AREAS}
    if (all(any(_name(o) == name for o in initial[area])
            for area in FIELD_AREAS for name in getattr(stage, area))
            and all(evaluation.state == "satisfied"
                    for evaluation in evaluate_role_requirements(config, stage, initial).values())
            and not any(_assignment_copy_upgrade(config, source, target)
                        for source in initial["in_hand"] for area in FIELD_AREAS for target in initial[area])
            and not (any(_movable(obs) and _name(obs) in _configured_interim_targets(config, stage)
                         and _name(obs) not in _field_names(initial) for obs in initial["in_hand"])
                     and any(_name(obs) and _name(obs) not in config.purchase_targets
                             for area in FIELD_AREAS for obs in initial[area]))):
        return ()
    baseline = _target_score(config, stage, initial, preferred_names)
    progress = _target_progress(config, stage, initial, preferred_names)
    settled = {(area, _name(o)) for area in FIELD_AREAS for o in initial[area]
               if _name(o) in getattr(stage, area)}
    frontier, seen, expanded = [(initial, ())], {_board_key(initial)}, 0
    for _ in range(min(max_moves, 3)):
        next_frontier, completed = [], []
        for before, plan in frontier:
            expanded += 1
            if expanded > 512:
                break
            for move, after in _sequence_edges(config, stage, before, capacity, set(excluded_moves),
                                                _include_interim_targets):
                key = _board_key(after)
                if key in seen:
                    continue
                seen.add(key)
                score = _target_score(config, stage, after, preferred_names)
                steps = plan + (move,)
                final_placements = {(area, _name(o)) for area in FIELD_AREAS for o in after[area]}
                if (score > baseline and _target_progress(config, stage, after, preferred_names) > progress
                        and settled <= final_placements):
                    completed.append((score, steps))
                else:
                    next_frontier.append((score, after, steps))
        if completed:
            return max(completed, key=lambda item: item[0])[1]
        frontier = [(after, plan) for _, after, plan in
                    sorted(next_frontier, key=lambda item: item[0], reverse=True)[:64]]
        if not frontier or expanded > 512:
            break
    return ()


def validate_formation_sequence(config: FormationConfig | None, stage: FormationStage | None,
                                observations: Mapping[str, Sequence[Any]], capacity: int | None,
                                moves: Sequence[FormationMove],
                                preferred_names: Sequence[str] = (),
                                excluded_moves: Sequence[tuple[str, int, str, int]] = ()) -> bool:
    """Validate the remaining steps against actual identities/stars and guards."""
    if config is None or stage is None or not moves or len(moves) > 3:
        return False
    if len(moves) == 1 and not moves[0].requires_completion:
        greedy = _plan_greedy_formation_move(config, stage, observations, capacity, preferred_names, excluded_moves)
        return greedy is not None and _identified_move(greedy, observations) == moves[0]
    current = {area: list(observations.get(area, ())) for area in ALL_AREAS}
    baseline = _target_score(config, stage, current, preferred_names)
    for expected in moves:
        found = None
        for move, after in _sequence_edges(config, stage, current, capacity, excluded_moves):
            if (move.source_area, move.source_index, move.target_area, move.target_index,
                move.source_name, move.target_name, move.source_stars, move.target_stars) == (
                expected.source_area, expected.source_index, expected.target_area, expected.target_index,
                expected.source_name, expected.target_name, expected.source_stars, expected.target_stars):
                found = after
                break
        if found is None:
            return False
        current = found
    return _target_score(config, stage, current, preferred_names) > baseline


def plan_formation_move(config: FormationConfig | None, stage: FormationStage | None,
                        observations: Mapping[str, Sequence[Any]], capacity: int | None,
                        preferred_names: Sequence[str] = (),
                        excluded_moves: Sequence[tuple[str, int, str, int]] = ()) -> FormationMove | None:
    plan = plan_formation_sequence(config, stage, observations, capacity,
                                   preferred_names, excluded_moves)
    return plan[0] if plan else None
