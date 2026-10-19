"use client";

import React from "react";
import { I18nextProvider } from "react-i18next";
import i18n from "src/i18n/config";

/**
 * Makes the configured i18next instance available to every page. The root
 * layout is a server component, so the client-side init lives here.
 */
export default function I18nProvider({ children }: { children: React.ReactNode }) {
  return <I18nextProvider i18n={i18n}>{children}</I18nextProvider>;
}
