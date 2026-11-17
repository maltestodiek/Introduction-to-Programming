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
