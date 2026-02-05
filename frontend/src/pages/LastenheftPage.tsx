import React from "react";
import { useTranslation } from "react-i18next";

const LastenheftPage: React.FC = () => {
  const { t } = useTranslation();
  return (
    <div data-testid="lastenheft-page">
      <h1>{t("lastenheft.title")}</h1>
      <button>{t("lastenheft.upload")}</button>
    </div>
  );
};

export default LastenheftPage;
