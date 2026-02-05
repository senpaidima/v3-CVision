import { Configuration, LogLevel } from "@azure/msal-browser";

const MSAL_CLIENT_ID =
  import.meta.env.VITE_MSAL_CLIENT_ID || "d133bb3d-6457-4912-96b8-285255380743";
const MSAL_TENANT_ID =
  import.meta.env.VITE_MSAL_TENANT_ID || "09bad365-2d15-46e7-bd21-7415ce025c4b";
const MSAL_REDIRECT_URI =
  import.meta.env.VITE_MSAL_REDIRECT_URI || "http://localhost:5173";

export const msalConfig: Configuration = {
  auth: {
    clientId: MSAL_CLIENT_ID,
    authority: `https://login.microsoftonline.com/${MSAL_TENANT_ID}`,
    redirectUri: MSAL_REDIRECT_URI,
    postLogoutRedirectUri: MSAL_REDIRECT_URI,
    navigateToLoginRequestUrl: false,
  },
  cache: {
    cacheLocation: "sessionStorage",
    storeAuthStateInCookie: true,
  },
  system: {
    loggerOptions: {
      loggerCallback: (level, message, containsPii) => {
        if (containsPii) return;
        if (level === LogLevel.Error) {
          console.error("[MSAL]", message);
        }
      },
      logLevel: LogLevel.Warning,
    },
  },
};

export const loginRequest = {
  scopes: [`api://${MSAL_CLIENT_ID}/access_as_user`],
};

export const appRoles = {
  ADMIN: "Admin",
  MANAGER: "Manager",
  EDITOR: "Editor",
  VIEWER: "Viewer",
} as const;

export type AppRole = (typeof appRoles)[keyof typeof appRoles];
