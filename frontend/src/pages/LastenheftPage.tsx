import React, { useState, useRef } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import apiClient from "../services/apiClient";
import "./LastenheftPage.css";

// ----------------------------------------------------------------------
// Interfaces
// ----------------------------------------------------------------------

interface QualityScore {
  completeness: number;
  clarity: number;
  specificity: number;
  feasibility: number;
  overall: number;
  summary: string;
}

interface OpenQuestion {
  question: string;
  category: "technical" | "team" | "timeline" | "budget" | "domain";
  priority: "high" | "medium" | "low";
}

interface ExtractedSkill {
  name: string;
  category: string;
  mandatory: boolean;
  level: string | null;
}

interface AnalysisResult {
  quality_assessment: QualityScore;
  open_questions: OpenQuestion[];
  extracted_skills: ExtractedSkill[];
}

interface ScoreBreakdown {
  skill_match: number;
  experience: number;
  semantic_similarity: number;
  availability: number;
}

interface CandidateMatch {
  employee_name: string;
  employee_alias: string;
  title: string;
  location: string;
  skills: string[];
  total_score: number;
  breakdown: ScoreBreakdown;
  explanation: string;
}

interface MatchResult {
  matches: CandidateMatch[];
  total_candidates_searched: number;
  query_skills: string[];
}

interface UploadResponse {
  extracted_text: string;
  char_count: number;
  format: string;
}

type Phase = "upload" | "analyzing" | "analyzed" | "matching" | "matched";
type Tab = "file" | "text";

// ----------------------------------------------------------------------
// Component
// ----------------------------------------------------------------------

