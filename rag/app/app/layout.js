import "./globals.css";

export const metadata = {
  title: "Family Office Intelligence",
  description: "Search verified single- and multi-family office records — principals, contacts, and recent activity.",
  robots: { index: false, follow: false }, // demo URL: reachable for review, not search-indexed
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
