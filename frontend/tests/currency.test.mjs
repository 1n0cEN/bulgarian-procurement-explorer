import { test } from "node:test";
import assert from "node:assert/strict";
import { bgnToEur, displayMoney } from "../lib/currency.ts";

test("official full rate and BNB rounding example", () => {
  assert.equal(bgnToEur("1.70"), "0.87");
  assert.equal(bgnToEur("1.95583"), "1.00");
  assert.equal(bgnToEur("0.977915"), "0.50");
  assert.equal(bgnToEur("0.00977915"), "0.01");
  assert.equal(bgnToEur("0.00977914"), "0.00");
  assert.equal(bgnToEur("0"), "0.00");
  assert.equal(bgnToEur("5367011.18"), "2744109.24");
  assert.equal(bgnToEur("19558300000000000"), "10000000000000000.00");
});

test("historical source and missing amounts remain distinguishable", () => {
  assert.equal(
    displayMoney("1.70", "BGN"),
    "0.87 EUR equivalent (source: 1.70 BGN)",
  );
  assert.equal(displayMoney("2.00", "EUR"), "2 EUR");
  assert.equal(displayMoney(null, "BGN"), "Not reported");
  assert.throws(() => bgnToEur("-1"));
});
