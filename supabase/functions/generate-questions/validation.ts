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
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    throw new Error("The AI response was not a JSON object.");
  }

  const questions = (payload as Record<string, unknown>).questions;
  if (!Array.isArray(questions) || questions.length !== allowedSourceCardIds.length) {
    throw new Error("The AI response did not contain exactly one question per source card.");
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

    if (typeof sourceCardId !== "string" || !allowed.has(sourceCardId) || seen.has(sourceCardId)) {
      throw new Error(`Question ${index + 1} has an invalid source card.`);
    }
    seen.add(sourceCardId);

    if (typeof question !== "string" || !question.trim()) {
      throw new Error(`Question ${index + 1} has no question text.`);
    }
    if (typeof explanation !== "string" || !explanation.trim()) {
      throw new Error(`Question ${index + 1} has no explanation.`);
    }
    if (!Array.isArray(options) || options.length !== 4 || options.some((option) => typeof option !== "string" || !option.trim())) {
      throw new Error(`Question ${index + 1} must have four non-empty options.`);
    }
    const normalisedOptions = options.map((option) => normalise(option));
    if (new Set(normalisedOptions).size !== 4) {
      throw new Error(`Question ${index + 1} has duplicate options.`);
    }
    if (!Number.isInteger(correctOptionIndex) || correctOptionIndex < 0 || correctOptionIndex > 3) {
      throw new Error(`Question ${index + 1} has an invalid correct option.`);
    }

    return {
      sourceCardId,
      question: question.trim(),
      options: options.map((option) => option.trim()),
      correctOptionIndex,
      explanation: explanation.trim(),
    };
  });
}

export function parseRequestyContent(
  content: unknown,
  allowedSourceCardIds: readonly string[],
): GeneratedQuestion[] {
  if (typeof content !== "string") {
    throw new Error("The AI response did not contain text.");
  }
  let payload: unknown;
  try {
    payload = JSON.parse(content);
  } catch {
    throw new Error("The AI response was not valid JSON.");
  }
  return validateGeneratedQuestions(payload, allowedSourceCardIds);
}
