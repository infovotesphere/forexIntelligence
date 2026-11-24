export function startVisiblePolling(refresh: () => Promise<void>, intervalMs: number): () => void {
  let active = true;
  let inFlight = false;
  let lastStartedAt = 0;

  const poll = () => {
    const now = Date.now();
    if (
      !active
      || document.visibilityState !== "visible"
      || inFlight
      || now - lastStartedAt < 1000
    ) return;

    lastStartedAt = now;
    inFlight = true;
    void refresh().finally(() => { inFlight = false; });
  };

  const timer = window.setInterval(poll, intervalMs);
  document.addEventListener("visibilitychange", poll);
  window.addEventListener("focus", poll);
  poll();

  return () => {
    active = false;
    window.clearInterval(timer);
    document.removeEventListener("visibilitychange", poll);
    window.removeEventListener("focus", poll);
  };
}
