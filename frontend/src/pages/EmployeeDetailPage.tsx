import React, { useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import useApi from "../hooks/useApi";
import "./EmployeeDetailPage.css";

interface EmployeeDetail {
  id: string;
  name?: string;
  title?: string;
  department?: string;
  unit?: string;
  unitAlias?: string;
  location?: string;
  email?: string;
  phone?: string;
  office?: string;
  experience_level?: string;
  years_of_experience?: string;
  manager?: string;
  manager_alias?: string;
  company?: string;
  division?: string;
  start_date?: string;
  employee_id?: string;
  job_code?: string;
  project_role?: string;
  type?: string;
  street?: string;
  postalCode?: string;
  city?: string;
  state?: string;
  country?: string;
  endDate?: string;
  billableJobPosition?: string;
  weeklyCapacity?: string;
}

const EmployeeDetailPage: React.FC = () => {
  const { t } = useTranslation();
  const { alias } = useParams<{ alias: string }>();
  const navigate = useNavigate();

  const {
    data: employee,
    loading,
    error,
    execute: fetchEmployee,
  } = useApi<EmployeeDetail>(`/api/v1/employees/${alias}`);

  useEffect(() => {
    if (alias) {
      fetchEmployee();
    }
  }, [alias, fetchEmployee]);

  const handleBack = () => {
    navigate("/search");
  };

  const getInitials = (name?: string) => {
    if (!name) return "";
    const parts = name.split(/[, ]+/).filter(Boolean);
    if (parts.length >= 2 && parts[0] && parts[1]) {
      return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
    }
    return name.charAt(0).toUpperCase();
  };

  if (loading) {
    return (
      <div className="loading-container" data-testid="loading-state">
        <div className="loading-message">{t("employee.loading")}</div>
      </div>
    );
  }

  if (error || !employee) {
    return (
      <div className="error-container" data-testid="error-state">
        <div className="not-found-message">
          <h3>{error ? t("common.error") : t("employee.notFound")}</h3>
          <p>{error?.message}</p>
          <button onClick={handleBack}>{t("employee.back")}</button>
        </div>
      </div>
    );
  }

  return (
    <div className="employee-detail-page" data-testid="employee-detail-page">
      {/* Employee Header */}
      <div className="employee-header">
        <div className="avatar">
          <span>{getInitials(employee.name)}</span>
        </div>
        <div className="employee-name">
          <h1 data-testid="employee-name">{employee.name}</h1>
          {employee.type && (
            <div className="employee-badge">{employee.type}</div>
          )}
        </div>
        <div className="employee-actions">
          <button
            className="btn-back"
            onClick={handleBack}
            data-testid="back-button"
          >
            {t("employee.back")}
          </button>
        </div>
      </div>

      {/* General Information Section */}
      <div className="info-section">
        <div className="section-header">
          <h2>{t("employee.title")}</h2>
        </div>
        <div className="section-content">
          <div className="info-card">
            <div className="field-label">{t("employee.title")}</div>
            <div className="field-value" data-testid="employee-title">
              {employee.title || "N/A"}
            </div>
          </div>
          <div className="info-card">
            <div className="field-label">{t("employee.department")}</div>
            <div className="field-value" data-testid="employee-department">
              {employee.department || "N/A"}
            </div>
          </div>
          <div className="info-card">
            <div className="field-label">{t("employee.unit")}</div>
            <div className="field-value">{employee.unit || "N/A"}</div>
          </div>
          <div className="info-card">
            <div className="field-label">{t("employee.location")}</div>
            <div className="field-value" data-testid="employee-location">
              {employee.location || "N/A"}
            </div>
          </div>
          <div className="info-card">
            <div className="field-label">{t("employee.experience")}</div>
            <div className="field-value">
              {employee.years_of_experience || "N/A"}
            </div>
          </div>
        </div>
      </div>

      {/* Contact Information Section */}
      <div className="info-section">
        <div className="section-header">
          <h2>
            {t("employee.email")} & {t("employee.phone")}
          </h2>
        </div>
        <div className="section-content">
          <div className="info-card">
            <div className="field-label">{t("employee.email")}</div>
            <div className="field-value">
              {employee.email ? (
                <a href={`mailto:${employee.email}`}>{employee.email}</a>
              ) : (
                "N/A"
              )}
            </div>
          </div>
          <div className="info-card">
            <div className="field-label">{t("employee.phone")}</div>
            <div className="field-value">
              {employee.phone ? (
                <a href={`tel:${employee.phone.replace(/[() ]/g, "")}`}>
                  {employee.phone}
                </a>
              ) : (
                "N/A"
              )}
            </div>
          </div>
          <div className="info-card">
            <div className="field-label">{t("employee.office")}</div>
            <div className="field-value">{employee.office || "N/A"}</div>
          </div>
        </div>
      </div>

      {/* Reporting Structure Section */}
      <div className="info-section">
        <div className="section-header">
          <h2>{t("employee.manager")}</h2>
        </div>
        <div className="section-content">
          <div className="info-card">
            <div className="field-label">{t("employee.manager")}</div>
            <div className="field-value">{employee.manager || "N/A"}</div>
          </div>
          {employee.manager_alias && (
            <div className="info-card">
              <div className="field-label">Manager Alias</div>
              <div className="field-value">{employee.manager_alias}</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default EmployeeDetailPage;
