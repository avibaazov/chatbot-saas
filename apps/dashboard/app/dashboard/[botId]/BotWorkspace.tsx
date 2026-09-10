"use client";

import type { ReactNode } from "react";
import { useState, useSyncExternalStore } from "react";
import { useFormStatus } from "react-dom";

const emptySubscribe = () => () => {};

type FontSize = "small" | "medium" | "large";

// px values mirror FONT_SIZE_PX in packages/widget/src/widget.ts so the preview matches
// the real widget.
const FONT_SIZES: { value: FontSize; label: string; px: number }[] = [
  { value: "small", label: "Small", px: 13 },
  { value: "medium", label: "Medium", px: 14 },
  { value: "large", label: "Large", px: 16 },
];

const HEX = /^#[0-9a-fA-F]{6}$/;

const fieldClass =
  "w-full rounded-lg border border-border bg-transparent px-3 py-2 text-sm outline-none transition-colors focus:border-accent";

function SaveButton({ dirty }: { dirty: boolean }) {
  const { pending } = useFormStatus();
  // `dirty` comes from client-only state, so gating on it during SSR / first paint risks a
  // hydration mismatch. Stay on a stable button until mounted, then reflect it.
  const mounted = useSyncExternalStore(
    emptySubscribe,
    () => true,
    () => false,
  );
  const showClean = mounted && !dirty;

  return (
    <div className="flex items-center gap-3">
      <button
        type="submit"
        disabled={pending || showClean}
        className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-foreground transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
      >
        {pending ? "Saving…" : "Save changes"}
      </button>
      {showClean && (
        <span className="flex items-center gap-1.5 text-xs text-muted">
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            aria-hidden
          >
            <path
              d="m5 13 4 4L19 7"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          All changes saved
        </span>
      )}
    </div>
  );
}

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-xs font-medium text-foreground">{label}</span>
      {children}
      {hint && <span className="text-xs text-muted">{hint}</span>}
    </div>
  );
}

