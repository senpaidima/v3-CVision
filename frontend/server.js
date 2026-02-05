import express from "express";
import path from "path";
import { fileURLToPath } from "url";
import compression from "compression";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 3000;
const isProduction = process.env.NODE_ENV === "production";

app.use(compression());

if (isProduction) {
  app.use((req, res, next) => {
    res.setHeader("X-Content-Type-Options", "nosniff");
    res.setHeader("X-Frame-Options", "DENY");
    res.setHeader("X-XSS-Protection", "1; mode=block");
    res.setHeader("Referrer-Policy", "strict-origin-when-cross-origin");
    res.setHeader(
      "Permissions-Policy",
      "camera=(), microphone=(), geolocation=()",
    );
    next();
  });
}

const staticPath = path.join(__dirname, "dist");
app.use(
  express.static(staticPath, {
    maxAge: isProduction ? "1y" : 0,
    etag: true,
  }),
);

app.get("/health", (req, res) => {
  res.json({ status: "ok", timestamp: new Date().toISOString() });
});

app.get("*", (req, res) => {
  res.sendFile(path.join(staticPath, "index.html"));
});

app.listen(PORT, "0.0.0.0", () => {
  console.log(`CVision v3 Frontend running on port ${PORT}`);
});
