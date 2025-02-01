"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ref, onValue } from "firebase/database";
import { db, auth } from "../../../firebaseClient";
import BotChart from "../../../components/BotChart";

export default function BotPage() {
  const { botId } = useParams(); // ✅ Get botId from URL
  const [userId, setUserId] = useState(null);
  const [trades, setTrades] = useState([]);
  const [botBalances, setBotBalances] = useState({ USD: 0, BTC: 0, ETH: 0 });
  const [loading, setLoading] = useState(true);

  // ✅ Get the logged-in user's ID
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

  // ✅ Fetch data only when both `botId` and `userId` are available
  useEffect(() => {
    if (!botId || !userId) return;

    console.log(`📡 Fetching bot data: bots/${userId}/${botId}`);

    // ✅ Fetch trades
    const tradesRef = ref(db, `bots/${userId}/${botId}/trades`);
    const tradesListener = onValue(tradesRef, (snapshot) => {
      if (snapshot.exists()) {
        const tradesData = snapshot.val();
        setTrades(Object.entries(tradesData).map(([id, trade]) => ({ id, ...trade })));
      } else {
        console.warn("⚠️ No trades found.");
        setTrades([]);
      }
    });

    // ✅ Fetch bot balances
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

  if (loading) return <p className="text-gray-600 text-center">Loading bot data...</p>;

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-4xl mx-auto bg-white p-8 rounded shadow">
        <h1 className="text-3xl font-bold mb-6 text-gray-800">Trading Bot Dashboard</h1>

        {/* Display the Chart */}
        <BotChart trades={trades} botBalances={botBalances} botId={botId} userId={userId} />
      </div>
    </div>
  );
}
