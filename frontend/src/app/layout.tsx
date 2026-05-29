import "./globals.css";
import type { ReactNode } from "react";

export const metadata = {
  title: "ADLO Terminal",
  description: "African Debt Liquidity Oracle — Macro & Credit Risk Engine",
  icons: {
    icon: "/favicon.svg",
  },
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
