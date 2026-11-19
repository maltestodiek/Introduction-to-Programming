export type GeneratedQuestion = {
  sourceCardId: string;
  question: string;
  options: string[];
  correctOptionIndex: number;
  explanation: string;
};

const normalise = (value: string) => value.trim().replace(/\s+/g, " ").toLocaleLowerCase();

export function validateGeneratedQuestions(
  payload: unknown,
  allowedSourceCardIds: readonly string[],
): GeneratedQuestion[] {
  return validateQuestions(payload, allowedSourceCardIds, true);
}

/** Validates well-formed questions without requiring every source to be present.
 * This is used only to recover omitted sources before anything is persisted.
 */
export function validatePartialGeneratedQuestions(
  payload: unknown,
  allowedSourceCardIds: readonly string[],
): GeneratedQuestion[] {
  return validateQuestions(payload, allowedSourceCardIds, false);
}

function validateQuestions(
  payload: unknown,
  allowedSourceCardIds: readonly string[],
  requireEverySource: boolean,
): GeneratedQuestion[] {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    throw new Error("The AI response was not a JSON object.");
  }

  const questions = (payload as Record<string, unknown>).questions;
  if (!Array.isArray(questions)) {
    throw new Error("The AI response did not contain a questions list.");
  }
  if (requireEverySource && questions.length !== allowedSourceCardIds.length) {
    throw new Error(
      `The AI returned ${questions.length} question${questions.length === 1 ? "" : "s"}, but this batch requires exactly ${allowedSourceCardIds.length} (one per selected source card).`,
    );
  }

  const allowed = new Set(allowedSourceCardIds);
  const seen = new Set<string>();

  return questions.map((candidate, index) => {
    if (!candidate || typeof candidate !== "object" || Array.isArray(candidate)) {
      throw new Error(`Question ${index + 1} is not an object.`);
    }

    const value = candidate as Record<string, unknown>;
    const sourceCardId = value.sourceCardId;
    const question = value.question;
    const options = value.options;
    const correctOptionIndex = value.correctOptionIndex;
    const explanation = value.explanation;

    if (typeof sourceCardId !== "string" || !allowed.has(sourceCardId)) {
      throw new Error(`Question ${index + 1} referenced a source card outside this selected batch.`);
    }
    if (seen.has(sourceCardId)) {
      throw new Error(`Question ${index + 1} duplicated a source card already used in this batch.`);
    }
    seen.add(sourceCardId);

    if (typeof question !== "string" || !question.trim()) {
      throw new Error(`Question ${index + 1} has no question text.`);
    }
    if (explanation !== undefined && typeof explanation !== "string") {
      throw new Error(`Question ${index + 1} has an invalid explanation.`);
    }
    if (!Array.isArray(options) || options.length !== 4 || options.some((option) => typeof option !== "string" || !option.trim())) {
      throw new Error(`Question ${index + 1} must have four non-empty options.`);
    }
    const normalisedOptions = options.map((option) => normalise(option));
    if (new Set(normalisedOptions).size !== 4) {
      throw new Error(`Question ${index + 1} has duplicate options.`);
    }
    if (
      typeof correctOptionIndex !== "number" || !Number.isInteger(correctOptionIndex) ||
      correctOptionIndex < 0 || correctOptionIndex > 3
    ) {
      throw new Error(`Question ${index + 1} has an invalid correct option.`);
    }

    return {
      sourceCardId,
      question: question.trim(),
      options: options.map((option) => option.trim()),
      correctOptionIndex,
      explanation: typeof explanation === "string" ? explanation.trim() : "",
    };
  });
}

export function parseRequestyContent(
  content: unknown,
  allowedSourceCardIds: readonly string[],
): GeneratedQuestion[] {
  return parseContent(content, allowedSourceCardIds, true);
}

export function parsePartialRequestyContent(
  content: unknown,
  allowedSourceCardIds: readonly string[],
): GeneratedQuestion[] {
  return parseContent(content, allowedSourceCardIds, false);
}

function parseContent(
  content: unknown,
  allowedSourceCardIds: readonly string[],
  requireEverySource: boolean,
): GeneratedQuestion[] {
  if (typeof content !== "string") {
    throw new Error("The AI response did not contain text.");
  }
  // Some OpenAI-compatible providers wrap otherwise valid JSON in a Markdown
  // code fence even when JSON mode is requested. Accept that transport quirk,
  // while keeping the actual question schema strict below.
  const json = content.trim().replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/, "");
  let payload: unknown;
  try {
    payload = JSON.parse(json);
  } catch {
    throw new Error("The AI response was not valid JSON.");
  }
  return requireEverySource
    ? validateGeneratedQuestions(payload, allowedSourceCardIds)
    : validatePartialGeneratedQuestions(payload, allowedSourceCardIds);
}
