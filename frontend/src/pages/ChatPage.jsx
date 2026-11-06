import { useCallback, useEffect, useRef, useState } from "react";

import AnswerSources from "../components/AnswerSources.jsx";
import { describeError } from "../formatting.js";
import { askQuestion, deleteSession, getSessionMessages, listSessions } from "../services/api/chatApi.js";
import { getCapabilities, listConfigurations } from "../services/api/modelConfigApi.js";

function fromHistory(message) {
  return {
    id: message.id,
    role: message.role,
    content: message.content,
    insufficient: message.insufficient_context,
    error: message.error_message,
    citations: message.citations,
    sources: message.sources,
    metrics: message.role === "assistant" && !message.error_message ? message.metrics : null,
  };
}

export default function ChatPage() {
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const [configs, setConfigs] = useState([]);
  const [configId, setConfigId] = useState("");
  const [capabilities, setCapabilities] = useState(null);
  const endRef = useRef(null);

  const loadSessions = useCallback(async () => {
    try {
      setSessions((await listSessions()).items);
    } catch (caught) {
      setError(describeError(caught));
    }
  }, []);

  useEffect(() => {
    loadSessions();
    listConfigurations()
      .then((result) => setConfigs(result.items))
      .catch(() => setConfigs([]));
    getCapabilities()
      .then(setCapabilities)
      .catch(() => setCapabilities(null));
  }, [loadSessions]);

  useEffect(() => {
    endRef.current?.scrollIntoView?.({ behavior: "smooth" });
  }, [messages]);

  async function openSession(sessionId) {
    setError(null);
    setActiveSessionId(sessionId);
    try {
      setMessages((await getSessionMessages(sessionId)).items.map(fromHistory));
    } catch (caught) {
      setError(describeError(caught));
    }
  }

  function startNewConversation() {
    setActiveSessionId(null);
    setMessages([]);
    setError(null);
  }

  async function handleDeleteSession(session) {
    if (!window.confirm(`Xóa cuộc hội thoại "${session.title}"?`)) return;
    try {
      await deleteSession(session.id);
      if (session.id === activeSessionId) startNewConversation();
      await loadSessions();
    } catch (caught) {
      setError(describeError(caught));
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const text = question.trim();
    if (!text || sending) return;
    setSending(true);
    setError(null);
    setQuestion("");
    setMessages((current) => [...current, { id: `local-${Date.now()}`, role: "user", content: text }]);
    try {
      const answer = await askQuestion({
        question: text,
        sessionId: activeSessionId,
        modelConfigurationId: configId || undefined,
      });
      setMessages((current) => [
        ...current,
        {
          id: answer.message_id,
          role: "assistant",
          content: answer.answer,
          insufficient: answer.insufficient_context,
          mode: answer.mode,
          citations: answer.citations,
          sources: answer.sources,
          metrics: answer.metrics,
        },
      ]);
      if (!activeSessionId) {
        setActiveSessionId(answer.session_id);
        loadSessions();
      }
    } catch (caught) {
      setMessages((current) => [
        ...current,
        { id: `error-${Date.now()}`, role: "assistant", content: "", error: describeError(caught) },
      ]);
    } finally {
      setSending(false);
    }
  }

  return (
    <section className="chat-layout">
      <aside className="chat-sessions" aria-label="Các cuộc hội thoại">
        <button type="button" className="button button--primary" onClick={startNewConversation}>
          Cuộc hội thoại mới
        </button>
        {sessions.length === 0 ? (
          <p className="muted">Chưa có cuộc hội thoại nào.</p>
        ) : (
          <ul>
            {sessions.map((session) => (
              <li key={session.id} className={session.id === activeSessionId ? "active" : ""}>
                <button type="button" className="chat-sessions__open" onClick={() => openSession(session.id)}>
                  {session.title}
                </button>
                <button
                  type="button"
                  className="chat-sessions__delete"
                  aria-label={`Xóa cuộc hội thoại ${session.title}`}
                  onClick={() => handleDeleteSession(session)}
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
        )}
      </aside>

      <div className="chat-main">
        <div className="chat-toolbar">
          <h1>Hỏi đáp</h1>
          <label className="chat-config">
            Cấu hình
            <select value={configId} onChange={(event) => setConfigId(event.target.value)}>
              <option value="">Mặc định của máy chủ</option>
              {configs.map((config) => (
                <option key={config.id} value={config.id}>
                  {config.name}
                </option>
              ))}
            </select>
          </label>
        </div>

        {capabilities && !capabilities.llm_configured && (
          <p className="notice" role="note">
            Máy chủ chưa cấu hình LLM: câu trả lời là các đoạn tài liệu liên quan nhất, chưa được viết lại bằng mô hình ngôn ngữ.
          </p>
        )}

        <div className="chat-messages" aria-live="polite">
          {messages.length === 0 && (
            <p className="empty-state">Đặt câu hỏi về các tài liệu bạn đã tải lên. Câu trả lời luôn kèm nguồn.</p>
          )}
          {messages.map((message) => (
            <article key={message.id} className={`message message--${message.role}`}>
              <div className="message__role">{message.role === "user" ? "Bạn" : "Hệ thống"}</div>
              {message.error ? (
                <p className="alert alert--error" role="alert">
                  {message.error}
                </p>
              ) : (
                <>
                  {message.role === "assistant" && (message.mode || message.insufficient) && (
                    <div className="message__badges">
                      {message.mode === "extractive" && <span className="badge badge--uploaded">Không dùng LLM</span>}
                      {message.mode === "llm" && <span className="badge badge--ready">LLM</span>}
                      {message.insufficient && <span className="badge badge--processing">Không đủ thông tin</span>}
                    </div>
                  )}
                  <div className="message__content">{message.content}</div>
                  {message.role === "assistant" && (
                    <AnswerSources citations={message.citations} sources={message.sources} metrics={message.metrics} />
                  )}
                </>
              )}
            </article>
          ))}
          {sending && <p className="page-message">Đang tìm trong tài liệu và soạn câu trả lời...</p>}
          <div ref={endRef} />
        </div>

        {error && (
          <p className="alert alert--error" role="alert">
            {error}
          </p>
        )}

        <form className="chat-input" onSubmit={handleSubmit}>
          <label className="visually-hidden" htmlFor="chat-question">
            Câu hỏi
          </label>
          <textarea
            id="chat-question"
            rows={2}
            maxLength={2000}
            placeholder="Ví dụ: Thời hạn nộp hồ sơ là bao lâu?"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                handleSubmit(event);
              }
            }}
          />
          <button type="submit" className="button button--primary" disabled={sending || !question.trim()}>
            Gửi
          </button>
        </form>
      </div>
    </section>
  );
}
