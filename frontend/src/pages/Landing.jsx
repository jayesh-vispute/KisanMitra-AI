import React from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { Leaf, Award, Target, ArrowRight, Zap, TrendingUp, CloudSun } from 'lucide-react';
import { useSettings } from '../contexts/SettingsContext';
import { useTranslation } from '../locales/translations';

const Landing = () => {
  const { language } = useSettings();
  const { t } = useTranslation(language);

  return (
    <div className="relative min-h-screen bg-slate-50 font-sans text-slate-900 overflow-x-hidden">
      
      {/* Global Background Grid & Shapes */}
      <div className="fixed inset-0 z-0 pointer-events-none">
        <div 
          className="absolute inset-0 opacity-[0.2]" 
          style={{ backgroundImage: "linear-gradient(to right, #059669 1px, transparent 1px), linear-gradient(to bottom, #059669 1px, transparent 1px)", backgroundSize: "40px 40px" }}
        />
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[50%] bg-emerald-200/60 rounded-full blur-[80px]" />
        <div className="absolute top-[40%] right-[-5%] w-[50%] h-[60%] bg-teal-200/60 rounded-full blur-[100px]" />
        <div className="absolute bottom-[10%] left-[10%] w-[30%] h-[40%] bg-lime-200/60 rounded-full blur-[80px]" />
      </div>

      {/* Floating Glassmorphic Navbar */}
      <div className="fixed top-0 w-full z-50 px-4 py-4 sm:px-6 lg:px-8 flex justify-center">
        <nav className="w-full max-w-7xl bg-white/70 backdrop-blur-xl border border-white/40 shadow-[0_8px_30px_rgb(0,0,0,0.04)] rounded-2xl flex items-center justify-between px-6 py-3">
          {/* Logo Area */}
          <div className="font-black text-2xl tracking-tighter flex items-center gap-2 text-emerald-900">
            <div className="bg-emerald-500 p-1.5 rounded-lg">
              <Leaf className="w-6 h-6 text-white" />
            </div>
            KisanMitra AI
          </div>
          
          {/* Navigation Links */}
          <div className="hidden md:flex items-center gap-1 font-semibold text-sm text-slate-600">
            <Link 
              to="/dashboard" 
              className="ml-4 px-6 py-2.5 rounded-xl bg-slate-900 text-white hover:bg-emerald-600 hover:shadow-lg hover:shadow-emerald-500/30 transition-all duration-300 flex items-center gap-2"
            >
              {language === 'hi' ? 'डैशबोर्ड खोलें' : 'Open Dashboard'} <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </nav>
      </div>

      {/* Hero Section */}
      <div className="relative w-full pt-40 pb-20 lg:pt-48 lg:pb-32 flex items-center justify-center">
        <div className="relative z-10 max-w-5xl mx-auto px-6 w-full text-center">
          <motion.div 
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: "easeOut" }}
            className="flex flex-col items-center"
          >
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white border border-slate-200 shadow-sm mb-8">
              <span className="flex h-2.5 w-2.5 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
              </span>
              <span className="text-sm font-bold text-slate-700 uppercase tracking-wide">
                {language === 'hi' ? 'भविष्य के बाजार भाव का सटीक अनुमान' : 'Predict the Future Price'}
              </span>
            </div>
            
            <h1 className="text-5xl sm:text-6xl md:text-7xl lg:text-8xl font-black text-slate-900 leading-[1.1] mb-6 tracking-tight">
              {language === 'hi' ? (
                <>किसान और व्यापारियों के लिए <br className="hidden md:block"/><span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-600 to-teal-500">स्मार्ट AI</span> समाधान</>
              ) : (
                <>AI-Powered Insights <br className="hidden md:block"/>for <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-600 to-teal-500">Sustainable</span> Farming</>
              )}
            </h1>
            
            <p className="text-lg md:text-xl text-slate-600 max-w-2xl mb-10 leading-relaxed">
              {t('welcome_subtitle')}
            </p>
            
            <div className="flex flex-col sm:flex-row gap-4 w-full sm:w-auto">
              <Link 
                to="/dashboard" 
                className="group bg-emerald-600 text-white font-bold text-lg py-4 px-10 rounded-2xl shadow-[0_8px_30px_rgb(5,150,105,0.3)] transition-all hover:-translate-y-1 flex items-center justify-center gap-2"
              >
                {language === 'hi' ? 'पूर्वानुमान देखें' : 'Explore Predictions'}
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </Link>
            </div>
          </motion.div>
        </div>
      </div>

      {/* Modern Bento Box Features Section */}
      <div id="about" className="relative z-10 max-w-7xl mx-auto px-6 py-24">
        <div className="text-center mb-16">
          <h2 className="text-4xl md:text-5xl font-bold text-slate-900 tracking-tight mb-4">
            {language === 'hi' ? 'हम कृषि भविष्य का सटीक अनुमान लगाते हैं' : 'We Predict the Agriculture Future'}
          </h2>
          <p className="text-slate-500 text-lg max-w-2xl mx-auto">
            {t('forecast_disclaimer')}
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Bento Box 1: Accuracy */}
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="md:col-span-2 bg-gradient-to-br from-slate-900 to-slate-800 rounded-3xl p-8 md:p-12 text-white relative overflow-hidden group"
          >
            <div className="absolute top-0 right-0 p-8 opacity-10 group-hover:opacity-20 transition-opacity group-hover:scale-110 duration-500">
              <Target className="w-48 h-48" />
            </div>
            <div className="relative z-10 h-full flex flex-col justify-between">
              <div>
                <div className="w-14 h-14 bg-emerald-500/20 backdrop-blur-md rounded-2xl flex items-center justify-center mb-6">
                  <Target className="w-8 h-8 text-emerald-400" />
                </div>
                <h3 className="text-5xl font-black mb-4">98%<span className="text-3xl text-slate-400"> {t('model_confidence')}</span></h3>
                <p className="text-slate-300 text-lg max-w-md leading-relaxed">
                  {language === 'hi' ? 'SARIMA, XGBoost और LSTM मॉडल का संयोजन उच्च सटीकता प्रदान करता है।' : 'Our hybrid ML pipeline combining SARIMA, XGBoost, and LSTM produces highly accurate real-time market predictions.'}
                </p>
              </div>
            </div>
          </motion.div>

          {/* Bento Box 2: Award */}
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.1 }}
            className="bg-white rounded-3xl p-8 border border-slate-200 shadow-sm hover:shadow-xl transition-shadow"
          >
            <div className="w-14 h-14 bg-yellow-100 rounded-2xl flex items-center justify-center mb-6">
              <Award className="w-8 h-8 text-yellow-600" />
            </div>
            <h3 className="text-2xl font-bold text-slate-900 mb-3">{t('ai_active')}</h3>
            <p className="text-slate-500 leading-relaxed">
              {t('data_source_notice')}
            </p>
          </motion.div>

          {/* Bento Box 3: Live Data */}
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.2 }}
            className="bg-white rounded-3xl p-8 border border-slate-200 shadow-sm hover:shadow-xl transition-shadow"
          >
            <div className="w-14 h-14 bg-blue-100 rounded-2xl flex items-center justify-center mb-6">
              <TrendingUp className="w-8 h-8 text-blue-600" />
            </div>
            <h3 className="text-2xl font-bold text-slate-900 mb-3">{t('live_feed')}</h3>
            <p className="text-slate-500 leading-relaxed">
              {t('data_source_notice')}
            </p>
          </motion.div>
        </div>
      </div>
    </div>
  );
};

export default Landing;
