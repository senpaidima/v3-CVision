import React from "react";
import { useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

const EmployeeDetailPage: React.FC = () => {
  const { t } = useTranslation();
  const { alias } = useParams<{ alias: string }>();

  return (
    <div data-testid="employee-detail-page">
      <h1>{t("employee.title")}</h1>
      <p>Alias: {alias}</p>
    </div>
  );
};

export default EmployeeDetailPage;
