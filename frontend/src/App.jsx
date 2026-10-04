import { useEffect, useRef, useState } from "react";
import "./App.css";

const API = import.meta.env.VITE_API_URL;

const TOPICS = [
  {
    icon: "⌘",
    title: "Transformer Architecture",
    description: "Attention, encoders and model design",
    question:
      "Explain the Transformer architecture and how self-attention works.",
  },
  {
    icon: "◈",
    title: "Research Papers",
    description: "Explore key findings and methods",
    question:
      "Summarize the main findings of the uploaded research papers.",
  },
  {
    icon: "✳",
    title: "Language Models",
    description: "Understand LLMs and their capabilities",
    question:
      "Explain how large language models work based on the uploaded papers.",
  },
  {
    icon: "⌕",
    title: "RAG & Embeddings",
    description: "Retrieval, vectors and semantic search",
    question:
      "Explain retrieval-augmented generation and embeddings using the uploaded papers.",
  },
];

function createSessionId() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }

  return `session-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function TypingIndicator() {
  return (
    <div className="bubble bot" aria-live="polite">
      <div className="loading-dots" aria-label="Creozen is thinking">
        <span />
        <span />
        <span />
      </div>
    </div>
  );
}

function SourceList({ sources }) {
  if (!sources?.length) return null;

  return (
    <div className="meta">
      <strong>Research sources</strong>
      <ul>
        {sources.map((source, index) => (
          <li key={`${source.source}-${source.page}-${index}`}>
            <span>{source.source}</span>
            {" — "}
            Page {source.page}
          </li>
        ))}
      </ul>
    </div>
  );
}

function AgentSteps({ steps }) {
  if (!steps?.length) return null;

  return (
    <details className="meta">
      <summary>View research steps ({steps.length})</summary>
      <ol>
        {steps.map((step, index) => (
          <li key={`${step.tool}-${index}`}>
            <strong>{step.tool}</strong>
            <pre
              style={{
                whiteSpace: "pre-wrap",
                overflowWrap: "anywhere",
                fontSize: "11px",
                color: "var(--text-secondary)",
              }}
            >
              {JSON.stringify(step.args, null, 2)}
            </pre>
          </li>
        ))}
      </ol>
    </details>
  );
}

function Message({ message }) {
  const isUser = message.role === "user";

  return (
    <div
      className={`bubble ${isUser ? "user" : "bot"}`}
      aria-label={isUser ? "Your message" : "Assistant response"}
    >
      <div className="text">{message.text}</div>

      {!isUser && (
        <>
          <SourceList sources={message.sources} />
          <AgentSteps steps={message.steps} />
        </>
      )}
    </div>
  );
}

export default function App() {
  const [sessionId] = useState(createSessionId);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const inputRef = useRef(null);
  const chatRef = useRef(null);

  useEffect(() => {
    const chat = chatRef.current;

    if (chat) {
      chat.scrollTo({
        top: chat.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [messages, loading]);

  async function sendMessage(text = input) {
    const question = text.trim();

    if (!question || loading) return;

    setError("");
    setInput("");
    setLoading(true);

    setMessages((current) => [
      ...current,
      {
        role: "user",
        text: question,
      },
    ]);

    try {
      if (!API) {
        throw new Error(
          "The API URL is not configured. Check frontend/.env.development."
        );
      }

      const response = await fetch(`${API}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          session_id: sessionId,
          message: question,
        }),
      });

      if (!response.ok) {
        let detail = "";

        try {
          const errorData = await response.json();
          detail = errorData.detail || "";
        } catch {
          // The server did not return JSON.
        }

        throw new Error(
          detail || `The server returned error ${response.status}.`
        );
      }

      const data = await response.json();

      setMessages((current) => [
        ...current,
        {
          role: "bot",
          text:
            data.answer ||
            "I couldn't generate an answer. Please try again.",
          sources: Array.isArray(data.sources) ? data.sources : [],
          steps: Array.isArray(data.steps) ? data.steps : [],
        },
      ]);
    } catch (err) {
      setError(
        err.message ||
        "Unable to connect to the backend. Check that your FastAPI server is running."
      );

      setMessages((current) => [
        ...current,
        {
          role: "bot",
          text:
            "I couldn't connect to the research assistant service. " +
            "Please check the backend server and try again.",
        },
      ]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }

  function handleSubmit(event) {
    event.preventDefault();
    sendMessage();
  }

  function handleNewChat() {
    if (loading) return;

    setMessages([]);
    setInput("");
    setError("");
    inputRef.current?.focus();
  }

  return (
    <div className="app">
      {/* Top navigation */}
      <nav className="topbar">
        <a
          className="brand"
          href="#home"
          onClick={(event) => {
            event.preventDefault();
            handleNewChat();
          }}
          aria-label="Creozen GenAI home"
        >
          <div className="brand-mark">
            C<span>.</span>
          </div>

          <div className="brand-name">
            CREOZEN <span>GENAI</span>
          </div>
        </a>

        <div className="topbar-status">
          <span className="status-dot" />
          RESEARCH ASSISTANT
        </div>
      </nav>

      <main className="main" id="home">
        {/* Main introduction */}
        <section className="hero">
          <div className="eyebrow">
            <span className="eyebrow-star">✦</span>
            AI-POWERED RESEARCH
          </div>

          <h1>
            Research deeper.
            <br />
            <span className="gradient-text">Understand more.</span>
          </h1>

          <p className="hero-description">
            Explore AI research papers, uncover key concepts, and get
            evidence-based answers grounded in your document collection.
          </p>

          <div className="hero-tags">
            <span>RESEARCH-DRIVEN</span>
            <span className="tag-line" />
            <span>DOCUMENT-GROUNDED</span>
            <span className="tag-line" />
            <span>AI-POWERED</span>
          </div>
        </section>

        {/* Chat workspace */}
        <section className="workspace">
          <div className="workspace-header">
            <div className="workspace-title">
              <div className="workspace-icon">✧</div>

              <div>
                <h2>Research workspace</h2>
                <p>Ask a question about your research papers</p>
              </div>
            </div>

            <div className="model-badge">
              <span className="status-dot" />
              LOCAL AI
            </div>
          </div>

          <div className="chat" ref={chatRef} aria-live="polite">
            {messages.length === 0 && !loading && (
              <div className="welcome">
                <div className="welcome-orbit" aria-hidden="true">
                  <div className="orbit orbit-outer" />
                  <div className="orbit orbit-inner" />

                  <div className="orbit-core">✧</div>

                  <span className="orbit-particle particle-one" />
                  <span className="orbit-particle particle-two" />
                  <span className="orbit-particle particle-three" />
                </div>

                <p className="welcome-kicker">YOUR RESEARCH STARTS HERE</p>

                <h3>What would you like to discover?</h3>

                <p className="welcome-description">
                  Choose a topic to get started, or ask your own question
                  about the AI research papers in your knowledge base.
                </p>

                <div className="topic-grid">
                  {TOPICS.map((topic) => (
                    <button
                      className="topic-card"
                      key={topic.title}
                      type="button"
                      onClick={() => sendMessage(topic.question)}
                      disabled={loading}
                    >
                      <span className="topic-icon" aria-hidden="true">
                        {topic.icon}
                      </span>

                      <span className="topic-copy">
                        <strong>{topic.title}</strong>
                        <span>{topic.description}</span>
                      </span>

                      <span className="topic-arrow" aria-hidden="true">
                        ↗
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((message, index) => (
              <Message
                key={`${message.role}-${index}`}
                message={message}
              />
            ))}

            {loading && <TypingIndicator />}
          </div>

          {/* Message composer */}
          <form className="inputRow" onSubmit={handleSubmit}>
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Ask something about your research..."
              aria-label="Your research question"
              disabled={loading}
              autoComplete="off"
            />

            <button
              type="submit"
              disabled={loading || !input.trim()}
              aria-label="Send message"
            >
              {loading ? "Thinking…" : "Ask ↗"}
            </button>
          </form>
        </section>

        {error && (
          <p
            role="alert"
            style={{
              maxWidth: "900px",
              margin: "12px auto 0",
              color: "#ffaaa8",
              fontSize: "13px",
            }}
          >
            {error}
          </p>
        )}

        <footer className="footer">
          <span>
            POWERED BY <strong>CREOZEN GENAI</strong>
          </span>

          <span>RESEARCH WITH CONTEXT</span>
        </footer>
      </main>
    </div>
  );
}