import { motion, AnimatePresence } from 'framer-motion';

export default function StatusText({ state, text }) {
  // state: "idle", "listening", "speaking"
  
  return (
    <div className="flex flex-col items-center justify-center mt-8 mb-12 h-24">
      <AnimatePresence mode="wait">
        <motion.h2
          key={text}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          className="text-2xl md:text-3xl font-bold text-gray-900 text-center max-w-2xl px-4">
          {text}
        </motion.h2>
      </AnimatePresence>
      
      <div className="flex items-center gap-2 mt-4">
        <div className="relative flex h-3 w-3">
          {state !== 'idle' && (
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
          )}
          <span className={`relative inline-flex rounded-full h-3 w-3 ${state === 'idle' ? 'bg-gray-300' : 'bg-blue-500'}`}></span>
        </div>
        <p className="text-sm font-semibold tracking-widest text-gray-500 uppercase">
          {state === 'idle' ? 'Ready' : state === 'listening' ? 'Listening...' : state === 'thinking' ? 'Processing...' : 'Speaking...'}
        </p>
      </div>
    </div>
  );
}
