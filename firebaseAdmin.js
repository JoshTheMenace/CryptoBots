import admin from "firebase-admin";
import { getDatabase } from "firebase-admin/database";

// Initialize Firebase Admin if not already initialized
if (!admin.apps.length) {
  admin.initializeApp({
    credential: admin.credential.cert({
      projectId: "cryptobots-7ae5a",
      clientEmail: process.env.FIREBASE_CLIENT_EMAIL,
      privateKey: process.env.FIREBASE_PRIVATE_KEY.replace(/\\n/g, "\n"), // Fix newline issues
    }),
    databaseURL: "https://cryptobots-7ae5a-default-rtdb.firebaseio.com",
  });
}

export const adminDb = getDatabase();
