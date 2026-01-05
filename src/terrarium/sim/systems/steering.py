from __future__ import annotations

import math
from typing import List, TYPE_CHECKING

from pygame.math import Vector2

from ..core.agent import Agent, AgentState, AgentTraits
from ..utils.math2d import ZERO, _clamp_length_xy, _clamp_length_xy_f, _safe_normalize_xy
from . import fields

if TYPE_CHECKING:
    from ..core.world import World


def compute_desired_velocity(
    world: World,
    agent: Agent,
    neighbors: List[Agent],
    neighbor_offsets: List[Vector2],
    base_speed: float,
    return_sensed: bool = False,
    neighbor_dist_sq: List[float] | None = None,
    traits: AgentTraits | None = None,
    danger_present: bool | None = None,
    base_cell_key: tuple[int, int] | None = None,
) -> tuple[Vector2, bool] | Vector2:
    desired_x = 0.0
    desired_y = 0.0
    flee_vector = Vector2()
    sensed_danger = False
    traits = world._clamp_traits(agent.traits) if traits is None else traits
    species = world._config.species
    feedback = world._config.feedback
    environment = world._config.environment
    sociality = max(0.0, traits.sociality)
    territoriality = max(0.0, traits.territoriality)
    dist_sq_list = neighbor_dist_sq
    if dist_sq_list is None or len(dist_sq_list) != len(neighbor_offsets):
        dist_sq_list = world._neighbor_dist_sq
        dist_sq_list.clear()
        for offset in neighbor_offsets:
            dist_sq_list.append(offset.x * offset.x + offset.y * offset.y)

    if danger_present is None:
        danger_present = world._environment.has_danger()
    if base_cell_key is None:
        base_cell_key = fields.cell_key(world, agent.position)
    danger_level = 0.0
    danger_gradient = Vector2()
    if danger_present:
        danger_level = world._environment.sample_danger(base_cell_key)
        danger_gradient = fields.danger_gradient(world, agent.position, base_cell_key)
    if danger_level > 0.1:
        sensed_danger = True
        if danger_gradient.length_squared() < 1e-4:
            danger_gradient = world._rng.next_unit_circle()
        if danger_gradient.length_squared() > 1e-12:
            danger_gradient.normalize_ip()
            flee_scale = base_speed * min(1.0, danger_level)
            flee_vector.x -= danger_gradient.x * flee_scale
            flee_vector.y -= danger_gradient.y * flee_scale

    for other, dist_sq, offset in zip(neighbors, dist_sq_list, neighbor_offsets):
        groups_differ = (
            agent.group_id != world._UNGROUPED
            and other.group_id != world._UNGROUPED
            and other.group_id != agent.group_id
        )
        if groups_differ and dist_sq < 4.0:
            if dist_sq > 1e-12:
                inv_len = 1.0 / math.sqrt(dist_sq)
                flee_vector.x -= offset.x * inv_len * base_speed
                flee_vector.y -= offset.y * inv_len * base_speed
                sensed_danger = True

    if flee_vector.length_squared() > 1e-3:
        agent.state = AgentState.FLEE
        flee_strength = 1.0
        if danger_present:
            flee_strength = max(flee_strength, min(1.0, danger_level))
        desired_x = flee_vector.x
        desired_y = flee_vector.y
        if agent.group_id != world._UNGROUPED and neighbors:
            cohesion_bias = group_cohesion(world, agent, neighbors, neighbor_offsets, dist_sq_list)
            alignment_bias = alignment(world, agent, neighbors)
            separation_bias = separation(world, agent, neighbors, neighbor_offsets, dist_sq_list)
            keep = max(0.0, 1.0 - 0.7 * flee_strength)
            desired_x += cohesion_bias.x * base_speed * 0.8 * keep
            desired_y += cohesion_bias.y * base_speed * 0.8 * keep
            desired_x += alignment_bias.x * base_speed * 0.5 * keep
            desired_y += alignment_bias.y * base_speed * 0.5 * keep
            desired_x += separation_bias.x * base_speed * 0.7
            desired_y += separation_bias.y * base_speed * 0.7
        boundary_bias, _boundary_proximity = boundary_avoidance(world, agent.position)
        boundary_scale = base_speed * world._config.boundary_avoidance_weight
        desired_x += boundary_bias.x * boundary_scale
        desired_y += boundary_bias.y * boundary_scale
        desired = Vector2(desired_x, desired_y)
        return (desired, sensed_danger) if return_sensed else desired

    food_here = world._environment.sample_food(base_cell_key)
    food_gradient = Vector2()
    pheromone_gradient = (
        ZERO
        if agent.group_id == world._UNGROUPED
        else fields.pheromone_gradient(world, agent.group_id, agent.position, base_cell_key)
    )
    grouped = agent.group_id != world._UNGROUPED
    if neighbors:
        personal_space_bias = (
            personal_space(world, neighbor_offsets, dist_sq_list)
            if feedback.personal_space_weight > 0.0 and feedback.personal_space_radius > 1e-6
            else ZERO
        )
        separation_bias = (
            separation(world, agent, neighbors, neighbor_offsets, dist_sq_list)
            if feedback.ally_separation_weight > 0.0
            or feedback.other_group_separation_weight > 0.0
            or feedback.min_separation_weight > 0.0
            else ZERO
        )
        intergroup_bias = (
            intergroup_avoidance(world, agent, neighbors, neighbor_offsets, dist_sq_list)
            if grouped
            and territoriality > 1e-6
            and feedback.other_group_avoid_weight > 0.0
            and feedback.other_group_avoid_radius > 1e-6
            else ZERO
        )
        group_cohesion_bias = (
            group_cohesion(world, agent, neighbors, neighbor_offsets, dist_sq_list)
            if grouped
            and sociality > 1e-6
            and feedback.group_cohesion_weight > 0.0
            and feedback.ally_cohesion_weight > 0.0
            and feedback.group_cohesion_radius > 1e-6
            else ZERO
        )
        alignment_bias = alignment(world, agent, neighbors) if grouped and sociality > 1e-6 else ZERO
    else:
        personal_space_bias = ZERO
        separation_bias = ZERO
        intergroup_bias = ZERO
        group_cohesion_bias = ZERO
        alignment_bias = ZERO
    group_seek_bias_vec = (
        group_seek_bias(world, agent, neighbors, neighbor_offsets, dist_sq_list)
        if not grouped and feedback.group_seek_weight > 0.0 and feedback.group_seek_radius > 1e-6
        else ZERO
    )
    base_bias = (
        group_base_attraction(world, agent)
        if grouped and feedback.group_base_attraction_weight > 0.0
        else ZERO
    )

    pheromone_bias_x = 0.0
    pheromone_bias_y = 0.0
    pheromone_len_sq = pheromone_gradient.length_squared()
    if pheromone_len_sq > 1e-4:
        inv_len = 1.0 / math.sqrt(pheromone_len_sq)
        pheromone_bias_x = pheromone_gradient.x * inv_len
        pheromone_bias_y = pheromone_gradient.y * inv_len
    danger_bias_x = 0.0
    danger_bias_y = 0.0
    danger_len_sq = danger_gradient.length_squared()
    if danger_len_sq > 1e-4:
        inv_len = 1.0 / math.sqrt(danger_len_sq)
        danger_bias_x = danger_gradient.x * inv_len
        danger_bias_y = danger_gradient.y * inv_len

    needs_food = agent.energy < species.reproduction_energy_threshold * 0.6 or food_here > environment.food_per_cell * 0.5
    if needs_food:
        food_gradient = fields.food_gradient(world, agent.position, base_cell_key)
        if food_gradient.length_squared() > 1e-4:
            food_gradient.normalize_ip()
        agent.state = AgentState.SEEKING_FOOD
        food_scale = base_speed * 0.4
        desired_x += food_gradient.x * food_scale
        desired_y += food_gradient.y * food_scale
        wander = wander_direction(world, agent)
        wander_scale = base_speed * 0.25
        desired_x += wander.x * wander_scale
        desired_y += wander.y * wander_scale
    elif agent.energy > species.reproduction_energy_threshold and agent.age > species.adult_age:
        agent.state = AgentState.SEEKING_MATE
        cohesion_all = cohesion(neighbor_offsets)
        cohesion_scale = base_speed * 0.8
        desired_x += cohesion_all.x * cohesion_scale
        desired_y += cohesion_all.y * cohesion_scale
        pheromone_scale = base_speed * 0.25
        desired_x += pheromone_bias_x * pheromone_scale
        desired_y += pheromone_bias_y * pheromone_scale
    else:
        agent.state = AgentState.WANDER
        wander = wander_direction(world, agent)
        wander_scale = base_speed * species.wander_jitter
        desired_x += wander.x * wander_scale
        desired_y += wander.y * wander_scale
        pheromone_scale = base_speed * 0.15
        desired_x += pheromone_bias_x * pheromone_scale
        desired_y += pheromone_bias_y * pheromone_scale

    personal_scale = base_speed * feedback.personal_space_weight
    desired_x += personal_space_bias.x * personal_scale
    desired_y += personal_space_bias.y * personal_scale
    intergroup_scale = base_speed * feedback.other_group_avoid_weight * territoriality
    desired_x += intergroup_bias.x * intergroup_scale
    desired_y += intergroup_bias.y * intergroup_scale
    seek_scale = base_speed * feedback.group_seek_weight
    desired_x += group_seek_bias_vec.x * seek_scale
    desired_y += group_seek_bias_vec.y * seek_scale
    separation_scale = base_speed * 1.4
    desired_x += separation_bias.x * separation_scale
    desired_y += separation_bias.y * separation_scale
    alignment_scale = base_speed * 0.3 * sociality
    desired_x += alignment_bias.x * alignment_scale
    desired_y += alignment_bias.y * alignment_scale
    cohesion_scale = base_speed * feedback.group_cohesion_weight * feedback.ally_cohesion_weight * sociality
    desired_x += group_cohesion_bias.x * cohesion_scale
    desired_y += group_cohesion_bias.y * cohesion_scale
    base_scale = base_speed * feedback.group_base_attraction_weight
    desired_x += base_bias.x * base_scale
    desired_y += base_bias.y * base_scale
    boundary_bias, boundary_proximity = boundary_avoidance(world, agent.position)
    boundary_scale = base_speed * world._config.boundary_avoidance_weight
    desired_x += boundary_bias.x * boundary_scale
    desired_y += boundary_bias.y * boundary_scale
    boundary_len_sq = boundary_bias.x * boundary_bias.x + boundary_bias.y * boundary_bias.y
    desired_len_sq = desired_x * desired_x + desired_y * desired_y
    if boundary_proximity > 0.0 and boundary_len_sq > 1e-8 and desired_len_sq > 1e-8:
        turn = min(1.0, boundary_proximity * world._config.boundary_turn_weight)
        inward_x = boundary_bias.x * base_speed
        inward_y = boundary_bias.y * base_speed
        desired_x += (inward_x - desired_x) * turn
        desired_y += (inward_y - desired_y) * turn
    danger_scale = base_speed * 0.2
    desired_x -= danger_bias_x * danger_scale
    desired_y -= danger_bias_y * danger_scale
    desired = Vector2(desired_x, desired_y)
    if return_sensed:
        return desired, sensed_danger
    return desired


