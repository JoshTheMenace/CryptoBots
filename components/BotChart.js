"use client";
import React, { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { getDatabase, ref, onValue } from "firebase/database"; // Firebase Realtime DB
import { getLatestPrice } from "../coinbasePriceFeed"; // Real-time price feed

// Dynamically import ApexCharts for client-side rendering
const Chart = dynamic(() => import("react-apexcharts"), { ssr: false });

export default function BotChart({ botId, userId, trades, botBalances }) {
  const db = getDatabase();

  // 🔹 Market Data for BTC Chart
  const [marketData, setMarketData] = useState([]);
  // 🔹 Live BTC/ETH Prices
  const [liveBTCPrice, setLiveBTCPrice] = useState(getLatestPrice("BTC") || 0);
  const [liveETHPrice, setLiveETHPrice] = useState(getLatestPrice("ETH") || 0);
  const [liveXRPPrice, setLiveXRPPrice] = useState(getLatestPrice("XRP") || 0);
  // 🔹 Total Bot Value
  const [totalBotValue, setTotalBotValue] = useState(0);

  // 🔹 Optional: If you prefer fetching trades in this component (instead of receiving via props), uncomment:
  /*
  const [trades, setTrades] = useState([]);

  useEffect(() => {
    const tradesRef = ref(db, `bots/${userId}/${botId}/trades`);
    onValue(tradesRef, (snapshot) => {
      if (snapshot.exists()) {
        const tradeData = Object.values(snapshot.val());
        // Example filtering...
        setTrades(tradeData);
      }
    });
  }, [botId, userId]);
  */

  // 🔹 Update Live Market Data every 15 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      const btcPrice = getLatestPrice("BTC");
      const ethPrice = getLatestPrice("ETH");
      const xrpPrice = getLatestPrice("XRP");

      if (btcPrice) {
        setLiveBTCPrice(btcPrice);
        // Keep last 100 data points for the BTC chart
        setMarketData((prev) => [
          ...prev.slice(-99),
          { x: new Date().getTime(), y: btcPrice },
        ]);
      }
      if (ethPrice) {
        setLiveETHPrice(ethPrice);
      }
      if (xrpPrice) {
        setLiveXRPPrice(xrpPrice);
      }

    }, 15000);

    return () => clearInterval(interval);
  }, []);

  // 🔹 Calculate Total Bot Value whenever balances or prices change
  useEffect(() => {
    const usd = botBalances?.USD || 0;
    const btc = botBalances?.BTC || 0;
    const eth = botBalances?.ETH || 0;
    const xrp = botBalances?.XRP || 0;
    const newTotal =
      usd + btc * liveBTCPrice + eth * liveETHPrice; + xrp * liveXRPPrice;

    setTotalBotValue(newTotal);
  }, [botBalances, liveBTCPrice, liveETHPrice, liveXRPPrice]);

  // 🔹 ApexCharts Configuration
  const options = {
    chart: {
      type: "line",
      background: "transparent",
      animations: { enabled: true },
      toolbar: { show: false },
    },
    xaxis: {
      type: "datetime",
      labels: { style: { colors: "#ccc" } },
    },
    yaxis: {
      labels: { style: { colors: "#ccc" } },
    },
    stroke: {
      curve: "smooth",
      width: 2,
    },
    markers: {
      size: 0,
    },
    tooltip: {
      theme: "dark",
      x: { format: "HH:mm:ss" },
    },
    // 🔹 Annotate Buy/Sell trades
    annotations: {
      points: trades?.map((trade) => ({
        x: trade.time,
        y: trade.price,
        marker: {
          size: 6,
          fillColor: trade.side === "buy" ? "#00c853" : "#d50000",
          strokeColor: "#fff",
          strokeWidth: 2,
        },
        label: {
          text: trade.side.toUpperCase(),
          style: {
            color: "#fff",
            backgroundColor: trade.side === "buy" ? "#00c853" : "#d50000",
          },
        },
      })),
    },
  };

  const series = [
    {
      name: "BTC Price",
      data: marketData,
    },
  ];

  return (
    <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl p-6 shadow-lg">
      {/* 🔹 Title and Live Data */}
      <div className="mb-6">
        <h2 className="text-2xl font-semibold text-white">
          Live Market & Trade Analysis
        </h2>
        <p className="text-sm text-gray-300 mt-2">
          Real-time BTC chart and your bot’s trading history.
        </p>
      </div>

      {/* 🔹 Bot Value + Current Prices */}
      <div className="flex flex-col md:flex-row md:items-center gap-4 mb-6 bg-white/10 rounded-lg p-4 justify-between">
        <div>
          <p className="text-gray-200 text-xs">Bot’s Total Value</p>
          <h3 className="text-2xl font-bold text-green-400">
            ${totalBotValue.toFixed(2)}
          </h3>
        </div>
        <div className="flex items-center gap-6">
          <div>
            <p className="text-gray-200 text-xs">BTC Price</p>
            <p className="text-lg font-semibold">${liveBTCPrice.toFixed(2)}</p>
          </div>
          <div>
            <p className="text-gray-200 text-xs">ETH Price</p>
            <p className="text-lg font-semibold">${liveETHPrice.toFixed(2)}</p>
          </div>
          <div>
            <p className="text-gray-200 text-xs">XRP Price</p>
            <p className="text-lg font-semibold">${liveXRPPrice.toFixed(2)}</p>
          </div>
        </div>
      </div>

      {/* 🔹 Balances */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-white/10 rounded-lg p-4 text-center">
          <p className="text-gray-200 text-sm">USD Balance</p>
          <p className="text-lg font-bold">${botBalances.USD.toFixed(2)}</p>
        </div>
        <div className="bg-white/10 rounded-lg p-4 text-center">
          <p className="text-gray-200 text-sm">BTC Balance</p>
          <p className="text-lg font-bold">
            {botBalances.BTC.toFixed(6)} BTC
          </p>
        </div>
        <div className="bg-white/10 rounded-lg p-4 text-center">
          <p className="text-gray-200 text-sm">ETH Balance</p>
          <p className="text-lg font-bold">
            {botBalances.ETH.toFixed(6)} ETH
          </p>
        </div>
      </div>

      {/* 🔹 Chart Component */}
      <div className="bg-white/5 rounded-lg p-4">
        <Chart options={options} series={series} type="line" height={400} />
      </div>
    </div>
  );
}
