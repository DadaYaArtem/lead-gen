// src/components/CoverLetterGenerator.jsx
import { useState, useRef, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";
import axios from "axios";
import {
  Loader2,
  Send,
  Save,
  Trash2,
  AlertCircle,
  FileText,
  User,
  Bot,
  Plus,
  X,
  MessageSquare,
  CheckCircle2,
  Circle,
} from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "http://localhost:8000";
const API = `${BACKEND_URL}/api`;

const MAX_SESSIONS = 20;

function getUserId() {
  let id = localStorage.getItem("coverLetterUserId");
  if (!id) {
    id = `user_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    localStorage.setItem("coverLetterUserId", id);
  }
  return id;
}

export function CoverLetterGenerator() {
  const [userId] = useState(getUserId);
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [savedState, setSavedState] = useState(null);
  const [isSaved, setIsSaved] = useState(false);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingSessions, setIsLoadingSessions] = useState(false);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  // Загрузка списка сессий с сервера
  const loadSessions = useCallback(async () => {
    setIsLoadingSessions(true);
    try {
      const res = await axios.get(`${API}/sessions/${userId}`);
      // Сортировка по timestamp (новые сверху)
      const sessionsData = (res.data.sessions || []).sort((a, b) => b.timestamp - a.timestamp);
      setSessions(sessionsData);
      if (sessionsData.length > 0 && !currentSessionId) {
        const active = sessionsData.find(s => s.active);
        const target = active || sessionsData[0];
        await loadSession(target.id);
      } else if (sessionsData.length === 0) {
        await createNewSession();
      }
    } catch (e) {
      console.error("Failed to load sessions:", e);
      toast.error("Failed to load sessions");
    } finally {
      setIsLoadingSessions(false);
    }
  }, [userId]);

  // Загрузка конкретной сессии
  const loadSession = useCallback(async (sessionId) => {
    try {
      const res = await axios.get(`${API}/sessions/${userId}/${sessionId}`);
      const session = res.data.session;
      setCurrentSessionId(sessionId);
      setMessages(session.messages || []);
      setSavedState(session.saved_state || null);
      setIsSaved(session.saved || false);
      // Обновить список сессий, чтобы отметить активную и обновить метаданные
      setSessions(prev => prev.map(s => ({
        ...s,
        active: s.id === sessionId,
        saved: s.id === sessionId ? session.saved : s.saved,
        message_count: session.messages ? session.messages.length : 0,
      })));
      setInput("");
      // Прокрутка вниз после загрузки
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
    } catch (e) {
      console.error("Failed to load session:", e);
      toast.error("Failed to load session");
    }
  }, [userId]);

  // Загрузка сессий при монтировании
  useEffect(() => {
    loadSessions();
  }, []);

  // Прокрутка вниз при изменении сообщений
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  // Создание новой сессии
  const createNewSession = useCallback(async () => {
    try {
      const res = await axios.post(`${API}/sessions/create`, {
        user_id: userId,
        title: "New session",
      });
      const newSession = res.data.session;
      setSessions(prev => {
        let updated = prev.map(s => ({ ...s, active: false }));
        if (updated.length >= MAX_SESSIONS) {
          const sorted = [...updated].sort((a, b) => a.timestamp - b.timestamp);
          sorted.shift();
          updated = sorted;
        }
        return [...updated, { ...newSession, active: true, saved: false, message_count: 0 }];
      });
      setCurrentSessionId(newSession.id);
      setMessages([]);
      setSavedState(null);
      setIsSaved(false);
      setInput("");
      toast.info("New session created");
    } catch (e) {
      console.error("Failed to create session:", e);
      toast.error("Failed to create session");
    }
  }, [userId]);

  // Переключение на сессию
  const switchSession = useCallback((sessionId) => {
    loadSession(sessionId);
  }, [loadSession]);

  // Удаление сессии
  const deleteSession = useCallback(async (sessionId, e) => {
    e?.stopPropagation();
    if (!window.confirm("Delete this session?")) return;
    try {
      await axios.delete(`${API}/sessions/${userId}/${sessionId}`);
      setSessions(prev => prev.filter(s => s.id !== sessionId));
      if (currentSessionId === sessionId) {
        const remaining = sessions.filter(s => s.id !== sessionId);
        if (remaining.length > 0) {
          await loadSession(remaining[0].id);
        } else {
          setCurrentSessionId(null);
          setMessages([]);
          setSavedState(null);
          setIsSaved(false);
          await createNewSession();
        }
      }
    } catch (e) {
      console.error("Failed to delete session:", e);
      toast.error("Failed to delete session");
    }
  }, [userId, currentSessionId, sessions, loadSession, createNewSession]);

  // Отправка сообщения
  const sendMessage = async () => {
    const text = input.trim();
    if (!text || isLoading) return;

    let sessionId = currentSessionId;
    if (!sessionId) {
      await createNewSession();
      sessionId = currentSessionId;
      if (!sessionId) {
        toast.error("Failed to create session");
        return;
      }
    }

    const userMsg = { role: "user", content: text };
    const updatedMessages = [...messages, userMsg];
    setMessages(updatedMessages);
    setInput("");
    setIsLoading(true);

    try {
      const payload = {
        job_description: text,
        user_id: userId,
        session_id: sessionId,
      };

      const res = await axios.post(`${API}/generate-cover-letter`, payload);
      const data = res.data;
      const result = data.result;
      const newSavedState = data.saved_state;

      // Перезагружаем сессию, чтобы обновить сообщения и состояние
      await loadSession(sessionId);
      toast.success("Cover letters generated");
    } catch (e) {
      const msg = e.response?.data?.detail || e.message || "Generation failed";
      toast.error(msg);
      setMessages(messages);
      setInput(text);
    } finally {
      setIsLoading(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  };

  // Сброс сессии (создание новой)
  const handleReset = async () => {
    await createNewSession();
  };

  const handleSave = async (profileName, profileData) => {
    const jobEval = profileData.job_evaluation || {};
    if (jobEval.decision !== "PASS") {
      toast.info(`Profile ${profileName} is SKIP, not saved`);
      return;
    }
    const letterParts = profileData.letter_parts || {};
    const fullLetter = [
      letterParts.hook,
      letterParts.bridge,
      letterParts.case1_text,
      letterParts.case2_text,
      letterParts.closing,
      letterParts.cta,
      letterParts.signature,
    ]
      .filter(Boolean)
      .join("\n\n");
    try {
      const firstUserMsg = messages.find(m => m.role === "user");
      await axios.post(`${API}/save-cover-letter`, {
        job_description: firstUserMsg ? firstUserMsg.content : "",
        profile_name: profileName,
        cover_letter: fullLetter,
        screening_answers: profileData.screening_answers || "",
        user_id: userId,
        session_id: currentSessionId,
      });
      setIsSaved(true);
      setSessions(prev => prev.map(s => s.id === currentSessionId ? { ...s, saved: true } : s));
      toast.success(`Saved ${profileName} to Google Sheets`);
    } catch (e) {
      const msg = e.response?.data?.detail || e.message || "Save failed";
      toast.error(`Save failed: ${msg}`);
    }
  };

  // Рендер карточки профиля – используется внутри renderAssistantMessage
  const renderProfileCard = (name, data, isLast, isSaved) => {
    const jobEval = data.job_evaluation || {};
    const letterParts = data.letter_parts || {};
    const screening = data.screening_answers || "";
    const isPass = jobEval.decision === "PASS";

    return (
      <Card key={name} className="border-slate-200 shadow-sm overflow-hidden">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base font-semibold flex items-center gap-2">
              <User className="h-4 w-4 text-slate-400" />
              {name}
            </CardTitle>
            <Badge
              variant={isPass ? "default" : "destructive"}
              className={isPass ? "bg-emerald-100 text-emerald-700 hover:bg-emerald-100" : ""}
            >
              {isPass ? "PASS" : "SKIP"}
            </Badge>
          </div>
          <p className="text-xs text-slate-500">{jobEval.reasoning || "No reasoning"}</p>
          {jobEval.observations && jobEval.observations.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1">
              {jobEval.observations.map((obs, i) => (
                <span key={i} className="text-[10px] bg-slate-100 text-slate-500 rounded px-1.5 py-0.5">
                  {obs.type}
                </span>
              ))}
            </div>
          )}
        </CardHeader>
        <CardContent className="space-y-3">
          {isPass && (
            <>
              {data.selected_cases && data.selected_cases.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-slate-500">Selected Cases</p>
                  <ul className="mt-1 space-y-1">
                    {data.selected_cases.map((c, i) => (
                      <li key={i} className="text-xs text-slate-700">
                        <span className="font-medium">{c.name}</span>
                        {c.link && (
                          <a href={c.link} target="_blank" rel="noopener noreferrer" className="ml-1 text-[#10b981] hover:underline">
                            (link)
                          </a>
                        )}
                        <span className="block text-slate-500 text-[11px]">{c.reasoning}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <div>
                <p className="text-xs font-medium text-slate-500">Cover Letter</p>
                <div className="mt-1 text-sm text-slate-700 whitespace-pre-wrap bg-slate-50 p-3 rounded-lg border border-slate-100 max-h-60 overflow-y-auto">
                  {[
                    letterParts.hook,
                    letterParts.bridge,
                    letterParts.case1_text,
                    letterParts.case2_text,
                    letterParts.closing,
                    letterParts.cta,
                    letterParts.signature,
                  ]
                    .filter(Boolean)
                    .join("\n\n")}
                </div>
              </div>
              {screening && (
                <div>
                  <p className="text-xs font-medium text-slate-500">Screening Answers</p>
                  <div className="mt-1 text-sm text-slate-700 whitespace-pre-wrap bg-slate-50 p-3 rounded-lg border border-slate-100 max-h-40 overflow-y-auto">
                    {screening}
                  </div>
                </div>
              )}
              {isLast && !isSaved && (
                <Button
                  onClick={() => handleSave(name, data)}
                  size="sm"
                  variant="outline"
                  className="border-[#10b981] text-[#10b981] hover:bg-[#10b981]/10"
                >
                  <Save className="h-3.5 w-3.5 mr-1.5" />
                  Save to Google Sheets
                </Button>
              )}
            </>
          )}
        </CardContent>
      </Card>
    );
  };

  const renderAssistantMessage = (msg) => {
    if (!msg.result) return <p>{msg.content}</p>;
    const results = msg.result;
    const hasPass = Object.values(results).some(d => d.job_evaluation?.decision === "PASS");
    const isLast = messages.indexOf(msg) === messages.length - 1;

    return (
      <div className="space-y-4">
        {Object.entries(results).map(([name, data]) =>
          renderProfileCard(name, data, isLast, isSaved)
        )}
        {!hasPass && (
          <div className="text-center py-4">
            <AlertCircle className="h-8 w-8 text-slate-300 mx-auto mb-2" />
            <p className="text-sm text-slate-500">All profiles were SKIPped for this job</p>
          </div>
        )}
      </div>
    );
  };

  // Текущая сессия для отображения в заголовке
  const currentSession = sessions.find(s => s.id === currentSessionId);

  // Получение количества PASS из последнего сообщения модели
  const getPassCount = (msgs) => {
    for (let i = msgs.length - 1; i >= 0; i--) {
      const msg = msgs[i];
      if (msg.role === "assistant" && msg.result) {
        const results = msg.result;
        let passCount = 0;
        for (const [name, data] of Object.entries(results)) {
          if (data.job_evaluation?.decision === "PASS") passCount++;
        }
        return passCount;
      }
    }
    return 0;
  };

  const passCount = getPassCount(messages);

  return (
    <div className="flex h-full bg-[#f8fafc]" data-testid="cover-letter-page">
      {/* Sidebar со списком сессий */}
      <aside className="w-64 shrink-0 border-r border-slate-200 bg-white flex flex-col">
        <div className="px-3 py-3 border-b border-slate-100 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-[#1a2744] flex items-center gap-2">
            <FileText className="h-4 w-4 text-[#10b981]" />
            Sessions
          </h2>
          <Button
            onClick={createNewSession}
            size="sm"
            variant="ghost"
            className="h-7 w-7 p-0 text-slate-500 hover:text-[#10b981]"
            title="New session"
            disabled={isLoadingSessions}
          >
            <Plus className="h-4 w-4" />
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto py-2">
          {isLoadingSessions ? (
            <div className="flex items-center justify-center py-4">
              <Loader2 className="h-4 w-4 animate-spin text-slate-400" />
            </div>
          ) : sessions.length === 0 ? (
            <p className="text-xs text-slate-400 text-center py-4">No sessions yet</p>
          ) : (
            sessions.map((s) => {
              // Статус: количество PASS в последнем ответе модели
              let passCount = 0;
              const msgs = s.messages || [];
              for (let i = msgs.length - 1; i >= 0; i--) {
                const msg = msgs[i];
                if (msg.role === "assistant" && msg.result) {
                  const results = msg.result;
                  for (const [name, data] of Object.entries(results)) {
                    if (data.job_evaluation?.decision === "PASS") passCount++;
                  }
                  break;
                }
              }
              const saved = s.saved || false;
              return (
                <div
                  key={s.id}
                  onClick={() => switchSession(s.id)}
                  className={`group flex items-center justify-between px-3 py-2 mx-1 rounded-lg cursor-pointer transition-colors ${
                    s.id === currentSessionId
                      ? "bg-emerald-50 border border-emerald-200"
                      : "hover:bg-slate-50"
                  }`}
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-slate-700 truncate">
                      {s.title || "New session"}
                    </p>
                    <div className="flex items-center gap-2 text-[10px] text-slate-400">
                      <span>{passCount} PASS</span>
                      <span>·</span>
                      {saved ? (
                        <span className="flex items-center gap-0.5 text-emerald-600">
                          <CheckCircle2 className="h-3 w-3" /> saved
                        </span>
                      ) : (
                        <span className="flex items-center gap-0.5 text-amber-500">
                          <Circle className="h-3 w-3" /> not saved
                        </span>
                      )}
                    </div>
                  </div>
                  <Button
                    onClick={(e) => deleteSession(s.id, e)}
                    size="sm"
                    variant="ghost"
                    className="h-6 w-6 p-0 text-slate-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </div>
              );
            })
          )}
        </div>
        <div className="px-3 py-2 border-t border-slate-100 text-[10px] text-slate-400 text-center">
          {sessions.length} / {MAX_SESSIONS} sessions
        </div>
      </aside>

      {/* Основная область чата */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Заголовок с информацией о текущей сессии */}
        <div className="px-4 py-2 border-b border-slate-200 bg-white shrink-0 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MessageSquare className="h-4 w-4 text-[#10b981]" />
            <span className="text-sm font-medium text-slate-700">
              {currentSession ? currentSession.title : "No session"}
            </span>
            <Badge variant="outline" className="text-[10px] font-mono">
              {userId.slice(0, 6)}…
            </Badge>
          </div>
        </div>

        {/* Сообщения */}
        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4" data-testid="cover-letter-chat-messages">
          {messages.length === 0 && !isLoading && (
            <EmptyState onSuggest={(text) => { setInput(text); inputRef.current?.focus(); }} />
          )}

          {messages.map((msg, i) => (
            <ChatBubble
              key={i}
              message={msg}
              renderAssistant={renderAssistantMessage}
            />
          ))}

          {isLoading && (
            <div className="flex items-start gap-2" data-testid="cover-letter-loading">
              <div className="w-7 h-7 rounded-full bg-[#10b981]/10 border border-[#10b981]/20 flex items-center justify-center shrink-0">
                <Bot className="h-3.5 w-3.5 text-[#10b981]" />
              </div>
              <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-sm px-3.5 py-2.5 shadow-sm">
                <div className="flex items-center gap-2 text-slate-400 text-sm">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Generating cover letters…</span>
                </div>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Поле ввода */}
        <div className="px-4 pb-4 pt-2 border-t border-slate-200 bg-white shrink-0">
          <div className="flex items-end gap-2">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  sendMessage();
                }
              }}
              placeholder="Paste job description here… (Shift+Enter for new line)"
              rows={3}
              className="flex-1 resize-none rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#10b981]/40 focus:border-[#10b981] transition-colors"
              disabled={isLoading}
              data-testid="cover-letter-input"
            />
            <Button
              onClick={sendMessage}
              disabled={!input.trim() || isLoading || !currentSessionId}
              size="icon"
              className="h-11 w-11 shrink-0 rounded-xl bg-[#10b981] hover:bg-[#0d9469] text-white disabled:opacity-40"
              data-testid="cover-letter-send-button"
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

// Компонент ChatBubble – стили поменяны местами
function ChatBubble({ message, renderAssistant }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex items-start gap-2 ${isUser ? "flex-row-reverse" : ""}`}>
      <div
        className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 ${
          isUser
            ? "bg-[#10b981]/10 border border-[#10b981]/20"
            : "bg-[#1a2744] text-white"
        }`}
      >
        {isUser ? (
          <User className="h-3.5 w-3.5 text-[#10b981]" />
        ) : (
          <Bot className="h-3.5 w-3.5" />
        )}
      </div>
      <div className={`flex flex-col gap-1.5 max-w-[85%] ${isUser ? "items-end" : "items-start"}`}>
        <div
          className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
            isUser
              ? "bg-white border border-slate-200 text-slate-800 rounded-tr-sm shadow-sm"
              : "bg-[#1a2744] text-white rounded-tl-sm"
          }`}
        >
          {isUser ? (
            <div className="whitespace-pre-wrap">{message.content}</div>
          ) : (
            renderAssistant(message)
          )}
        </div>
      </div>
    </div>
  );
}

// EmptyState и SuggestionChip без изменений
function EmptyState({ onSuggest }) {
  const suggestions = [
    "Agentic AI Developer for Tele-health Company (HIPAA - Ongoing Hourly)",
    "Full Stack Developer for SaaS platform",
    "Senior AI/ML Engineer with RAG experience",
  ];
  return (
    <div className="flex flex-col items-center py-12 text-center px-8" data-testid="cover-letter-empty">
      <div className="w-14 h-14 rounded-2xl bg-emerald-50 border border-emerald-100 flex items-center justify-center mb-4">
        <FileText className="h-7 w-7 text-[#10b981]" />
      </div>
      <h3 className="text-base font-semibold text-[#1a2744] mb-1">Generate Cover Letters</h3>
      <p className="text-sm text-slate-500 mb-6 max-w-sm">
        Paste a job description and get personalised cover letters for all profiles.
      </p>
      <div className="grid grid-cols-1 gap-2 w-full max-w-lg">
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