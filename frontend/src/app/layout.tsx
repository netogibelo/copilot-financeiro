import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "@/components/layout/Providers";

export const metadata: Metadata = {
  title: "Copilot Financeiro | Gestão Inteligente",
  description: "Plataforma de gestão financeira pessoal com IA",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR" className="dark">
      <body className="antialiased bg-surface-950 text-white">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
