// Utility helpers for the web viewer. Keep these functions free of DOM/Three.js
// dependencies so they remain easy to test in Node.

/**
 * Derive a deterministic hue for a group identifier.
 * Anchors the palette on the ungrouped base hue (50°) and rotates from there
 * for group ids while keeping results in [0, 360).
 */
const baseGroupHue = 50;

export function computeGroupHue(id) {
  const safeId = Number.isFinite(id) ? id : -1;
  if (safeId < 0) return baseGroupHue;
  const rawHue = baseGroupHue + ((safeId + 1) * 47) % 360;
  return (rawHue + 360) % 360;
}

function clamp01(value) {
  if (!Number.isFinite(value)) return 0;
  if (value < 0) return 0;
  if (value > 1) return 1;
  return value;
}

/**
 * Map an energy value onto an HSL lightness in [floor, ceiling].
 * Uses a smooth tanh curve so mid-range energies are easy to distinguish while
 * extremes saturate softly instead of clipping.
 */
export function energyToLightness(energy, opts = {}) {
  const floor = opts.floor ?? 0.28;
  const ceiling = opts.ceiling ?? 0.82;
  const mid = opts.mid ?? 12.0;
  const spread = Math.max(1e-3, opts.spread ?? 8.0);
  const safeEnergy = Number.isFinite(energy) ? energy : 0;
  const normalized = Math.tanh((safeEnergy - mid) / spread); // [-1, 1]
  const t = 0.5 + 0.5 * normalized; // [0, 1]
  const lightness = floor + (ceiling - floor) * t;
  return Math.min(ceiling, Math.max(floor, lightness));
}

/**
 * Shrink older agents slightly; returns a multiplier to apply on top of the
 * base size provided by the snapshot. Adults (<= adultAge) stay at 1.0.
 */
export function elderScaleMultiplier(age, opts = {}) {
  const adultAge = Math.max(0.1, opts.adultAge ?? 20.0);
  const maxAge = Math.max(adultAge + 0.1, opts.maxAge ?? 80.0);
  const elderShrink = clamp01(opts.elderShrink ?? 0.18);
  const safeAge = Math.max(0, Number.isFinite(age) ? age : 0);
  const oldness = clamp01((safeAge - adultAge) / (maxAge - adultAge));
  return 1 - elderShrink * Math.pow(oldness, 0.6);
}

/**
 * Estimate reproduction drive (0..1) from energy, age, and behavior state.
 * Assumes default thresholds from the Phase 1 species config but keeps values
 * overridable for other configs.
 */
export function reproductionDesire(energy, age, behaviorState, opts = {}) {
  const reproductionThreshold = opts.reproductionThreshold ?? 12.0;
  const energySoftCap = Math.max(reproductionThreshold + 0.5, opts.energySoftCap ?? 20.0);
  const adultAge = Math.max(0.1, opts.adultAge ?? 20.0);

  const safeEnergy = Number.isFinite(energy) ? energy : 0;
  const safeAge = Math.max(0, Number.isFinite(age) ? age : 0);
  if (safeAge < adultAge) return 0;

  const span = Math.max(1e-3, energySoftCap - reproductionThreshold);
  const energyTerm = clamp01((safeEnergy - reproductionThreshold) / span);
  const stateName = typeof behaviorState === 'string' ? behaviorState.toLowerCase() : '';
  const seekingBoost = stateName === 'seekingmate' ? 0.3 : 0;
  return clamp01(energyTerm + seekingBoost);
}

/**
 * Low-amplitude pulse to add on top of lightness for high reproduction desire.
 * Returns an additive offset (>= 0). Phase may be shifted per-agent to avoid
 * synchronized flashing.
 */
export function pulseLightnessOffset(timeMs, desire, opts = {}) {
  const amplitude = (opts.amplitude ?? 0.08) * clamp01(desire);
  if (amplitude <= 0) return 0;
  const frequencyHz = opts.frequencyHz ?? 1.35;
  const phase = opts.phase ?? 0;
  const omega = frequencyHz * 2 * Math.PI; // radians per second
  const t = (Number.isFinite(timeMs) ? timeMs : 0) / 1000;
  return amplitude * (0.5 + 0.5 * Math.sin(omega * t + phase));
}
