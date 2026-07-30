import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/components/AuthProvider";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const BASE_URL = "https://crypto.tanzhongyan.com";

export const metadata: Metadata = {
  metadataBase: new URL(BASE_URL),
  title: {
    default: "Yorkshire Crypto Exchange - Secure Fiat-to-Crypto Trading",
    template: "%s | Yorkshire Crypto Exchange",
  },
  description:
    "Secure and efficient fiat-to-crypto transactions, wallet management, and trade execution built on a modern microservices architecture.",
  alternates: {
    canonical: BASE_URL,
  },
  openGraph: {
    type: "website",
    url: BASE_URL,
    siteName: "Yorkshire Crypto Exchange",
    title: "Yorkshire Crypto Exchange - Secure Fiat-to-Crypto Trading",
    description:
      "Secure and efficient fiat-to-crypto transactions, wallet management, and trade execution.",
  },
  twitter: {
    card: "summary_large_image",
    title: "Yorkshire Crypto Exchange - Secure Fiat-to-Crypto Trading",
    description:
      "Secure and efficient fiat-to-crypto transactions, wallet management, and trade execution.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <AuthProvider>
          {" "}
          {/* AuthProvider must wrap your entire app */}
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
