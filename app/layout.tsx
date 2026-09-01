import type { Metadata } from "next";
import { Bebas_Neue, DM_Sans } from "next/font/google";
import "@/styles/globals.css";

const display = Bebas_Neue({
  weight: "400",
  subsets: ["latin"],
  variable: "--font-display-loaded",
});

const body = DM_Sans({
  subsets: ["latin"],
  variable: "--font-body-loaded",
});

export const metadata: Metadata = {
  title: "PULSE",
  description: "Find your pace. Find your people.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${display.variable} ${body.variable} ${body.className}`}>
        {children}
      </body>
    </html>
  );
}
