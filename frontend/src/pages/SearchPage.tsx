import React from "react";
import { useTranslation } from "react-i18next";

const SearchPage: React.FC = () => {
  const { t } = useTranslation();
  return (
    <div data-testid="search-page">
      <h1>{t("search.title")}</h1>
      <p>{t("search.placeholder")}</p>
    </div>
  );
};

export default SearchPage;
