import { initializeApp } from 'firebase/app';
import { getAuth } from 'firebase/auth';

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY || 'AIzaSyB9IZTtx3sNbGNMmQZuHX9_xy5fBWL_BJI',
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || 'plutochatbot.firebaseapp.com',
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || 'plutochatbot',
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET || 'plutochatbot.firebasestorage.app',
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || '609028491307',
  appId: import.meta.env.VITE_FIREBASE_APP_ID || '1:609028491307:web:8ae08e7dc085aaf3b2026e',
  measurementId: import.meta.env.VITE_FIREBASE_MEASUREMENT_ID || 'G-VDZ5QTH3JT',
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Export Firebase Authentication
export const auth = getAuth(app);
export default app;
