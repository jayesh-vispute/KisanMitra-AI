import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import ForecastChart from '../components/ForecastChart';
import { Activity, BarChart3, TrendingUp, TrendingDown, Target, IndianRupee } from 'lucide-react';
import { cn } from '../lib/utils';
import { useSettings } from '../contexts/SettingsContext';
import { useTranslation } from '../locales/translations';

const Forecast = ({ commodity, mandi, horizon }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const { mode, language } = useSettings();
  const { t } = useTranslation(language);
  const isFarmer = mode === 'farmer';

  useEffect(() => {
    if (!commodity || !mandi) return;
    const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
    const fetchForecast = async () => {
      setLoading(true);
      try {
        const res = await fetch(
          `${API_BASE}/predict?commodity=${encodeURIComponent(commodity)}&mandi=${encodeURIComponent(mandi)}&horizon=${horizon}`
        );
        if (!res.ok) {
          setData(null);
          setError(`Prediction unavailable: ${res.status}`);
          setLoading(false);
          return;
        }
        const responseData = await res.json();
        setData(responseData);
        setError(null);
      } catch (err) {
        setData(null);
        setError("Could not connect to prediction server.");
      } finally {
        setLoading(false);
      }
    };
    fetchForecast();
  }, [commodity, mandi, horizon]);

  if (loading) return (
    <div className="w-full h-[600px] bg-white shadow-sm rounded-3xl border border-gray-200 relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-r from-zinc-900/50 via-zinc-800/50 to-zinc-900/50 animate-[loading_2s_infinite_linear] bg-[length:200%_100%]" />
    </div>
  );
  
  if (!data && !error) return <div className="p-8 text-center text-gray-500 font-medium">{t('data_unavailable')}</div>;

  const currentPrice = data?.current_price ?? 0;
  const startPrice = data?.forecast?.[0]?.price ?? 0;
  const endPrice = data?.forecast?.[data?.forecast?.length - 1]?.price ?? 0;
  const diff = endPrice - startPrice;
  const percentChange = data?.trend_percent != null
    ? Math.abs(data.trend_percent).toFixed(1)
    : startPrice > 0 ? Math.abs((diff / startPrice) * 100).toFixed(1) : "0.0";
  const isUp = (data?.trend_percent ?? diff) >= 0;

  return (
    <div className="space-y-6 animate-fade-in">
      {error && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-amber-800 text-sm">
          {error} — Select a commodity and market to load predictions.
        </div>
      )}
      
      {/* Top terminal bar */}
      <motion.div 
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col md:flex-row md:items-center justify-between bg-white shadow-sm border border-gray-200 rounded-2xl p-4 shadow-xl"
      >
        <div className="flex flex-wrap gap-4 items-center mb-4 md:mb-0">
          <div className="px-3 py-1.5 bg-gray-50 rounded-lg border border-gray-200 flex items-center">
            <span className="text-gray-500 text-xs font-bold tracking-widest uppercase mr-2">{t('commodity_label')}</span>
            <span className="text-primary font-mono font-bold capitalize">{commodity}</span>
          </div>
          <div className="px-3 py-1.5 bg-gray-50 rounded-lg border border-gray-200 flex items-center">
            <span className="text-gray-500 text-xs font-bold tracking-widest uppercase mr-2">{t('mandi_label')}</span>
            <span className="text-gray-800 font-mono font-bold capitalize">{mandi}</span>
          </div>
          <div className="px-3 py-1.5 bg-gray-50 rounded-lg border border-gray-200 flex items-center">
            <span className="text-gray-500 text-xs font-bold tracking-widest uppercase mr-2">{t('forecast_horizon')}</span>
            <span className="text-gray-800 font-mono font-bold">{horizon} {language === 'hi' ? 'दिन' : 'Days'}</span>
          </div>
        </div>

        {!isFarmer && (
          <div className="flex items-center space-x-3">
            <span className="text-gray-500 text-xs font-bold tracking-widest uppercase">AI Signal</span>
            <div className={cn(
              "px-4 py-1.5 rounded-full font-bold text-sm tracking-wide border flex items-center",
              isUp ? "bg-primary/10 text-primary border-primary/20" : "bg-red-500/10 text-red-400 border-red-500/20"
            )}>
              {isUp ? <TrendingUp className="w-4 h-4 mr-2" /> : <TrendingDown className="w-4 h-4 mr-2" />}
              {isUp ? (language === 'hi' ? 'बिक्री रोकें / रुकें' : 'STRONG BUY / HOLD') : (language === 'hi' ? 'तुरंत बेचें' : 'SELL NOW')}
            </div>
          </div>
        )}
      </motion.div>

      {/* Main Area */}
      <motion.div 
        initial={{ opacity: 0, scale: 0.98 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.1 }}
        className="bg-white shadow-sm  border border-gray-200 rounded-3xl p-6 shadow-2xl relative"
      >
        {!isFarmer && data?.forecast && (
          <div className="absolute top-6 right-6">
            <div className="flex items-end space-x-4">
              <div className="text-right">
                <p className="text-xs text-gray-500 font-bold tracking-widest uppercase mb-1">{t('predicted_price')}</p>
                <p className="text-3xl font-mono font-black text-gray-900">₹{endPrice.toFixed(0)}</p>
                <p className="text-xs text-gray-400 font-medium">₹{(endPrice / 100).toFixed(2)}/kg</p>
              </div>
              <div className={cn(
                "px-3 py-1 rounded-lg text-lg font-mono font-bold flex items-center mb-1",
                isUp ? "text-primary bg-primary/10" : "text-red-400 bg-red-500/10"
              )}>
                {isUp ? "+" : ""}{percentChange}%
              </div>
            </div>
          </div>
        )}

        <div className="mb-8">
          <h2 className="text-xl font-bold text-gray-900 flex items-center">
            <Activity className="w-5 h-5 mr-2 text-primary" /> 
            {t('price_prediction_overview')}
          </h2>
          <p className="text-gray-600 text-sm mt-1">
            {language === 'hi' 
              ? `${mandi} में ${commodity} के भाव अगले ${horizon} दिनों में ${isUp ? 'बढ़ने' : 'घटने'} की संभावना है।` 
              : `${commodity} prices expected to ${isUp ? "rise" : "fall"} by ${Math.abs(percentChange)}% over the next ${horizon} days in ${mandi}.`}
          </p>
        </div>

        {isFarmer ? (
          <div className="flex flex-col items-center justify-center p-8 bg-white shadow-sm rounded-2xl border border-gray-200">
            <motion.div 
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              className={cn(
                "w-32 h-32 rounded-full flex items-center justify-center mb-6 shadow-[0_0_50px_rgba(0,0,0,0.5)] border-4",
                isUp ? "bg-primary/20 border-primary text-primary" : "bg-red-500/20 border-red-500 text-red-400"
              )}
            >
              {isUp ? <TrendingUp className="w-16 h-16" /> : <TrendingDown className="w-16 h-16" />}
            </motion.div>
            <h3 className="text-4xl font-extrabold text-gray-900 mb-2">
              {isUp ? (language === 'hi' ? 'कीमत बढ़ने की संभावना है' : 'Prices are going UP') : (language === 'hi' ? 'कीमत घटने की संभावना है' : 'Prices are going DOWN')}
            </h3>
            <div className="flex items-center text-3xl font-bold text-gray-700 mt-4 bg-gray-50 px-6 py-3 rounded-2xl border border-gray-200">
              <IndianRupee className="w-8 h-8 mr-2 text-primary" />
              {endPrice.toFixed(0)} 
              <div className="flex flex-col ml-3">
                <span className="text-xl text-gray-500">{t('per_quintal')}</span>
                <span className="text-sm text-gray-400">₹{(endPrice / 100).toFixed(2)}/kg</span>
              </div>
            </div>
          </div>
        ) : (
          <div className="w-full bg-white shadow-sm rounded-2xl p-4 border border-gray-200">
            <ForecastChart data={data?.forecast ?? []} />
          </div>
        )}
      </motion.div>
    </div>
  );
};

export default Forecast;
