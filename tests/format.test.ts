import assert from "node:assert/strict";
import { test } from "node:test";
import {
  formatDistance,
  formatDuration,
  formatPace,
  paceSecondsPerKm,
  usernameFromSeed,
} from "../lib/format";

test("formats distance with two decimals", () => {
  assert.equal(formatDistance(8.01), "8.01 KM");
  assert.equal(formatDistance(12.42), "12.42 KM");
});

test("formats duration with hours", () => {
  assert.equal(formatDuration(3741), "01:02:21");
});

test("formats pace from distance and time", () => {
  assert.equal(formatPace(12.42, 3741), "5:01 /KM");
  assert.ok(paceSecondsPerKm(12.42, 3741) > 300);
});

test("builds a username from an email seed", () => {
  assert.equal(usernameFromSeed("Joana.Run"), "joanarun");
  assert.equal(usernameFromSeed("x"), "runx");
  assert.equal(usernameFromSeed("admin"), "run_admin");
});
