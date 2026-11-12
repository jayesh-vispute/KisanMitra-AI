import { AlertTriangle, TrendingUp } from 'lucide-react';
import { motion } from 'framer-motion';
import { cn } from '../lib/utils';

const AlertBanner = ({ alert, index = 0 }) => {
  const { commodity, mandi, alert_level, trigger_price, avg_price, forecast_date } = alert;
  
  const isCritical = alert_level === 'CRITICAL';
  const isHigh = alert_level === 'HIGH';
  
  const colorClass = isCritical 
    ? 'bg-red-500/10 border-red-500/20 text-red-400' 
    : isHigh 
      ? 'bg-orange-500/10 border-orange-500/20 text-orange-400'
      : 'bg-yellow-500/10 border-yellow-500/20 text-yellow-400';
      
  const badgeClass = isCritical 
    ? 'bg-red-500 text-zinc-950 shadow-[0_0_15px_rgba(239,68,68,0.5)]' 
    : isHigh 
      ? 'bg-orange-500 text-zinc-950' 
      : 'bg-yellow-500 text-zinc-950';
  
  const devPct = (((trigger_price - avg_price) / avg_price) * 100).toFixed(1);

  return (
    <motion.div 
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4, delay: index * 0.1 }}
      className={cn("flex items-center p-4 rounded-2xl border mb-3  relative overflow-hidden group hover:bg-gray-100 transition-colors", colorClass)}
    >
      {/* Background Warning Glow for Critical */}
      {isCritical && (
        <div className="absolute inset-0 bg-red-500/5 animate-pulse pointer-events-none"></div>
      )}

      <div className="flex-shrink-0 mr-5 relative z-10">
        <div className={cn("p-2 rounded-xl relative", badgeClass)}>
          {isCritical && (
            <span className="absolute inset-0 rounded-xl bg-red-500 animate-ping opacity-75"></span>
          )}
          <AlertTriangle className="w-5 h-5 relative z-10" />
        </div>
      </div>
      
      <div className="flex-1 relative z-10">
        <div className="flex items-center justify-between mb-1">
          <h4 className="font-bold text-lg capitalize text-gray-900">{commodity} <span className="text-gray-500 font-normal">in</span> {mandi}</h4>
          <span className={cn("px-2.5 py-0.5 rounded-md text-[10px] font-black uppercase tracking-widest", badgeClass)}>
            {alert_level}
          </span>
        </div>
        <div className="mt-1 flex items-center text-sm font-medium text-gray-600">
          <TrendingUp className="w-4 h-4 mr-2 text-gray-500" />
          Hitting <span className="font-mono font-bold text-gray-800 mx-1">₹{trigger_price}</span> by {new Date(forecast_date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })}
          <span className={cn(
            "ml-3 px-2 py-0.5 rounded text-[10px] border font-bold uppercase tracking-wide",
            isCritical ? "border-red-500/30 text-red-400 bg-red-500/10" : "border-orange-500/30 text-orange-400 bg-orange-500/10"
          )}>
            +{devPct}% vs Avg
          </span>
        </div>
      </div>
    </motion.div>
  );
};

export default AlertBanner;
