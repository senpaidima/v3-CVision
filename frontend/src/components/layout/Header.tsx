import React from "react";
import { NavLink, Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { User, Menu } from "lucide-react";
import "./Header.css";

const Header: React.FC = () => {
  const { t, i18n } = useTranslation();

  const toggleLanguage = () => {
    const newLang = i18n.language === "de" ? "en" : "de";
    i18n.changeLanguage(newLang);
  };

  return (
    <header className="header-root" data-testid="header">
      <div style={{ display: "flex", alignItems: "center" }}>
        <Link to="/" className="header-logo">
          CVision
        </Link>
      </div>

      <nav className="header-nav">
        <NavLink
          to="/search"
          className={({ isActive }) =>
            `header-link ${isActive ? "active" : ""}`
          }
          data-testid="nav-search"
        >
          {t("nav.search")}
        </NavLink>
        <NavLink
          to="/lastenheft"
          className={({ isActive }) =>
            `header-link ${isActive ? "active" : ""}`
          }
          data-testid="nav-lastenheft"
        >
          {t("nav.lastenheft")}
        </NavLink>
      </nav>

      <div className="header-actions">
        <button
          className="header-lang-btn"
          onClick={toggleLanguage}
          data-testid="language-toggle"
        >
          {i18n.language.toUpperCase()}
        </button>

        <div className="header-user">
          <User size={20} />
        </div>

        <div className="mobile-menu-trigger" style={{ display: "none" }}>
          <Menu size={24} />
        </div>
      </div>
    </header>
  );
};

export default Header;
