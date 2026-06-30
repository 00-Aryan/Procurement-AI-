"use client";

import { useState, useEffect, useRef, useTransition } from "react";
import { Bot, Send, RefreshCw } from "lucide-react";
import { submitCopilotMessage } from "../actions";

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  suggestedAction?: string;
  confidenceScore?: number;
};

export default function CopilotPage() {
  const [sessionId, setSessionId] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isPending, startTransition] = useTransition();

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setSessionId(crypto.randomUUID());
    setMessages([
      {
        id: "welcome",
        role: "assistant",
        content: "Hello! I am your ProcureMind AI copilot. How can I help you analyze procurement risks, reorders, or anomalies today?",
      }
    ]);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isPending]);

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || isPending) return;

    const userMsgText = inputValue;
    setInputValue("");

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: userMsgText,
    };
    setMessages((prev) => [...prev, userMsg]);

    startTransition(async () => {
      try {
        const response = await submitCopilotMessage(userMsgText, sessionId);
        const assistantMsg: Message = {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content: response.executive_summary,
          suggestedAction: response.suggested_action_enum,
          confidenceScore: response.confidence_score,
        };
        setMessages((prev) => [...prev, assistantMsg]);
      } catch {
        const errMsg: Message = {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content: "Sorry, I encountered an error communicating with the backend. Please check if the FastAPI gateway is running.",
        };
        setMessages((prev) => [...prev, errMsg]);
      }
    });
  };

  const getActionBadgeColor = (action?: string) => {
    if (!action) return "bg-slate-100 text-slate-700";
    switch (action) {
      case "flag_anomaly":
        return "bg-rose-50 border border-rose-200 text-rose-700";
      case "trigger_reorder":
        return "bg-amber-50 border border-amber-200 text-amber-700";
      case "hold_contract":
        return "bg-orange-50 border border-orange-200 text-orange-700";
      case "no_action":
      default:
        return "bg-emerald-50 border border-emerald-200 text-emerald-700";
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-2rem)] px-12 py-8 bg-slate-50">
      <header className="flex items-center justify-between border-b pb-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-950">AI Copilot</h1>
          <p className="mt-2 text-sm text-slate-600">ProcureMind conversational gateway</p>
        </div>
        <div className="flex h-10 items-center gap-2 rounded-md border border-indigo-100 bg-white px-4 text-sm font-semibold text-indigo-600 shadow-soft">
          <Bot className="h-4 w-4" />
          Live Session: {sessionId.substring(0, 6)}
        </div>
      </header>

      <div className="flex-1 overflow-y-auto mt-6 pr-2 space-y-4 min-h-0">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex gap-4 p-4 rounded-lg border max-w-3xl ${
              msg.role === "user"
                ? "ml-auto bg-indigo-600 border-indigo-700 text-white flex-row-reverse"
                : "bg-white border-slate-200 text-slate-800"
            }`}
          >
            <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${
              msg.role === "user" ? "bg-indigo-700 text-indigo-100" : "bg-indigo-50 text-indigo-600"
            }`}>
              {msg.role === "user" ? <span className="text-xs font-bold">U</span> : <Bot className="h-4 w-4" />}
            </div>

            <div className="flex-1 space-y-2 min-w-0">
              <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>

              {msg.role === "assistant" && (msg.suggestedAction || msg.confidenceScore !== undefined) && (
                <div className="mt-4 pt-3 border-t border-slate-100 flex flex-wrap gap-4 text-xs font-semibold">
                  {msg.suggestedAction && (
                    <div className="flex items-center gap-1.5">
                      <span className="text-slate-400">Suggested Action:</span>
                      <span className={`px-2 py-0.5 rounded-full capitalize ${getActionBadgeColor(msg.suggestedAction)}`}>
                        {msg.suggestedAction.replace("_", " ")}
                      </span>
                    </div>
                  )}
                  {msg.confidenceScore !== undefined && (
                    <div className="flex items-center gap-1.5">
                      <span className="text-slate-400">Confidence:</span>
                      <span className="text-indigo-600">{(msg.confidenceScore * 100).toFixed(0)}%</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}

        {isPending && (
          <div className="flex gap-4 p-4 rounded-lg border bg-white border-slate-200 text-slate-800 max-w-3xl">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-50 text-indigo-600">
              <RefreshCw className="h-4 w-4 animate-spin" />
            </div>
            <div className="flex-1 py-1">
              <p className="text-sm text-slate-500">ProcureMind is reasoning...</p>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSend} className="mt-4 flex gap-3">
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder="Ask about anomalies, inventory reorder shock limits, or compliance..."
          disabled={isPending}
          className="flex-1 rounded-md border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 shadow-soft focus:border-indigo-500 focus:outline-none disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={isPending || !inputValue.trim()}
          className="inline-flex h-12 w-12 items-center justify-center rounded-md bg-indigo-600 text-white shadow hover:bg-indigo-700 transition disabled:opacity-50"
        >
          <Send className="h-5 w-5" />
        </button>
      </form>
    </div>
  );
}
