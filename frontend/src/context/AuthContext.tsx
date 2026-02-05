import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
} from "react";
import { useMsal, useIsAuthenticated } from "@azure/msal-react";
import { InteractionRequiredAuthError } from "@azure/msal-browser";
import { loginRequest, appRoles, type AppRole } from "../config/authConfig";

export interface AuthUser {
  name: string;
  email: string;
  id: string;
}

export interface AuthContextValue {
  isAuthenticated: boolean;
  loading: boolean;
  user: AuthUser | null;
  roles: string[];
  login: () => Promise<void>;
  logout: () => Promise<void>;
  getAccessToken: () => Promise<string | null>;
  hasRole: (role: string) => boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export const useAuth = (): AuthContextValue => {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const { instance, accounts } = useMsal();
  const msalAuthenticated = useIsAuthenticated();
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [roles, setRoles] = useState<string[]>([]);

  useEffect(() => {
    if (accounts.length > 0) {
      const account = accounts[0]!;
      const claims = account.idTokenClaims as
        | Record<string, unknown>
        | undefined;

      setUser({
        name: account.name ?? account.username,
        email: account.username,
        id:
          (claims?.oid as string) ??
          account.homeAccountId ??
          `user_${account.username}`,
      });

      const tokenRoles = (claims?.roles as string[]) ?? [];
      setRoles(tokenRoles);
    } else {
      setUser(null);
      setRoles([]);
    }
    setLoading(false);
  }, [accounts]);

  useEffect(() => {
    instance.handleRedirectPromise().catch((err) => {
      console.error("[Auth] Redirect handling failed:", err);
    });
  }, [instance]);

  const login = useCallback(async () => {
    try {
      await instance.loginRedirect({
        ...loginRequest,
        prompt: "select_account",
      });
    } catch (err) {
      const error = err as Error;
      if (!error.message.includes("interaction_in_progress")) {
        console.error("[Auth] Login failed:", error);
      }
    }
  }, [instance]);

  const logout = useCallback(async () => {
    await instance.logoutRedirect({
      postLogoutRedirectUri: window.location.origin,
    });
  }, [instance]);

  const getAccessToken = useCallback(async (): Promise<string | null> => {
    if (accounts.length === 0) return null;

    try {
      const response = await instance.acquireTokenSilent({
        ...loginRequest,
        account: accounts[0]!,
      });
      return response.accessToken;
    } catch (err) {
      if (err instanceof InteractionRequiredAuthError) {
        try {
          const response = await instance.acquireTokenPopup(loginRequest);
          return response.accessToken;
        } catch (popupErr) {
          console.error("[Auth] Token popup failed:", popupErr);
          return null;
        }
      }
      console.error("[Auth] Token acquisition failed:", err);
      return null;
    }
  }, [instance, accounts]);

  const hasRole = useCallback(
    (role: string): boolean => {
      return roles.includes(role);
    },
    [roles],
  );

  const value: AuthContextValue = {
    isAuthenticated: msalAuthenticated && !!user,
    loading,
    user,
    roles,
    login,
    logout,
    getAccessToken,
    hasRole,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export { appRoles };
export type { AppRole };
export default AuthProvider;
