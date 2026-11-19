import { assertEquals, assertRejects } from "https://deno.land/std@0.224.0/assert/mod.ts";
import { requestQuestionsFromRequesty, requestQuestionsWithRetry } from "./requesty.ts";

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

Deno.test("retries one malformed response and returns the valid replacement", async () => {
  let calls = 0;
  const fakeFetch: typeof fetch = async () => {
    calls += 1;
    const content = calls === 1 ? JSON.stringify({ questions: [] }) : JSON.stringify({
      questions: [{
        sourceCardId: cards[0].id,
        question: "Which statement describes the time value of money?",
        options: ["Money today can earn returns", "Money never changes value", "Inflation is impossible", "Only debt has value"],
        correctOptionIndex: 0,
        explanation: "",
      }],
    });
    return new Response(JSON.stringify({ choices: [{ message: { content } }] }), { status: 200 });
  };
  const drafts = await requestQuestionsWithRetry("test-key", "test-model", cards, fakeFetch);
  assertEquals(calls, 2);
  assertEquals(drafts.length, 1);
});

Deno.test("recovers an omitted source with a targeted follow-up request", async () => {
  const twoCards = [cards[0], { ...cards[0], id: "22222222-2222-4222-8222-222222222222", front: "What is discounting?" }];
  let calls = 0;
  const fakeFetch: typeof fetch = async (_input, init) => {
    calls += 1;
    const sent = JSON.parse(String(init?.body)).messages[1].content;
    const source = JSON.parse(sent).cards;
    const questions = source.length === 2
      ? [
        { sourceCardId: twoCards[0].id, question: "What describes time value?", options: ["A", "B", "C", "D"], correctOptionIndex: 0, explanation: "" },
      ]
      : [
        { sourceCardId: twoCards[1].id, question: "What is discounting?", options: ["A", "B", "C", "D"], correctOptionIndex: 0, explanation: "" },
      ];
    return new Response(JSON.stringify({ choices: [{ message: { content: JSON.stringify({ questions }) } }] }), { status: 200 });
  };
  const drafts = await requestQuestionsWithRetry("test-key", "test-model", twoCards, fakeFetch);
  assertEquals(drafts.map((draft) => draft.sourceCardId), twoCards.map((card) => card.id));
  assertEquals(calls, 3);
});

const reply = (questions: unknown[]) =>
  new Response(JSON.stringify({ choices: [{ message: { content: JSON.stringify({ questions }) } }] }), { status: 200 });

const balancedOptions = ["Money today can earn a return", "Money today is always taxed", "Money later earns more", "Money today has no risk"];
const lengthCueOptions = [
  "Money available today is worth more because it can be invested and earn a return",
  "Money loses value",
  "Interest is fixed",
  "Cash is risk free",
];

Deno.test("requests strict structured JSON output", async () => {
  let format: Record<string, unknown> | undefined;
  const fakeFetch: typeof fetch = async (_input, init) => {
    format = JSON.parse(String(init?.body)).response_format;
    return reply([{ sourceCardId: cards[0].id, question: "Q?", options: balancedOptions, correctOptionIndex: 0, explanation: "" }]);
  };
  await requestQuestionsFromRequesty("test-key", "test-model", cards, fakeFetch);
  assertEquals(format?.type, "json_schema");
  assertEquals((format?.json_schema as { strict?: boolean })?.strict, true);
});

Deno.test("falls back to JSON mode when a model rejects structured output", async () => {
  const formats: string[] = [];
  const fakeFetch: typeof fetch = async (_input, init) => {
    const type = JSON.parse(String(init?.body)).response_format.type;
    formats.push(type);
    if (type === "json_schema") return new Response("unsupported response_format", { status: 400 });
    return reply([{ sourceCardId: cards[0].id, question: "Q?", options: balancedOptions, correctOptionIndex: 0, explanation: "" }]);
  };
  const drafts = await requestQuestionsFromRequesty("test-key", "test-model", cards, fakeFetch);
  assertEquals(formats, ["json_schema", "json_object"]);
  assertEquals(drafts.length, 1);
});

Deno.test("asks once more for options of similar length when the answer stands out", async () => {
  const bodies: Array<{ cards: unknown[]; rewrite?: string }> = [];
  const fakeFetch: typeof fetch = async (_input, init) => {
    const sent = JSON.parse(JSON.parse(String(init?.body)).messages[1].content);
    bodies.push(sent);
    const options = bodies.length === 1 ? lengthCueOptions : balancedOptions;
    return reply([{ sourceCardId: cards[0].id, question: "Which statement is true?", options, correctOptionIndex: 0, explanation: "" }]);
  };
  const drafts = await requestQuestionsWithRetry("test-key", "test-model", cards, fakeFetch);
  assertEquals(bodies.length, 2);
  assertEquals(typeof bodies[1].rewrite, "string");
  assertEquals(drafts[0].options, balancedOptions);
});

Deno.test("keeps the original draft when the length rewrite fails", async () => {
  let calls = 0;
  const fakeFetch: typeof fetch = async () => {
    calls += 1;
    if (calls === 1) {
      return reply([{ sourceCardId: cards[0].id, question: "Which statement is true?", options: lengthCueOptions, correctOptionIndex: 0, explanation: "" }]);
    }
    return new Response("bad request", { status: 400 });
  };
  const drafts = await requestQuestionsWithRetry("test-key", "test-model", cards, fakeFetch);
  assertEquals(drafts[0].options, lengthCueOptions);
});
