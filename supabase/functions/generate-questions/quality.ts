import type { GeneratedQuestion } from "./validation.ts";

type Random = () => number;

const shuffled = <T>(values: readonly T[], random: Random): T[] => {
  const copy = [...values];
  for (let index = copy.length - 1; index > 0; index -= 1) {
    const swap = Math.floor(random() * (index + 1));
    [copy[index], copy[swap]] = [copy[swap], copy[index]];
  }
  return copy;
};

/** Move each correct answer to a server-chosen position.
 * Language models strongly prefer the first option, so the model's own order is
 * never trusted: positions are spread evenly over A-D for the whole request and
 * the distractors are shuffled into the remaining slots.
 */
export function balanceAnswerPositions(
  questions: readonly GeneratedQuestion[],
  random: Random = Math.random,
): GeneratedQuestion[] {
  const offset = Math.floor(random() * 4);
  const targets = shuffled(questions.map((_, index) => (index + offset) % 4), random);
  return questions.map((question, index) => {
    const correct = question.options[question.correctOptionIndex];
    const distractors = shuffled(
      question.options.filter((_, optionIndex) => optionIndex !== question.correctOptionIndex),
      random,
    );
    const target = targets[index];
    const options = [...distractors.slice(0, target), correct, ...distractors.slice(target)];
    return { ...question, options, correctOptionIndex: target };
  });
}

/** True when the correct option can be guessed because it is much longer than the rest.
 * The answer must be the longest option, at least 1.5x the average distractor and
 * at least 12 characters longer than the longest distractor, so short terms such
 * as "NPV" versus "Bond yield" are not flagged.
 */
export function givesAwayAnswerByLength(question: GeneratedQuestion): boolean {
  const correct = question.options[question.correctOptionIndex].length;
  const distractors = question.options
    .filter((_, index) => index !== question.correctOptionIndex)
    .map((option) => option.length);
  const longest = Math.max(...distractors);
  const average = distractors.reduce((sum, length) => sum + length, 0) / distractors.length;
  return correct > longest && correct >= average * 1.5 && correct - longest >= 12;
}
