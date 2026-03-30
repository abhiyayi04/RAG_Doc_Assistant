/**
 * Three softly pulsing dots with staggered timing.
 * Inherits color from the parent via `bg-current`.
 */
export default function LoadingDots() {
  return (
    <span className="inline-flex items-center gap-1" aria-hidden>
      <span className="block h-1.5 w-1.5 rounded-full bg-current animate-pulse" />
      <span className="block h-1.5 w-1.5 rounded-full bg-current animate-pulse [animation-delay:0.2s]" />
      <span className="block h-1.5 w-1.5 rounded-full bg-current animate-pulse [animation-delay:0.4s]" />
    </span>
  );
}
