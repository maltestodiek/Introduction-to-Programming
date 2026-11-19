export const chunks = <T>(values: readonly T[], size: number): T[][] =>
  Array.from({ length: Math.ceil(values.length / size) }, (_, index) =>
    values.slice(index * size, (index + 1) * size)
  );

/** Run `task` for every item with at most `limit` tasks at once, keeping result order.
 * After the first failure no new task starts; running tasks finish before the
 * error is rethrown, so callers can release locks only when all work has stopped.
 */
export async function mapWithConcurrency<T, R>(
  items: readonly T[],
  limit: number,
  task: (item: T, index: number) => Promise<R>,
): Promise<R[]> {
  const results = new Array<R>(items.length);
  let next = 0;
  let failure: { error: unknown } | undefined;

  const worker = async () => {
    while (!failure && next < items.length) {
      const index = next;
      next += 1;
      try {
        results[index] = await task(items[index], index);
      } catch (error) {
        failure ??= { error };
      }
    }
  };

  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, worker));
  if (failure) throw failure.error;
  return results;
}