def separation(
    world: World,
    agent: Agent,
    neighbors: List[Agent],
    neighbor_vectors: List[Vector2],
    neighbor_dist_sq: List[float] | None = None,
) -> Vector2:
    if not neighbor_vectors:
        return ZERO
    feedback = world._config.feedback
    dist_sq_list = neighbor_dist_sq
    if dist_sq_list is None or len(dist_sq_list) != len(neighbor_vectors):
        dist_sq_list = [offset.length_squared() for offset in neighbor_vectors]
    accum_x = 0.0
    accum_y = 0.0
    closest_dist_sq = float("inf")
    min_sep = max(0.0, float(feedback.min_separation_distance))
    min_sep_sq = min_sep * min_sep
    min_sep_weight = max(0.0, float(feedback.min_separation_weight))
    ally_weight = float(feedback.ally_separation_weight)
    other_weight = float(feedback.other_group_separation_weight)
    for other, offset, raw_dist_sq in zip(neighbors, neighbor_vectors, dist_sq_list):
        if raw_dist_sq < closest_dist_sq:
            closest_dist_sq = raw_dist_sq
        dist_sq = max(raw_dist_sq, 0.1)
        same_group = agent.group_id != world._UNGROUPED and other.group_id == agent.group_id
        weight = ally_weight if same_group else other_weight
        inv_dist_sq = 1.0 / dist_sq
        accum_x -= offset.x * inv_dist_sq * weight
        accum_y -= offset.y * inv_dist_sq * weight
        if min_sep_weight > 0.0 and min_sep_sq > 1e-12 and raw_dist_sq > 1e-12 and raw_dist_sq < min_sep_sq:
            strength = (min_sep_sq - raw_dist_sq) / min_sep_sq
            strength = max(0.0, min(1.0, strength))
            dist = math.sqrt(raw_dist_sq)
            inv_len = 1.0 / dist
            scale = (strength * strength) * min_sep_weight
            accum_x -= offset.x * inv_len * scale
            accum_y -= offset.y * inv_len * scale
    if accum_x * accum_x + accum_y * accum_y < 1e-12:
        return ZERO
    if closest_dist_sq < float("inf") and closest_dist_sq > 1e-12 and min_sep > 1e-6:
        closest = math.sqrt(closest_dist_sq)
        if closest < min_sep:
            scale = min(4.0, max(1.0, min_sep / max(closest, 1e-4)))
            accum_x *= scale
            accum_y *= scale
    return _clamp_length_xy(accum_x, accum_y, 3.5)


