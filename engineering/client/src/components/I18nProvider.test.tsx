import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { useTranslation } from "react-i18next";
import I18nProvider from "./I18nProvider";
import i18n from "src/i18n/config";

function Probe() {
  const { i18n: active } = useTranslation();
  return <p>{`${active.language}:${String(active.isInitialized)}`}</p>;
}

describe("I18nProvider", () => {
  it("provides the initialised English instance", () => {
    render(
      <I18nProvider>
        <Probe />
      </I18nProvider>,
    );

    expect(screen.getByText("en:true")).toBeInTheDocument();
    expect(i18n.isInitialized).toBe(true);
  });
});
