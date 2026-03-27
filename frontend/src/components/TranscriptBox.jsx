import { useEffect, useRef } from "react";
import { Mic, Send } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export default function TranscriptBox({ messages, inputText, setInputText, onSend, language }) {
  const scrollRef = useRef(null);

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full max-w-2xl mx-auto mt-4 bg-white/80 backdrop-blur-md border border-surface-border rounded-2xl shadow-premium overflow-hidden flex flex-col"
    >
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-4 max-h-[250px] min-h-[150px] flex flex-col gap-4 scroll-smooth"
      >
        <AnimatePresence>
          {messages.length === 0 ? (
            <motion.div 
              initial={{ opacity: 0 }} 
              animate={{ opacity: 1 }} 
              className="flex items-center justify-center h-full text-secondary/60 text-sm italic"
            >
              Your conversation will appear here...
            </motion.div>
          ) : (
            messages.map((m) => (
              <motion.div 
                key={m.id} 
                initial={{ opacity: 0, scale: 0.95, y: 10 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                className={`flex w-full ${m.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div 
                  className={`max-w-[80%] px-4 py-3 rounded-2xl text-sm leading-relaxed ${
                    m.role === "user" 
                      ? "bg-brand text-white rounded-tr-sm shadow-md" 
                      : "bg-surface border border-surface-border text-primary rounded-tl-sm shadow-sm"
                  }`}
                >
                  {m.content}
                </div>
              </motion.div>
            ))
          )}
        </AnimatePresence>
      </div>

      <div className="flex items-center gap-2 p-3 bg-white border-t border-surface-border">
        <button className="p-2 text-secondary hover:text-brand transition-colors rounded-full hover:bg-brand-light/30">
          <Mic size={20} />
        </button>
        <input
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder={language === "hi" ? "अपना प्रश्न लिखें" : language === "mr" ? "तुमचा प्रश्न लिहा" : "Type your question"}
          onKeyDown={(e) => {
            if (e.key === "Enter") onSend(inputText);
          }}
          className="flex-1 bg-surface border border-surface-border px-4 py-2.5 rounded-full text-sm outline-none focus:border-brand/40 focus:ring-2 focus:ring-brand/10 transition-all text-primary"
        />
        <button 
          onClick={() => onSend(inputText)}
          disabled={!inputText.trim()}
          className="p-2.5 bg-brand text-white rounded-full hover:bg-brand-accent transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-md"
        >
          <Send size={16} className="-ml-0.5" />
        </button>
      </div>
    </motion.div>
  );
}