def resolve_overlap(
    world: World,
    position: Vector2,
    neighbor_offsets: List[Vector2],
    neighbor_dist_sq: List[float] | None = None,
) -> Vector2:
    min_sep = max(0.0, float(world._config.feedback.min_separation_distance))
    if min_sep <= 1e-6 or not neighbor_offsets:
        return position
    dist_sq_list = neighbor_dist_sq
    if dist_sq_list is None or len(dist_sq_list) != len(neighbor_offsets):
        dist_sq_list = [offset.length_squared() for offset in neighbor_offsets]
    min_sep_sq = min_sep * min_sep
    correction_x = 0.0
    correction_y = 0.0
    count = 0
    for offset, dist_sq in zip(neighbor_offsets, dist_sq_list):
        if dist_sq <= 1e-12 or dist_sq >= min_sep_sq:
            continue
        dist = math.sqrt(dist_sq)
        overlap = min_sep - dist
        if overlap <= 0.0:
            continue
        inv_len = 1.0 / dist
        correction_x -= offset.x * inv_len * overlap
        correction_y -= offset.y * inv_len * overlap
        count += 1
    if count == 0:
        return position
    inv = 1.0 / count
    correction_x *= inv
    correction_y *= inv
    correction_x, correction_y = _clamp_length_xy_f(correction_x, correction_y, min_sep * 0.5)
    position.update(position.x + correction_x, position.y + correction_y)
    return position


