"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ref, onValue } from "firebase/database";
import { db, auth } from "../../../firebaseClient";
import BotChart from "../../../components/BotChart";

export default function BotPage() {
  const { botId } = useParams(); // Retrieve botId from the URL
  const [userId, setUserId] = useState(null);
  const [trades, setTrades] = useState([]);
  const [botBalances, setBotBalances] = useState({ USD: 0, BTC: 0, ETH: 0 });
  const [loading, setLoading] = useState(true);

  // Listen for Firebase Authentication changes to get user ID
  useEffect(() => {
    const unsubscribe = auth.onAuthStateChanged((user) => {
      if (user) {
        console.log(`✅ Logged in as: ${user.uid}`);
        setUserId(user.uid);
      } else {
        console.error("❌ No user logged in.");
        setUserId(null);
        setLoading(false);
      }
    });
    return () => unsubscribe();
  }, []);

  // Fetch trades and balances when both botId and userId are available
  useEffect(() => {
    if (!botId || !userId) return;

    console.log(`📡 Fetching bot data: bots/${userId}/${botId}`);

    // Fetch trades
    const tradesRef = ref(db, `bots/${userId}/${botId}/trades`);
    const tradesListener = onValue(tradesRef, (snapshot) => {
      if (snapshot.exists()) {
        const tradesData = snapshot.val();
        const formattedTrades = Object.entries(tradesData).map(([id, trade]) => ({
          id,
          ...trade,
        }));
        setTrades(formattedTrades);
      } else {
        console.warn("⚠️ No trades found.");
        setTrades([]);
      }
    });

    // Fetch bot balances
    const balanceRef = ref(db, `bots/${userId}/${botId}/balances`);
    const balanceListener = onValue(balanceRef, (snapshot) => {
      if (snapshot.exists()) {
        console.log("📊 Bot balances updated:", snapshot.val());
        setBotBalances(snapshot.val());
      } else {
        console.warn("⚠️ No bot balances found.");
        setBotBalances({ USD: 0, BTC: 0, ETH: 0 });
      }
      setLoading(false);
    });

    return () => {
      tradesListener();
      balanceListener();
    };
  }, [botId, userId]);

  if (loading) {
    // Loading state with a centered animated pulse
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-purple-900 via-black to-gray-900">
        <p className="text-white text-xl animate-pulse">Loading bot data...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-900 via-black to-gray-900 p-6 text-white">
      <div className="max-w-4xl mx-auto bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl shadow-lg p-8">
        <h1 className="text-3xl font-bold mb-6">Trading Bot Dashboard</h1>

        {/* Display the Chart (passes data to the BotChart component) */}
        <BotChart
          trades={trades}
          botBalances={botBalances}
          botId={botId}
          userId={userId}
        />
      </div>
    </div>
  );
}