const LastenheftPage: React.FC = () => {
  const { t, i18n } = useTranslation();
  const { getAccessToken } = useAuth();

  // State
  const [phase, setPhase] = useState<Phase>("upload");
  const [activeTab, setActiveTab] = useState<Tab>("file");
  const [extractedText, setExtractedText] = useState("");
  const [inputText, setInputText] = useState("");
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [matches, setMatches] = useState<MatchResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isDragActive, setIsDragActive] = useState(false);

  // Refs
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ----------------------------------------------------------------------
  // Handlers
  // ----------------------------------------------------------------------

  const handleReset = () => {
    setPhase("upload");
    setExtractedText("");
    setInputText("");
    setAnalysis(null);
    setMatches(null);
    setError(null);
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setIsDragActive(true);
    } else if (e.type === "dragleave") {
      setIsDragActive(false);
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      await handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      await handleFileUpload(e.target.files[0]);
    }
  };

  const handleFileUpload = async (file: File) => {
    const extension = file.name.split(".").pop()?.toLowerCase();
    if (extension !== "pdf" && extension !== "docx") {
      setError(t("lastenheft.unsupportedFormat"));
      return;
    }

    setPhase("analyzing");
    setError(null);

    try {
      // Direct fetch for multipart/form-data
      const formData = new FormData();
      formData.append("file", file);

      const token = await getAccessToken();
      const headers: HeadersInit = {};
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      const API_BASE_URL =
        import.meta.env.VITE_API_URL || "http://localhost:8000";

      const response = await fetch(`${API_BASE_URL}/api/v1/lastenheft/upload`, {
        method: "POST",
        headers,
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.status}`);
      }

      const data: UploadResponse = await response.json();
      setExtractedText(data.extracted_text);
      await runAnalysis(data.extracted_text);
    } catch (err) {
      console.error(err);
      setError(t("lastenheft.error"));
      setPhase("upload");
    }
  };

  const handleTextAnalyze = async () => {
    if (!inputText.trim()) {
      setError(t("lastenheft.noText"));
      return;
    }

    setPhase("analyzing");
    setError(null);

    try {
      const data = await apiClient.post<UploadResponse>(
        "/api/v1/lastenheft/text",
        { text: inputText },
      );
      setExtractedText(data.extracted_text);
      await runAnalysis(data.extracted_text);
    } catch (err) {
      console.error(err);
      setError(t("lastenheft.error"));
      setPhase("upload");
    }
  };

  const runAnalysis = async (text: string) => {
    try {
      const result = await apiClient.post<AnalysisResult>(
        "/api/v1/lastenheft/analyze",
        { text },
      );
      setAnalysis(result);
      setPhase("analyzed");
    } catch (err) {
      console.error(err);
      setError(t("lastenheft.error"));
      setPhase("upload");
    }
  };

  const handleMatchCandidates = async () => {
    if (!analysis || !extractedText) return;

    setPhase("matching");
    setError(null);

    try {
      const result = await apiClient.post<MatchResult>(
        "/api/v1/lastenheft/match",
        {
          extracted_skills: analysis.extracted_skills,
          text: extractedText,
        },
      );
      setMatches(result);
      setPhase("matched");
    } catch (err) {
      console.error(err);
      setError(t("lastenheft.error"));
      setPhase("analyzed");
    }
  };

  // ----------------------------------------------------------------------
  // Render Helpers
  // ----------------------------------------------------------------------

  const getScoreColor = (score: number) => {
    if (score >= 70) return "#047857"; // Green
    if (score >= 40) return "#b45309"; // Yellow
    return "#b91c1c"; // Red
  };

  const renderUploadPhase = () => (
    <div className="upload-card">
      <div className="upload-tabs">
        <button
          className={`tab-btn ${activeTab === "file" ? "active" : ""}`}
          onClick={() => setActiveTab("file")}
          data-testid="file-upload-tab"
        >
          {t("lastenheft.fileTab")}
        </button>
        <button
          className={`tab-btn ${activeTab === "text" ? "active" : ""}`}
          onClick={() => setActiveTab("text")}
          data-testid="text-paste-tab"
        >
          {t("lastenheft.pasteTab")}
        </button>
      </div>

      <div className="tab-content">
        {activeTab === "file" ? (
          <>
            <input
              type="file"
              ref={fileInputRef}
              style={{ display: "none" }}
              onChange={handleFileSelect}
              accept=".pdf,.docx"
            />
            <div
              className={`drop-zone ${isDragActive ? "drag-active" : ""}`}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              data-testid="file-upload"
            >
              <p>{t("lastenheft.uploadHint")}</p>
            </div>
          </>
        ) : (
          <div className="text-area-container">
            <textarea
              className="text-input"
              placeholder={t("lastenheft.textPlaceholder")}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              data-testid="text-input"
            />
            <button
              className="analyze-btn"
              onClick={handleTextAnalyze}
              disabled={!inputText.trim()}
              data-testid="analyze-btn"
            >
              {t("lastenheft.analyze")}
            </button>
          </div>
        )}
      </div>
    </div>
  );

  const renderAnalysisResults = () => {
    if (!analysis) return null;

    return (
      <div className="analysis-results">
        {/* Quality Score */}
        <div className="result-card" data-testid="quality-score">
          <div className="result-header">
            <h2>{t("lastenheft.quality")}</h2>
            <button
              className="lang-btn"
              onClick={handleReset}
              data-testid="new-analysis-btn"
            >
              {t("lastenheft.newAnalysis")}
            </button>
          </div>

          <div className="score-container">
            <div className="score-bar-bg">
              <div
                className="score-bar-fill"
                style={{
                  width: `${analysis.quality_assessment.overall}%`,
                  backgroundColor: getScoreColor(
                    analysis.quality_assessment.overall,
                  ),
                }}
              />
            </div>
            <div
              className="score-value"
              style={{
                color: getScoreColor(analysis.quality_assessment.overall),
              }}
            >
              {analysis.quality_assessment.overall}/100
            </div>
          </div>
          <p className="summary-text">{analysis.quality_assessment.summary}</p>
        </div>

        {/* Open Questions */}
        <div className="result-card" data-testid="open-questions">
          <div className="result-header">
            <h2>{t("lastenheft.questions")}</h2>
          </div>
          <div className="questions-list">
            {analysis.open_questions.map((q, idx) => (
              <div key={idx} className="question-item">
                <span
                  className={`priority-badge priority-${q.priority}`}
                  data-testid={`priority-${q.priority}`}
                >
                  {t(`lastenheft.priorities.${q.priority}`)}
                </span>
                <span>{q.question}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Extracted Skills */}
        <div className="result-card" data-testid="extracted-skills">
          <div className="result-header">
            <h2>{t("lastenheft.skills")}</h2>
          </div>
          <div className="skills-container">
            {analysis.extracted_skills.map((skill, idx) => (
              <span
                key={idx}
                className={`skill-tag ${skill.mandatory ? "skill-mandatory" : "skill-optional"}`}
              >
                {skill.name}
              </span>
            ))}
          </div>
        </div>

        {/* Action Button */}
        {phase === "analyzed" && (
          <div className="match-action-container">
            <button
              className="find-candidates-btn"
              onClick={handleMatchCandidates}
              data-testid="find-candidates-btn"
            >
              {t("lastenheft.findCandidates")}
            </button>
          </div>
        )}
      </div>
    );
  };

  const renderMatches = () => {
    if (!matches) return null;

    return (
      <div className="analysis-results">
        {renderAnalysisResults()}

        <div className="result-card" data-testid="matched-candidates">
          <div className="result-header">
            <h2>
              {t("lastenheft.candidatesFound", {
                count: matches.matches.length,
              })}
            </h2>
          </div>

          <div className="candidates-grid">
            {matches.matches.map((match, idx) => (
              <Link
                key={idx}
                to={`/employee/${match.employee_alias}`}
                className="candidate-card-link"
              >
                <div
                  className="candidate-match-card"
                  data-testid="candidate-card"
                >
                  <div className="candidate-header">
                    <h3 className="candidate-name">{match.employee_name}</h3>
                    <p className="candidate-title">{match.title}</p>
                  </div>

                  <div className="total-match-score">
                    <div className="score-bar-bg">
                      <div
                        className="score-bar-fill"
                        style={{
                          width: `${match.total_score * 100}%`,
                          backgroundColor: "#0056b3",
                        }}
                      />
                    </div>
                    <span className="score-value" style={{ fontSize: "1rem" }}>
                      {Math.round(match.total_score * 100)}%
                    </span>
                  </div>

                  <div className="match-breakdown">
                    <div className="breakdown-item">
                      <span>{t("lastenheft.skillMatch")}</span>
                      <div className="breakdown-bar">
                        <div
                          className="score-bar-fill"
                          style={{
                            width: `${match.breakdown.skill_match * 100}%`,
                            backgroundColor: "#0056b3",
                          }}
                        />
                      </div>
                    </div>
                    <div className="breakdown-item">
                      <span>{t("lastenheft.experience")}</span>
                      <div className="breakdown-bar">
                        <div
                          className="score-bar-fill"
                          style={{
                            width: `${match.breakdown.experience * 100}%`,
                            backgroundColor: "#0056b3",
                          }}
                        />
                      </div>
                    </div>
                    <div className="breakdown-item">
                      <span>{t("lastenheft.semantic")}</span>
                      <div className="breakdown-bar">
                        <div
                          className="score-bar-fill"
                          style={{
                            width: `${match.breakdown.semantic_similarity * 100}%`,
                            backgroundColor: "#0056b3",
                          }}
                        />
                      </div>
                    </div>
                  </div>

                  <p className="explanation-text">
                    "{match.explanation.substring(0, 120)}..."
                  </p>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </div>
    );
  };

  // ----------------------------------------------------------------------
  // Main Render
  // ----------------------------------------------------------------------

  return (
    <div className="lastenheft-page" data-testid="lastenheft-page">
      <header className="lastenheft-header">
        <h1>{t("lastenheft.title")}</h1>
        <div className="language-toggle">
          <button
            className={`lang-btn ${i18n.language === "en" ? "active" : ""}`}
            onClick={() => i18n.changeLanguage("en")}
          >
            EN
          </button>
          <button
            className={`lang-btn ${i18n.language === "de" ? "active" : ""}`}
            onClick={() => i18n.changeLanguage("de")}
          >
            DE
          </button>
        </div>
      </header>

      <div className="lastenheft-container">
        {error && <div className="error-message">{error}</div>}

        {phase === "upload" && renderUploadPhase()}

        {(phase === "analyzing" || phase === "matching") && (
          <div className="loading-spinner" />
        )}

        {(phase === "analyzed" ||
          phase === "matching" ||
          phase === "matched") &&
          renderAnalysisResults()}

        {phase === "matched" && renderMatches()}
      </div>
    </div>
  );
};

export default LastenheftPage;