def alignment(world: World, agent: Agent, neighbors: List[Agent]) -> Vector2:
    if agent.group_id == world._UNGROUPED:
        return ZERO
    sum_x = 0.0
    sum_y = 0.0
    count = 0
    for other in neighbors:
        if other.group_id != agent.group_id:
            continue
        velocity = other.velocity
        sum_x += velocity.x
        sum_y += velocity.y
        count += 1
    if count == 0:
        return ZERO
    inv = 1.0 / count
    return _safe_normalize_xy(sum_x * inv, sum_y * inv)


def group_seek_bias(
    world: World,
    agent: Agent,
    neighbors: List[Agent],
    neighbor_offsets: List[Vector2],
    neighbor_dist_sq: List[float] | None = None,
) -> Vector2:
    if agent.group_id != world._UNGROUPED:
        return ZERO
    feedback = world._config.feedback
    radius = max(0.0, float(feedback.group_seek_radius))
    if radius <= 1e-6:
        return ZERO
    radius_sq = radius * radius
    accum_x = 0.0
    accum_y = 0.0
    weight_sum = 0.0
    base_bias_x = 0.0
    base_bias_y = 0.0
    dist_sq_list = neighbor_dist_sq
    if dist_sq_list is None or len(dist_sq_list) != len(neighbor_offsets):
        dist_sq_list = [offset.length_squared() for offset in neighbor_offsets]
    if world._group_bases:
        nearest_dx = 0.0
        nearest_dy = 0.0
        nearest_dist_sq = radius_sq
        for base in world._group_bases.values():
            dx = base.x - agent.position.x
            dy = base.y - agent.position.y
            dist_sq = dx * dx + dy * dy
            if dist_sq <= 1e-12 or dist_sq > radius_sq:
                continue
            if dist_sq < nearest_dist_sq:
                nearest_dx = dx
                nearest_dy = dy
                nearest_dist_sq = dist_sq
        if nearest_dist_sq < radius_sq:
            dist = math.sqrt(nearest_dist_sq)
            falloff = 1.0 - min(1.0, dist / radius)
            if falloff > 1e-6 and dist > 1e-12:
                inv_len = 1.0 / dist
                base_bias_x = nearest_dx * inv_len * falloff
                base_bias_y = nearest_dy * inv_len * falloff
    for other, offset, dist_sq in zip(neighbors, neighbor_offsets, dist_sq_list):
        if other.group_id == world._UNGROUPED:
            continue
        if dist_sq <= 1e-12 or dist_sq > radius_sq:
            continue
        dist = math.sqrt(dist_sq)
        falloff = 1.0 - min(1.0, dist / radius)
        if falloff <= 1e-5:
            continue
        accum_x += offset.x * falloff
        accum_y += offset.y * falloff
        weight_sum += falloff
    if weight_sum <= 1e-6:
        return _safe_normalize_xy(base_bias_x, base_bias_y)
    inv = 1.0 / weight_sum
    blended_x = accum_x * inv
    blended_y = accum_y * inv
    if base_bias_x * base_bias_x + base_bias_y * base_bias_y > 1e-12:
        blended_x += base_bias_x
        blended_y += base_bias_y
    return _safe_normalize_xy(blended_x, blended_y)


