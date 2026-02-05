import React from "react";
import ReactDOM from "react-dom/client";
import { msalInstance } from "./config/msalInstance";
import App from "./App";

msalInstance
  .initialize()
  .then(() => msalInstance.handleRedirectPromise())
  .then(() => {
    ReactDOM.createRoot(document.getElementById("root")!).render(
      <React.StrictMode>
        <App msalInstance={msalInstance} />
      </React.StrictMode>,
    );
  })
  .catch((err) => {
    console.error("[MSAL] Initialization failed:", err);
    ReactDOM.createRoot(document.getElementById("root")!).render(
      <React.StrictMode>
        <App msalInstance={msalInstance} />
      </React.StrictMode>,
    );
  });
