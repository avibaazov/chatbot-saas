import { ClerkProvider, Show, SignInButton, SignUpButton, UserButton } from "@clerk/nextjs";
import Link from "next/link";
import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: "Askbox — train a chatbot on your content, embed it anywhere",
    template: "%s · Askbox",
  },
  description:
    "Upload your docs, get a chatbot that answers from them, and drop it on any website with one script tag.",
};

function Logo() {
  return (
    <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight">
      <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-accent text-accent-foreground">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path
            d="M4 5.5A2.5 2.5 0 0 1 6.5 3h11A2.5 2.5 0 0 1 20 5.5v8A2.5 2.5 0 0 1 17.5 16H9l-4 4v-4H6.5A2.5 2.5 0 0 1 4 13.5z"
            fill="currentColor"
          />
        </svg>
      </span>
      Askbox
    </Link>
  );
}

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-background text-foreground">
        <ClerkProvider>
          <header className="sticky top-0 z-40 border-b border-border bg-background/80 backdrop-blur">
            <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-3.5">
              <Logo />
              <div className="flex items-center gap-3 text-sm">
                <Show when="signed-in">
                  <Link
                    href="/dashboard"
                    className="rounded-lg px-3 py-1.5 font-medium text-muted transition-colors hover:text-foreground"
                  >
                    Dashboard
                  </Link>
                  <UserButton />
                </Show>
                <Show when="signed-out">
                  <SignInButton mode="modal">
                    <button className="rounded-lg px-3 py-1.5 font-medium text-muted transition-colors hover:text-foreground">
                      Sign in
                    </button>
                  </SignInButton>
                  <SignUpButton mode="modal">
                    <button className="rounded-lg bg-accent px-3.5 py-1.5 font-medium text-accent-foreground transition-opacity hover:opacity-90">
                      Get started
                    </button>
                  </SignUpButton>
                </Show>
              </div>
            </div>
          </header>

          <div className="flex flex-1 flex-col">{children}</div>

          <footer className="border-t border-border">
            <div className="mx-auto flex w-full max-w-6xl flex-col items-center justify-between gap-2 px-6 py-6 text-sm text-muted sm:flex-row">
              <span>© {new Date().getFullYear()} Askbox</span>
              <span>Built with Next.js · FastAPI · MongoDB Atlas</span>
            </div>
          </footer>
        </ClerkProvider>
      </body>
    </html>
  );
}
