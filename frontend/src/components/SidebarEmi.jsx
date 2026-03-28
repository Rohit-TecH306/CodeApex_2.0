import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Calculator, X, ChevronRight, IndianRupee, Calendar, Percent, ShieldCheck } from 'lucide-react';
import { calculateEmi } from '../services/api';

export default function SidebarEmi() {
  const [isOpen, setIsOpen] = useState(false);
  const [principal, setPrincipal] = useState('');
  const [duration, setDuration] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  const handleCalculate = async (e) => {
    e.preventDefault();
    setError('');
    setResult(null);
    if (!principal || !duration) {
      setError('Please fill all fields');
      return;
    }
    setLoading(true);
    try {
      const data = await calculateEmi(Number(principal), Number(duration));
      
      // Calculate breakdown
      const totalPayable = data.emi * data.duration_years * 12;
      const totalInterest = totalPayable - data.principal;
      const principalPercent = (data.principal / totalPayable) * 100;
      const interestPercent = (totalInterest / totalPayable) * 100;

      setResult({
        ...data,
        totalPayable,
        totalInterest,
        principalPercent,
        interestPercent
      });
    } catch (err) {
      setError(err.message || 'Error calculating EMI');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Toggle Button */}
      <motion.button
        onClick={() => setIsOpen(true)}
        className="fixed left-0 top-1/2 -translate-y-1/2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white p-3 rounded-r-2xl shadow-[0_8px_30px_rgb(0,0,0,0.12)] z-30 hover:shadow-[0_8px_30px_rgb(59,130,246,0.5)] transition-all flex flex-col items-center justify-center group border border-l-0 border-white/20 backdrop-blur-md"
        whileHover={{ x: 5, scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
      >
        <Calculator className="w-6 h-6 mb-1 text-blue-100 group-hover:text-white transition-colors" />
        <span className="font-bold text-xs tracking-wider" style={{ writingMode: 'vertical-rl', textOrientation: 'mixed' }}>SMART EMI</span>
        <ChevronRight className="w-5 h-5 mt-1 opacity-50 group-hover:opacity-100 transition-opacity translate-x-[-2px] group-hover:translate-x-0" />
      </motion.button>

      {/* Backdrop */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setIsOpen(false)}
            className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40"
          />
        )}
      </AnimatePresence>

      {/* Sidebar Panel */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ x: '-100%', opacity: 0, borderTopRightRadius: '100px', borderBottomRightRadius: '100px' }}
            animate={{ x: 0, opacity: 1, borderTopRightRadius: '32px', borderBottomRightRadius: '32px' }}
            exit={{ x: '-100%', opacity: 0, borderTopRightRadius: '100px', borderBottomRightRadius: '100px' }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
            className="fixed left-0 top-0 h-full w-[380px] bg-white/95 backdrop-blur-xl shadow-2xl shadow-blue-900/20 z-50 flex flex-col border-r border-white/40 overflow-hidden"
          >
            {/* Header */}
            <div className="relative p-6 pb-8 bg-gradient-to-br from-blue-600 to-indigo-700 text-white rounded-br-[32px]">
              <div className="absolute top-0 right-0 w-32 h-32 bg-white/10 rounded-full blur-2xl -translate-y-1/2 translate-x-1/2"></div>
              
              <div className="flex items-start justify-between relative z-10">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-white/20 rounded-xl backdrop-blur-sm border border-white/20">
                    <Calculator className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <h2 className="text-xl font-bold tracking-tight">Smart EMI</h2>
                    <p className="text-blue-100 text-xs mt-0.5 font-medium">AI-Powered Profiling</p>
                  </div>
                </div>
                <button 
                  onClick={() => setIsOpen(false)} 
                  className="text-white/70 hover:text-white hover:bg-white/20 rounded-full p-2 transition-colors cursor-pointer"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Content Body */}
            <div className="flex-1 overflow-y-auto custom-scrollbar p-6 space-y-6">
              
              <form onSubmit={handleCalculate} className="space-y-5">
                <div className="space-y-1.5">
                  <label className="block text-sm font-semibold text-gray-700">Loan Principal</label>
                  <div className="relative group">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-400 group-focus-within:text-brand transition-colors">
                      <IndianRupee className="w-5 h-5" />
                    </div>
                    <input
                      type="number"
                      min="1000"
                      step="100"
                      value={principal}
                      onChange={(e) => setPrincipal(e.target.value)}
                      className="w-full pl-10 pr-4 py-3.5 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 bg-white shadow-sm transition-all text-gray-800 font-semibold text-lg"
                      placeholder="e.g. 500000"
                    />
                  </div>
                </div>
                
                <div className="space-y-1.5">
                  <label className="block text-sm font-semibold text-gray-700">Duration (Years)</label>
                  <div className="relative group">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-400 group-focus-within:text-brand transition-colors">
                      <Calendar className="w-5 h-5" />
                    </div>
                    <input
                      type="number"
                      min="1"
                      step="1"
                      max="30"
                      value={duration}
                      onChange={(e) => setDuration(e.target.value)}
                      className="w-full pl-10 pr-4 py-3.5 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 bg-white shadow-sm transition-all text-gray-800 font-semibold text-lg"
                      placeholder="e.g. 5"
                    />
                  </div>
                </div>

                {error && (
                  <motion.p initial={{ opacity: 0, y: -5 }} animate={{ opacity: 1, y: 0 }} className="text-red-500 text-sm font-medium px-1">
                    {error}
                  </motion.p>
                )}

                <button
                  type="submit"
                  disabled={loading}
                  className="relative w-full py-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 disabled:opacity-70 text-white rounded-xl font-bold transition-all shadow-lg shadow-blue-500/30 overflow-hidden group"
                >
                  <span className="relative z-10 flex items-center justify-center gap-2">
                    {loading ? (
                      <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1, ease: "linear" }}>
                        <Calculator className="w-5 h-5" />
                      </motion.div>
                    ) : (
                      'Calculate My Match'
                    )}
                  </span>
                  <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform cursor-pointer"></div>
                </button>
              </form>

              {/* Results Area */}
              <AnimatePresence>
                {result && (
                  <motion.div 
                    className="pt-4 border-t border-gray-100"
                    initial={{ scale: 0.95, opacity: 0, y: 20 }}
                    animate={{ scale: 1, opacity: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.9 }}
                    transition={{ type: "spring", damping: 20, stiffness: 100 }}
                  >
                    <div className="bg-gradient-to-br from-indigo-50 via-white to-blue-50 border border-blue-100 rounded-2xl p-5 shadow-[0_4px_20px_rgb(59,130,246,0.05)]">
                      
                      {/* Highlighted EMI */}
                      <div className="text-center mb-6">
                        <p className="text-sm font-medium text-gray-500 mb-1">Your Estimated EMI</p>
                        <div className="flex items-baseline justify-center gap-1 text-primary">
                          <span className="text-2xl font-bold">₹</span>
                          <span className="text-4xl font-extrabold tracking-tight">{Math.round(result.emi).toLocaleString('en-IN')}</span>
                          <span className="text-gray-500 font-medium text-sm">/mo</span>
                        </div>
                      </div>

                      {/* Visual Breakdown Bar */}
                      <div className="mb-6 space-y-2">
                        <div className="flex justify-between text-xs font-semibold text-gray-500 px-1">
                          <span className="flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-brand"></div>Principal</span>
                          <span className="flex items-center gap-1">Interest<div className="w-2 h-2 rounded-full bg-orange-400"></div></span>
                        </div>
                        <div className="h-3 w-full bg-gray-100 rounded-full overflow-hidden flex shadow-inner">
                          <motion.div 
                            initial={{ width: 0 }} 
                            animate={{ width: `${result.principalPercent}%` }} 
                            transition={{ duration: 1, delay: 0.2 }}
                            className="h-full bg-brand" 
                          />
                          <motion.div 
                            initial={{ width: 0 }} 
                            animate={{ width: `${result.interestPercent}%` }} 
                            transition={{ duration: 1, delay: 0.2 }}
                            className="h-full bg-orange-400" 
                          />
                        </div>
                        <div className="flex justify-between text-[11px] text-gray-400 px-1">
                          <span>₹{result.principal.toLocaleString('en-IN')}</span>
                          <span>₹{Math.round(result.totalInterest).toLocaleString('en-IN')}</span>
                        </div>
                      </div>

                      {/* Info Grid */}
                      <div className="grid grid-cols-2 gap-3 mb-2">
                        <div className="bg-white p-3 rounded-xl border border-gray-100 shadow-sm flex flex-col items-center text-center">
                          <Percent className="w-4 h-4 text-green-500 mb-1" />
                          <span className="text-[10px] text-gray-400 font-semibold uppercase">Interest Rate</span>
                          <span className="font-bold text-gray-800">{result.interest_rate}%</span>
                        </div>
                        <div className="bg-white p-3 rounded-xl border border-gray-100 shadow-sm flex flex-col items-center text-center">
                          <ShieldCheck className="w-4 h-4 text-brand mb-1" />
                          <span className="text-[10px] text-gray-400 font-semibold uppercase">CIBIL Match</span>
                          <span className="font-bold text-gray-800">{result.cibil_score}</span>
                        </div>
                      </div>
                      
                      <div className="mt-4 p-3 bg-green-50/50 border border-green-100 rounded-xl text-center">
                         <p className="text-xs text-green-700 font-medium">
                           Approval Status: <strong>{result.loan_approval_likelihood}</strong>
                         </p>
                      </div>

                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
