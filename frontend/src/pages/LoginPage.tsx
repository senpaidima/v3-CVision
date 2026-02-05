import React from "react";
import { useTranslation } from "react-i18next";

const LoginPage: React.FC = () => {
  const { t } = useTranslation();
  return (
    <div
      data-testid="login-page"
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        height: "100%",
      }}
    >
      <h1>{t("auth.login")}</h1>
      <button
        style={{
          marginTop: "1rem",
          padding: "0.75rem 1.5rem",
          backgroundColor: "#0056b3",
          color: "white",
          border: "none",
          borderRadius: "4px",
          cursor: "pointer",
        }}
      >
        {t("auth.loginWith")}
      </button>
    </div>
  );
};

export default LoginPage;
