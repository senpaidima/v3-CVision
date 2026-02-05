import React, { useState, useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import ReactMarkdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import "highlight.js/styles/github.css";
import { useStreamingSearch, Employee } from "../hooks/useStreamingSearch";
import EmployeeCard from "../components/chat/EmployeeCard";
import "./SearchPage.css";

interface Message {
  role: "user" | "ai";
  content: string;
  employees?: Employee[];
}

const SearchPage: React.FC = () => {
  const { t, i18n } = useTranslation();
  const {
    isLoading,
    isStreaming,
    aiResponse,
    employees,
    error: streamError,
    sendQuery,
  } = useStreamingSearch();

  const [messages, setMessages] = useState<Message[]>([]);
  const [query, setQuery] = useState("");
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const wasStreaming = useRef(false);

  useEffect(() => {
    if (!isStreaming && wasStreaming.current) {
      if (aiResponse || employees.length > 0) {
        setMessages((prev) => [
          ...prev,
          { role: "ai", content: aiResponse, employees },
        ]);
      }
    }
    wasStreaming.current = isStreaming;
  }, [isStreaming, aiResponse, employees]);

  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop =
        chatContainerRef.current.scrollHeight;
    }
  }, [messages, aiResponse, isStreaming]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || isLoading) return;

    const userQuery = query;
    setQuery("");
    setMessages((prev) => [...prev, { role: "user", content: userQuery }]);

    await sendQuery(userQuery);
  };

  return (
    <div className="search-page" data-testid="search-page">
      <header className="search-header">
        <h1>{t("search.title")}</h1>
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

      <div className="chat-container" ref={chatContainerRef}>
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role}`}>
            <div className="message-bubble">
              {msg.role === "ai" ? (
                <div className="markdown-content" data-testid="ai-response">
                  <ReactMarkdown rehypePlugins={[rehypeHighlight]}>
                    {msg.content}
                  </ReactMarkdown>
                </div>
              ) : (
                msg.content
              )}
            </div>
            {msg.employees && msg.employees.length > 0 && (
              <div className="employee-grid">
                {msg.employees.map((emp, i) => (
                  <EmployeeCard key={i} employee={emp} />
                ))}
              </div>
            )}
          </div>
        ))}

        {isStreaming && (
          <div className="message ai">
            <div className="message-bubble">
              <div className="markdown-content" data-testid="ai-response">
                <ReactMarkdown rehypePlugins={[rehypeHighlight]}>
                  {aiResponse}
                </ReactMarkdown>
              </div>
            </div>
            {employees.length > 0 && (
              <div className="employee-grid">
                {employees.map((emp, i) => (
                  <EmployeeCard key={i} employee={emp} />
                ))}
              </div>
            )}
          </div>
        )}

        {isLoading && !isStreaming && !aiResponse && (
          <div className="message ai">
            <div className="message-bubble">{t("search.loading")}</div>
          </div>
        )}

        {streamError && (
          <div className="error-banner">
            {t("search.error")}: {streamError}
          </div>
        )}

        {messages.length === 0 && !isLoading && (
          <div style={{ textAlign: "center", color: "#888", marginTop: "20%" }}>
            <p>{t("search.placeholder")}</p>
          </div>
        )}
      </div>

      <div className="input-area">
        <form className="input-form" onSubmit={handleSubmit}>
          <input
            type="text"
            className="chat-input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t("search.placeholder")}
            disabled={isLoading}
            data-testid="chat-input"
          />
          <button
            type="submit"
            className="submit-btn"
            disabled={!query.trim() || isLoading}
            data-testid="chat-submit"
          >
            {t("search.submit")}
          </button>
        </form>
      </div>
    </div>
  );
};

export default SearchPage;
