"use client";
import React, { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { getDatabase, ref, onValue } from "firebase/database"; // Firebase Realtime DB
import { getLatestPrice } from "../coinbasePriceFeed"; // Real-time price feed

// Dynamically import ApexCharts
const Chart = dynamic(() => import("react-apexcharts"), { ssr: false });

export default function BotChart({ botId, userId }) {
  const db = getDatabase();

  // 🔹 Market Data (Updated Every 30 Seconds)
  const [marketData, setMarketData] = useState([]);

  // 🔹 Trades (Fetched from Firebase)
  const [trades, setTrades] = useState([]);

  // 🔹 Bot Balances
  const [botBalances, setBotBalances] = useState({ USD: 0, BTC: 0, ETH: 0 });

  // 🔹 Total Bot Value
  const [totalBotValue, setTotalBotValue] = useState(0);

  // 🔹 Market Prices (to track real-time updates)
  const [liveBTCPrice, setLiveBTCPrice] = useState(getLatestPrice("BTC") || 0);
  const [liveETHPrice, setLiveETHPrice] = useState(getLatestPrice("ETH") || 0);

  // 🔹 Fetch Trades from Firebase in Real-Time
  useEffect(() => {
    const tradesRef = ref(db, `bots/${userId}/${botId}/trades`);
    onValue(tradesRef, (snapshot) => {
      if (snapshot.exists()) {
        const tradeData = Object.values(snapshot.val());
        // Keep only trades at 1-minute intervals (last 60 minutes)
        const filteredTrades = tradeData.filter(
          (trade) => Date.now() - trade.time < 60 * 60 * 1000
        );
        setTrades(filteredTrades);
      }
    });
  }, [botId, userId]);

  // 🔹 Fetch Bot Balances from Firebase in Real-Time
  useEffect(() => {
    const balanceRef = ref(db, `bots/${userId}/${botId}/balances`);
    onValue(balanceRef, (snapshot) => {
      if (snapshot.exists()) {
        setBotBalances(snapshot.val()); // ✅ Update botBalances in real-time
      }
    });
  }, [botId, userId]);

  // 🔹 Fetch Market Data (Every 15 Seconds)
  useEffect(() => {
    const interval = setInterval(() => {
      const btcPrice = getLatestPrice("BTC");
      const ethPrice = getLatestPrice("ETH");

      if (btcPrice) setLiveBTCPrice(btcPrice);
      if (ethPrice) setLiveETHPrice(ethPrice);

      if (btcPrice) {
        setMarketData((prev) => [
          ...prev.slice(-100), // Keep last 100 data points
          { x: new Date().getTime(), y: btcPrice },
        ]);
      }
    }, 15000); // 15s interval

    return () => clearInterval(interval);
  }, []);

  // 🔹 Calculate Total Bot Value When Market Data or Balances Change
  useEffect(() => {
    console.log("🔥 Recalculating Bot Value...");
    if (botBalances) {
      console.log("📊 Bot Balances:", botBalances);
      const newTotalValue =
        (botBalances.USD || 0) +
        (botBalances.BTC || 0) * liveBTCPrice +
        (botBalances.ETH || 0) * liveETHPrice;

      setTotalBotValue(newTotalValue); // ✅ Ensure this updates dynamically
    }
  }, [botBalances, liveBTCPrice, liveETHPrice]); // 🔥 Recalculate when market prices OR balances change

  // 🔹 Chart Configuration
  const options = {
    chart: {
      type: "line",
      background: "transparent",
      animations: { enabled: true },
    },
    xaxis: {
      type: "datetime",
    },
    stroke: {
      curve: "smooth",
      width: 2,
    },
    markers: {
      size: 0,
    },
    // 🔹 Trade Annotations (Buy/Sell Markers)
    annotations: {
      points: trades.map((trade) => ({
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
            background: trade.side === "buy" ? "#00c853" : "#d50000",
          },
        },
      })),
    },
    tooltip: {
      x: {
        format: "dd MMM yyyy HH:mm:ss",
      },
    },
  };

  const series = [
    {
      name: "BTC Price (30s intervals)",
      data: marketData,
    },
  ];

  return (
    <div className="p-4 bg-white rounded shadow-md">
      {/* 🔹 Header Section */}
      <h2 className="text-xl font-semibold mb-4">Trading Bot Dashboard</h2>
      <p className="text-gray-600">Live Market & Trade Analysis</p>

      {/* 🔹 Bot Value Display */}
      <div className="p-4 rounded-lg bg-gray-100 flex items-center justify-between mt-4">
        <div>
          <p className="text-sm text-gray-600">Bot’s Total Value</p>
          <h2 className="text-2xl font-bold text-green-700">
            ${totalBotValue.toFixed(2)}
          </h2>
        </div>
        <div className="space-x-6 flex">
          <div>
            <p className="text-xs text-gray-500">BTC Price</p>
            <p className="text-sm font-semibold">${liveBTCPrice.toFixed(2)}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">ETH Price</p>
            <p className="text-sm font-semibold">${liveETHPrice.toFixed(2)}</p>
          </div>
        </div>
      </div>

      {/* 🔹 Balance Display */}
      <div className="grid grid-cols-3 gap-4 mt-4">
        <div className="p-4 border rounded-lg bg-gray-50">
          <h3 className="text-gray-800 text-sm">USD Balance</h3>
          <p className="text-lg font-semibold">${botBalances.USD.toFixed(2)}</p>
        </div>
        <div className="p-4 border rounded-lg bg-gray-50">
          <h3 className="text-gray-800 text-sm">BTC Balance</h3>
          <p className="text-lg font-semibold">
            {botBalances.BTC.toFixed(6)} BTC
          </p>
        </div>
        <div className="p-4 border rounded-lg bg-gray-50">
          <h3 className="text-gray-800 text-sm">ETH Balance</h3>
          <p className="text-lg font-semibold">
            {botBalances.ETH.toFixed(6)} ETH
          </p>
        </div>
      </div>

      {/* 🔹 Chart Display */}
      <div className="bg-white p-4 rounded-lg shadow mt-4">
        <Chart options={options} series={series} type="line" height={400} />
      </div>
    </div>
  );
}
