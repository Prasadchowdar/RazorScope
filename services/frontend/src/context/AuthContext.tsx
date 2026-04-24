import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import { logout as apiLogout, refreshAccessToken } from "../api/auth";

interface AuthState {
  accessToken: string | null;
  merchantId: string | null;
  userName: string | null;
  userEmail: string | null;
}

interface AuthContextValue extends AuthState {
  setSession: (token: string, merchantId: string, name: string, email: string) => void;
  clearSession: () => Promise<void>;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function decodeJwtPayload(token: string): Record<string, unknown> {
  try {
    return JSON.parse(atob(token.split(".")[1]));
  } catch {
    return {};
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({
    accessToken: null,
    merchantId: null,
    userName: null,
    userEmail: null,
  });
  const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  function scheduleRefresh(expiresInMs: number) {
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    const refreshAt = Math.max(expiresInMs - 60_000, 10_000);
    refreshTimerRef.current = setTimeout(async () => {
      try {
        const newToken = await refreshAccessToken();
        const payload = decodeJwtPayload(newToken);
        const exp = (payload.exp as number) * 1000;
        setState((s) => ({ ...s, accessToken: newToken }));
        scheduleRefresh(exp - Date.now());
      } catch {
        setState({ accessToken: null, merchantId: null, userName: null, userEmail: null });
      }
    }, refreshAt);
  }

  // On mount: attempt silent refresh using the httpOnly cookie
  useEffect(() => {
    refreshAccessToken()
      .then((token) => {
        const payload = decodeJwtPayload(token);
        const mid = payload.mid as string;
        const exp = (payload.exp as number) * 1000;
        setState({ accessToken: token, merchantId: mid, userName: null, userEmail: null });
        scheduleRefresh(exp - Date.now());
      })
      .catch(() => {
        // No valid session — stay on login page
      });

    return () => {
      if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    };
  }, []);

  const setSession = useCallback(
    (token: string, merchantId: string, name: string, email: string) => {
      setState({ accessToken: token, merchantId, userName: name, userEmail: email });
      const payload = decodeJwtPayload(token);
      const exp = (payload.exp as number) * 1000;
      scheduleRefresh(exp - Date.now());
    },
    [],
  );

  const clearSession = useCallback(async () => {
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    await apiLogout().catch(() => {});
    setState({ accessToken: null, merchantId: null, userName: null, userEmail: null });
  }, []);

  return (
    <AuthContext.Provider
      value={{
        ...state,
        setSession,
        clearSession,
        isAuthenticated: !!state.accessToken,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
