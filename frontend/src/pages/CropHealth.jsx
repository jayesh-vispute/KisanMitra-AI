import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { getCropHealth } from '../utils/api';
import { Map, Droplets, Thermometer, Leaf, Satellite, CloudRain, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { cn } from '../lib/utils';
import { useSettings } from '../contexts/SettingsContext';
import { useTranslation } from '../locales/translations';

const CircularProgress = ({ value, max, label, color, delay }) => {
  const percentage = (value / max) * 100;
  const radius = 40;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  return (
    <motion.div 
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5, delay }}
      className="flex flex-col items-center relative"
    >
      <div className="relative w-32 h-32 flex items-center justify-center mb-4">
        <svg className="w-full h-full transform -rotate-90">
          <circle
            cx="64"
            cy="64"
            r={radius}
            stroke="currentColor"
            strokeWidth="8"
            fill="transparent"
            className="text-zinc-800"
          />
          <motion.circle
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset }}
            transition={{ duration: 1.5, delay: delay + 0.2, ease: "easeOut" }}
            cx="64"
            cy="64"
            r={radius}
            stroke="currentColor"
            strokeWidth="8"
            fill="transparent"
            strokeDasharray={circumference}
            className={color}
            strokeLinecap="round"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-black text-gray-900">{value.toFixed(1)}</span>
        </div>
      </div>
      <h3 className="text-xs font-bold text-gray-500 uppercase tracking-widest text-center">{label}</h3>
    </motion.div>
  );
};

const FarmerStatusCard = ({ title, status, icon: Icon, colorClass, delay }) => (
  <motion.div 
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ delay }}
    className="bg-white shadow-sm  border border-gray-200 rounded-3xl p-8 flex items-center space-x-6"
  >
    <div className={cn("p-4 rounded-full", colorClass.replace('text-', 'bg-').replace('500', '500/20'))}>
      <Icon className={cn("w-12 h-12", colorClass)} />
    </div>
    <div>
      <h3 className="text-xl font-bold text-gray-600 mb-1">{title}</h3>
      <p className="text-3xl font-extrabold text-gray-900">{status}</p>
    </div>
  </motion.div>
);

