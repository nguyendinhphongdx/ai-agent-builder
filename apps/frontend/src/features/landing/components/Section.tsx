import { cn } from "@/lib/utils";

interface SectionProps {
  id?: string;
  eyebrow?: string;
  title?: React.ReactNode;
  description?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  bordered?: boolean;
  muted?: boolean;
}

export function Section({
  id,
  eyebrow,
  title,
  description,
  children,
  className,
  bordered = true,
  muted = false,
}: SectionProps) {
  return (
    <section
      id={id}
      className={cn(
        bordered && "border-t border-border",
        muted && "bg-muted/30",
        className,
      )}
    >
      <div className="mx-auto max-w-7xl px-6 py-24 md:py-32 lg:px-8">
        {(eyebrow || title || description) && (
          <div className="mx-auto mb-16 max-w-2xl text-center">
            {eyebrow && (
              <p className="mb-3 text-sm font-semibold text-primary">{eyebrow}</p>
            )}
            {title && (
              <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
                {title}
              </h2>
            )}
            {description && (
              <p className="mt-4 text-base leading-relaxed text-muted-foreground">
                {description}
              </p>
            )}
          </div>
        )}
        {children}
      </div>
    </section>
  );
}
