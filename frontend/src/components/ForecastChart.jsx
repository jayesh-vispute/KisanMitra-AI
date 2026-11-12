import { ComposedChart, Line, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { motion } from 'framer-motion';

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-gray-50/90  p-4 border border-gray-200 shadow-2xl rounded-2xl">
        <p className="font-bold text-gray-900 mb-3 tracking-wide">{label}</p>
        
        <div className="flex items-center space-x-3 bg-gray-100 p-2 rounded-lg border border-gray-200 mb-2">
          <div className="w-2 h-2 rounded-full bg-primary animate-pulse"></div>
          <div>
            <p className="text-[10px] text-gray-600 uppercase tracking-widest font-bold">Predicted</p>
            <p className="font-mono text-primary font-bold text-lg">
              ₹{payload[0].value.toFixed(0)}/q
            </p>
          </div>
        </div>

        {payload[1] && payload[2] && (
          <div className="text-xs text-gray-500 mt-2 px-2">
            <span className="block mb-1">Confidence Interval (95%)</span>
            <span className="font-mono text-gray-700">
              ₹{payload[1].value.toFixed(0)} — ₹{payload[2].value.toFixed(0)}
            </span>
          </div>
        )}
      </div>
    );
  }
  return null;
};

const ForecastChart = ({ data }) => {
  if (!data || data.length === 0) return null;

  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 1 }}
      className="w-full h-[400px] relative"
    >
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 20, right: 20, bottom: 20, left: 0 }}>
          <defs>
            <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
              <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
            </linearGradient>
            <linearGradient id="colorConfidence" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#10b981" stopOpacity={0.1}/>
              <stop offset="100%" stopColor="#10b981" stopOpacity={0}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
          
          <XAxis 
            dataKey="date" 
            tickFormatter={(tick) => {
              const date = new Date(tick);
              return `${date.getDate()} ${date.toLocaleString('default', { month: 'short' })}`;
            }}
            stroke="#52525b"
            fontSize={12}
            tickLine={false}
            axisLine={false}
            dy={10}
            fontFamily="Inter, sans-serif"
          />
          
          <YAxis 
            tickFormatter={(tick) => `₹${tick}`} 
            stroke="#52525b" 
            fontSize={12}
            tickLine={false}
            axisLine={false}
            dx={-10}
            domain={['dataMin - 100', 'dataMax + 100']}
            fontFamily="JetBrains Mono, monospace"
          />
          
          <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#3f3f46', strokeWidth: 1, strokeDasharray: '4 4' }} />
          
          <Area 
            type="monotone" 
            dataKey="upper" 
            stroke="none" 
            fill="url(#colorConfidence)" 
          />
          <Area 
            type="monotone" 
            dataKey="lower" 
            stroke="none" 
            fill="#09090b" 
          />
          
          <Line 
            type="monotone" 
            dataKey="price" 
            name="Predicted Price" 
            stroke="#10b981" 
            strokeWidth={3} 
            dot={false}
            activeDot={{ r: 6, fill: "#10b981", stroke: "#000", strokeWidth: 2 }} 
            animationDuration={2500}
            animationEasing="ease-out"
          />
        </ComposedChart>
      </ResponsiveContainer>
    </motion.div>
  );
};

export default ForecastChart;