const CropHealth = ({ mandi }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const { mode, language } = useSettings();
  const { t } = useTranslation(language);
  const isFarmer = mode === 'farmer';

  useEffect(() => {
    const fetchHealth = async () => {
      setLoading(true);
      try {
        const res = await getCropHealth(mandi);
        setData(res);
      } catch (error) {
        console.error(error);
      } finally {
        setLoading(false);
      }
    };
    fetchHealth();
  }, [mandi]);

  if (loading) return (
    <div className="w-full h-[600px] bg-white shadow-sm rounded-3xl border border-gray-200 relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-r from-zinc-900/50 via-zinc-800/50 to-zinc-900/50 animate-[loading_2s_infinite_linear] bg-[length:200%_100%]" />
    </div>
  );
  if (!data) return <div>{t('data_unavailable')}</div>;

  const isHighRisk = data.stress_level === 'High';
  const isModRisk = data.stress_level === 'Moderate';

  return (
    <div className="max-w-6xl mx-auto space-y-8 animate-fade-in">
      
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4 border-b border-gray-200 pb-6">
        <div>
          {!isFarmer && (
            <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-bold tracking-wide mb-4">
              <Satellite className="w-3 h-3 animate-pulse" />
              <span>MODIS SATELLITE TELEMETRY</span>
            </div>
          )}
          <h1 className="text-3xl font-extrabold text-gray-900 capitalize">
            {isFarmer ? t('nav_farmer_health') : t('nav_health')}
          </h1>
          <p className="text-gray-500 mt-1 flex items-center text-sm font-medium">
            <Map className="w-4 h-4 mr-2 text-zinc-600" /> 
            {isFarmer ? `${mandi}, ${data.state}` : `Monitoring active farm clusters in ${mandi}, ${data.state}`}
          </p>
        </div>
        
        <div className="text-right">
          {!isFarmer && <p className="text-xs text-zinc-600 font-mono mb-1">LAT {data.coordinates?.lat} / LON {data.coordinates?.lon}</p>}
          <div className={cn(
            "inline-flex items-center px-4 py-1.5 rounded-full text-sm font-bold border",
            isHighRisk ? "bg-red-500/10 text-red-400 border-red-500/20 shadow-[0_0_15px_rgba(239,68,68,0.2)]" :
            isModRisk ? "bg-orange-500/10 text-orange-400 border-orange-500/20" :
            "bg-primary/10 text-primary border-primary/20 shadow-[0_0_15px_rgba(16,185,129,0.2)]"
          )}>
            {isHighRisk ? <AlertTriangle className="w-4 h-4 mr-2" /> : <CheckCircle2 className="w-4 h-4 mr-2" />}
            {isFarmer ? (isHighRisk ? "Crop is in Danger" : isModRisk ? "Crop Needs Attention" : t('healthy_crop')) : `${data.stress_level} Stress Detected`}
          </div>
        </div>
      </div>

      {/* Main Gauges or Cards */}
      {isFarmer ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <FarmerStatusCard 
            title={language === 'hi' ? 'फसल की हरियाली' : 'Crop Greenness'} 
            status={data.ndvi_proxy > 0.6 ? (language === 'hi' ? 'बहुत अच्छी' : 'Very Good') : data.ndvi_proxy > 0.4 ? (language === 'hi' ? 'सामान्य' : 'Okay') : (language === 'hi' ? 'कमजोर' : 'Poor')} 
            icon={Leaf} 
            colorClass="text-primary" 
            delay={0.1} 
          />
          <FarmerStatusCard 
            title={t('precipitation')} 
            status={data.rainfall_30d_mm > 50 ? (language === 'hi' ? 'पर्याप्त' : 'Plenty') : (language === 'hi' ? 'कम' : 'Low')} 
            icon={CloudRain} 
            colorClass="text-blue-500" 
            delay={0.2} 
          />
          <FarmerStatusCard 
            title={t('temperature')} 
            status={data.temperature_avg > 35 ? (language === 'hi' ? 'अधिक गर्मी' : 'Very Hot') : (language === 'hi' ? 'सामान्य' : 'Normal')} 
            icon={Thermometer} 
            colorClass="text-orange-500" 
            delay={0.3} 
          />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="bg-white shadow-sm  border border-gray-200 rounded-3xl p-8 flex flex-col items-center justify-center relative overflow-hidden"
          >
            <div className="absolute -top-10 -right-10 w-32 h-32 bg-primary/10 blur-[50px] rounded-full pointer-events-none" />
            <CircularProgress 
              value={data.ndvi_proxy} 
              max={1.0} 
              label="Vegetation Index (NDVI)" 
              color="text-primary"
              delay={0.2}
            />
          </motion.div>

          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="bg-white shadow-sm  border border-gray-200 rounded-3xl p-8 flex flex-col items-center justify-center relative overflow-hidden"
          >
            <div className="absolute -top-10 -right-10 w-32 h-32 bg-blue-500/10 blur-[50px] rounded-full pointer-events-none" />
            <CircularProgress 
              value={data.rainfall_30d_mm} 
              max={200} 
              label="30D Precipitation (mm)" 
              color="text-blue-500"
              delay={0.3}
            />
          </motion.div>

          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="bg-white shadow-sm  border border-gray-200 rounded-3xl p-8 flex flex-col items-center justify-center relative overflow-hidden"
          >
            <div className="absolute -top-10 -right-10 w-32 h-32 bg-orange-500/10 blur-[50px] rounded-full pointer-events-none" />
            <CircularProgress 
              value={data.temperature_avg} 
              max={50} 
              label="7D Avg Temperature (°C)" 
              color="text-orange-500"
              delay={0.4}
            />
          </motion.div>
        </div>
      )}

      {/* AI Recommendation */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        className="relative rounded-3xl p-1 bg-gradient-to-r from-primary/20 via-blue-500/20 to-primary/20"
      >
        <div className="bg-white shadow-sm rounded-[22px] p-8 relative overflow-hidden">
          <div className="absolute top-0 right-0 p-8 opacity-5">
            <Leaf className="w-64 h-64" />
          </div>
          
          <div className="relative z-10">
            <h3 className="text-xs font-black uppercase tracking-[0.2em] text-primary mb-4 flex items-center">
              <span className="w-2 h-2 rounded-full bg-primary mr-2 animate-pulse"></span>
              {t('treatment_recommendation')}
            </h3>
            <p className="text-xl md:text-2xl text-gray-900 font-medium leading-relaxed max-w-4xl">
              {data.recommendation}
            </p>
          </div>
        </div>
      </motion.div>
    </div>
  );
};

export default CropHealth;
