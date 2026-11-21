import {
  parsePartialRequestyContent,
  parseRequestyContent,
  type GeneratedQuestion,
} from "./validation.ts";
import { givesAwayAnswerByLength } from "./quality.ts";

type SourceCard = { id: string; front: string; back: string };
type FetchLike = typeof fetch;
const MAX_ATTEMPTS = 2;

const LENGTH_REWRITE = [
  "In your previous draft the correct option was much longer and more detailed than the others, which gives the answer away.",
  "Write the question again with four options of similar length, detail and style.",
  "The correct option must not be the longest or the only qualified statement.",
].join(" ");

const SYSTEM_PROMPT = [
  "You generate reviewable UniArena multiple-choice question drafts from Anki cards or lecture slides.",
  "Return only one valid JSON object. Do not use Markdown or add commentary.",
  "Use only information supported by the front and back of the source card.",
  "Preserve the source card language. If a card is German, generate German; if English, generate English.",
  "Create exactly one clear, factual question per source card, and return a question for every card.",
  "Use a mixed difficulty level: prefer conceptual understanding, but vary between direct recall and application where the source allows it.",
  "Each question must be self-contained, concise, and unambiguous. Do not use double negatives, trick wording, or reveal the answer in the stem.",
  "Provide exactly four distinct, non-empty answer options. Exactly one must be correct.",
  "Incorrect options must be plausible and closely related to the topic, not nonsense. Never use 'all of the above', 'none of the above', or equivalents.",
  "All four options must have similar length, level of detail and grammatical form. The correct option must not be noticeably longer, more precise or more hedged than the incorrect ones.",
  "Put the correct option first (correctOptionIndex 0); UniArena shuffles the positions afterwards.",
  "Do not invent facts, context, calculations, or definitions that are absent from the source card.",
  "If a card is too incomplete to make a reliable question, still return a source-grounded direct-recall question rather than adding external knowledge.",
  "Do not generate explanations; set explanation to an empty string.",
].join(" ");

/** Strict output schema; the validator below still enforces counts and ranges. */
const QUESTIONS_SCHEMA = {
  type: "json_schema",
  json_schema: {
    name: "uniarena_questions",
    strict: true,
    schema: {
      type: "object",
      additionalProperties: false,
      required: ["questions"],
      properties: {
        questions: {
          type: "array",
          items: {
            type: "object",
            additionalProperties: false,
            required: ["sourceCardId", "question", "options", "correctOptionIndex", "explanation"],
            properties: {
              sourceCardId: { type: "string" },
              question: { type: "string" },
              options: { type: "array", items: { type: "string" } },
              correctOptionIndex: { type: "integer" },
              explanation: { type: "string" },
            },
          },
        },
      },
    },
  },
};
const JSON_MODE = { type: "json_object" };

class IncompleteBatchError extends Error {
  constructor(message: string, readonly drafts: GeneratedQuestion[]) {
    super(message);
    this.name = "IncompleteBatchError";
  }
}

const canRetry = (error: unknown) => {
  const message = error instanceof Error ? error.message : "";
  return message.startsWith("The AI response") ||
    message.startsWith("The AI returned") ||
    message.startsWith("Question ") ||
    message.includes("The AI provider took too long") ||
    /HTTP (429|5\d\d)/.test(message);
};

