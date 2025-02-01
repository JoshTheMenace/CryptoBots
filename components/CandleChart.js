import React from "react";
import Chart from "react-apexcharts";

const CandleChart = ({ data }) => {
  const options = {
    chart: { type: "candlestick", toolbar: { show: true } },
    xaxis: { type: "datetime" },
  };

  const series = [
    {
      data: data.map(({ date, open, high, low, close }) => ({
        x: new Date(date),
        y: [open, high, low, close],
      })),
    },
  ];

  return <Chart options={options} series={series} type="candlestick" height={500} />;
};

export default CandleChart;
