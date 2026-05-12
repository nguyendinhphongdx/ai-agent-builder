"use client";

import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { I18nProvider } from "@/lib/i18n/context";
import { QueryProvider } from "./QueryProvider";
import { SocketProvider } from "./SocketProvider";
import { ThemeProvider } from "./ThemeProvider";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <I18nProvider>
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
    </I18nProvider>
  );
}
