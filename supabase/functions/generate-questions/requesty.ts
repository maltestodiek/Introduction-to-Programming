import {
  parseRequestyContent,
  type GeneratedQuestion,
} from "./validation.ts";

type SourceCard = { id: string; front: string; back: string };
type FetchLike = typeof fetch;

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
            content: "Return only a valid JSON object. Do not use Markdown.",
          },
          {
            role: "user",
            content: JSON.stringify({
              task: "Create exactly one factual multiple-choice question for every source card.",
              requirements: {
                responseShape: "{ questions: [{ sourceCardId, question, options, correctOptionIndex, explanation }] }",
                options: "exactly four distinct, non-empty strings",
                correctOptionIndex: "integer from 0 through 3",
                sourceCardId: "must match the input card",
              },
              cards,
            }),
          },
        ],
      }),
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new Error("The AI provider could not generate questions.");
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
