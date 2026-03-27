import { motion } from "framer-motion";

const SUGGESTIONS = {
  en: ["Check account balance", "Last 5 transactions", "My account details", "Loan interest info"],
  hi: ["मेरा बैलेंस बताओ", "पिछले पांच लेनदेन", "मेरा खाता विवरण", "लोन ब्याज जानकारी"],
  mr: ["माझी शिल्लक सांगा", "माझे शेवटचे पाच व्यवहार", "माझे खाते तपशील", "कर्ज व्याज माहिती"],
};

export default function SuggestionChips({ language = "en", onPick, customList = null }) {
  const baseLang = language.split('-')[0];
  const list = customList || SUGGESTIONS[baseLang] || SUGGESTIONS.en;

  if (!list || list.length === 0) return null;
  
  return (
    <motion.div 
      className="flex flex-wrap justify-center gap-3 w-full max-w-2xl mx-auto my-6 px-4"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3 }}
    >
      {list.map((text, i) => (
        <motion.button 
          key={text} 
          onClick={() => onPick(text)}
          className="px-4 py-2 bg-white/60 hover:bg-white border border-surface-border text-primary text-sm font-medium rounded-full shadow-sm hover:shadow-md transition-all duration-200 cursor-pointer text-center"
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.4 + i * 0.1 }}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          {text}
        </motion.button>
      ))}
    </motion.div>
  );
}
