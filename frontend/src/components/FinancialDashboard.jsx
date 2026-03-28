import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, PieChart, TrendingUp, CreditCard, Activity } from 'lucide-react';
import { 
  PieChart as RechartsPieChart, Pie, Cell, Tooltip as RechartsTooltip, 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, ResponsiveContainer 
} from 'recharts';
import { getUserData } from '../services/api';

export default function FinancialDashboard({ isOpen, onClose }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (isOpen) {
      setLoading(true);
      getUserData()
        .then(res => {
          setData(res);
          setLoading(false);
        })
        .catch(err => {
          console.error(err);
          setLoading(false);
        });
    }
  }, [isOpen]);

  // Derived metrics from transactions
  const processTransactions = (txns) => {
    if (!txns || !txns.length) return { spending: [], summary: { totalDebit: 0, totalCredit: 0 } };
    
    let totalDebit = 0;
    let totalCredit = 0;
    const categories = { 'UPI/Shopping': 0, 'EMI': 0, 'Utilities': 0, 'Other': 0 };

    txns.forEach(t => {
      const amt = Number(t.amount) || 0;
      if (t.type.toLowerCase() === 'credit') {
        totalCredit += amt;
      } else {
        totalDebit += amt;
        const desc = t.description.toLowerCase();
        if (desc.includes('emi')) categories['EMI'] += amt;
        else if (desc.includes('utility') || desc.includes('bill')) categories['Utilities'] += amt;
        else if (desc.includes('upi') || desc.includes('shopping')) categories['UPI/Shopping'] += amt;
        else categories['Other'] += amt;
      }
    });

    const spendingData = Object.keys(categories)
      .filter(k => categories[k] > 0)
      .map(k => ({ name: k, value: categories[k] }));

    return { spending: spendingData, summary: { totalDebit, totalCredit } };
  };

  const { spending, summary } = processTransactions(data?.transactions);
  const profile = data?.credit_profile || {};
  const cibil = profile.cibil_score || 0;

  const COLORS = ['#3b82f6', '#f97316', '#10b981', '#6366f1', '#eab308'];

  // Speedometer calculation
  const getCibilColor = (score) => {
    if (score >= 750) return '#10b981'; // Green
    if (score >= 650) return '#f59e0b'; // Yellow
    return '#ef4444'; // Red
  };

  const cibilData = [
    { name: 'Score', value: cibil },
    { name: 'Remainder', value: 900 - cibil }
  ];

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40"
          />
          <motion.div
            initial={{ y: '100%', opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: '100%', opacity: 0 }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
            className="fixed bottom-0 left-0 w-full h-[85vh] bg-gray-50 rounded-t-[40px] shadow-2xl z-50 overflow-hidden flex flex-col md:h-[80vh] md:w-[800px] md:left-1/2 md:-translate-x-1/2 md:bottom-auto md:top-1/2 md:-translate-y-1/2 md:rounded-3xl"
          >
            {/* Header */}
            <div className="bg-white p-6 pb-4 border-b border-gray-100 flex items-center justify-between sticky top-0 z-10">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-50 text-blue-600 rounded-xl">
                  <Activity className="w-6 h-6" />
                </div>
                <div>
                  <h2 className="text-xl font-bold tracking-tight text-gray-900">Financial Insights</h2>
                  <p className="text-sm text-gray-500 font-medium">Your money at a glance</p>
                </div>
              </div>
              <button onClick={onClose} className="p-2 text-gray-400 hover:text-gray-900 hover:bg-gray-100 rounded-full transition-colors">
                <X className="w-6 h-6" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6 custom-scrollbar">
              {loading ? (
                <div className="flex-1 flex flex-col items-center justify-center pt-20">
                  <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}>
                    <Activity className="w-8 h-8 text-blue-500" />
                  </motion.div>
                  <p className="mt-4 text-gray-500 font-medium animate-pulse">Analyzing financials...</p>
                </div>
              ) : (
                <div className="flex flex-col gap-6">
                  
                  {/* Top Stats */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="bg-white p-4 rounded-2xl shadow-sm border border-gray-100">
                      <p className="text-xs text-gray-500 font-semibold mb-1 uppercase tracking-wider">Credit Limit</p>
                      <p className="text-lg font-bold text-gray-900">₹{(profile.total_credit_limit || 0).toLocaleString('en-IN')}</p>
                    </div>
                    <div className="bg-white p-4 rounded-2xl shadow-sm border border-gray-100">
                      <p className="text-xs text-gray-500 font-semibold mb-1 uppercase tracking-wider">Credit Used</p>
                      <p className="text-lg font-bold text-orange-500">₹{(profile.credit_used || 0).toLocaleString('en-IN')}</p>
                    </div>
                    <div className="bg-white p-4 rounded-2xl shadow-sm border border-gray-100">
                      <p className="text-xs text-gray-500 font-semibold mb-1 uppercase tracking-wider">Total Debits</p>
                      <p className="text-lg font-bold text-red-500">₹{summary.totalDebit.toLocaleString('en-IN')}</p>
                    </div>
                    <div className="bg-white p-4 rounded-2xl shadow-sm border border-gray-100">
                      <p className="text-xs text-gray-500 font-semibold mb-1 uppercase tracking-wider">Total Credits</p>
                      <p className="text-lg font-bold text-green-500">₹{summary.totalCredit.toLocaleString('en-IN')}</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* CIBIL Speedometer */}
                    <div className="bg-white p-6 rounded-3xl shadow-sm border border-gray-100 flex flex-col items-center relative overflow-hidden">
                      <div className="absolute top-0 right-0 p-4">
                        <CreditCard className="w-5 h-5 text-gray-300" />
                      </div>
                      <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-widest mb-6 w-full text-left">CIBIL Health</h3>
                      
                      <div className="relative w-48 h-24 mb-4">
                        <ResponsiveContainer width="100%" height="200%">
                          <RechartsPieChart>
                            <Pie
                              data={cibilData}
                              cx="50%"
                              cy="50%"
                              startAngle={180}
                              endAngle={0}
                              innerRadius={70}
                              outerRadius={90}
                              paddingAngle={0}
                              dataKey="value"
                              stroke="none"
                            >
                              <Cell fill={getCibilColor(cibil)} />
                              <Cell fill="#f1f5f9" />
                            </Pie>
                          </RechartsPieChart>
                        </ResponsiveContainer>
                        <div className="absolute bottom-0 left-1/2 -translate-x-1/2 text-center">
                          <p className="text-4xl font-extrabold text-gray-900 tracking-tighter" style={{ color: getCibilColor(cibil) }}>
                            {cibil}
                          </p>
                          <p className="text-xs font-semibold text-gray-400 mt-1 uppercase">{profile.credit_rating || 'Good'}</p>
                        </div>
                      </div>
                      
                      <div className="mt-8 text-center bg-gray-50 rounded-xl p-3 w-full">
                        <p className="text-sm font-medium text-gray-700">Risk Assessment</p>
                        <p className="text-xs text-gray-500 mt-1">{profile.credit_risk_description || 'Evaluating risk profile...'}</p>
                      </div>
                    </div>

                    {/* Spending Analytics */}
                    <div className="bg-white p-6 rounded-3xl shadow-sm border border-gray-100 relative">
                      <div className="absolute top-0 right-0 p-4">
                        <PieChart className="w-5 h-5 text-gray-300" />
                      </div>
                      <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-widest w-full text-left mb-4">Expenses</h3>
                      
                      {spending.length > 0 ? (
                        <div className="h-64 w-full">
                          <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={spending} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                              <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#94a3b8' }} />
                              <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#94a3b8' }} />
                              <RechartsTooltip 
                                cursor={{ fill: '#f8fafc' }}
                                contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)' }}
                              />
                              <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                                {spending.map((entry, index) => (
                                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                ))}
                              </Bar>
                            </BarChart>
                          </ResponsiveContainer>
                        </div>
                      ) : (
                        <div className="h-64 w-full flex items-center justify-center bg-gray-50 rounded-2xl">
                          <p className="text-gray-400 text-sm font-medium">No recent expenses found.</p>
                        </div>
                      )}
                    </div>
                  </div>

                </div>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}