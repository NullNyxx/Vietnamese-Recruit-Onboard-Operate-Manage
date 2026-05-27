import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Providers } from "@/components/providers";
import { Toaster } from "@/components/ui/sonner";
import "./globals.css";

const inter = Inter({
  subsets: ["latin", "latin-ext", "vietnamese"],
  variable: "--font-inter",
  weight: ["300", "400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "Vroom HR",
  description: "Nền tảng quản lý nhân sự thông minh cho doanh nghiệp Việt Nam",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="vi" suppressHydrationWarning className="dark">
      <body
        className={`${inter.variable} font-sans antialiased`}
        style={{
          fontFamily: "var(--font-inter), ui-sans-serif, system-ui, sans-serif",
        }}
      >
        <Providers>
          {children}
          <Toaster
            position="bottom-right"
            richColors
            closeButton
            visibleToasts={5}
          />
        </Providers>
      </body>
    </html>
  );
}
