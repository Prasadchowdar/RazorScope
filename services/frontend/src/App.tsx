import { Suspense, lazy, useState } from "react";
import { useAuth } from "./context/AuthContext";
import LandingPage from "./pages/LandingPage";

const Dashboard = lazy(() => import("./pages/Dashboard"));
const LoginPage = lazy(() => import("./pages/LoginPage"));
const RegisterPage = lazy(() => import("./pages/RegisterPage"));

type View = "landing" | "login" | "register";

function AppBootSplash() {
  return (
    <div className="relative min-h-screen overflow-hidden bg-[var(--bg-0)] text-white">
      <div className="orb orb-cyan" />
      <div className="orb orb-rose" />
      <div className="noise-overlay" />
      <div className="relative flex min-h-screen items-center justify-center px-6">
        <div className="landing-surface w-full max-w-lg p-8 text-center">
          <div className="mx-auto mb-5 h-14 w-14 animate-pulse rounded-2xl bg-white/10" />
          <p className="text-3xl font-semibold tracking-tight">RazorScope</p>
          <p className="mt-3 text-sm text-slate-400">
            Loading the revenue workspace...
          </p>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const { isAuthenticated, setSession } = useAuth();
  const [view, setView] = useState<View>("landing");

  if (!isAuthenticated) {
    if (view === "register") {
      return (
        <Suspense fallback={<AppBootSplash />}>
          <RegisterPage
            onSuccess={(token, mid, name, email) => setSession(token, mid, name, email)}
            onLoginClick={() => setView("login")}
            onBackClick={() => setView("landing")}
          />
        </Suspense>
      );
    }

    if (view === "login") {
      return (
        <Suspense fallback={<AppBootSplash />}>
          <LoginPage
            onSuccess={(token, mid, name, email) => setSession(token, mid, name, email)}
            onRegisterClick={() => setView("register")}
            onBackClick={() => setView("landing")}
          />
        </Suspense>
      );
    }

    return (
      <LandingPage
        onGetStarted={() => setView("register")}
        onSignIn={() => setView("login")}
      />
    );
  }

  return (
    <Suspense fallback={<AppBootSplash />}>
      <Dashboard />
    </Suspense>
  );
}
