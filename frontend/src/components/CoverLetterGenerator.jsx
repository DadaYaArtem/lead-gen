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
const STATUS_POLL_INTERVAL = 3000;

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
  const [savedProfiles, setSavedProfiles] = useState(new Set());
  const [isGenerating, setIsGenerating] = useState(false);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingSessions, setIsLoadingSessions] = useState(false);
  const [isCreatingSession, setIsCreatingSession] = useState(false);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);
  const statusPollInterval = useRef(null);

  const currentSessionIdRef = useRef(currentSessionId);
  useEffect(() => {
    currentSessionIdRef.current = currentSessionId;
  }, [currentSessionId]);

  // -------------------------------------------------------------------------
  // Load a single session from the server and update all local state
  // -------------------------------------------------------------------------
  const loadSession = useCallback(async (sessionId) => {
    try {
      const res = await axios.get(`${API}/sessions/${userId}/${sessionId}`);
      const session = res.data.session;
      setCurrentSessionId(sessionId);
      currentSessionIdRef.current = sessionId;
      setMessages(session.messages || []);
      setSavedState(session.saved_state || null);
      const alreadySaved = Object.keys(session.profile_rows || {});
      setSavedProfiles(new Set(alreadySaved));
      setIsGenerating(session.is_generating || false);
      setSessions(prev => prev.map(s => {
        if (s.id === sessionId) {
          return {
            ...s,
            active: true,
            saved: session.saved || false,
            message_count: session.messages ? session.messages.length : 0,
            messages: session.messages || [],
            saved_state: session.saved_state || null,
            pass_count: session.pass_count || 0,
            is_generating: session.is_generating || false,
            title: session.title || s.title,
          };
        }
        return { ...s, active: false };
      }));
      setInput("");
      localStorage.setItem("coverLetterCurrentSessionId", sessionId);
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
    } catch (e) {
      console.error("Failed to load session:", e);
      toast.error("Failed to load session");
    }
  }, [userId]);

  // -------------------------------------------------------------------------
  // Create a new session on the server and switch to it
  // -------------------------------------------------------------------------
  const createNewSession = useCallback(async () => {
    if (isCreatingSession) return null;
    setIsCreatingSession(true);
    try {
      const res = await axios.post(`${API}/sessions/create`, {
        user_id: userId,
        title: "New session",
      });
      const newSession = res.data.session;
      const sessionId = newSession.id || res.data.session_id;
      setSessions(prev => {
        let updated = prev.map(s => ({ ...s, active: false }));
        if (updated.length >= MAX_SESSIONS) {
          const sorted = [...updated].sort((a, b) => b.timestamp - a.timestamp);
          sorted.pop();
          updated = sorted;
        }
        return [{
          ...newSession,
          id: sessionId,
          active: true,
          saved: false,
          message_count: 0,
          messages: [],
          saved_state: null,
          pass_count: 0,
          is_generating: false,
        }, ...updated];
      });
      setCurrentSessionId(sessionId);
      currentSessionIdRef.current = sessionId;
      localStorage.setItem("coverLetterCurrentSessionId", sessionId);
      setMessages([]);
      setSavedState(null);
      setSavedProfiles(new Set());
      setIsGenerating(false);
      setInput("");
      toast.info("New session created");
      return sessionId;
    } catch (e) {
      console.error("Failed to create session:", e);
      toast.error("Failed to create session");
      return null;
    } finally {
      setIsCreatingSession(false);
    }
  }, [userId, isCreatingSession]);

  // -------------------------------------------------------------------------
  // Poll generation status for the currently-active session
  // -------------------------------------------------------------------------
  const pollGenerationStatus = useCallback(async () => {
    const sessionId = currentSessionIdRef.current;
    if (!sessionId) return;
    try {
      const res = await axios.get(`${API}/sessions/${userId}/${sessionId}/status`);
      const { is_generating, messages_count, pass_count, saved, has_result } = res.data;
      setSessions(prev => prev.map(s =>
        s.id === sessionId
          ? { ...s, is_generating, pass_count, saved, message_count: messages_count }
          : s
      ));
      setIsGenerating(is_generating);
      if (!is_generating && has_result && messages_count > 0) {
        // Load fresh session data
        const sessionData = await axios.get(`${API}/sessions/${userId}/${sessionId}`);
        const session = sessionData.data.session;
        setCurrentSessionId(sessionId);
        currentSessionIdRef.current = sessionId;
        setMessages(session.messages || []);
        setSavedState(session.saved_state || null);
        setSavedProfiles(new Set(Object.keys(session.profile_rows || {})));
        setIsGenerating(session.is_generating || false);
        setSessions(prev => prev.map(s => {
          if (s.id === sessionId) {
            return {
              ...s,
              active: true,
              saved: session.saved || false,
              message_count: session.messages ? session.messages.length : 0,
              messages: session.messages || [],
              saved_state: session.saved_state || null,
              pass_count: session.pass_count || 0,
              is_generating: session.is_generating || false,
              title: session.title || s.title,
            };
          }
          return { ...s, active: false };
        }));

        const lastAssistant = [...(session.messages || [])].reverse().find(m => m.role === "assistant");
        if (lastAssistant?.error) {
          toast.error("Model returned an invalid response format");
        } else {
          toast.success("Cover letters generated");
        }

        setIsLoading(false);
        if (statusPollInterval.current) {
          clearInterval(statusPollInterval.current);
          statusPollInterval.current = null;
        }
      }
    } catch (e) {
      console.error("Status poll error:", e);
    }
  }, [userId]);

  // -------------------------------------------------------------------------
  // Load all sessions for this user on mount
  // -------------------------------------------------------------------------
  useEffect(() => {
    let cancelled = false;

    const init = async () => {
      setIsLoadingSessions(true);
      try {
        const res = await axios.get(`${API}/sessions/${userId}`);
        if (cancelled) return;

        const sessionsData = (res.data.sessions || []).sort((a, b) => b.timestamp - a.timestamp);
        setSessions(sessionsData.map(s => ({
          ...s,
          messages: s.messages || [],
          saved_state: s.saved_state || null,
          pass_count: s.pass_count || 0,
          is_generating: s.is_generating || false,
        })));

        if (sessionsData.length === 0) {
          // No sessions – show empty state, do NOT auto-create
          setCurrentSessionId(null);
          currentSessionIdRef.current = null;
          setMessages([]);
          setSavedState(null);
          setSavedProfiles(new Set());
          setIsGenerating(false);
          localStorage.removeItem("coverLetterCurrentSessionId");
          return;
        }

        const savedSessionId = localStorage.getItem("coverLetterCurrentSessionId");
        const target = savedSessionId
          ? sessionsData.find(s => s.id === savedSessionId)
          : null;
        const toLoad = target || sessionsData.find(s => s.active) || sessionsData[0];
        await loadSession(toLoad.id);
      } catch (e) {
        console.error("Failed to load sessions:", e);
        toast.error("Failed to load sessions");
      } finally {
        if (!cancelled) setIsLoadingSessions(false);
      }
    };

    init();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  useEffect(() => {
    return () => {
      if (statusPollInterval.current) {
        clearInterval(statusPollInterval.current);
        statusPollInterval.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (isGenerating && currentSessionId) {
      if (statusPollInterval.current) clearInterval(statusPollInterval.current);
      pollGenerationStatus();
      statusPollInterval.current = setInterval(pollGenerationStatus, STATUS_POLL_INTERVAL);
    } else {
      if (statusPollInterval.current) {
        clearInterval(statusPollInterval.current);
        statusPollInterval.current = null;
      }
    }
    return () => {
      if (statusPollInterval.current) {
        clearInterval(statusPollInterval.current);
        statusPollInterval.current = null;
      }
    };
  }, [isGenerating, currentSessionId, pollGenerationStatus]);

  // -------------------------------------------------------------------------
  // Switch to an already-loaded session (prefer local state, fall back to API)
  // -------------------------------------------------------------------------
  const switchSession = useCallback((sessionId) => {
    const session = sessions.find(s => s.id === sessionId);
    if (session && Array.isArray(session.messages)) {
      setCurrentSessionId(sessionId);
      currentSessionIdRef.current = sessionId;
      localStorage.setItem("coverLetterCurrentSessionId", sessionId);
      setMessages(session.messages || []);
      setSavedState(session.saved_state || null);
      setSavedProfiles(new Set(Object.keys(session.profile_rows || {})));
      setIsGenerating(session.is_generating || false);
      setSessions(prev => prev.map(s => ({ ...s, active: s.id === sessionId })));
      setInput("");
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
    } else {
      loadSession(sessionId);
    }
  }, [sessions, loadSession]);

  // -------------------------------------------------------------------------
  // Delete a session
  // -------------------------------------------------------------------------
  const deleteSession = useCallback(async (sessionId, e) => {
    e?.stopPropagation();
    if (!window.confirm("Delete this session?")) return;
    try {
      await axios.delete(`${API}/sessions/${userId}/${sessionId}`);

      // Update local sessions list
      setSessions(prev => {
        const remaining = prev.filter(s => s.id !== sessionId);
        return remaining;
      });

      // If the deleted session was the current one, switch or reset
      if (currentSessionIdRef.current === sessionId) {
        localStorage.removeItem("coverLetterCurrentSessionId");
        // Find the next session to activate
        const remaining = sessions.filter(s => s.id !== sessionId);
        if (remaining.length > 0) {
          // Switch to the first remaining session (most recent)
          const nextSession = remaining[0];
          setCurrentSessionId(nextSession.id);
          currentSessionIdRef.current = nextSession.id;
          localStorage.setItem("coverLetterCurrentSessionId", nextSession.id);
          setMessages(nextSession.messages || []);
          setSavedState(nextSession.saved_state || null);
          setSavedProfiles(new Set(Object.keys(nextSession.profile_rows || {})));
          setIsGenerating(nextSession.is_generating || false);
          setSessions(prev => prev.map(s => ({ ...s, active: s.id === nextSession.id })));
          setInput("");
          setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
        } else {
          // No sessions left – reset to empty state
          setCurrentSessionId(null);
          currentSessionIdRef.current = null;
          setMessages([]);
          setSavedState(null);
          setSavedProfiles(new Set());
          setIsGenerating(false);
          setInput("");
        }
      }
      toast.info("Session deleted");
    } catch (e) {
      console.error("Failed to delete session:", e);
      toast.error("Failed to delete session");
    }
  }, [userId, sessions]);

  // -------------------------------------------------------------------------
  // Send a message / trigger generation
  // -------------------------------------------------------------------------
  const sendMessage = async () => {
    const text = input.trim();
    if (!text || isLoading || isLoadingSessions || isCreatingSession) return;

    let sessionId = currentSessionIdRef.current;
    if (!sessionId) {
      sessionId = await createNewSession();
      if (!sessionId) {
        toast.error("Failed to create session");
        return;
      }
    }

    const userMsg = { role: "user", content: text };
    const prevMessages = messages;
    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);
    setIsGenerating(true);

    try {
      await axios.post(`${API}/generate-cover-letter`, {
        job_description: text,
        user_id: userId,
        session_id: sessionId,
      });
    } catch (e) {
      const errMsg = e.response?.data?.detail || e.message || "Generation failed";
      toast.error(errMsg);
      setMessages([
        ...prevMessages,
        { role: "assistant", content: errMsg, error: errMsg },
      ]);
      setInput(text);
      setIsLoading(false);
      setIsGenerating(false);
      if (statusPollInterval.current) {
        clearInterval(statusPollInterval.current);
        statusPollInterval.current = null;
      }
    }
  };

  // -------------------------------------------------------------------------
  // Save to Google Sheets
  // -------------------------------------------------------------------------
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
        session_id: currentSessionIdRef.current,
      });
      setSavedProfiles(prev => new Set([...prev, profileName]));
      setSessions(prev => prev.map(s =>
        s.id === currentSessionIdRef.current ? { ...s, saved: true } : s
      ));
      toast.success(`Saved ${profileName} to Google Sheets`);
    } catch (e) {
      const msg = e.response?.data?.detail || e.message || "Save failed";
      toast.error(`Save failed: ${msg}`);
    }
  };

  // -------------------------------------------------------------------------
  // Render helpers
  // -------------------------------------------------------------------------
  const renderProfileCard = (name, data, isLast, isSavedFlag) => {
    const jobEval = data.job_evaluation || {};
    const letterParts = data.letter_parts || {};
    const screening = data.screening_answers || "";
    const isPass = jobEval.decision === "PASS";
    const selectedCases = data.selected_cases || [];

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
              {selectedCases.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-slate-500">Selected cases for {name}:</p>
                  <ul className="mt-1 space-y-1">
                    {selectedCases.map((c) => (
                      <li key={c.case_id} className="text-xs text-slate-700">
                        <span className="font-medium text-emerald-600">{c.name}</span>
                        {c.link && (
                          <a href={c.link} target="_blank" rel="noopener noreferrer" className="ml-1 text-[#10b981] hover:underline">
                            (link)
                          </a>
                        )}
                        <span className="block text-[10px] text-slate-500 ml-1">
                          Reason: {c.reasoning}
                        </span>
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
              {isLast && !isSavedFlag && (
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
    if (msg.error) {
      return (
        <div className="flex items-start gap-2 text-red-300">
          <AlertCircle className="h-4 w-4 mt-0.5 shrink-0 text-red-400" />
          <div>
            <p className="text-xs font-semibold text-red-400 mb-0.5">Generation failed</p>
            <p className="text-xs whitespace-pre-wrap">{String(msg.error)}</p>
          </div>
        </div>
      );
    }

    if (!msg.result) return <p>{msg.content}</p>;

    const results = msg.result;

    if (typeof results !== "object" || Array.isArray(results)) {
      return (
        <div className="flex items-start gap-2 text-red-300">
          <AlertCircle className="h-4 w-4 mt-0.5 shrink-0 text-red-400" />
          <p className="text-xs">Unexpected response format from the model.</p>
        </div>
      );
    }

    if (typeof results.__error__ === "string") {
      return (
        <div className="flex items-start gap-2 text-red-300">
          <AlertCircle className="h-4 w-4 mt-0.5 shrink-0 text-red-400" />
          <div>
            <p className="text-xs font-semibold text-red-400 mb-0.5">Model returned an invalid response</p>
            <p className="text-xs whitespace-pre-wrap">{results.__error__}</p>
          </div>
        </div>
      );
    }

    const allCases = msg.all_cases || [];
    const hasPass = Object.values(results).some(d => d.job_evaluation?.decision === "PASS");
    const isLast = messages.indexOf(msg) === messages.length - 1;

    let passCount = 0;
    let totalCount = 0;
    for (const [, data] of Object.entries(results)) {
      totalCount++;
      if (data.job_evaluation?.decision === "PASS") passCount++;
    }

    return (
      <div className="space-y-4">
        <div className="bg-gray-800 p-2 rounded-lg text-white text-sm font-medium">
          Профилей с PASS: {passCount} из {totalCount}
          {savedProfiles.size > 0 && ` (сохранено: ${[...savedProfiles].join(", ")})`}
        </div>

        {allCases.length > 0 && (
          <div className="bg-gray-800 p-3 rounded-lg">
            <p className="text-xs font-medium text-gray-300">Potential cases (RAG) for this job:</p>
            <ul className="mt-1 space-y-1">
              {allCases.map((c) => (
                <li key={c.id} className="text-xs text-white">
                  <span className="font-medium">{c.name || c.id}</span>
                  {c.link && (
                    <a href={c.link} target="_blank" rel="noopener noreferrer" className="ml-1 text-emerald-400 hover:underline">
                      (link)
                    </a>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}

        {Object.entries(results).map(([name, data]) =>
          renderProfileCard(name, data, isLast, savedProfiles.has(name))
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

  const currentSession = sessions.find(s => s.id === currentSessionId);

  return (
    <div className="flex flex-1 w-full bg-[#f8fafc]" data-testid="cover-letter-page">
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
            disabled={isLoadingSessions || isCreatingSession}
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
                      <span>{s.pass_count || 0} PASS</span>
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

      <main className="flex-1 flex flex-col overflow-hidden min-h-0">
        <div className="px-4 py-2 border-b border-slate-200 bg-white shrink-0 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MessageSquare className="h-4 w-4 text-[#10b981]" />
            <span className="text-sm font-medium text-slate-700">
              {currentSession ? currentSession.title : "No session"}
            </span>
            <Badge variant="outline" className="text-[10px] font-mono">
              {userId.slice(0, 6)}…
            </Badge>
            {isGenerating && (
              <Badge variant="outline" className="bg-amber-100 text-amber-700 border-amber-300 text-[10px] animate-pulse">
                Generating…
              </Badge>
            )}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4" data-testid="cover-letter-chat-messages">
          {messages.length === 0 && !isLoading && !isGenerating && (
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
              disabled={isLoading || isLoadingSessions}
              data-testid="cover-letter-input"
            />
            <Button
              onClick={sendMessage}
              disabled={
                !input.trim() ||
                isLoading ||
                isLoadingSessions ||
                isCreatingSession ||
                !currentSessionIdRef.current
              }
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