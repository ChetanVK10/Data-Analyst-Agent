import { User } from "lucide-react";

export function UserMessage({ text }: { text: string }) {
  return (
    <div className="flex justify-end">
      <div className="flex max-w-2xl items-start gap-3">
        <div className="rounded-2xl rounded-tr-md border border-primary/30 bg-primary/10 px-4 py-3 text-sm leading-relaxed text-foreground">
          {text}
        </div>
        <div className="grid h-8 w-8 shrink-0 place-items-center rounded-full border border-border bg-secondary">
          <User className="h-4 w-4 text-muted-foreground" />
        </div>
      </div>
    </div>
  );
}