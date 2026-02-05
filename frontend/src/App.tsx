import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { MsalProvider } from "@azure/msal-react";
import type { IPublicClientApplication } from "@azure/msal-browser";
import { AuthProvider } from "./context/AuthContext";
import ProtectedRoute from "./components/common/ProtectedRoute";
import Layout from "./components/layout/Layout";
import SearchPage from "./pages/SearchPage";
import LastenheftPage from "./pages/LastenheftPage";
import EmployeeDetailPage from "./pages/EmployeeDetailPage";
import LoginPage from "./pages/LoginPage";
import { AuthTokenConnector } from "./services/apiClient";
import "./i18n";

export const AppRoutes: React.FC = () => {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route index element={<Navigate to="/search" replace />} />
          <Route path="search" element={<SearchPage />} />
          <Route path="lastenheft" element={<LastenheftPage />} />
          <Route path="employee/:alias" element={<EmployeeDetailPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/search" replace />} />
    </Routes>
  );
};

function App({ msalInstance }: { msalInstance: IPublicClientApplication }) {
  return (
    <MsalProvider instance={msalInstance}>
      <AuthProvider>
        <AuthTokenConnector />
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </AuthProvider>
    </MsalProvider>
  );
}

export default App;
