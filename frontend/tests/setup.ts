import "@testing-library/jest-dom";
import { vi } from "vitest";

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

const mockAccount = {
  homeAccountId: "mock-home-id",
  environment: "login.microsoftonline.com",
  tenantId: "09bad365-2d15-46e7-bd21-7415ce025c4b",
  username: "test@emposo.eu",
  localAccountId: "mock-local-id",
  name: "Test User",
  idTokenClaims: {
    oid: "mock-oid",
    roles: ["Admin"],
  },
};

const stableAccounts = [mockAccount];

const mockInstance = {
  loginRedirect: vi.fn(),
  logoutRedirect: vi.fn(),
  acquireTokenSilent: vi.fn().mockResolvedValue({ accessToken: "mock-token" }),
  acquireTokenPopup: vi.fn().mockResolvedValue({ accessToken: "mock-token" }),
  handleRedirectPromise: vi.fn().mockResolvedValue(null),
  getAllAccounts: () => stableAccounts,
};

vi.mock("@azure/msal-react", () => ({
  MsalProvider: ({ children }: { children: React.ReactNode }) => children,
  useMsal: () => ({
    instance: mockInstance,
    accounts: stableAccounts,
    inProgress: "none",
  }),
  useIsAuthenticated: () => true,
}));

vi.mock("@azure/msal-browser", () => ({
  PublicClientApplication: vi.fn().mockImplementation(() => ({
    initialize: vi.fn().mockResolvedValue(undefined),
    handleRedirectPromise: vi.fn().mockResolvedValue(null),
    loginRedirect: vi.fn(),
    logoutRedirect: vi.fn(),
    acquireTokenSilent: vi
      .fn()
      .mockResolvedValue({ accessToken: "mock-token" }),
    acquireTokenPopup: vi.fn().mockResolvedValue({ accessToken: "mock-token" }),
    getAllAccounts: () => stableAccounts,
  })),
  InteractionRequiredAuthError: class InteractionRequiredAuthError extends Error {},
  LogLevel: {
    Error: 0,
    Warning: 1,
    Info: 2,
    Verbose: 3,
    Trace: 4,
  },
}));

vi.mock("../src/config/msalInstance", () => ({
  msalInstance: {
    initialize: vi.fn().mockResolvedValue(undefined),
    handleRedirectPromise: vi.fn().mockResolvedValue(null),
    loginRedirect: vi.fn(),
    logoutRedirect: vi.fn(),
    acquireTokenSilent: vi
      .fn()
      .mockResolvedValue({ accessToken: "mock-token" }),
    acquireTokenPopup: vi.fn().mockResolvedValue({ accessToken: "mock-token" }),
    getAllAccounts: () => stableAccounts,
  },
}));
