import i18next from "i18next";
import { initReactI18next } from "react-i18next";
import common from "./en/common.json";
import basic from "./en/basic.json";
import address from "./en/address.json";
import date from "./en/date.json";
import country from "./en/country.json";
export const defaultNS = "common";

// TODO: implement error handling
void i18next.use(initReactI18next).init({
  lng: "en", // if you're using a language detector, do not define the lng option
  resources: {
    en: {
      common,
      basic,
      address,
      date,
      country,
    },
  },
  defaultNS,
});
