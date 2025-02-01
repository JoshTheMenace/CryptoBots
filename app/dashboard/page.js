"use client";

import { onAuthStateChanged } from "firebase/auth";
import { auth } from "../../firebase";
import { ref, onValue, push, set } from "firebase/database";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import BotList from "../../components/BotList";
import { db } from "../../firebase";

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [bots, setBots] = useState([]);
  const [marketData, setMarketData] = useState({ BTC: null, ETH: null });
  const [overallBalance, setOverallBalance] = useState(0);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (firebaseUser) => {
      if (!firebaseUser) {
        router.push("/");
      } else {
        setUser(firebaseUser);
      }
    });
    return () => unsubscribe();
  }, [router]);

  useEffect(() => {
    if (user) {
      const botsRef = ref(db, `bots/${user.uid}`);
      onValue(botsRef, (snapshot) => {
        const data = snapshot.val() || {};
        const botArray = Object.entries(data).map(([botId, botData]) => ({
          id: botId,
          ...botData,
        }));
        setBots(botArray);
      });
    }
  }, [user]);

  // Poll market data every 30 seconds
  useEffect(() => {
    async function fetchMarketData() {
      try {
        const res = await fetch("/api/market-data");
        const data = await res.json();
        setMarketData(data);
      } catch (error) {
        console.error("Error fetching market data:", error);
      }
    }
    fetchMarketData();
    const interval = setInterval(fetchMarketData, 30000);
    return () => clearInterval(interval);
  }, []);

  // Compute overall portfolio balance (sum of all bots' values)
  useEffect(() => {
    if (bots.length > 0 && marketData.BTC && marketData.ETH) {
      let total = 0;
      bots.forEach((bot) => {
        const usd = bot.balances?.USD || 0;
        const btc = bot.balances?.BTC || 0;
        const eth = bot.balances?.ETH || 0;
        total += usd + btc * marketData.BTC + eth * marketData.ETH;
      });
      setOverallBalance(total);
    }
  }, [bots, marketData]);

  async function handleCreateBot() {
    const name = prompt("Enter Bot Name:");
    if (!name) return;

    const userBotsRef = ref(db, `bots/${user.uid}`);
    const newBotRef = push(userBotsRef); // Generates a unique bot ID

    // Seed the new bot with $10,000 USD and zero crypto
    await set(ref(db, `bots/${user.uid}/${newBotRef.key}`), {
      name,
      createdAt: Date.now(),
      balances: {
        USD: 10000,
        BTC: 0.0,
        ETH: 0.0,
      },
      trades: {},
    });

    console.log("✅ Bot Created:", newBotRef.key);
  }

  if (!user) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-gray-800 to-black text-white">
        <p className="text-xl animate-pulse">Loading user...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-900 via-black to-gray-900 text-white">
      {/* Top Container */}
      <div className="max-w-7xl mx-auto px-6 py-10">
        {/* Header */}
        <header className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-4xl font-extrabold tracking-tight mb-2">
              My Trading Dashboard
            </h1>
            <p className="text-lg text-gray-300">
              Overall Portfolio Value:{" "}
              <span className="text-2xl font-semibold text-white ml-1">
                ${overallBalance.toFixed(2)}
              </span>
            </p>
          </div>

          <button
            className="bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 hover:from-indigo-400 hover:to-pink-400 px-6 py-3 rounded-lg shadow-lg font-semibold transition-transform transform hover:scale-105 focus:outline-none"
            onClick={handleCreateBot}
          >
            Create Bot
          </button>
        </header>

        {/* Bot List Section */}
        <div
          className="bg-white/5 rounded-xl p-6 shadow-lg 
                     backdrop-blur-sm border border-white/10"
        >
          <BotList bots={bots} userId={user.uid} marketData={marketData} />
        </div>
      </div>
    </div>
  );
}
