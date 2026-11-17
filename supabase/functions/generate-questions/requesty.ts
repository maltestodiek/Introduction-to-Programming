import {
  parseRequestyContent,
  type GeneratedQuestion,
} from "./validation.ts";

type SourceCard = { id: string; front: string; back: string };
type FetchLike = typeof fetch;
const MAX_ATTEMPTS = 2;

const canRetry = (error: unknown) => {
  const message = error instanceof Error ? error.message : "";
  return message.startsWith("The AI response") ||
    message.startsWith("Question ") ||
    message.includes("The AI provider took too long") ||
    /HTTP (429|5\d\d)/.test(message);
};

export async function requestQuestionsFromRequesty(
  apiKey: string,
  model: string,
  cards: SourceCard[],
  fetcher: FetchLike = fetch,
): Promise<GeneratedQuestion[]> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 45_000);

  try {
    const response = await fetcher("https://router.requesty.ai/v1/chat/completions", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model,
        response_format: { type: "json_object" },
        messages: [
          {
            role: "system",
            content: [
              "You generate reviewable StudyDuel multiple-choice question drafts from Anki cards.",
              "Return only one valid JSON object. Do not use Markdown or add commentary.",
              "Use only information supported by the front and back of the source card.",
              "Preserve the source card language. If a card is German, generate German; if English, generate English.",
              "Create exactly one clear, factual question per source card.",
              "Use a mixed difficulty level: prefer conceptual understanding, but vary between direct recall and application where the source allows it.",
              "Each question must be self-contained, concise, and unambiguous. Do not use double negatives, trick wording, or reveal the answer in the stem.",
              "Provide exactly four distinct, non-empty answer options. Exactly one must be correct.",
              "Incorrect options must be plausible and closely related to the topic, not nonsense. Never use 'all of the above', 'none of the above', or equivalents.",
              "Vary the correct option position across questions instead of repeatedly using the same index.",
              "Do not invent facts, context, calculations, or definitions that are absent from the source card.",
              "If a card is too incomplete to make a reliable question, still return a source-grounded direct-recall question rather than adding external knowledge.",
              "Do not generate explanations; set explanation to an empty string.",
            ].join(" "),
          },
          {
            role: "user",
            content: JSON.stringify({
              task: "Create exactly one StudyDuel multiple-choice draft for every source card.",
              responseShape: {
                questions: [{
                  sourceCardId: "input card id",
                  question: "question text",
                  options: ["option 1", "option 2", "option 3", "option 4"],
                  correctOptionIndex: 0,
                  explanation: "",
                }],
              },
              cards,
            }),
          },
        ],
      }),
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new Error(`The AI provider could not generate questions (HTTP ${response.status}).`);
    }
    const body: unknown = await response.json();
    const content = (body as { choices?: Array<{ message?: { content?: unknown } }> })
      ?.choices?.[0]?.message?.content;
    return parseRequestyContent(content, cards.map((card) => card.id));
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("The AI provider took too long to respond.");
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

/** Retry a malformed or temporarily unavailable provider response once.
 * Each attempt validates before it is returned, so callers never save partial drafts.
 */
export async function requestQuestionsWithRetry(
  apiKey: string,
  model: string,
  cards: SourceCard[],
  fetcher: FetchLike = fetch,
): Promise<GeneratedQuestion[]> {
  let lastError: unknown;
  for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt += 1) {
    try {
      return await requestQuestionsFromRequesty(apiKey, model, cards, fetcher);
    } catch (error) {
      lastError = error;
      if (attempt === MAX_ATTEMPTS || !canRetry(error)) break;
    }
  }
  const message = lastError instanceof Error ? lastError.message : "The AI provider returned an unknown error.";
  throw new Error(`Generation failed for a batch of ${cards.length} source cards after ${MAX_ATTEMPTS} attempts. ${message}`);
}
