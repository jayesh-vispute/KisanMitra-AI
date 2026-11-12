import { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import { Sprout, Globe, Tractor, Briefcase, Type } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { getDashboardSummary } from '../utils/api';
import { cn } from '../lib/utils';
import { useSettings } from '../contexts/SettingsContext';
import { useTranslation, translations } from '../locales/translations';

const Navbar = () => {
  const [lastUpdated, setLastUpdated] = useState(null);
  const [isStale, setIsStale] = useState(false);
  const [showLangMenu, setShowLangMenu] = useState(false);

  const { language, setLanguage, mode, setMode, fontSize, setFontSize } = useSettings();
  const { t } = useTranslation(language);

  const fetchTimestamp = async () => {
    try {
      const data = await getDashboardSummary();
      const ts = new Date(data.last_updated);
      setLastUpdated(ts);
      const diffMs = Date.now() - ts.getTime();
      setIsStale(diffMs > 2 * 60 * 60 * 1000); // > 2 hours
    } catch (e) {
      console.error("Navbar poll error:", e);
    }
  };

  useEffect(() => {
    fetchTimestamp();
    const interval = setInterval(fetchTimestamp, 60000);
    return () => clearInterval(interval);
  }, []);

  const formatTimestamp = (d) => {
    if (!d) return "";
    return d.toLocaleString("en-IN", {
      day: "2-digit", month: "short", year: "numeric",
      hour: "2-digit", minute: "2-digit", timeZone: "Asia/Kolkata",
    }) + " IST";
  };

  const isFarmer = mode === 'farmer';

  const navItems = [
    { name: isFarmer ? t('nav_farmer_dashboard') : t('nav_command_center'), path: '/dashboard' },
    { name: isFarmer ? t('nav_farmer_prices') : t('nav_forecast'), path: '/forecast' },
    { name: isFarmer ? t('nav_farmer_health') : t('nav_health'), path: '/crop-health' },
    { name: isFarmer ? t('nav_farmer_weather') : t('nav_weather'), path: '/weather' },
    { name: isFarmer ? t('nav_farmer_help') : t('nav_advisor'), path: '/farmer-advisory' },
    { name: isFarmer ? t('nav_farmer_warnings') : t('nav_alerts'), path: '/alerts' },
  ];

  const langs = [
    { code: 'en', name: t('lang_en') },
    { code: 'hi', name: t('lang_hi') },
    { code: 'mr', name: t('lang_mr') },
    { code: 'gu', name: t('lang_gu') },
    { code: 'pa', name: t('lang_pa') },
    { code: 'ta', name: t('lang_ta') },
    { code: 'te', name: t('lang_te') },
    { code: 'kn', name: t('lang_kn') },
  ];

  return (
    <nav className="glass-nav px-6 py-3 flex justify-between items-center flex-shrink-0 sticky top-0 z-50">
      <div className="flex items-center space-x-3 cursor-pointer group">
        <div className="relative">
          <div className="absolute inset-0 bg-primary rounded-lg blur opacity-40 group-hover:opacity-70 transition-opacity"></div>
          <div className="relative bg-gray-50 border border-gray-200 p-2 rounded-lg shadow-2xl">
            <Sprout className="w-5 h-5 text-primary" />
          </div>
        </div>
        <span className="text-lg font-bold tracking-tight text-gray-900">
          KisanMitra<span className="text-primary ml-0.5">AI</span>
        </span>
      </div>

      <div className="hidden lg:flex items-center space-x-1 bg-white shadow-md p-1.5 rounded-full border border-gray-200 shadow-lg ">
        <AnimatePresence mode="popLayout">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                cn(
                  "relative px-4 py-1.5 text-sm font-medium rounded-full transition-all duration-300",
                  isActive ? "text-gray-900 font-bold" : "text-gray-600 hover:text-gray-800 hover:bg-gray-50",
                  isFarmer && "text-base font-bold px-5"
                )
              }
            >
              {({ isActive }) => (
                <>
                  <motion.span 
                    key={item.name}
                    initial={{ opacity: 0, y: 5 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -5 }}
                    className="relative z-10"
                  >
                    {item.name}
                  </motion.span>
                  {isActive && (
                    <motion.div
                      layoutId="navbar-indicator"
                      className="absolute inset-0 bg-gray-100 border border-gray-200 rounded-full shadow-lg"
                      transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                    />
                  )}
                </>
              )}
            </NavLink>
          ))}
        </AnimatePresence>
      </div>

      <div className="flex items-center space-x-4">
        
        {/* Mode Switcher */}
        <button 
          onClick={() => setMode(isFarmer ? 'professional' : 'farmer')}
          className="flex items-center space-x-2 bg-gray-50 border border-gray-200 px-3 py-1.5 rounded-full hover:bg-gray-100 transition-colors"
        >
          {isFarmer ? <Tractor className="w-4 h-4 text-primary" /> : <Briefcase className="w-4 h-4 text-blue-400" />}
          <span className={cn("text-xs font-bold", isFarmer ? "text-primary" : "text-blue-400")}>
            {isFarmer ? t('mode_farmer') : t('mode_pro')}
          </span>
        </button>

        {/* Font Size Toggle */}
        <button 
          onClick={() => setFontSize(fontSize === 'normal' ? 'large' : 'normal')}
          className="bg-gray-50 border border-gray-200 p-1.5 rounded-full hover:bg-gray-100 transition-colors"
          title="Toggle Text Size"
        >
          <Type className="w-4 h-4 text-gray-600" />
        </button>

        {/* Language Switcher */}
        <div className="relative">
          <button 
            onClick={() => setShowLangMenu(!showLangMenu)}
            className="flex items-center space-x-2 bg-gray-50 border border-gray-200 px-3 py-1.5 rounded-full hover:bg-gray-100 transition-colors"
          >
            <Globe className="w-4 h-4 text-gray-700" />
            <span className="text-xs font-bold text-gray-700 uppercase">{language}</span>
          </button>
          
          <AnimatePresence>
            {showLangMenu && (
              <motion.div 
                initial={{ opacity: 0, y: 10, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 10, scale: 0.95 }}
                className="absolute right-0 mt-2 w-48 bg-gray-50 border border-gray-200 rounded-2xl shadow-2xl overflow-hidden py-2 z-50"
              >
                {langs.map(l => (
                  <button
                    key={l.code}
                    onClick={() => { setLanguage(l.code); setShowLangMenu(false); }}
                    className={cn(
                      "w-full text-left px-4 py-2 text-sm font-medium transition-colors hover:bg-white/5",
                      language === l.code ? "text-primary bg-primary/10" : "text-gray-700"
                    )}
                  >
                    {l.name}
                  </button>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Live badge */}
        <div className={cn(
          "hidden md:flex items-center space-x-2 px-3 py-1.5 rounded-full border shadow-sm ",
          isStale ? "bg-orange-500/10 border-orange-500/20" : "bg-primary/10 border-primary/20"
        )}>
          <div className="relative flex h-2 w-2">
            <span className={cn(
              "animate-ping absolute inline-flex h-full w-full rounded-full opacity-75",
              isStale ? "bg-orange-400" : "bg-primary"
            )}></span>
            <span className={cn(
              "relative inline-flex rounded-full h-2 w-2",
              isStale ? "bg-orange-500" : "bg-primary"
            )}></span>
          </div>
          <span className={cn(
            "text-[11px] font-bold tracking-wide uppercase",
            isStale ? "text-orange-400" : "text-primary"
          )}>
            {isStale ? "Syncing..." : t('live_feed')}
          </span>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
