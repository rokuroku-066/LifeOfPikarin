from __future__ import annotations

import math
from typing import List, Set, TYPE_CHECKING

from pygame.math import Vector2

from ..core.agent import Agent, AgentTraits

if TYPE_CHECKING:
    from ..core.world import World


def decay_group_cooldown(world: World, agent: Agent) -> None:
    if agent.group_cooldown > 0.0:
        agent.group_cooldown = max(0.0, agent.group_cooldown - world._config.time_step)


def set_group(world: World, agent: Agent, group_id: int) -> None:
    agent.group_id = group_id
    agent.group_lonely_seconds = 0.0
    if group_id == world._UNGROUPED:
        agent.group_cooldown = 0.0
        return
    if world._config.feedback.group_merge_cooldown_seconds > 0.0:
        agent.group_cooldown = max(
            agent.group_cooldown, world._config.feedback.group_merge_cooldown_seconds
        )


def register_group_base(world: World, group_id: int, position: Vector2) -> None:
    if group_id == world._UNGROUPED:
        return
    if group_id in world._group_bases:
        return
    world._group_bases[group_id] = Vector2(position)


def prune_group_bases(world: World, active_groups: Set[int]) -> None:
    if not world._group_bases:
        return
    if not active_groups:
        world._group_bases.clear()
        return
    for gid in list(world._group_bases.keys()):
        if gid not in active_groups:
            world._group_bases.pop(gid, None)


def recruit_split_neighbors(
    world: World,
    previous_group: int,
    new_group: int,
    neighbors: List[Agent],
    neighbor_offsets: List[Vector2],
) -> None:
    max_recruits = world._config.feedback.group_split_recruitment_count
    if max_recruits <= 0 or new_group == world._UNGROUPED:
        return
    radius_sq = world._config.feedback.group_cohesion_radius * world._config.feedback.group_cohesion_radius
    candidates: List[tuple[float, Agent]] = []
    for other, offset in zip(neighbors, neighbor_offsets):
        if other.group_id != previous_group:
            continue
        dist_sq = offset.length_squared()
        if dist_sq > radius_sq:
            continue
        candidates.append((dist_sq, other))
    if not candidates:
        return
    candidates.sort(key=lambda item: item[0])
    for _, recruit in candidates[:max_recruits]:
        set_group(world, recruit, new_group)


def update_group_membership(
    world: World,
    agent: Agent,
    neighbors: List[Agent],
    neighbor_offsets: List[Vector2],
    neighbor_dist_sq: List[float],
    can_form_groups: bool,
    detach_radius_sq: float,
    close_threshold: int,
    traits: AgentTraits | None = None,
) -> int:
    original_group = agent.group_id
    traits = world._clamp_traits(agent.traits) if traits is None else traits
    feedback = world._config.feedback
    loyalty = max(0.1, traits.loyalty)
    kin_bias = traits.kin_bias
    use_kin_bias = abs(kin_bias - 1.0) > 1e-6
    prev_lonely = agent.group_lonely_seconds
    decay_group_cooldown(world, agent)
    world._group_counts_scratch.clear()
    world._ungrouped_neighbors.clear()
    if use_kin_bias:
        world._group_lineage_counts.clear()
    same_group_neighbors = 0
    same_group_close_neighbors = 0
    for other, offset, dist_sq in zip(neighbors, neighbor_offsets, neighbor_dist_sq):
        if other.group_id == world._UNGROUPED:
            world._ungrouped_neighbors.append(other)
        if agent.group_id != world._UNGROUPED and other.group_id == agent.group_id:
            same_group_neighbors += 1
            if dist_sq <= detach_radius_sq:
                same_group_close_neighbors += 1
        if other.group_id >= 0:
            world._group_counts_scratch[other.group_id] = world._group_counts_scratch.get(other.group_id, 0) + 1
            if use_kin_bias and other.lineage_id == agent.lineage_id:
                world._group_lineage_counts[other.group_id] = world._group_lineage_counts.get(other.group_id, 0) + 1

    majority_group = world._UNGROUPED
    majority_count = 0
    switch_group = world._UNGROUPED
    switch_count = 0
    majority_score = -float("inf")
    switch_score = -float("inf")
    for gid, count in world._group_counts_scratch.items():
        if use_kin_bias:
            kin_count = world._group_lineage_counts.get(gid, 0)
            score = count + (kin_bias - 1.0) * kin_count
        else:
            score = float(count)
        if score > majority_score or (math.isclose(score, majority_score) and count > majority_count):
            majority_group = gid
            majority_count = count
            majority_score = score
        if gid == agent.group_id:
            continue
        if score > switch_score or (math.isclose(score, switch_score) and count > switch_count):
            switch_group = gid
            switch_count = count
            switch_score = score

    if agent.group_id == world._UNGROUPED:
        agent.group_lonely_seconds = 0.0
    else:
        if same_group_close_neighbors >= close_threshold:
            agent.group_lonely_seconds = 0.0
        else:
            agent.group_lonely_seconds = prev_lonely + world._config.time_step
        effective_detach_seconds = feedback.group_detach_after_seconds * loyalty
        if agent.group_lonely_seconds >= effective_detach_seconds:
            switch_threshold = max(1, feedback.group_adoption_neighbor_threshold)
            switch_chance = min(1.0, feedback.group_switch_chance / max(0.1, loyalty))
            if (
                switch_group != world._UNGROUPED
                and switch_count >= switch_threshold
                and world._rng.next_float() < switch_chance
            ):
                set_group(world, agent, switch_group)
            else:
                if (
                    can_form_groups
                    and world._rng.next_float()
                    < min(1.0, feedback.group_detach_new_group_chance * max(0.0, traits.founder))
                ):
                    new_group = world._next_group_id
                    world._next_group_id += 1
                    register_group_base(world, new_group, agent.position)
                    set_group(world, agent, new_group)
                else:
                    set_group(world, agent, world._UNGROUPED)
            agent.group_lonely_seconds = 0.0

    if can_form_groups:
        try_form_group(world, agent)
        if agent.group_id == original_group:
            try_adopt_group(
                world, agent, majority_group, majority_count, same_group_neighbors, traits=traits
            )
    if agent.group_id == world._UNGROUPED and world._group_bases:
        seek_radius = world._config.feedback.group_seek_radius * 1.5
        seek_radius_sq = seek_radius * seek_radius
        nearest_group = world._UNGROUPED
        nearest_dist_sq = seek_radius_sq
        for gid, base in world._group_bases.items():
            offset = base - agent.position
            dist_sq = offset.length_squared()
            if dist_sq <= 1e-12 or dist_sq > seek_radius_sq:
                continue
            if dist_sq < nearest_dist_sq:
                nearest_group = gid
                nearest_dist_sq = dist_sq
        if nearest_group != world._UNGROUPED and world._rng.next_float() < feedback.group_adoption_chance:
            set_group(world, agent, nearest_group)
    if agent.group_id == original_group:
        try_split_group(
            world, agent, same_group_neighbors, neighbors, neighbor_offsets, can_form_groups, traits=traits
        )
    return same_group_neighbors


