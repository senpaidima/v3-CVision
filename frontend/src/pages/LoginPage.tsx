import React, { useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../context/AuthContext";
import { Shield } from "lucide-react";

const LoginPage: React.FC = () => {
  const { t } = useTranslation();
  const { isAuthenticated, loading, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from =
    (location.state as { from?: Location })?.from?.pathname ?? "/search";

  useEffect(() => {
    if (isAuthenticated && !loading) {
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, loading, navigate, from]);

  const handleLogin = async () => {
    await login();
  };

  return (
    <div
      data-testid="login-page"
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "100vh",
        background: "linear-gradient(135deg, #f0f4f8 0%, #d9e2ec 100%)",
        fontFamily: "system-ui, -apple-system, sans-serif",
      }}
    >
      <div
        style={{
          background: "#fff",
          borderRadius: 12,
          padding: "3rem 2.5rem",
          boxShadow: "0 4px 24px rgba(0, 0, 0, 0.08)",
          maxWidth: 420,
          width: "100%",
          textAlign: "center",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 8,
            marginBottom: "1.5rem",
          }}
        >
          <Shield size={28} color="#0056b3" />
          <span
            style={{
              fontSize: "1.5rem",
              fontWeight: 700,
              color: "#0056b3",
              letterSpacing: "-0.02em",
            }}
          >
            CVision
          </span>
        </div>

        <h1
          style={{
            fontSize: "1.25rem",
            fontWeight: 600,
            color: "#1a1a2e",
            margin: "0 0 0.5rem",
          }}
        >
          {t("auth.login")}
        </h1>

        <p
          style={{
            color: "#627d98",
            fontSize: "0.875rem",
            margin: "0 0 2rem",
            lineHeight: 1.5,
          }}
        >
          Emposo GmbH
        </p>

        <button
          data-testid="login-button"
          onClick={handleLogin}
          disabled={loading}
          style={{
            width: "100%",
            padding: "0.875rem 1.5rem",
            backgroundColor: loading ? "#7a9ec2" : "#0056b3",
            color: "#fff",
            border: "none",
            borderRadius: 8,
            fontSize: "0.95rem",
            fontWeight: 600,
            cursor: loading ? "not-allowed" : "pointer",
            transition: "background-color 0.2s",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 8,
          }}
        >
          {loading ? t("common.loading") : t("auth.loginWith")}
        </button>
      </div>

      <p
        style={{
          marginTop: "2rem",
          color: "#829ab1",
          fontSize: "0.75rem",
        }}
      >
        &copy; {new Date().getFullYear()} Emposo GmbH
      </p>
    </div>
  );
};

export default LoginPage;
