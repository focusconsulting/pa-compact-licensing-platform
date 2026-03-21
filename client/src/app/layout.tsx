import "src/styles/styles.scss";

/**
 * Root layout component, wraps all pages.
 * @see https://nextjs.org/docs/app/api-reference/file-conventions/layout
 */
import { Metadata } from "next";

export const metadata: Metadata = {
  icons: [`${process.env.NEXT_PUBLIC_BASE_PATH ?? ""}/img/logo.svg`],
};

interface LayoutProps {
  children: React.ReactNode;
  params: {
    locale: string;
  };
}

export default function RootLayout({ children, params }: LayoutProps) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