def try_form_group(world: World, agent: Agent) -> None:
    if agent.group_id != world._UNGROUPED:
        return
    if len(world._ungrouped_neighbors) < world._config.feedback.group_formation_neighbor_threshold:
        return
    if world._rng.next_float() >= world._config.feedback.group_formation_chance:
        return

    new_group = world._next_group_id
    world._next_group_id += 1
    register_group_base(world, new_group, agent.position)
    set_group(world, agent, new_group)
    recruits = min(len(world._ungrouped_neighbors), world._config.feedback.group_formation_neighbor_threshold + 2)
    for neighbor in world._ungrouped_neighbors[:recruits]:
        set_group(world, neighbor, new_group)


def try_adopt_group(
    world: World,
    agent: Agent,
    majority_group: int,
    majority_count: int,
    same_group_neighbors: int,
    traits: AgentTraits | None = None,
) -> None:
    if majority_group == world._UNGROUPED or agent.group_id == majority_group:
        return
    if agent.group_cooldown > 0.0:
        return
    if agent.group_id != world._UNGROUPED and same_group_neighbors >= world._config.feedback.group_adoption_guard_min_allies:
        return
    target_size = world._group_sizes.get(majority_group, majority_count)
    size_for_threshold = target_size if target_size > 0 else majority_count
    effective_threshold = max(
        1,
        min(world._config.feedback.group_adoption_neighbor_threshold, max(1, size_for_threshold)),
    )
    if majority_count < effective_threshold:
        return
    base_chance = world._config.feedback.group_adoption_chance
    small_bonus = world._config.feedback.group_adoption_small_group_bonus
    size_for_bonus = max(1, target_size)
    traits = world._clamp_traits(agent.traits) if traits is None else traits
    sociality = max(0.0, traits.sociality)
    loyalty = max(0.1, traits.loyalty)
    adoption_chance = base_chance * (1.0 + small_bonus / size_for_bonus) * sociality
    if agent.group_id != world._UNGROUPED:
        adoption_chance *= 1.0 / loyalty
    adoption_chance = min(1.0, max(0.0, adoption_chance))
    if world._rng.next_float() < adoption_chance:
        set_group(world, agent, majority_group)


def try_split_group(
    world: World,
    agent: Agent,
    same_group_neighbors: int,
    neighbors: List[Agent],
    neighbor_offsets: List[Vector2],
    can_form_groups: bool,
    traits: AgentTraits | None = None,
) -> None:
    if agent.group_id == world._UNGROUPED:
        return
    traits = world._clamp_traits(agent.traits) if traits is None else traits
    if same_group_neighbors < world._config.feedback.group_split_neighbor_threshold:
        return
    effective_stress = agent.stress + same_group_neighbors * world._config.feedback.group_split_size_stress_weight
    if effective_stress < world._config.feedback.group_split_stress_threshold:
        return
    bonus_neighbors = max(0, same_group_neighbors - world._config.feedback.group_split_neighbor_threshold)
    size_bonus = bonus_neighbors * world._config.feedback.group_split_size_bonus_per_neighbor
    base_chance = world._config.feedback.group_split_chance
    split_chance = base_chance + size_bonus
    split_chance = min(world._config.feedback.group_split_chance_max, split_chance, 1.0)
    if split_chance <= 0.0:
        return
    if world._rng.next_float() < split_chance:
        previous_group = agent.group_id
        target_group = world._UNGROUPED
        if (
            can_form_groups
            and world._rng.next_float()
            < min(1.0, world._config.feedback.group_split_new_group_chance * max(0.0, traits.founder))
        ):
            target_group = world._next_group_id
            world._next_group_id += 1
            register_group_base(world, target_group, agent.position)
        set_group(world, agent, target_group)
        if target_group != world._UNGROUPED and can_form_groups:
            recruit_split_neighbors(world, previous_group, target_group, neighbors, neighbor_offsets)
