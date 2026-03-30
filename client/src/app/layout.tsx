import type { Metadata } from "next";
import "./globals.css";
import { AppShell } from "../components/navigation/app-shell";
import { SessionProvider } from "../components/session/session-provider";

export const metadata: Metadata = {
  title: "Iron Council Client",
  description: "Client session bootstrap and public match browser for Iron Council"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <SessionProvider>
          <AppShell>{children}</AppShell>
        </SessionProvider>
      </body>
    </html>
  );
}
