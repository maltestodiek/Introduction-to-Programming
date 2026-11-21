// Provider tests stay offline even if a developer runs the suite with -A.
export function offlineTest(name: string, fn: () => void | Promise<void>) {
  Deno.test({ name, permissions: "none", fn });
}
