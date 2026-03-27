import React, { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import Header from './components/Header';
import VoiceOrb from './components/VoiceOrb';
import StatusText from './components/StatusText';
import BankInfoCards from './components/BankInfoCards';
import SuggestionChips from './components/SuggestionChips';
import { loginByMobile, processText, getTtsAudio } from './services/api';

export default function App() {
  const [user, setUser] = useState(null);
  const [mobileInput, setMobileInput] = useState('');
  const [loginError, setLoginError] = useState('');
  const [language, setLanguage] = useState('en-IN');

  const [sessionActive, setSessionActive] = useState(false);
  const [orbState, setOrbState] = useState('idle');
  const [statusMessage, setStatusMessage] = useState('How can I help you today?');
  const [currentSuggestions, setCurrentSuggestions] = useState(null);

  const recognitionRef = useRef(null);
  const audioRef = useRef(null);

  const getSuggestionsForQuery = (query, lang) => {
    const q = query.toLowerCase();
    if (lang.startsWith('hi')) {
      if (q.includes("बैलेंस") || q.includes("खाता")) return ["पिछले पांच लेनदेन", "मेरा खाता विवरण", "लोन ब्याज जानकारी"];
      if (q.includes("लेनदेन") || q.includes("पिछले")) return ["मेरा बैलेंस बताओ", "मेरा खाता विवरण", "क्या मेरा खाता सक्रिय है?"];
      return ["मेरा बैलेंस बताओ", "पिछले पांच लेनदेन", "मेरा खाता विवरण", "लोन ब्याज जानकारी"];
    } else if (lang.startsWith('mr')) {
      if (q.includes("शिल्लक") || q.includes("खाते")) return ["माझे शेवटचे पाच व्यवहार", "माझे खाते तपशील", "कर्ज व्याज माहिती"];
      if (q.includes("व्यवहार") || q.includes("शेवटचे")) return ["माझी शिल्लक सांगा", "माझे खाते तपशील", "माझे खाते सक्रिय आहे का?"];
      return ["माझी शिल्लक सांगा", "माझे शेवटचे पाच व्यवहार", "माझे खाते तपशील", "कर्ज व्याज माहिती"];
    }
    // Default English
    if (q.includes("balance")) return ["Show last 5 transactions", "My account details", "Is my account active?"];
    if (q.includes("transaction") || q.includes("last")) return ["What is my balance?", "My account details", "Loan interest info"];
    if (q.includes("loan") || q.includes("interest")) return ["Am I eligible for a loan?", "Check account balance", "What is the repo rate?"];
    return ["Check account balance", "Last 5 transactions", "My account details", "Loan interest info"];
  };

  const stopAudio = (e) => {
    if (e) e.stopPropagation();
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    setOrbState('idle');
    setStatusMessage('How can I help you today?');
    setSessionActive(false);
  };

  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recog = new SpeechRecognition();
      recog.continuous = false;
      recog.interimResults = false;
      recog.lang = 'en-IN';

      recog.onresult = async (event) => {
        const transcript = event.results[0][0].transcript;
        setStatusMessage(`"${transcript}"`);
        setOrbState('thinking');

        try {
          const chatRes = await processText(transcript);
          setStatusMessage(chatRes.response_text);
          const suggestions = getSuggestionsForQuery(transcript, chatRes.language || language);
          setCurrentSuggestions(suggestions);
          setOrbState('speaking');

          const audioBlob = await getTtsAudio(chatRes.response_text, chatRes.language);
          const audioUrl = URL.createObjectURL(audioBlob);

          if (audioRef.current) {
            audioRef.current.pause();
          }
          audioRef.current = new Audio(audioUrl);
          await audioRef.current.play();

          audioRef.current.onended = () => {
            setOrbState('idle');
            setStatusMessage('How can I help you today?');
            setSessionActive(false);
          };
        } catch (err) {
          console.error(err);
          setStatusMessage('Error: ' + err.message);
          setOrbState('idle');
          setSessionActive(false);
        }
      };

      recog.onerror = (event) => {
        console.error('Speech error:', event.error);
        setStatusMessage('Could not hear you. Might be mic permissions.');
        setOrbState('idle');
        setSessionActive(false);
      };

      recog.onend = () => {
        setOrbState((prev) => (prev === 'listening' ? 'thinking' : prev));
      };

      recognitionRef.current = recog;
    } else {
      console.warn('Speech Recognition API not supported.');
    }
  }, []);

  const handleLogin = async  (e) => {
    e.preventDefault();
    setLoginError('');
    try {
      const data = await loginByMobile(mobileInput);
      setUser(data.user);
      
      const welcomeText = `Welcome ${data.user.name} to BharatTrust Bank.`;
      setStatusMessage(welcomeText);
      setOrbState('speaking');
      
      const audioBlob = await getTtsAudio(welcomeText, 'en');
      const audioUrl = URL.createObjectURL(audioBlob);
      if (audioRef.current) audioRef.current.pause();
      audioRef.current = new Audio(audioUrl);
      
      audioRef.current.onended = () => {
        setOrbState('idle');
        setStatusMessage('How can I help you today?');
      };
      
      await audioRef.current.play();
    } catch (err) {
      setLoginError(err.message || 'Login failed.');
    }
  };

  const startVoiceSession = () => {
    if (!recognitionRef.current) {
      setStatusMessage('Voice not supported on this browser.');
      return;
    }

    recognitionRef.current.lang = language;
    if (audioRef.current) audioRef.current.pause();

    setSessionActive(true);
    setOrbState('listening');
    setStatusMessage('Listening...');

    try {
      recognitionRef.current.start();
    } catch (err) {
      recognitionRef.current.stop();
      try {
        recognitionRef.current.start();
      } catch(e) {
         setStatusMessage('Mic occupied.');
      }
    }
  };

  if (!user) return (
    <div className="min-h-screen bg-[#F9FAFB] font-sans flex items-center justify-center relative overflow-hidden">
      <div className="absolute top-0 right-0 w-[800px] h-[800px] bg-blue-50 rounded-full blur-[120px] opacity-60 -translate-y-1/2 translate-x-1/3 pointer-events-none"></div>
      <div className="absolute bottom-0 left-0 w-[600px] h-[600px] bg-blue-100/50 rounded-full blur-[100px] opacity-60 translate-y-1/3 -translate-x-1/4 pointer-events-none"></div>

      <div className="bg-white p-10 rounded-3xl shadow-xl z-10 w-full max-w-md border border-gray-100 flex flex-col items-center">
        <div className="w-16 h-16 bg-blue-600 rounded-2xl flex items-center justify-center text-white text-3xl shadow-lg mb-6">🏦</div>
        <h2 className="text-2xl font-extrabold text-gray-900 mb-2">Welcome to Kiosk</h2>
        <p className="text-gray-500 mb-8 text-center">Please enter your registered mobile number to proceed.</p>

        <form onSubmit={handleLogin} className="w-full flex flex-col gap-4">
          <div>
            <input
              type="text"
              value={mobileInput}
              onChange={(e) => setMobileInput(e.target.value)}
              placeholder="e.g. 9000007124"
              className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500 text-lg text-center tracking-wider font-semibold"
              autoFocus
            />
          </div>
          {loginError && <p className="text-red-500 text-sm text-center font-medium">{loginError}</p>}
          <button
            type="submit"
            className="w-full py-4 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-bold text-lg transition-colors shadow-md"
          >
            Access Account
          </button>
        </form>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-[#F9FAFB] font-sans selection:bg-blue-100 flex flex-col relative overflow-hidden">
      <div className="absolute top-0 right-0 w-[800px] h-[800px] bg-blue-50 rounded-full blur-[120px] opacity-60 -translate-y-1/2 translate-x-1/3 pointer-events-none"></div>
      <div className="absolute bottom-0 left-0 w-[600px] h-[600px] bg-blue-100/50 rounded-full blur-[100px] opacity-60 translate-y-1/3 -translate-x-1/4 pointer-events-none"></div>


      <Header />

      <div className="absolute top-6 right-8 z-20">
        <select
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
          className="bg-white/80 backdrop-blur-md border border-gray-200 text-gray-700 py-2 px-4 rounded-xl shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium cursor-pointer"
        >
          <option value="en-IN">English</option>
          <option value="hi-IN">Hindi</option>
          <option value="mr-IN">Marathi</option>
          <option value="gu-IN">Gujarati</option>
          <option value="ta-IN">Tamil</option>
          <option value="te-IN">Telugu</option>
        </select>
      </div>

      <main className="flex-1 flex flex-col items-center justify-center relative z-10 -mt-10">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className="flex flex-col items-center cursor-pointer"
          onClick={!sessionActive ? startVoiceSession : undefined}
          title={!sessionActive ? "Click to interact" : ""}
        >
          <VoiceOrb state={orbState} />
          <StatusText state={orbState} text={statusMessage} />
          {orbState === 'speaking' && (
            <button
              onClick={stopAudio}
              className="mt-6 px-6 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-600 rounded-full font-medium transition-colors border border-red-500/30 flex items-center gap-2"
            >
              <svg className="w-5 h-5 text-red-600" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8 7a1 1 0 00-1 1v4a1 1 0 001 1h4a1 1 0 001-1V8a1 1 0 00-1-1H8z" clipRule="evenodd" /></svg>
              Stop Audio
            </button>
          )}
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.3 }}
          className="w-full mt-4"
        >
          {currentSuggestions ? (
            <div className="flex flex-col items-center gap-4">
              <p className="text-gray-500 text-sm font-medium">Recommended for you:</p>
              <SuggestionChips language={language} customList={currentSuggestions} />
            </div>
          ) : (
            <BankInfoCards />
          )}
        </motion.div>
      </main>
    </div>
  );
}


