import { motion } from 'framer-motion';

export default function VoiceOrb({ state }) {
  const orbVariants = {
    idle: {
      scale: [1, 1.05, 1],
      boxShadow: [
        "0 0 0 0 rgba(59, 130, 246, 0.4)",
        "0 0 40px 10px rgba(59, 130, 246, 0.2)",
        "0 0 0 0 rgba(59, 130, 246, 0.4)"
      ],
      transition: { duration: 4, repeat: Infinity, ease: "easeInOut" }
    },
    listening: {
      scale: [1, 1.25, 1],
      boxShadow: [
        "0 0 20px 5px rgba(59, 130, 246, 0.6)",
        "0 0 80px 20px rgba(59, 130, 246, 0.8)",
        "0 0 20px 5px rgba(59, 130, 246, 0.6)"
      ],
      transition: { duration: 1.5, repeat: Infinity, ease: "easeInOut" }
    },
    speaking: {
      scale: [1, 1.1, 1.05, 1.2, 1],
      boxShadow: [
        "0 0 30px 10px rgba(59, 130, 246, 0.6)",
        "0 0 60px 15px rgba(59, 130, 246, 0.5)",
        "0 0 40px 10px rgba(59, 130, 246, 0.7)",
        "0 0 70px 20px rgba(59, 130, 246, 0.4)",
        "0 0 30px 10px rgba(59, 130, 246, 0.6)"
      ],
      transition: { duration: 0.8, repeat: Infinity, ease: "easeInOut" }
    }
  };

  const coreVariants = {
    idle: { scale: 1 },
    listening: { scale: 1.15 },
    speaking: { scale: [1, 1.2, 0.9, 1.1, 1], transition: { duration: 0.8, repeat: Infinity } }
  };

  return (
    <div className="flex justify-center items-center py-16">
      <div className="relative w-64 h-64 flex justify-center items-center">
        {/* Outer glowing aura */}
        <motion.div
          animate={state}
          variants={orbVariants}
          className="absolute inset-0 rounded-full bg-blue-500/10"
        />

        {/* Middle gradient ring */}
        <motion.div
          animate={state}
          variants={orbVariants}
          style={{ transitionDelay: "100ms" }}
          className="absolute inset-4 rounded-full bg-gradient-to-br from-blue-400/20 to-blue-600/20 backdrop-blur-sm border border-white/30"
        />

        {/* Inner solid core */}
        <motion.div
          animate={state}
          variants={coreVariants}
          className="absolute inset-8 rounded-full bg-gradient-to-br from-blue-500 to-blue-700 shadow-inner flex items-center justify-center overflow-hidden"
        >
          <div className="absolute inset-0 bg-white/10 blur-xl rounded-full" />
          <div className="w-full h-full bg-[radial-gradient(ellipse_at_top_left,_var(--tw-gradient-stops))] from-white/40 via-transparent to-transparent opacity-50 z-10"></div>

          <motion.div 
            animate={{ opacity: state === 'listening' ? [0.4, 1, 0.4] : 0 }}
            transition={{ duration: 1.5, repeat: Infinity }}
            className="w-4 h-4 bg-white rounded-full z-20"
          />
        </motion.div>
      </div>
    </div>
  );
}
