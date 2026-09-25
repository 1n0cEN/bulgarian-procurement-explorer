import type { Metadata } from "next";
import Link from "next/link";
import "./style.css";

export const metadata: Metadata = {
  title: "BG Transparency Explorer",
  description:
    "Explore original Bulgarian procurement records, understand award values, and follow the evidence.",
};
export default function Layout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <a className="skip" href="#main">
          Skip to content
        </a>
        <header>
          <div className="nav-wrap">
            <Link className="brand" href="/">
              <span className="brand-mark" aria-hidden="true">
                БГ
              </span>
              <span>
                BG Transparency
                <span className="brand-sub">EXPLORER / ОБЩЕСТВЕНИ ПОРЪЧКИ</span>
              </span>
            </Link>
            <nav aria-label="Main navigation">
              <Link href="/search">Explore contracts</Link>
              <Link href="/organizations">Organizations</Link>
              <Link href="/suppliers">Suppliers</Link>
              <Link href="/compare">Compare</Link>
              <Link href="/methodology">Methodology</Link>
            </nav>
          </div>
        </header>
        <main id="main">{children}</main>
        <footer>
          <div>
            <strong>Public records. Clear context.</strong>
            <p>
              Independent open-source explorer. Not an official government
              service.
            </p>
          </div>
          <div>
            <Link href="/sources">Sources & update status</Link>
            <Link href="/methodology">Methods & limitations</Link>
            <a href="https://ted.europa.eu/en/legal-notice">
              Data reuse terms ↗
            </a>
          </div>
          <p className="fine">
            © European Union — source notices. Statistics are derived
            calculations. An indicator is not evidence of misconduct.
          </p>
        </footer>
      </body>
    </html>
  );
}
