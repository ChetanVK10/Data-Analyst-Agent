import React, { useEffect, useRef } from 'react';
import Plotly from 'plotly.js-dist-min';

export interface PlotlyChartProps {
  chartData: any; // The Plotly JSON object (e.g. { data: [...], layout: {...} })
  chartId?: string;
}

export const PlotlyChart: React.FC<PlotlyChartProps> = ({ chartData, chartId }) => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current || !chartData) return;

    try {
      // Clean previous plots
      Plotly.purge(containerRef.current);
      
      const plotData = chartData.data || [];
      const layout = chartData.layout || {};
      
      // Override layout for dark premium theme integration
      const themedLayout = {
        ...layout,
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: {
          family: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
          color: '#f4f4f5',
          size: 11
        },
        xaxis: {
          ...layout.xaxis,
          gridcolor: 'rgba(255, 255, 255, 0.05)',
          linecolor: 'rgba(255, 255, 255, 0.08)',
          zerolinecolor: 'rgba(255, 255, 255, 0.08)',
        },
        yaxis: {
          ...layout.yaxis,
          gridcolor: 'rgba(255, 255, 255, 0.05)',
          linecolor: 'rgba(255, 255, 255, 0.08)',
          zerolinecolor: 'rgba(255, 255, 255, 0.08)',
        },
        margin: { t: 40, r: 20, l: 50, b: 40 }
      };

      Plotly.newPlot(
        containerRef.current, 
        plotData, 
        themedLayout, 
        { responsive: true, displayModeBar: false }
      );
    } catch (e) {
      console.error("Plotly rendering failed:", e);
    }
    
    return () => {
      if (containerRef.current) {
        try {
          Plotly.purge(containerRef.current);
        } catch (e) {}
      }
    };
  }, [chartData]);

  return (
    <div 
      id={chartId}
      ref={containerRef} 
      className="w-full h-full min-h-[450px]" 
      style={{ minHeight: '450px' }} 
    />
  );
};
export default PlotlyChart;
