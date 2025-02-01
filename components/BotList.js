"use client";

import { useState } from "react";
import Link from "next/link";
import { ref, get, set } from "firebase/database";
import { db } from "../firebaseClient";

export default function BotList({ bots, userId, marketData }) {
  const initialCapital = 10000; // Each bot starts with $10,000

  async function handleAddBalance(botId) {
    try {
      const botRef = ref(db, `bots/${userId}/${botId}/balances/USD`);
      const snapshot = await get(botRef);
      let currentBalance = snapshot.val() || 0.0;

      const newBalance = currentBalance + 5000; // Add $5000 to the bot
      await set(botRef, newBalance);

      console.log(
        `✅ Added $5000 to bot ${botId}. New balance: $${newBalance}`
      );
      alert(`Added $5000 to bot ${botId}. New balance: $${newBalance}`);
    } catch (error) {
      console.error("🔥 Error adding balance:", error);
    }
  }

  function calculateBotValue(bot) {
    if (!marketData || !marketData.BTC || !marketData.ETH) return 0;
    const usd = bot.balances?.USD || 0;
    const btc = bot.balances?.BTC || 0;
    const eth = bot.balances?.ETH || 0;
    return usd + btc * marketData.BTC + eth * marketData.ETH;
  }

  return (
    <div className="grid grid-cols-1 gap-6">
      {(!bots || bots.length === 0) && (
        <div className="text-gray-300 text-center text-lg">
          No bots yet. Create your first bot above!
        </div>
      )}
      {bots?.map((bot) => {
        const value = calculateBotValue(bot);
        const percentageChange =
          ((value - initialCapital) / initialCapital) * 100;
        const isPositive = percentageChange >= 0;

        return (
          <div
            key={bot.id}
            className="bg-white/5 backdrop-blur-md border border-white/10 
                       rounded-xl shadow-lg p-6 flex flex-col md:flex-row 
                       items-start md:items-center justify-between gap-4 
                       hover:shadow-2xl transition-shadow"
          >
            {/* Left Section: Bot Info */}
            <div>
              <h2 className="text-2xl font-bold text-white tracking-tight">
                {bot.name}
              </h2>
              <p className="mt-1 text-sm text-gray-400">Bot ID: {bot.id}</p>

              <div className="mt-3 text-gray-300 text-sm space-y-1">
                <p>💰 USD: ${bot.balances?.USD?.toFixed(2) || "0.00"}</p>
                <p>₿ BTC: {bot.balances?.BTC || "0.00"}</p>
                <p>Ξ ETH: {bot.balances?.ETH || "0.00"}</p>
              </div>
            </div>

            {/* Right Section: Bot Value and Actions */}
            <div className="md:text-right flex flex-col items-start md:items-end">
              <div>
                <p className="text-lg font-semibold text-white">
                  Value: ${value.toFixed(2)}
                </p>
                <p
                  className={`text-md ${
                    isPositive ? "text-green-400" : "text-red-400"
                  }`}
                >
                  {isPositive ? "+" : ""}
                  {percentageChange.toFixed(2)}%
                </p>
              </div>

              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4 mt-4">
                <Link
                  href={`/bots/${bot.id}`}
                  className="text-sm font-medium text-indigo-400 underline-offset-2 
                             hover:text-indigo-300 transition"
                >
                  View Bot &rarr;
                </Link>
                <Link
                  href={`/bots/${bot.id}/history`}
                  className="text-sm font-medium text-indigo-400 underline-offset-2 
                             hover:text-indigo-300 transition"
                >
                  View Trade History 📈
                </Link>
                <button
                  onClick={() => handleAddBalance(bot.id)}
                  className="bg-gradient-to-r from-green-500 to-emerald-600 
                             hover:from-green-400 hover:to-emerald-500 
                             text-white px-4 py-2 rounded-md font-semibold 
                             transition-transform transform hover:scale-105"
                >
                  ➕ 5000 VBucks
                </button>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
