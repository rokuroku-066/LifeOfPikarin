import assert from 'node:assert/strict';
import test from 'node:test';

import {
  computeGroupHue,
  energyToLightness,
  elderScaleMultiplier,
  reproductionDesire,
  pulseLightnessOffset,
} from '../../src/terrarium/app/static/color.js';

test('returns hue within [0, 360) for typical ids', () => {
  assert.equal(computeGroupHue(0), 0);
  assert.equal(computeGroupHue(1), 47);
  assert.equal(computeGroupHue(2), 94);
  assert.equal(computeGroupHue(8), 16);
});

test('wraps negative ids into the positive range', () => {
  assert.equal(computeGroupHue(-1), 313);
  assert.equal(computeGroupHue(-5), 125);
});

test('normalizes very large ids deterministically', () => {
  assert.equal(computeGroupHue(100), 20);
  assert.equal(computeGroupHue(1000000), computeGroupHue(1000000 + 360));
});

test('falls back to zero hue for non-finite values', () => {
  assert.equal(computeGroupHue(NaN), 0);
  assert.equal(computeGroupHue(Infinity), 0);
});

test('energyToLightness brightens with higher energy', () => {
  const low = energyToLightness(0);
  const mid = energyToLightness(12);
  const high = energyToLightness(30);
  assert.ok(low < mid && mid < high);
  assert.ok(low <= 0.4);
  assert.ok(high >= 0.75);
});

test('elderScaleMultiplier shrinks toward max age', () => {
  assert.equal(elderScaleMultiplier(5), 1);
  const mid = elderScaleMultiplier(50, { adultAge: 20, maxAge: 80, elderShrink: 0.2 });
  const old = elderScaleMultiplier(80, { adultAge: 20, maxAge: 80, elderShrink: 0.2 });
  assert.ok(old < mid);
  assert.ok(old < 0.9 && old > 0.75);
});

test('reproductionDesire zero for juveniles and boosted when seeking', () => {
  assert.equal(reproductionDesire(20, 5, 'Wander'), 0);
  const base = reproductionDesire(14, 25, 'Wander');
  const seeking = reproductionDesire(14, 25, 'SeekingMate');
  assert.ok(seeking > base);
  assert.ok(seeking <= 1);
});

test('pulseLightnessOffset stays within amplitude and uses desire', () => {
  assert.equal(pulseLightnessOffset(0, 0.0), 0);
  const offset = pulseLightnessOffset(250, 1.0, { amplitude: 0.1, frequencyHz: 1.0, phase: 0 });
  assert.ok(offset >= 0);
  assert.ok(offset <= 0.1 + 1e-6);
});
