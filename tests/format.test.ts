import assert from "node:assert/strict";
import { test } from "node:test";
import {
  formatDistance,
  formatDuration,
  formatPace,
  paceSecondsPerKm,
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
