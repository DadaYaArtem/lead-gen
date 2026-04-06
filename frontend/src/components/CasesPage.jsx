import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import {
  BookOpen,
  Send,
  Bot,
  User,
  Loader2,
  Info,
  Tag,
  Building2,
  Sparkles,
  MessageSquare,
} from "lucide-react";
import { MarkdownMessage } from "@/components/MarkdownMessage";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "http://localhost:8000";
const API = `${BACKEND_URL}/api`;

export function CasesPage() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [cases, setCases] = useState([]);
  const [casesLoading, setCasesLoading] = useState(true);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  // Load available cases from knowledge base
  useEffect(() => {
    const fetchCases = async () => {
      try {
        const res = await fetch(`${API}/knowledge-base`);
        if (!res.ok) throw new Error(`Server ${res.status}`);
        const data = await res.json();
        setCases(data.cases || []);
      } catch (e) {
        console.error("Failed to load knowledge base:", e);
        toast.error("Could not load case library");
      } finally {
        setCasesLoading(false);
      }
    };
    fetchCases();
  }, []);

  // Scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  // Focus input on mount
  useEffect(() => {
    setTimeout(() => inputRef.current?.focus(), 100);
  }, []);

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || isLoading) return;

    const userMsg = { role: "user", content: text };
    const updatedMessages = [...messages, userMsg];
    setMessages(updatedMessages);
    setInput("");
    setIsLoading(true);

    try {
      const res = await fetch(`${API}/case-chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: updatedMessages }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Server error ${res.status}`);
      }

      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.reply,
          retrieved_cases: data.retrieved_cases || [],
        },
      ]);
    } catch (e) {
      toast.error(`Chat error: ${e.message}`);
      setMessages((prev) => prev.slice(0, -1));
      setInput(text);
    } finally {
      setIsLoading(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="flex h-full bg-[#f8fafc]" data-testid="cases-page">
      {/* ── Sidebar ── */}
      <aside
        className="w-72 shrink-0 border-r border-slate-200 bg-white flex flex-col overflow-hidden"
        data-testid="cases-sidebar"
      >
        <div className="px-4 py-4 border-b border-slate-100">
          <h2 className="text-sm font-semibold text-[#1a2744] flex items-center gap-2">
            <BookOpen className="h-4 w-4 text-[#10b981]" />
            Case Library
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            {casesLoading
              ? "Loading…"
              : `${cases.length} case${cases.length !== 1 ? "s" : ""} in knowledge base`}
          </p>
        </div>

        <div className="flex-1 overflow-y-auto py-2">
          {casesLoading ? (
            <div className="flex items-center justify-center py-10">
              <Loader2 className="h-5 w-5 animate-spin text-slate-300" />
            </div>
          ) : cases.length === 0 ? (
            <p className="text-xs text-slate-400 text-center py-8 px-4">
              No cases found. Add Markdown files to{" "}
              <code className="font-mono text-xs">backend/knowledge_base/cases/</code>
            </p>
          ) : (
            cases.map((c) => (
              <CaseCard key={c.id} case_={c} />
            ))
          )}
        </div>

        <div className="px-4 py-3 border-t border-slate-100 bg-slate-50">
          <p className="text-[10px] text-slate-400 leading-relaxed">
            Cases are retrieved automatically based on your query using semantic similarity.
          </p>
        </div>
      </aside>

      {/* ── Chat area ── */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Banner */}
        <div className="mx-4 mt-4 mb-2 flex items-start gap-2 rounded-lg bg-emerald-50 border border-emerald-200 px-4 py-3 shrink-0">
          <Info className="h-4 w-4 text-emerald-600 mt-0.5 shrink-0" />
          <p className="text-xs text-emerald-700 leading-relaxed">
            <strong>Standalone Case Assistant</strong> — ask about Interexy's portfolio without
            needing a specific lead. GPT-5.1 retrieves relevant cases and answers using them.
            Try: <em>"What healthcare experience do we have?"</em> or <em>"Show me IoT projects."</em>
          </p>
        </div>

        {/* Messages */}
        <div
          className="flex-1 overflow-y-auto px-4 py-3 space-y-4"
          data-testid="case-chat-messages"
        >
          {messages.length === 0 && !isLoading && (
            <EmptyState onSuggest={(text) => { setInput(text); inputRef.current?.focus(); }} />
          )}

          {messages.map((msg, i) => (
            <CaseChatBubble key={i} message={msg} />
          ))}

          {isLoading && (
            <div className="flex items-start gap-2" data-testid="case-chat-loading">
              <div className="w-7 h-7 rounded-full bg-[#10b981]/10 border border-[#10b981]/20 flex items-center justify-center shrink-0">
                <Bot className="h-3.5 w-3.5 text-[#10b981]" />
              </div>
              <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-sm px-3.5 py-2.5 shadow-sm">
                <div className="flex items-center gap-2 text-slate-400 text-sm">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Searching case library…</span>
                </div>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="px-4 pb-4 pt-2 border-t border-slate-200 bg-white shrink-0">
          <div className="flex items-end gap-2">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about our case portfolio… e.g. 'What fintech cases do we have?'"
              rows={2}
              className="flex-1 resize-none rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#10b981]/40 focus:border-[#10b981] transition-colors"
              disabled={isLoading}
              data-testid="case-chat-input"
            />
            <Button
              onClick={sendMessage}
              disabled={!input.trim() || isLoading}
              size="icon"
              className="h-11 w-11 shrink-0 rounded-xl bg-[#10b981] hover:bg-[#0d9469] text-white disabled:opacity-40"
              data-testid="case-chat-send-button"
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </div>
          <p className="text-[10px] text-slate-400 mt-1.5 pl-1">
            Press Enter to send · Shift+Enter for new line
          </p>
        </div>
      </main>
    </div>
  );
}

function CaseCard({ case_ }) {
  const isPopulated = case_.is_populated;

  return (
    <div
      className={`mx-3 mb-1 rounded-lg border px-3 py-2.5 transition-colors ${
        isPopulated
          ? "border-slate-200 bg-white hover:border-[#10b981]/40 hover:bg-emerald-50/30"
          : "border-dashed border-slate-200 bg-slate-50 opacity-60"
      }`}
      data-testid={`case-card-${case_.id}`}
    >
      <p className="text-xs font-medium text-[#1a2744] leading-tight">{case_.title}</p>

      {case_.industry && (
        <div className="flex items-center gap-1 mt-1">
          <Building2 className="h-3 w-3 text-slate-400 shrink-0" />
          <span className="text-[10px] text-slate-500">{case_.industry}</span>
        </div>
      )}

      {case_.tags && case_.tags.length > 0 && (
        <div className="flex items-start gap-1 mt-1.5 flex-wrap">
          <Tag className="h-3 w-3 text-slate-400 shrink-0 mt-0.5" />
          {case_.tags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="text-[9px] bg-slate-100 text-slate-500 rounded px-1 py-0.5 font-mono"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      {!isPopulated && (
        <p className="text-[9px] text-slate-400 mt-1 italic">placeholder — no content yet</p>
      )}
    </div>
  );
}

function CaseChatBubble({ message }) {
  const isUser = message.role === "user";
  const retrievedCases = message.retrieved_cases || [];

  return (
    <div className={`flex items-start gap-2 ${isUser ? "flex-row-reverse" : ""}`}>
      {/* Avatar */}
      <div
        className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 ${
          isUser
            ? "bg-[#1a2744] text-white"
            : "bg-[#10b981]/10 border border-[#10b981]/20"
        }`}
      >
        {isUser ? (
          <User className="h-3.5 w-3.5" />
        ) : (
          <Bot className="h-3.5 w-3.5 text-[#10b981]" />
        )}
      </div>

      <div className={`flex flex-col gap-1.5 max-w-[85%] ${isUser ? "items-end" : "items-start"}`}>
        {/* Bubble */}
        <div
          className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
            isUser
              ? "bg-[#1a2744] text-white rounded-tr-sm whitespace-pre-wrap"
              : "bg-white border border-slate-200 text-slate-800 rounded-tl-sm shadow-sm"
          }`}
        >
          <MarkdownMessage content={message.content} isUser={isUser} />
        </div>

        {/* Retrieved cases pills */}
        {!isUser && retrievedCases.length > 0 && (
          <div
            className="flex flex-wrap gap-1.5 pl-1"
            data-testid="retrieved-cases-pills"
          >
            <span className="text-[10px] text-slate-400 flex items-center gap-0.5">
              <Sparkles className="h-3 w-3" />
              Used:
            </span>
            {retrievedCases.map((c) => (
              <span
                key={c.id}
                title={`Relevance: ${Math.round(c.score * 100)}%`}
                className="text-[10px] bg-emerald-50 border border-emerald-200 text-emerald-700 rounded-full px-2 py-0.5 font-medium"
                data-testid={`case-pill-${c.id}`}
              >
                {c.title} · {Math.round(c.score * 100)}%
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function EmptyState({ onSuggest }) {
  const suggestions = [
    "What healthcare experience do we have?",
    "Show me cases with IoT or Bluetooth",
    "Which cases are best for a fintech lead?",
    "Summarise our energy sector projects",
  ];

  return (
    <div className="flex flex-col items-center py-12 text-center px-8" data-testid="case-chat-empty">
      <div className="w-14 h-14 rounded-2xl bg-emerald-50 border border-emerald-100 flex items-center justify-center mb-4">
        <MessageSquare className="h-7 w-7 text-[#10b981]" />
      </div>
      <h3 className="text-base font-semibold text-[#1a2744] mb-1">Ask about our portfolio</h3>
      <p className="text-sm text-slate-500 mb-6 max-w-sm">
        GPT-5.1 will search the case library and answer based on real Interexy projects.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-lg">
        {suggestions.map((s) => (
          <SuggestionChip key={s} text={s} onSuggest={onSuggest} />
        ))}
      </div>
    </div>
  );
}

function SuggestionChip({ text, onSuggest }) {
  return (
    <button
      className="text-left text-xs px-3 py-2 rounded-lg border border-slate-200 bg-white text-slate-600 hover:border-[#10b981]/40 hover:bg-emerald-50/40 hover:text-[#1a2744] transition-colors"
      data-testid="suggestion-chip"
      onClick={() => onSuggest(text)}
    >
      {text}
    </button>
  );
}
