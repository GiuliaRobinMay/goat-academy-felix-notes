import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Felix's Notes Archive | GOAT Academy",
  description:
    "The full archive of Felix's weekly market notes — searchable, with every original document one click away.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="site-header">
          <div className="wrap header-inner">
            <Link href="/" className="brand">
              Felix&rsquo;s Notes
              <span className="brand-sub">GOAT Academy</span>
            </Link>
          </div>
        </header>

        <main className="wrap">{children}</main>

        <footer className="site-footer">
          <div className="wrap">
            <p>
              Archived from the GOAT Academy community. Charts and watchlists stay in
              their original documents — each note links back to its source.
            </p>
            <p className="disclaimer">
              Historical market commentary, preserved for reference. Not financial
              advice.
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
