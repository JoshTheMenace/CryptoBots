"use client";

import { useState, useEffect } from "react";
import { ref, onValue } from "firebase/database";
import { db } from "../../firebaseClient"; // Update path to your firebase client
import { useRouter } from "next/navigation";

export default function LeaderboardPage() {
  const [allBots, setAllBots] = useState([]);
  const [marketData, setMarketData] = useState({ BTC: 0, ETH: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const router = useRouter();

  const INITIAL_CAPITAL = 10000; // Adjust if your bots start with different amounts

  // 1) Fetch all bots from "bots" root
  useEffect(() => {
    const botsRef = ref(db, "bots");

    // Provide an error callback so we don't get stuck in loading if there's a permission or network issue
    const unsubscribe = onValue(
      botsRef,
      (snapshot) => {
        const data = snapshot.val() || {};

        // Flatten the structure: { userId: { botId: {...}, ...} } --> [ { userId, botId, ... }, ... ]
        const botsArray = [];
        Object.entries(data).forEach(([userId, userBots]) => {
          if (userBots) {
            Object.entries(userBots).forEach(([botId, botData]) => {
              botsArray.push({
                userId,
                botId,
                ...botData,
              });
            });
          }
        });

        setAllBots(botsArray);
        setLoading(false);
      },
      (err) => {
        console.error("❌ onValue error:", err);
        setError("Failed to load leaderboard. Check database permissions.");
        setLoading(false);
      }
    );

    return () => unsubscribe();
  }, []);

  // 2) Fetch market data (BTC & ETH prices) from your existing API
  //    or adapt this to your internal fetching mechanism
  useEffect(() => {
    async function fetchMarketData() {
      try {
        const res = await fetch("/api/market-data");
        const data = await res.json();
        console.log("Market Data:", data);
        setMarketData(data);
      } catch (error) {
        console.error("Error fetching market data for leaderboard:", error);
        setError("Failed to load market data.");
      }
    }
    fetchMarketData();

    // Optionally refetch market data every 30 seconds
    const interval = setInterval(fetchMarketData, 30000);
    return () => clearInterval(interval);
  }, []);

  // 3) Calculate each bot's total value & profit margin, then sort descending by profit margin
  const leaderboard = allBots
    .map((bot) => {
      const usd = bot.balances?.USD || 0;
      const btc = bot.balances?.BTC || 0;
      const eth = bot.balances?.ETH || 0;

      const currentValue =
        usd + btc * (marketData.BTC || 0) + eth * (marketData.ETH || 0);

      const profitMargin = ((currentValue - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100;

      return {
        userId: bot.userId,
        botId: bot.botId,
        name: bot.name,
        currentValue,
        profitMargin,
      };
    })
    .sort((a, b) => b.profitMargin - a.profitMargin);

  // 4) Handle Loading and Error States
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-purple-900 via-black to-gray-900">
        <p className="text-white text-xl animate-pulse">Loading Leaderboard...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-900 via-black to-gray-900 flex items-center justify-center">
        <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl p-6 text-center">
          <h1 className="text-xl font-semibold text-red-400 mb-4">Error</h1>
          <p className="text-white">{error}</p>
          <button
            onClick={() => router.back()}
            className="mt-6 px-6 py-2 rounded-md font-semibold bg-gradient-to-r from-indigo-600 to-pink-600
                       hover:from-indigo-500 hover:to-pink-500 transition-transform transform hover:scale-105"
          >
            ← Go Back
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-900 via-black to-gray-900 p-6 text-white">
      <div className="max-w-5xl mx-auto bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl shadow-lg p-8">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-bold">Global Leaderboard</h1>
          <button
            onClick={() => router.back()}
            className="px-6 py-2 rounded-md font-semibold bg-gradient-to-r from-indigo-600 to-pink-600
                       hover:from-indigo-500 hover:to-pink-500 transition-transform transform hover:scale-105"
          >
            ← Back
          </button>
        </div>

        {leaderboard.length === 0 ? (
          <p className="text-center text-gray-300">No bots found in the system.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="bg-white/10 text-gray-200 uppercase text-xs tracking-wider">
                  <th className="px-4 py-3 border-b border-white/10">#</th>
                  <th className="px-4 py-3 border-b border-white/10">Bot Name</th>
                  <th className="px-4 py-3 border-b border-white/10">User</th>
                  <th className="px-4 py-3 border-b border-white/10">Total Value</th>
                  <th className="px-4 py-3 border-b border-white/10">Profit Margin</th>
                </tr>
              </thead>
              <tbody>
                {leaderboard.map((bot, index) => (
                  <tr
                    key={bot.botId}
                    className="border-b border-white/10 hover:bg-white/10 transition text-gray-100"
                  >
                    <td className="px-4 py-3">{index + 1}</td>
                    <td className="px-4 py-3 font-semibold">{bot.name}</td>
                    <td className="px-4 py-3">{bot.userId}</td>
                    <td className="px-4 py-3">${bot.currentValue.toFixed(2)}</td>
                    <td
                      className={`px-4 py-3 font-semibold ${
                        bot.profitMargin >= 0 ? "text-green-400" : "text-red-400"
                      }`}
                    >
                      {bot.profitMargin >= 0 ? "+" : ""}
                      {bot.profitMargin.toFixed(2)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
