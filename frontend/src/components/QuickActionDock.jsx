import React from 'react';
import { motion } from 'framer-motion';
import { Home, PieChart, CreditCard, Mic } from 'lucide-react';

export default function QuickActionDock({ onSpeakClicked, onDashboardClicked, onSendPrompt }) {
  const actions = [
    { icon: <Home className="w-5 h-5" />, label: 'Balance', action: () => onSendPrompt('What is my account balance?') },
    { icon: <CreditCard className="w-5 h-5" />, label: 'Card limit', action: () => onSendPrompt('What is my credit limit?') },
    { 
      icon: <div className="bg-blue-600 rounded-full p-3 shadow-lg shadow-blue-500/50 text-white transform -translate-y-2"><Mic className="w-6 h-6" /></div>, 
      label: '', 
      action: onSpeakClicked 
    },
    { icon: <PieChart className="w-5 h-5" />, label: 'Insights', action: onDashboardClicked },
    { icon: <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>, label: 'Help', action: () => onSendPrompt('What can you help me with?') },
  ];

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 w-fit">
      <motion.div 
        initial={{ y: 100, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ type: "spring", damping: 20, stiffness: 100, delay: 0.5 }}
        className="bg-white/80 backdrop-blur-xl border border-white shadow-xl rounded-full px-4 py-3 flex items-center gap-6"
      >
        {actions.map((item, i) => (
          <button
            key={i}
            onClick={item.action}
            className="flex flex-col items-center justify-center gap-1 group relative transition-transform hover:scale-105 active:scale-95"
          >
            <div className={`text-gray-500 group-hover:text-blue-600 transition-colors ${item.label === '' ? '' : 'p-2'}`}>
              {item.icon}
            </div>
            {item.label && (
              <span className="text-[10px] font-bold text-gray-400 group-hover:text-blue-600 tracking-wide uppercase">
                {item.label}
              </span>
            )}
          </button>
        ))}
      </motion.div>
    </div>
  );
}