def group_cohesion(
    world: World,
    agent: Agent,
    neighbors: List[Agent],
    neighbor_offsets: List[Vector2],
    neighbor_dist_sq: List[float] | None = None,
) -> Vector2:
    if agent.group_id == world._UNGROUPED:
        return ZERO
    feedback = world._config.feedback
    cohesion_radius_sq = feedback.group_cohesion_radius * feedback.group_cohesion_radius
    sum_x = 0.0
    sum_y = 0.0
    count = 0
    dist_sq_list = neighbor_dist_sq
    if dist_sq_list is None or len(dist_sq_list) != len(neighbor_offsets):
        dist_sq_list = [offset.length_squared() for offset in neighbor_offsets]
    for other, offset, dist_sq in zip(neighbors, neighbor_offsets, dist_sq_list):
        if other.group_id != agent.group_id:
            continue
        if dist_sq > cohesion_radius_sq:
            continue
        sum_x += offset.x
        sum_y += offset.y
        count += 1
    if count == 0:
        return ZERO
    inv = 1.0 / count
    return _safe_normalize_xy(sum_x * inv, sum_y * inv)


def group_base_attraction(world: World, agent: Agent) -> Vector2:
    if agent.group_id == world._UNGROUPED:
        return ZERO
    base = world._group_bases.get(agent.group_id)
    if base is None:
        return ZERO
    feedback = world._config.feedback
    to_base = base - agent.position
    dist_sq = to_base.length_squared()
    if dist_sq <= 1e-12:
        return ZERO
    dead_zone = max(0.0, float(feedback.group_base_dead_zone))
    dead_sq = dead_zone * dead_zone
    if dist_sq <= dead_sq:
        return ZERO
    soft_radius = max(dead_zone, float(feedback.group_base_soft_radius))
    soft_sq = soft_radius * soft_radius
    strength = 1.0
    if soft_radius > dead_zone and dist_sq < soft_sq:
        denom = max(1e-12, soft_sq - dead_sq)
        t = (dist_sq - dead_sq) / denom
        t = max(0.0, min(1.0, t))
        strength = t * t
    if to_base.length_squared() < 1e-12:
        return ZERO
    to_base.normalize_ip()
    to_base *= strength
    return to_base


def personal_space(
    world: World, neighbor_offsets: List[Vector2], neighbor_dist_sq: List[float] | None = None
) -> Vector2:
    feedback = world._config.feedback
    radius = feedback.personal_space_radius
    if radius <= 1e-6 or not neighbor_offsets:
        return ZERO
    radius_sq = radius * radius
    dist_sq_list = neighbor_dist_sq
    if dist_sq_list is None or len(dist_sq_list) != len(neighbor_offsets):
        dist_sq_list = [offset.length_squared() for offset in neighbor_offsets]
    accum_x = 0.0
    accum_y = 0.0
    count = 0
    for offset, dist_sq in zip(neighbor_offsets, dist_sq_list):
        if dist_sq <= 1e-9 or dist_sq > radius_sq:
            continue
        dist = math.sqrt(dist_sq)
        if dist <= 1e-12:
            continue
        strength = 1.0 - min(1.0, dist / radius)
        inv_len = 1.0 / dist
        accum_x -= offset.x * inv_len * strength
        accum_y -= offset.y * inv_len * strength
        count += 1
    if count == 0:
        return ZERO
    inv = 1.0 / count
    return _safe_normalize_xy(accum_x * inv, accum_y * inv)