export function BotWorkspace({
  action,
  initial,
  sources,
  tester,
}: {
  action: (formData: FormData) => void;
  initial: { display_name: string; primary_color: string; font_size: string };
  sources: ReactNode;
  tester: ReactNode;
}) {
  const initialColor = HEX.test(initial.primary_color)
    ? initial.primary_color
    : "#4f46e5";
  const initialFont = (FONT_SIZES.find((f) => f.value === initial.font_size)
    ?.value ?? "medium") as FontSize;

  const [displayName, setDisplayName] = useState(initial.display_name);
  const [color, setColor] = useState(initialColor);
  const [fontSize, setFontSize] = useState<FontSize>(initialFont);

  const colorValid = HEX.test(color);
  const previewColor = colorValid ? color : initialColor;
  const previewPx = FONT_SIZES.find((f) => f.value === fontSize)!.px;
  const previewName = displayName.trim() || "Assistant";

  const dirty =
    displayName.trim() !== initial.display_name ||
    (colorValid && color.toLowerCase() !== initialColor.toLowerCase()) ||
    fontSize !== initialFont;

  return (
    <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
      {/* Left: settings */}
      <div className="space-y-6">
        {sources}

        <section className="overflow-hidden rounded-2xl border border-border bg-surface">
          <div className="border-b border-border px-6 py-4">
            <h2 className="text-sm font-semibold">Appearance</h2>
            <p className="mt-0.5 text-xs text-muted">
              How the widget looks on your site — the preview updates as you
              type.
            </p>
          </div>

          <form action={action} className="space-y-5 px-6 py-5">
            <Field label="Display name" hint="Shown in the chat window header.">
              <input
                name="display_name"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                maxLength={40}
                required
                className={fieldClass}
              />
            </Field>

            <Field
              label="Accent color"
              hint={
                colorValid
                  ? undefined
                  : "Enter a 6-digit hex color, e.g. #4F46E5."
              }
            >
              <div className="flex items-center gap-2">
                <label
                  className="relative h-10 w-10 shrink-0 cursor-pointer overflow-hidden rounded-lg border border-border shadow-sm"
                  style={{ backgroundColor: previewColor }}
                >
                  <input
                    type="color"
                    value={previewColor}
                    onChange={(e) => setColor(e.target.value)}
                    className="absolute inset-0 h-full w-full cursor-pointer opacity-0"
                    aria-label="Pick accent color"
                  />
                </label>
                <input
                  name="primary_color"
                  value={color}
                  onChange={(e) => setColor(e.target.value)}
                  spellCheck={false}
                  aria-invalid={!colorValid}
                  className={`${fieldClass} font-mono uppercase ${
                    colorValid ? "" : "border-red-500 focus:border-red-500"
                  }`}
                />
              </div>
            </Field>

            <Field label="Font size">
              <input type="hidden" name="font_size" value={fontSize} />
              <div className="grid grid-cols-3 gap-1.5 rounded-lg border border-border p-1">
                {FONT_SIZES.map((f) => {
                  const active = fontSize === f.value;
                  return (
                    <button
                      key={f.value}
                      type="button"
                      onClick={() => setFontSize(f.value)}
                      aria-pressed={active}
                      className={`flex flex-col items-center gap-0.5 rounded-md py-2 transition-colors ${
                        active
                          ? "bg-accent text-accent-foreground"
                          : "text-muted hover:bg-surface-muted hover:text-foreground"
                      }`}
                    >
                      <span
                        style={{ fontSize: f.px }}
                        className="font-semibold leading-none"
                      >
                        Aa
                      </span>
                      <span className="text-[10px] font-medium">{f.label}</span>
                    </button>
                  );
                })}
              </div>
            </Field>

            <div className="border-t border-border pt-5">
              <SaveButton dirty={dirty} />
            </div>
          </form>
        </section>
      </div>

      {/* Right rail: live preview + real widget test */}
      <div className="space-y-4 lg:sticky lg:top-24">
        <div>
          <div className="mb-2 flex items-baseline justify-between">
            <span className="text-xs font-medium text-foreground">
              Live preview
            </span>
            {dirty && (
              <span className="text-[11px] font-medium text-amber-600 dark:text-amber-400">
                Unsaved changes
              </span>
            )}
          </div>

          <div className="rounded-2xl border border-border bg-surface-muted p-5">
            {/* Chat card — internals mirror the real widget (packages/widget/src/widget.ts):
                plain-text header, light bot bubbles, 10px bubble radius, input row. */}
            <div
              className="mx-auto flex h-[360px] w-full max-w-[300px] flex-col overflow-hidden rounded-xl bg-white text-[#111]"
              style={{
                boxShadow: "0 12px 40px rgba(0,0,0,0.28)",
                fontFamily: "system-ui, sans-serif",
              }}
            >
              <div
                className="flex items-center gap-2 px-4 py-3 text-white"
                style={{ backgroundColor: previewColor }}
              >
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-white/20 text-[11px] font-bold">
                  {previewName[0]?.toUpperCase() ?? "A"}
                </span>
                <span className="flex-1 truncate text-sm font-semibold">
                  {previewName}
                </span>
                <span className="text-white/70">×</span>
              </div>

              <div
                className="flex flex-1 flex-col gap-2 overflow-y-auto bg-[#f7f7f8] p-3"
                style={{ fontSize: previewPx, lineHeight: 1.45 }}
              >
                <span className="max-w-[85%] self-start rounded-[10px] bg-[#ececee] px-3 py-2">
                  Hi! How can I help you today?
                </span>
                <span
                  className="max-w-[85%] self-end rounded-[10px] px-3 py-2 text-white"
                  style={{ backgroundColor: previewColor }}
                >
                  What are your support hours?
                </span>
                <span className="max-w-[85%] self-start rounded-[10px] bg-[#ececee] px-3 py-2">
                  We&rsquo;re open Monday to Friday, 9am&ndash;6pm. Anything
                  else I can help with?
                </span>
                <span
                  className="max-w-[85%] self-end rounded-[10px] px-3 py-2 text-white"
                  style={{ backgroundColor: previewColor }}
                >
                  Do you ship internationally?
                </span>
                <span className="max-w-[85%] self-start rounded-[10px] bg-[#ececee] px-3 py-2">
                  Yes — worldwide, with tracked delivery.
                </span>
              </div>

              <div
                className="flex items-center gap-2 border-t border-black/10 px-3 py-2.5"
                style={{ fontSize: previewPx }}
              >
                <span className="flex-1 text-[#9a9a9a]">
                  Ask a question&hellip;
                </span>
                <span
                  className="rounded-full px-3 py-1 text-xs font-semibold text-white"
                  style={{ backgroundColor: previewColor }}
                >
                  Send
                </span>
              </div>
            </div>
          </div>
        </div>

        {tester}
      </div>
    </div>
  );
}
