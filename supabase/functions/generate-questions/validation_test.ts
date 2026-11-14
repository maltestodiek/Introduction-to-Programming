import { assertEquals, assertThrows } from "https://deno.land/std@0.224.0/assert/mod.ts";
import { parseRequestyContent, validateGeneratedQuestions } from "./validation.ts";

const sourceIds = [
  "11111111-1111-4111-8111-111111111111",
  "22222222-2222-4222-8222-222222222222",
];

const valid = {
  questions: sourceIds.map((sourceCardId, index) => ({
    sourceCardId,
    question: `Question ${index + 1}?`,
    options: ["One", "Two", "Three", "Four"],
    correctOptionIndex: index,
    explanation: "This is the correct answer.",
  })),
};

Deno.test("accepts one valid question for every requested source card", () => {
  const drafts = validateGeneratedQuestions(valid, sourceIds);
  assertEquals(drafts.length, 2);
  assertEquals(drafts[0].options.length, 4);
});

Deno.test("rejects malformed Requesty JSON without a provider call", () => {
  assertThrows(
    () => parseRequestyContent("{not json}", sourceIds),
    Error,
    "not valid JSON",
  );
});

Deno.test("rejects duplicate options and unknown source IDs", () => {
  const duplicate = structuredClone(valid);
  duplicate.questions[0].options = ["One", " one ", "Three", "Four"];
  assertThrows(() => validateGeneratedQuestions(duplicate, sourceIds), Error, "duplicate options");

  const foreign = structuredClone(valid);
  foreign.questions[1].sourceCardId = "33333333-3333-4333-8333-333333333333";
  assertThrows(() => validateGeneratedQuestions(foreign, sourceIds), Error, "invalid source card");
});