def intergroup_avoidance(
    world: World,
    agent: Agent,
    neighbors: List[Agent],
    neighbor_offsets: List[Vector2],
    neighbor_dist_sq: List[float] | None = None,
) -> Vector2:
    feedback = world._config.feedback
    radius = feedback.other_group_avoid_radius
    if radius <= 1e-6:
        return ZERO
    radius_sq = radius * radius
    dist_sq_list = neighbor_dist_sq
    if dist_sq_list is None or len(dist_sq_list) != len(neighbor_offsets):
        dist_sq_list = [offset.length_squared() for offset in neighbor_offsets]
    accum_x = 0.0
    accum_y = 0.0
    count = 0
    for other, offset, dist_sq in zip(neighbors, neighbor_offsets, dist_sq_list):
        if agent.group_id == world._UNGROUPED or other.group_id == world._UNGROUPED:
            continue
        if other.group_id == agent.group_id:
            continue
        if dist_sq <= 1e-9 or dist_sq > radius_sq:
            continue
        dist = math.sqrt(dist_sq)
        if dist <= 1e-12:
            continue
        falloff = 1.0 - min(1.0, dist / radius)
        if falloff <= 1e-5:
            continue
        inv_len = 1.0 / dist
        accum_x -= offset.x * inv_len * falloff
        accum_y -= offset.y * inv_len * falloff
        count += 1
    if count == 0:
        return ZERO
    inv = 1.0 / count
    return _safe_normalize_xy(accum_x * inv, accum_y * inv)


def wander_direction(world: World, agent: Agent) -> Vector2:
    refresh = max(1e-4, world._config.species.wander_refresh_seconds)
    if agent.wander_time <= 0.0 or agent.wander_dir.length_squared() < 1e-10:
        agent.wander_dir = world._rng.next_unit_circle()
        agent.wander_time = refresh
    else:
        agent.wander_time -= world._config.time_step
    return agent.wander_dir


def boundary_avoidance(world: World, position: Vector2) -> tuple[Vector2, float]:
    margin = world._config.boundary_margin
    size = world._config.world_size
    if margin <= 1e-6 or size <= 0.0:
        return ZERO, 0.0
    x = position.x
    y = position.y
    if margin <= x <= size - margin and margin <= y <= size - margin:
        return ZERO, 0.0

    push_x = 0.0
    push_y = 0.0
    if x < margin:
        push_x += 1.0 - (x / margin)
    elif x > size - margin:
        push_x -= 1.0 - ((size - x) / margin)
    if y < margin:
        push_y += 1.0 - (y / margin)
    elif y > size - margin:
        push_y -= 1.0 - ((size - y) / margin)

    proximity_x = 1.0 - min(x, size - x) / margin
    proximity_y = 1.0 - min(y, size - y) / margin
    if proximity_x < 0.0:
        proximity_x = 0.0
    if proximity_y < 0.0:
        proximity_y = 0.0
    proximity = min(1.0, max(proximity_x, proximity_y))

    push_len_sq = push_x * push_x + push_y * push_y
    if push_len_sq < 1e-8 or proximity <= 0.0:
        return ZERO, 0.0

    strength = proximity * (0.4 + 0.6 * proximity)
    inv_len = 1.0 / math.sqrt(push_len_sq)
    return Vector2(push_x * inv_len * strength, push_y * inv_len * strength), proximity


def cohesion(neighbor_vectors: List[Vector2]) -> Vector2:
    if not neighbor_vectors:
        return ZERO
    sum_x = 0.0
    sum_y = 0.0
    for offset in neighbor_vectors:
        sum_x += offset.x
        sum_y += offset.y
    inv = 1.0 / len(neighbor_vectors)
    return _safe_normalize_xy(sum_x * inv, sum_y * inv)