export async function requestQuestionsFromRequesty(
  apiKey: string,
  model: string,
  cards: SourceCard[],
  fetcher: FetchLike,
  rewrite?: string,
): Promise<GeneratedQuestion[]> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 45_000);
  const started = Date.now();

  try {
    let response: Response | undefined;
    let format = QUESTIONS_SCHEMA as Record<string, unknown>;
    for (const candidate of [QUESTIONS_SCHEMA, JSON_MODE]) {
      format = candidate;
      response = await fetcher("https://router.requesty.ai/v1/chat/completions", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${apiKey}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          model,
          response_format: candidate,
          messages: [
            { role: "system", content: SYSTEM_PROMPT },
            {
              role: "user",
              content: JSON.stringify({
                task: "Create exactly one UniArena multiple-choice draft for every source card.",
                ...(rewrite ? { rewrite } : {}),
                responseShape: {
                  questions: [{
                    sourceCardId: "input card id",
                    question: "question text",
                    options: ["correct option", "incorrect option", "incorrect option", "incorrect option"],
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
      // Some routed models do not support strict structured output and answer 400;
      // they still support plain JSON mode, which the validator checks just as strictly.
      if (response.status !== 400 || candidate === JSON_MODE) break;
    }

    if (!response!.ok) {
      throw new Error(`The AI provider could not generate questions (HTTP ${response!.status}).`);
    }
    const body = await response!.json() as {
      choices?: Array<{ message?: { content?: unknown } }>;
      usage?: { prompt_tokens?: number; completion_tokens?: number };
    };
    // Metrics only: never log card text, generated questions or credentials.
    console.log("Requesty batch", {
      model,
      cards: cards.length,
      format: format.type,
      rewrite: Boolean(rewrite),
      ms: Date.now() - started,
      promptTokens: body?.usage?.prompt_tokens,
      completionTokens: body?.usage?.completion_tokens,
    });
    const content = body?.choices?.[0]?.message?.content;
    const sourceCardIds = cards.map((card) => card.id);
    try {
      return parseRequestyContent(content, sourceCardIds);
    } catch (error) {
      // A provider may omit one otherwise valid question. Keep no partial data,
      // but retain the valid in-memory drafts so the retry layer can ask only
      // for the missing sources.
      try {
        const partial = parsePartialRequestyContent(content, sourceCardIds);
        if (partial.length < cards.length) {
          throw new IncompleteBatchError(
            error instanceof Error ? error.message : "The AI response was incomplete.",
            partial,
          );
        }
      } catch (partialError) {
        if (partialError instanceof IncompleteBatchError) throw partialError;
      }
      throw error;
    }
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("The AI provider took too long to respond.");
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

/** Ask once more for questions whose correct option stands out by length.
 * This is a soft quality gate: if the rewrite fails or is no better, the
 * original valid draft is kept, because the student reviews every draft anyway.
 */
async function rewriteLengthCues(
  apiKey: string,
  model: string,
  cards: SourceCard[],
  drafts: GeneratedQuestion[],
  fetcher: FetchLike,
): Promise<GeneratedQuestion[]> {
  const flagged = new Set(drafts.filter(givesAwayAnswerByLength).map((draft) => draft.sourceCardId));
  if (flagged.size === 0) return drafts;
  try {
    const rewritten = await requestQuestionsFromRequesty(
      apiKey,
      model,
      cards.filter((card) => flagged.has(card.id)),
      fetcher,
      LENGTH_REWRITE,
    );
    const better = new Map(
      rewritten.filter((draft) => !givesAwayAnswerByLength(draft)).map((draft) => [draft.sourceCardId, draft]),
    );
    return drafts.map((draft) => better.get(draft.sourceCardId) ?? draft);
  } catch {
    return drafts;
  }
}

/** Retry a malformed or temporarily unavailable provider response once.
 * Each attempt validates before it is returned, so callers never save partial drafts.
 */
export async function requestQuestionsWithRetry(
  apiKey: string,
  model: string,
  cards: SourceCard[],
  fetcher: FetchLike,
): Promise<GeneratedQuestion[]> {
  const drafts = await requestCompleteBatch(apiKey, model, cards, fetcher);
  return await rewriteLengthCues(apiKey, model, cards, drafts, fetcher);
}

async function requestCompleteBatch(
  apiKey: string,
  model: string,
  cards: SourceCard[],
  fetcher: FetchLike,
): Promise<GeneratedQuestion[]> {
  let lastError: unknown;
  let incomplete: IncompleteBatchError | undefined;
  for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt += 1) {
    try {
      return await requestQuestionsFromRequesty(apiKey, model, cards, fetcher);
    } catch (error) {
      lastError = error;
      if (error instanceof IncompleteBatchError) incomplete = error;
      if (attempt === MAX_ATTEMPTS || !canRetry(error)) break;
    }
  }
  if (incomplete && incomplete.drafts.length > 0 && incomplete.drafts.length < cards.length) {
    const returned = new Map(incomplete.drafts.map((draft) => [draft.sourceCardId, draft]));
    const missing = cards.filter((card) => !returned.has(card.id));
    try {
      const recovered = await requestCompleteBatch(apiKey, model, missing, fetcher);
      for (const draft of recovered) returned.set(draft.sourceCardId, draft);
      return cards.map((card) => returned.get(card.id)!).filter(Boolean);
    } catch (recoveryError) {
      const recoveryMessage = recoveryError instanceof Error ? recoveryError.message : "unknown recovery error";
      throw new Error(`The AI omitted ${missing.length} source card${missing.length === 1 ? "" : "s"} from a batch of ${cards.length}, and recovery failed. ${recoveryMessage}`);
    }
  }
  const message = lastError instanceof Error ? lastError.message : "The AI provider returned an unknown error.";
  throw new Error(`Generation failed for a batch of ${cards.length} source cards after ${MAX_ATTEMPTS} attempts. ${message}`);
}
