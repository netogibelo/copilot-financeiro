"use client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "react-hot-toast";
import { useState } from "react";

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 1000 * 60 * 2, // 2 minutes
            retry: 1,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: "#1a1d23",
            color: "#e5e7eb",
            border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: "10px",
            fontSize: "14px",
          },
          success: { iconTheme: { primary: "#22c55e", secondary: "#052e16" } },
          error: { iconTheme: { primary: "#f43f5e", secondary: "#fff0f3" } },
        }}
      />
    </QueryClientProvider>
  );
}
