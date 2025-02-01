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
        <div className="text-gray-500">No bots yet.</div>
      )}
      {bots.map((bot) => {
        const value = calculateBotValue(bot);
        const percentageChange =
          ((value - initialCapital) / initialCapital) * 100;
        const isPositive = percentageChange >= 0;
        return (
          <div
            key={bot.id}
            className="bg-white rounded-xl shadow p-6 flex flex-col md:flex-row items-center justify-between"
          >
            <div>
              <h2 className="text-2xl font-bold text-gray-800">{bot.name}</h2>
              <p className="text-sm text-gray-500">Bot ID: {bot.id}</p>
              <div className="mt-2 text-gray-700">
                <p>💰 USD: ${bot.balances?.USD?.toFixed(2) || "0.00"}</p>
                <p>₿ BTC: {bot.balances?.BTC || "0.00"}</p>
                <p>Ξ ETH: {bot.balances?.ETH || "0.00"}</p>
              </div>
            </div>
            <div className="mt-4 md:mt-0 text-right">
              <p className="text-lg font-semibold text-gray-800">
                Value: ${value.toFixed(2)}
              </p>
              <p
                className={`text-md ${
                  isPositive ? "text-green-600" : "text-red-600"
                }`}
              >
                {isPositive ? "+" : ""}
                {percentageChange.toFixed(2)}%
              </p>
              <div className="flex gap-4 mt-4">
                <Link
                  href={`/bots/${bot.id}`}
                  className="text-blue-600 hover:underline font-medium"
                >
                  View Bot &rarr;
                </Link>
                <Link
                  href={`/bots/${bot.id}/history`}
                  className="text-blue-600 hover:underline font-medium"
                >
                  View Trade History 📈
                </Link>
                <button
                  onClick={() => handleAddBalance(bot.id)}
                  className="bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600 transition"
                >
                  ➕ Add $5000
                </button>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
