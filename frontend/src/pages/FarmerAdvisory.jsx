import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { getFarmerAdvisory } from '../utils/api';
import { Bot, User, Sparkles, Send, Loader2 } from 'lucide-react';
import { cn } from '../lib/utils';
import { useSettings } from '../contexts/SettingsContext';
import { useTranslation } from '../locales/translations';

const FarmerAdvisory = ({ commodity, mandi }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [messages, setMessages] = useState([]);

  const { mode, language } = useSettings();
  const { t } = useTranslation(language);
  const isFarmer = mode === 'farmer';

  useEffect(() => {
    const fetchAdvisory = async () => {
      setLoading(true);
      try {
        const res = await getFarmerAdvisory(commodity, mandi);
        setData(res);
        
        const advisoryText = language === 'en' ? res.advisory_text : res.advisory_text_hi;

        setMessages([
          {
            role: 'user',
            content: isFarmer 
              ? (language === 'hi' ? `आज मुझे अपने ${commodity} का क्या करना चाहिए?` : `What should I do with my ${commodity} today?`)
              : `Analyze the market conditions for ${commodity} in ${mandi} and provide an advisory.`
          },
          {
            role: 'assistant',
            content: advisoryText,
            meta: isFarmer ? null : {
              window: res.best_sell_window,
              price: res.expected_price_range
            }
          }
        ]);
      } catch (error) {
        console.error(error);
      } finally {
        setLoading(false);
      }
    };
    fetchAdvisory();
  }, [commodity, mandi, language, isFarmer]);

  if (loading && messages.length === 0) return (
    <div className="flex items-center justify-center h-[500px]">
      <div className="flex flex-col items-center text-gray-500 space-y-4">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
        <p className="text-sm font-bold tracking-widest uppercase animate-pulse">
          {t('processing')}
        </p>
      </div>
    </div>
  );

  return (
    <div className="max-w-4xl mx-auto h-[calc(100vh-12rem)] flex flex-col relative animate-fade-in">
      
      {/* Chat Header */}
      <div className="flex justify-between items-center mb-6 pb-4 border-b border-gray-200">
        <div className="flex items-center space-x-4">
          <div className="w-12 h-12 bg-gray-50 border border-gray-200 rounded-xl flex items-center justify-center shadow-[0_0_15px_rgba(16,185,129,0.1)]">
            <Bot className="w-6 h-6 text-primary" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900 flex items-center">
              {t('ai_farmer_advisory')} <Sparkles className="w-4 h-4 ml-2 text-yellow-500" />
            </h1>
            <p className="text-xs text-gray-500 font-mono mt-1 uppercase tracking-wider">
              {commodity} · {mandi}
            </p>
          </div>
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex-1 overflow-y-auto space-y-8 pr-4 pb-10 scroll-smooth">
        <AnimatePresence>
          {messages.map((msg, idx) => (
            <motion.div 
              key={idx}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.2 }}
              className={cn(
                "flex space-x-4 max-w-[85%]",
                msg.role === 'user' ? "ml-auto flex-row-reverse space-x-reverse" : ""
              )}
            >
              <div className={cn(
                "w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mt-1",
                msg.role === 'user' ? "bg-gray-100 border border-gray-200" : "bg-primary/10 border border-primary/20"
              )}>
                {msg.role === 'user' ? <User className="w-4 h-4 text-gray-600" /> : <Bot className="w-4 h-4 text-primary" />}
              </div>
              
              <div className={cn(
                "rounded-2xl p-5 text-[15px] leading-relaxed shadow-sm",
                msg.role === 'user' 
                  ? "bg-gray-100 text-gray-800 rounded-tr-sm border border-gray-200" 
                  : "bg-transparent text-gray-700 font-medium"
              )}>
                <div className={isFarmer && msg.role === 'assistant' ? "text-xl font-bold leading-relaxed text-gray-900" : ""}>
                  {msg.content}
                </div>
                
                {/* Embedded Widgets for Assistant (Only in Pro Mode) */}
                {msg.meta && !isFarmer && (
                  <motion.div 
                    initial={{ opacity: 0, marginTop: 0 }}
                    animate={{ opacity: 1, marginTop: 24 }}
                    transition={{ delay: 1 }}
                    className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6 pt-6 border-t border-gray-200"
                  >
                    <div className="bg-gray-50 border border-gray-200 rounded-xl p-4">
                      <span className="text-[10px] uppercase tracking-widest text-gray-500 font-bold block mb-1">{t('best_sell_window')}</span>
                      <span className="text-primary font-bold">{msg.meta.window}</span>
                    </div>
                    <div className="bg-gray-50 border border-gray-200 rounded-xl p-4">
                      <span className="text-[10px] uppercase tracking-widest text-gray-500 font-bold block mb-1">{t('expected_price')}</span>
                      <span className="text-gray-900 font-mono font-bold">₹{msg.meta.price} <span className="text-zinc-600 text-xs font-sans">/ Qtl</span></span>
                    </div>
                  </motion.div>
                )}
              </div>
            </motion.div>
          ))}
          {loading && (
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex space-x-4 max-w-[85%]"
            >
              <div className="w-8 h-8 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center flex-shrink-0 mt-1">
                <Bot className="w-4 h-4 text-primary" />
              </div>
              <div className="bg-transparent p-5">
                <div className="flex space-x-2">
                  <div className="w-2 h-2 rounded-full bg-primary/40 animate-bounce"></div>
                  <div className="w-2 h-2 rounded-full bg-primary/60 animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                  <div className="w-2 h-2 rounded-full bg-primary/80 animate-bounce" style={{ animationDelay: '0.4s' }}></div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Input Area */}
      <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-white via-white to-transparent pt-10 pb-2">
        <div className="relative">
          <input 
            type="text" 
            placeholder={t('ask_placeholder')}
            disabled
            className="w-full bg-gray-50 border border-gray-200 rounded-full py-4 pl-6 pr-14 text-gray-900 focus:outline-none focus:border-primary/50 transition-colors shadow-lg cursor-not-allowed opacity-70"
          />
          <button className="absolute right-2 top-2 p-2 bg-primary rounded-full hover:bg-primary transition-colors opacity-50 cursor-not-allowed">
            <Send className="w-4 h-4 text-white" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default FarmerAdvisory;
