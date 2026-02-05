import React from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { FileQuestion } from "lucide-react";

const NotFoundPage: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();

  return (
    <div
      data-testid="not-found-page"
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "100vh",
        fontFamily: "system-ui, -apple-system, sans-serif",
        background: "linear-gradient(135deg, #f0f4f8 0%, #d9e2ec 100%)",
      }}
    >
      <FileQuestion size={64} color="#627d98" style={{ marginBottom: 24 }} />
      <h1
        style={{
          fontSize: "2rem",
          fontWeight: 700,
          color: "#1a1a2e",
          margin: "0 0 0.5rem",
        }}
      >
        404
      </h1>
      <p
        style={{
          fontSize: "1.125rem",
          color: "#627d98",
          margin: "0 0 2rem",
        }}
      >
        {t("notFound.message")}
      </p>
      <button
        data-testid="not-found-home-button"
        onClick={() => navigate("/search")}
        style={{
          padding: "0.875rem 2rem",
          backgroundColor: "#0056b3",
          color: "#fff",
          border: "none",
          borderRadius: 8,
          fontSize: "0.95rem",
          fontWeight: 600,
          cursor: "pointer",
        }}
      >
        {t("notFound.goHome")}
      </button>
    </div>
  );
};

export default NotFoundPage;
