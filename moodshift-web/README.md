# 🎵 MoodShift — Adaptive Music & Mood Journey App

MoodShift is an intelligent, privacy-first audio companion that estimates emotional states and guides harmonic, tempo-adaptive musical journeys. It runs as both a responsive web application and a native Android application via Capacitor.

---

## 🌟 Key Features

1. **Multi-Dimensional Mood Fusion**:
   - Integrates Valence, Arousal, and Energy coordinates.
   - Calculates journey distance, trajectory vector, and progression.
2. **Camelot Harmonic Key Matching**:
   - Recommends transitions based on Camelot Wheel harmonic compatibility (+1/-1, relative minor/major, parallel shifts, and energy boosts).
3. **Dynamic Pitch & Tempo Controller**:
   - Web Audio API real-time tempo shifts with smooth exponential/linear ramps.
   - Harmonic key transposition and micro-pitch shifts.
4. **Offline Procedural Synthesizer**:
   - Built-in multi-mode ambient sound generator (ambient pad, binaural beats, theta waves, uplifting arpeggio).
5. **Mobile-First Android App**:
   - Built with Capacitor 8 and Android SDK 36.
   - Safe-area inset handling for notch and edge-to-edge screens.
   - Background audio wake lock and network stream resilience.

---

## 📱 Mobile App & APK Build

### Native Android Structure
- Android project: `android/`
- App Identifier: `com.moodshift.app`
- Permissions: `INTERNET`, `ACCESS_NETWORK_STATE`, `WAKE_LOCK`, `MODIFY_AUDIO_SETTINGS`

### Local Commands
```bash
# Install dependencies
npm install

# Run unit tests
npm test

# Build production bundle
npm run build

# Sync web assets to Capacitor Android
npx cap sync android

# Open Android Studio
npx cap open android
```

---

## 🚀 Automated CI/CD & GitHub Releases

The GitHub Actions workflow at `.github/workflows/moodshift-apk-release.yml` automatically builds and signs the Android APK:

- **Triggers**:
  - Push to `main` with changes in `moodshift-web/`
  - Release tags (`moodshift-v*` or `v*`)
  - Manual trigger via `workflow_dispatch` in GitHub Actions
- **Outputs**:
  - `MoodShift-release.apk`: Production signed APK ready to install on Android phones
  - `MoodShift-debug.apk`: Development debug build
  - Automatic publish to **GitHub Releases** with release notes and downloadable APK binaries
