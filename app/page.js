"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { signInWithEmailAndPassword, createUserWithEmailAndPassword } from "firebase/auth";
import { auth, signUpUser } from "../firebaseClient"; // Now safe to import directly

export default function HomePage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSignUp, setIsSignUp] = useState(false);
  const [error, setError] = useState("");
  const [firebaseReady, setFirebaseReady] = useState(false);

  // Ensure Firebase is loaded before rendering
  useEffect(() => {
    if (auth) setFirebaseReady(true);
  }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(""); // Reset error state

    if (!firebaseReady) {
      setError("Authentication service not available. Please wait...");
      return;
    }

    try {
      if (isSignUp) {
        // ✅ Call signUpUser instead of createUserWithEmailAndPassword
        const user = await signUpUser(email, password);

        if (!user) {
          setError("Failed to sign up. Please try again.");
          return;
        }
      } else {
        await signInWithEmailAndPassword(auth, email, password);
      }
      router.push("/dashboard"); // Redirect to dashboard
    } catch (error) {
      setError("Failed to authenticate. Please check your credentials.");
      console.error("Auth error:", error);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-blue-600 to-purple-600 p-4">
      <div className="w-full max-w-md space-y-6 rounded-lg bg-white/20 p-8 shadow-lg backdrop-blur-md">
        {/* Header */}
        <h1 className="text-center text-3xl font-bold text-white">
          {isSignUp ? "Create an Account" : "Welcome Back"}
        </h1>
        <p className="text-center text-gray-200">
          {isSignUp ? "Join us today!" : "Sign in to your account"}
        </p>

        {/* Error Message */}
        {error && <p className="text-center text-sm text-red-500">{error}</p>}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="w-full rounded-lg border border-gray-300 bg-gray-100 p-3 focus:border-blue-500 focus:outline-none"
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className="w-full rounded-lg border border-gray-300 bg-gray-100 p-3 focus:border-blue-500 focus:outline-none"
          />
          <button
            type="submit"
            className="w-full rounded-lg bg-blue-500 p-3 text-white transition hover:bg-blue-600 disabled:bg-gray-400"
            disabled={!firebaseReady} // Disable button until Firebase is ready
          >
            {isSignUp ? "Sign Up" : "Login"}
          </button>
        </form>

        {/* Switch between Sign In / Sign Up */}
        <div className="text-center">
          <p className="text-gray-200">
            {isSignUp ? "Already have an account?" : "Don't have an account?"}
          </p>
          <button
            onClick={() => setIsSignUp(!isSignUp)}
            className="mt-2 font-medium text-white underline hover:text-gray-300"
          >
            {isSignUp ? "Sign In" : "Create an Account"}
          </button>
        </div>
      </div>
    </div>
  );
}
