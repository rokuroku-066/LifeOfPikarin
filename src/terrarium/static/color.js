// Utility helpers for the web viewer. Keep these functions free of DOM/Three.js
// dependencies so they remain easy to test in Node.

/**
 * Derive a deterministic hue for a group identifier.
 * Normalizes the value into [0, 360) to keep CSS/Three.js colors stable even
 * for negative or non-finite ids.
 */
export function computeGroupHue(id) {
  const safeId = Number.isFinite(id) ? id : 0;
  const rawHue = (safeId * 47) % 360;
  return (rawHue + 360) % 360;
}
