import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Iron Council Client",
  description: "Public match browser for Iron Council"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
