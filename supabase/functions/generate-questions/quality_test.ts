import { assertEquals } from "https://deno.land/std@0.224.0/assert/mod.ts";
import { balanceAnswerPositions, givesAwayAnswerByLength } from "./quality.ts";
import type { GeneratedQuestion } from "./validation.ts";

/** Deterministic pseudo-random numbers so shuffles are reproducible in tests.
 * Small seeds are spread over the full range first; otherwise the first value of
 * this simple generator is almost identical for neighbouring seeds.
 */
const seeded = (seed: number) => () => {
  seed = (seed * 2654435761) % 4294967296;
  seed = (seed * 1664525 + 1013904223) % 4294967296;
  return seed / 4294967296;
};

const question = (index: number, correctOptionIndex = 0): GeneratedQuestion => ({
  sourceCardId: `card-${index}`,
  question: `Question ${index}?`,
  options: [`Right ${index}`, `Wrong A ${index}`, `Wrong B ${index}`, `Wrong C ${index}`],
  correctOptionIndex,
  explanation: "",
});

Deno.test("spreads correct answers evenly over all four positions", () => {
  const drafts = Array.from({ length: 8 }, (_, index) => question(index));
  const balanced = balanceAnswerPositions(drafts, seeded(7));
  const counts = [0, 0, 0, 0];
  for (const draft of balanced) counts[draft.correctOptionIndex] += 1;
  assertEquals(counts, [2, 2, 2, 2]);
});

Deno.test("keeps the correct answer text and every option when moving positions", () => {
  const drafts = Array.from({ length: 5 }, (_, index) => question(index, index % 4));
  const balanced = balanceAnswerPositions(drafts, seeded(3));
  balanced.forEach((draft, index) => {
    const original = drafts[index];
    assertEquals(draft.sourceCardId, original.sourceCardId);
    assertEquals(draft.question, original.question);
    assertEquals(draft.options[draft.correctOptionIndex], original.options[original.correctOptionIndex]);
    assertEquals([...draft.options].sort(), [...original.options].sort());
  });
});

Deno.test("does not always place a single question's answer first", () => {
  const positions = new Set<number>();
  for (let seed = 1; seed <= 20; seed += 1) {
    positions.add(balanceAnswerPositions([question(1)], seeded(seed))[0].correctOptionIndex);
  }
  assertEquals(positions.size > 1, true);
});

Deno.test("does not change the input questions", () => {
  const drafts = [question(1)];
  balanceAnswerPositions(drafts, seeded(11));
  assertEquals(drafts[0], question(1));
});

Deno.test("flags a correct answer that is clearly longer than every distractor", () => {
  assertEquals(givesAwayAnswerByLength({
    ...question(1),
    options: [
      "Money available today is worth more because it can be invested and earn a return",
      "Money loses value",
      "Interest is fixed",
      "Cash is risk free",
    ],
  }), true);
});

Deno.test("accepts options of similar length", () => {
  assertEquals(givesAwayAnswerByLength({
    ...question(1),
    options: [
      "Money today can earn a return",
      "Money today is always taxed",
      "Money later earns more interest",
      "Money today has no risk at all",
    ],
  }), false);
});

Deno.test("ignores small absolute differences between short options", () => {
  assertEquals(givesAwayAnswerByLength({
    ...question(1),
    options: ["Bond yield", "NPV", "IRR", "WACC"],
  }), false);
});
