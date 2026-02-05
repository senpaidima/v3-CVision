import "@testing-library/jest-dom";
import { vi } from "vitest";

// Global i18next mock
vi.mock("react-i18next", async () => {
  const actual = await vi.importActual("react-i18next");
  return {
    ...actual,
    useTranslation: () => ({
      t: (key: string) => key,
      i18n: {
        language: "de",
        changeLanguage: vi.fn(),
      },
    }),
    initReactI18next: {
      type: "3rdParty",
      init: vi.fn(),
    },
  };
});
