import { assertEquals, assertRejects } from "https://deno.land/std@0.224.0/assert/mod.ts";
import { requestQuestionsFromRequesty } from "./requesty.ts";

const cards = [{
  id: "11111111-1111-4111-8111-111111111111",
  front: "What is the time value of money?",
  back: "Money available now is worth more than the same amount later.",
}];

Deno.test("uses a simulated Requesty response and sends only source-card text", async () => {
  let requestBody: Record<string, unknown> | undefined;
  const fakeFetch: typeof fetch = async (_input, init) => {
    requestBody = JSON.parse(String(init?.body));
    return new Response(JSON.stringify({
      choices: [{
        message: {
          content: JSON.stringify({
            questions: [{
              sourceCardId: cards[0].id,
              question: "Which statement describes the time value of money?",
              options: ["Money today can earn returns", "Money never changes value", "Inflation is impossible", "Only debt has value"],
              correctOptionIndex: 0,
              explanation: "Money today can be invested.",
            }],
          }),
        },
      }],
    }), { status: 200 });
  };

  const drafts = await requestQuestionsFromRequesty("test-key", "test-model", cards, fakeFetch);
  assertEquals(drafts.length, 1);
  const messages = requestBody?.messages as Array<{ content: string }>;
  assertEquals(messages.some((message) => message.content.includes(cards[0].front)), true);
  assertEquals(messages.some((message) => message.content.includes("test-key")), false);
});

Deno.test("does not accept a simulated provider failure", async () => {
  const fakeFetch: typeof fetch = async () => new Response("unavailable", { status: 503 });
  await assertRejects(
    () => requestQuestionsFromRequesty("test-key", "test-model", cards, fakeFetch),
    Error,
    "could not generate",
  );
});
