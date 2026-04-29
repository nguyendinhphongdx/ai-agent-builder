"use client";

import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";

interface RevealProps {
  children: React.ReactNode;
  delay?: number;
  className?: string;
  as?: "div" | "section" | "li" | "article";
}

/**
 * Wraps content so it animates in only when scrolled into view. Avoids the
 * "everything fired on load" feel of static animation classes.
 */
export function Reveal({ children, delay = 0, className, as: Tag = "div" }: RevealProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [shown, setShown] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setShown(true);
          obs.disconnect();
        }
      },
      { rootMargin: "0px 0px -10% 0px", threshold: 0.05 },
    );
    obs.observe(node);
    return () => obs.disconnect();
  }, []);

  return (
    <Tag
      ref={ref as never}
      style={shown ? { animationDelay: `${delay}ms` } : undefined}
      className={cn(
        "transition-opacity",
        shown ? "animate-fade-up" : "opacity-0 translate-y-4",
        className,
      )}
    >
      {children}
    </Tag>
  );
}
