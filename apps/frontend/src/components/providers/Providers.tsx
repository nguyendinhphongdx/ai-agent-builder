"use client";

import { QueryProvider } from "./QueryProvider";
import { ThemeProvider } from "./ThemeProvider";
import { SocketProvider } from "./SocketProvider";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Toaster } from "@/components/ui/sonner";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <QueryProvider>
      <ThemeProvider>
        <TooltipProvider>
          <SocketProvider>
            {children}
            <Toaster />
          </SocketProvider>
        </TooltipProvider>
      </ThemeProvider>
    </QueryProvider>
  );
}
