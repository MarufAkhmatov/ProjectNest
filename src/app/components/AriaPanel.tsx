import { useState } from "react";
import { Send, Plus, Mic } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";

const suggestions = ["Why is my HRV low?", "How's my recovery today?"];

const initialMessages = [
  { role: "assistant", text: "Hi! I'm Aria, your personal health AI. Ask me anything about your health data." },
];

export function AriaPanel() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState(initialMessages);

  const send = () => {
    if (!input.trim()) return;
    const userMsg = { role: "user", text: input };
    const aiMsg = {
      role: "assistant",
      text: "Based on your recent health data, I recommend maintaining consistent sleep patterns and staying hydrated. Your HRV trends suggest moderate stress — consider a 10-minute breathing exercise today.",
    };
    setMessages(prev => [...prev, userMsg, aiMsg]);
    setInput("");
  };

  return (
    <div
      className="rounded-2xl flex flex-col overflow-hidden"
      style={{
        background: "linear-gradient(160deg, #1a3040 0%, #0f2030 60%, #162840 100%)",
        border: "1px solid rgba(255,255,255,0.12)",
        minHeight: 280,
      }}
    >
      {/* Background blob */}
      <div style={{ position: "relative", height: 120, overflow: "hidden", flexShrink: 0 }}>
        <div style={{
          position: "absolute", inset: 0,
          background: "radial-gradient(ellipse at 60% 50%, rgba(155,89,182,0.4) 0%, rgba(45,122,95,0.3) 40%, transparent 70%)",
        }} />
        <img
          src="https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=400&h=200&fit=crop&auto=format"
          alt="Abstract flowing form"
          style={{ width: "100%", height: "100%", objectFit: "cover", opacity: 0.35, mixBlendMode: "luminosity" }}
        />
        <div style={{ position: "absolute", top: 16, left: 16 }}>
          <div style={{ fontSize: "1.1rem", fontWeight: 700, color: "#ffffff" }}>Aria</div>
          <div style={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.55)" }}>Your personal AI assistant</div>
        </div>
      </div>

      <div className="flex flex-col gap-3 p-4 flex-1">
        {/* Suggestion chips */}
        <div className="flex gap-2 flex-wrap">
          {suggestions.map(s => (
            <button
              key={s}
              onClick={() => setInput(s)}
              style={{
                background: "rgba(255,255,255,0.1)",
                border: "1px solid rgba(255,255,255,0.18)",
                borderRadius: 20,
                padding: "4px 12px",
                fontSize: "0.68rem",
                color: "rgba(255,255,255,0.85)",
                cursor: "pointer",
                backdropFilter: "blur(8px)",
              }}
            >
              {s}
            </button>
          ))}
        </div>

        {/* Messages */}
        <div style={{ flex: 1, maxHeight: 100, overflowY: "auto", display: "flex", flexDirection: "column", gap: 6 }}>
          <AnimatePresence>
            {messages.slice(1).map((m, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
                style={{
                  alignSelf: m.role === "user" ? "flex-end" : "flex-start",
                  background: m.role === "user" ? "rgba(155,89,182,0.5)" : "rgba(255,255,255,0.1)",
                  borderRadius: 10,
                  padding: "6px 10px",
                  fontSize: "0.68rem",
                  color: "rgba(255,255,255,0.9)",
                  maxWidth: "85%",
                  lineHeight: 1.4,
                }}
              >
                {m.text}
              </motion.div>
            ))}
          </AnimatePresence>
        </div>

        {/* Credits */}
        <div className="flex items-center justify-between">
          <span style={{ fontSize: "0.65rem", color: "rgba(255,255,255,0.4)" }}>100 Credits Remaining</span>
          <button style={{
            background: "rgba(255,255,255,0.15)",
            border: "1px solid rgba(255,255,255,0.2)",
            borderRadius: 8,
            padding: "3px 10px",
            fontSize: "0.65rem",
            color: "rgba(255,255,255,0.8)",
            cursor: "pointer",
          }}>
            Upgrade
          </button>
        </div>

        {/* Input */}
        <div style={{
          display: "flex", alignItems: "center", gap: 8,
          background: "rgba(255,255,255,0.1)",
          borderRadius: 12,
          padding: "8px 12px",
          border: "1px solid rgba(255,255,255,0.15)",
        }}>
          <button style={{ background: "none", border: "none", cursor: "pointer" }}>
            <Plus size={14} color="rgba(255,255,255,0.5)" />
          </button>
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && send()}
            placeholder="Ask anything..."
            style={{
              flex: 1, background: "none", border: "none", outline: "none",
              fontSize: "0.75rem", color: "rgba(255,255,255,0.85)",
              fontFamily: "DM Sans, sans-serif",
            }}
          />
          <button style={{ background: "none", border: "none", cursor: "pointer" }}>
            <Mic size={14} color="rgba(255,255,255,0.5)" />
          </button>
          <motion.button
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.95 }}
            onClick={send}
            style={{
              width: 28, height: 28, borderRadius: "50%",
              background: "#1a2030",
              border: "none", cursor: "pointer",
              display: "flex", alignItems: "center", justifyContent: "center",
            }}
          >
            <Send size={12} color="#ffffff" />
          </motion.button>
        </div>
      </div>
    </div>
  );
}
