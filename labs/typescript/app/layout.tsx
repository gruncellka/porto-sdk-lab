import type { ReactNode } from "react";

export const metadata = {
  title: "Porto SDK TypeScript Lab",
  description: "Next.js integration sandbox for @gruncellka/porto-sdk",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
