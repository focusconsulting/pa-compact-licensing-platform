import "src/styles/styles.scss";

/**
 * Root layout component, wraps all pages.
 * @see https://nextjs.org/docs/app/api-reference/file-conventions/layout
 */
import { Metadata } from "next";
import { AuthProvider } from "src/contexts/AuthContext";
import I18nProvider from "src/components/I18nProvider";

export const metadata: Metadata = {
  title: {
    default: "PA Compact Data System",
    template: "%s | PA Compact Data System",
  },
  icons: [`${process.env.NEXT_PUBLIC_BASE_PATH ?? ""}/img/logo.svg`],
};

interface LayoutProps {
  children: React.ReactNode;
}

export default function RootLayout({ children }: LayoutProps) {
  return (
    <html lang="en">
      <body>
        <I18nProvider>
          <AuthProvider>{children}</AuthProvider>
        </I18nProvider>
      </body>
    </html>
  );
}
