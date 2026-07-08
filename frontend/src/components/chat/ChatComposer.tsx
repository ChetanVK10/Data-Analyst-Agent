import { ArrowUp, Loader2, Sparkles } from "lucide-react";
import { useState, useRef, useEffect, useCallback } from "react";

interface ChatComposerProps {
  onSubmit?: (v: string) => void;
  disabled?: boolean;
  model?: string;
}

export function ChatComposer({ onSubmit, disabled, model }: ChatComposerProps) {
  const [v, setV] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea on content change
  const resize = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 160) + "px";
  }, []);

  useEffect(() => {
    resize();
  }, [v, resize]);

  // Auto-focus when disabled transitions to false (response complete)
  useEffect(() => {
    if (!disabled) {
      textareaRef.current?.focus();
    }
  }, [disabled]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = v.trim();
    if (!trimmed || disabled) return;
    onSubmit?.(trimmed);
    setV("");
    // Reset height after clear
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="glass-card rounded-2xl p-2 shadow-[var(--shadow-elegant)]"
    >
      <div className="flex items-end gap-2">
        <textarea
          ref={textareaRef}
          value={v}
          onChange={(e) => setV(e.target.value)}
          rows={1}
          placeholder="Ask anything about your dataset…"
          className="scrollbar-thin max-h-40 min-h-[36px] flex-1 resize-none border-0 bg-transparent px-2 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
          disabled={disabled}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSubmit(e as any);
            }
          }}
        />
        <div className="flex items-center gap-1.5 pb-1 pr-1">
          <span className="hidden items-center gap-1 rounded-md border border-border px-1.5 py-1 text-[10px] text-muted-foreground sm:inline-flex">
            <Sparkles className="h-3 w-3 text-primary" />
            {model || "Claude 3.5 Sonnet"}
          </span>
          <button
            type="submit"
            disabled={disabled || !v.trim()}
            className="grid h-9 w-9 place-items-center rounded-xl bg-[image:var(--gradient-primary)] text-primary-foreground shadow-[var(--shadow-glow)] transition-transform hover:scale-105 active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:scale-100"
            aria-label="Send"
          >
            {disabled ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowUp className="h-4 w-4" />}
          </button>
        </div>
      </div>
    </form>
  );
}