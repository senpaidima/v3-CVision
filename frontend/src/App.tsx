import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/layout/Layout";
import SearchPage from "./pages/SearchPage";
import LastenheftPage from "./pages/LastenheftPage";
import EmployeeDetailPage from "./pages/EmployeeDetailPage";
import LoginPage from "./pages/LoginPage";
import "./i18n";

export const AppRoutes: React.FC = () => {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Navigate to="/search" replace />} />
        <Route path="search" element={<SearchPage />} />
        <Route path="lastenheft" element={<LastenheftPage />} />
        <Route path="employee/:alias" element={<EmployeeDetailPage />} />
      </Route>
      <Route path="/login" element={<LoginPage />} />
      <Route path="*" element={<Navigate to="/search" replace />} />
    </Routes>
  );
};

function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  );
}

export default App;
