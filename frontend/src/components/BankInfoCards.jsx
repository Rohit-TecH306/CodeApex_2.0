import { Building2, Store, CreditCard, Layers, Bot } from 'lucide-react';
import bankData from '../data/bankData.json';

const iconMap = {
  Building2,
  Store,
  CreditCard,
  Layers,
  Bot
};

export default function BankInfoCards() {
  return (
    <div className="w-full max-w-6xl mx-auto mt-12 grid grid-cols-2 md:grid-cols-5 gap-4 relative z-10 px-6">
      {bankData.stats.map((stat, idx) => {
        const IconComponent = iconMap[stat.icon] || Building2;
        return (
          <div 
            key={stat.id} 
            className="bg-white shadow-sm border border-gray-100 rounded-3xl p-6 flex flex-col items-center justify-center text-center transition-all duration-300 hover:shadow-lg hover:-translate-y-1"
          >
            <div className="w-12 h-12 rounded-2xl bg-blue-50 flex items-center justify-center text-blue-600 mb-4">
              <IconComponent size={24} strokeWidth={2} />
            </div>
            <p className="text-3xl font-bold text-gray-900 mb-1">{stat.value}</p>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest">{stat.label}</p>
          </div>
        );
      })}
    </div>
  );
}
