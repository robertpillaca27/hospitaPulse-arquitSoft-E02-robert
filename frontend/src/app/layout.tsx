import type { Metadata } from "next";
import type { ReactNode } from "react";

import HelpChatbot from "@/components/help-chatbot";
import SessionExpiration from "@/components/session-expiration";

import "./globals.css";

export const metadata: Metadata = {
  title: "HospitaPulse",
  description: "Gestión del clima organizacional del Hospital Regional.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="es">
      <body>
        {children}
        <SessionExpiration />
        <HelpChatbot />
      </body>
    </html>
  );
}
