import i18next from "i18next";
import { initReactI18next } from "react-i18next";
import common from "./en/common.json";
import basic from "./en/basic.json";
import address from "./en/address.json";
import date from "./en/date.json";
import country from "./en/country.json";
import status from "./en/status.json";
import shell from "./en/shell.json";
import application from "./en/application.json";
import verify from "./en/verify.json";

export const defaultNS = "common";

// Resources are bundled, so init completes synchronously and needs no loading state.
void i18next.use(initReactI18next).init({
  lng: "en", // if you're using a language detector, do not define the lng option
  resources: {
    en: {
      common,
      basic,
      address,
      date,
      country,
      status,
      shell,
      application,
      verify,
    },
  },
  defaultNS,
  // React escapes what it renders; escaping here too shows "Kansas&#39;".
  interpolation: { escapeValue: false },
});

// "Kansas'" and "Oklahoma's": a name that ends in s takes only the apostrophe. Use as {{state, possessive}}.
i18next.services.formatter?.add("possessive", (value: string) =>
  value.endsWith("s") ? `${value}'` : `${value}'s`,
);

export default i18next;
