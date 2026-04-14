import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { ClerkProvider } from "@clerk/nextjs";
import { Toaster } from "@/components/ui/sonner";
import { QueryProvider } from "@/components/providers/QueryProvider";
import { ThemeProvider } from "@/components/providers/ThemeProvider";
import { ErrorBoundary } from "@/components/common/ErrorBoundary";
import { ConnectionGuard } from "@/components/common/ConnectionGuard";
import { themeScript } from "@/lib/theme-script";
import { I18nProvider } from "@/components/providers/I18nProvider";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Open Notebook",
  description: "Privacy-focused research and knowledge management",
};

// Clerk is optional — wrap only when a valid publishable key is provided at runtime.
// This allows the Docker image to build without Clerk credentials.
const clerkKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;
const isClerkEnabled = clerkKey && clerkKey.startsWith("pk_");

function MaybeClerkProvider({ children }: { children: React.ReactNode }) {
  if (isClerkEnabled) {
    return <ClerkProvider publishableKey={clerkKey}>{children}</ClerkProvider>;
  }
  return <>{children}</>;
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <MaybeClerkProvider>
      <html lang="en" suppressHydrationWarning>
        <head>
          <script dangerouslySetInnerHTML={{ __html: themeScript }} />
        </head>
        <body className={inter.className}>
          <ErrorBoundary>
            <ThemeProvider>
              <QueryProvider>
                <I18nProvider>
                  <ConnectionGuard>
                    {children}
                    <Toaster />
                  </ConnectionGuard>
                </I18nProvider>
              </QueryProvider>
            </ThemeProvider>
          </ErrorBoundary>
        </body>
      </html>
    </MaybeClerkProvider>
  );
}
