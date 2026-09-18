// @vitest-environment jsdom
import { render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ErrorToast } from "./ErrorToast";

describe("ErrorToast auto-dismiss", () => {
  beforeEach(() => { vi.useFakeTimers(); });
  afterEach(() => { vi.useRealTimers(); });

  it("does not restart the 8s timer when the parent re-renders with a new onDismiss reference but the same message", () => {
    const onDismiss = vi.fn();
    const { rerender } = render(<ErrorToast message="Bad Gateway" onDismiss={onDismiss} />);

    vi.advanceTimersByTime(5000);
    expect(onDismiss).not.toHaveBeenCalled();

    // Simulate an unrelated App re-render: same message, a fresh onDismiss closure (mirroring
    // App.tsx's inline `onDismiss={() => setToast(null)}` on every render).
    rerender(<ErrorToast message="Bad Gateway" onDismiss={() => onDismiss()} />);

    vi.advanceTimersByTime(4000); // total elapsed: 9s
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it("does restart the timer when a genuinely new message arrives", () => {
    const onDismiss = vi.fn();
    const { rerender } = render(<ErrorToast message="Bad Gateway" onDismiss={onDismiss} />);

    vi.advanceTimersByTime(5000);
    expect(onDismiss).not.toHaveBeenCalled();

    rerender(<ErrorToast message="Cannot reach the API." onDismiss={onDismiss} />);

    vi.advanceTimersByTime(5000); // 10s since first message, but only 5s since the new one
    expect(onDismiss).not.toHaveBeenCalled();

    vi.advanceTimersByTime(3000); // 8s since the new message
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });
});
