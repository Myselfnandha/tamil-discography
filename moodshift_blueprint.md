# MoodShift — Architecture & Implementation Blueprint

> **Android-first · Native Kotlin · Multi-signal mood estimation · Adaptive music journeys**
> Codename: **MoodShift** · Status: Pre-build · Effort: Ultra

---

## 1. Product Vision (One Sentence)

A privacy-first Android music companion that estimates your current emotional state from face + phone behavior + self-report, lets you choose where you want to be, and builds a transition journey playlist from your Spotify library + YouTube Music — played entirely in-app.

---

## 2. Architecture Decision: Why This Stack

| Decision | Choice | Rationale |
|:---|:---|:---|
| **Platform** | Android-first, Native Kotlin | Full access to CameraX, UsageStatsManager, sensors, Media3. Compose for premium UI. |
| **Architecture** | Clean Architecture + MVI | Unidirectional data flow. Domain layer free of Android deps. Testable mood engine. |
| **Face ML** | CameraX → ML Kit Face Detection → TFLite FER model + **Personal Calibration** | On-device, no cloud. ML Kit detects; TFLite classifies; personal baseline boosts accuracy from ~65% → ~90%+. |
| **Face Enrollment** | ML Kit Face Mesh (468 3D landmarks) + expression capture | Onboarding calibration: user's own neutral/happy/tired/surprised baselines. Re-calibration in settings. |
| **Device Signals** | UsageStatsManager + KeyguardManager | Unlock count, app usage times, session patterns. Permission-gated. |
| **Audio Backend** | Piped/InnerTube API → ExoPlayer (Media3) | YouTube Music audio streams. No Premium required. Same pattern as Spotube/SimpMusic. |
| **Spotify Integration** | OAuth PKCE → Web API → Deep-link handoff | Metadata, playlists, top tracks. Play via deep-link OR in-app via YouTube match. |
| **Local DB** | Room | Mood history, journey logs, feedback, cached metadata. |
| **DI** | Hilt | Standard for Android, integrates with ViewModel/WorkManager. |
| **Navigation** | Compose Navigation (type-safe routes) | Single-activity, Compose-first. |
| **Secrets** | Android Keystore + EncryptedSharedPreferences | Tokens, API keys never in plaintext. |

---

## 3. System Architecture (5 Subsystems)

```
┌──────────────────────────────────────────────────────────────────┐
│                     EXPERIENCE LAYER (UI)                        │
│  Home Dashboard · Mood Card (auto-sense) · Onboarding            │
│  Face Calibration · Target Picker · Journey Player · Queue       │
│  Insights · Settings · Widget · App Shortcuts                    │
├──────────────────────────────────────────────────────────────────┤
│                   AUTO-FLOW CONTROLLER                           │
│  AutoSenseManager · SmartTargetPredictor · FlowModeRouter        │
│  RoutineScheduler · JourneyAutoContinue                          │
├──────────────────────────────────────────────────────────────────┤
│                  SIGNAL COLLECTION LAYER                         │
│  PersonalizedFaceSensor · DeviceUsageSensor · SelfReportSensor   │
│  AppFeedbackSensor · MusicLibrarySensor                          │
├──────────────────────────────────────────────────────────────────┤
│               MOOD INTELLIGENCE ENGINE (Domain)                  │
│  PersonalCalibrator → SignalValidator → SignalFuser →             │
│  StateEstimator → ConfidenceScorer → UserCorrectionHandler       │
├──────────────────────────────────────────────────────────────────┤
│            JOURNEY & RECOMMENDATION ENGINE (Domain)              │
│  SmartTargetPredictor → CandidateRanker →                        │
│  TransitionSequencer → QueueBuilder → DynamicTempoController     │
├──────────────────────────────────────────────────────────────────┤
│              PROVIDER & PERSISTENCE LAYER (Data)                 │
│  SpotifyProvider · YouTubeProvider · LocalAudioProvider           │
│  RoomDatabase · EncryptedPrefs · TokenVault · FaceProfileVault   │
└──────────────────────────────────────────────────────────────────┘
```

### Key Boundary Rules

- **Domain layer** (`core/domain/`) has ZERO Android imports. Pure Kotlin. All interfaces defined here.
- **Data layer** (`core/data/`) implements domain interfaces with Android-specific code.
- **Feature modules** (`feature/home/`, `feature/scan/`, `feature/journey/`, `feature/player/`) depend on domain, never on each other.
- **Provider adapters** are individually swappable. YouTube dies? Swap adapter. Spotify changes? Swap adapter.

---

## 4. Gradle Module Structure

```
moodshift/
├── app/                          # Application entry, Hilt setup, navigation graph
├── core/
│   ├── domain/                   # Pure Kotlin: entities, use cases, interfaces
│   ├── data/                     # Room, Retrofit, CameraX impl, UsageStats impl
│   ├── model/                    # Shared data models (MoodSnapshot, Track, Journey)
│   ├── ui/                       # Design system: theme, tokens, common composables
│   ├── autoflow/                 # Auto-sense manager, smart target predictor, flow router
│   └── common/                   # Extensions, utilities, constants
├── feature/
│   ├── onboarding/               # Permissions + face calibration enrollment
│   ├── home/                     # Dashboard + ambient mood card + "Fix My Mood" CTA
│   ├── scan/                     # Manual camera scan + mood detection flow
│   ├── journey/                  # Target picker + journey builder + queue editor
│   ├── player/                   # Now playing, mini-player, queue, tempo tuning
│   ├── insights/                 # Mood history, patterns, feedback logs
│   ├── widget/                   # Android home screen widget
│   └── settings/                 # Permissions, Spotify auth, privacy, re-calibration
├── provider/
│   ├── spotify/                  # Spotify OAuth, Web API, deep-links
│   ├── youtube/                  # Piped/InnerTube client, stream resolver
│   └── local/                    # On-device audio files (future)
└── ml/
    ├── face-detection/           # ML Kit Face Detection wrapper
    ├── face-mesh/                # ML Kit Face Mesh (468 3D landmarks) for calibration
    ├── emotion-classifier/       # TFLite FER model, preprocessing
    └── personal-calibrator/      # Personal baseline storage, personalized classifier
```

---

## 5. Core Domain Models

### 5.1 MoodSnapshot — The Heart of the System

```kotlin
data class MoodSnapshot(
    val id: String = UUID.randomUUID().toString(),
    val energy: Float,          // 0.0 (depleted) → 1.0 (electric)
    val valence: Float,         // 0.0 (negative) → 1.0 (positive)
    val arousal: Float,         // 0.0 (calm/drowsy) → 1.0 (excited/tense)
    val confidence: Float,      // 0.0 → 1.0 — how sure are we?
    val isPersonalized: Boolean,// True if personal calibration was used
    val observedSignals: Set<SignalType>,
    val dominantEmotion: EmotionLabel?,  // Optional face-derived label
    val timestamp: Instant,
    val userCorrection: MoodCorrection? = null,
    val source: ScanSource = ScanSource.MANUAL
)

enum class SignalType {
    FACE_EXPRESSION, DEVICE_USAGE, SELF_REPORT, APP_FEEDBACK, MUSIC_HISTORY
}

enum class EmotionLabel {
    HAPPY, SAD, ANGRY, SURPRISED, FEARFUL, DISGUSTED, NEUTRAL
}

data class MoodCorrection(
    val correctedBy: CorrectionSource,
    val correctedEnergy: Float?,
    val correctedValence: Float?,
    val freeText: String? = null
)

enum class CorrectionSource { USER_MANUAL, USER_EMOJI_PICKER, SKIP_PATTERN }
enum class ScanSource { MANUAL, AUTO_SENSE, WIDGET, APP_SHORTCUT, ROUTINE }
```

### 5.2 Target Mood

```kotlin
data class TargetMood(
    val id: String,
    val name: String,           // "Calm", "Focus", "Uplift", "Energized", etc.
    val targetEnergy: Float,
    val targetValence: Float,
    val targetArousal: Float,
    val baseTempoMultiplier: Float = 1.0f, // [0.96f..1.04f]. Pitch invariant: strictly locked at 1.0f
    val idealBpmRange: ClosedFloatingPointRange<Float>? = null, // e.g. 65f..85f for Calm, 125f..140f for Energized
    val phase3ModeConstraint: ModeConstraint = ModeConstraint.ANY, // Strict Major, Strict Minor, or Flexible
    val preferredTonality: String? = null, // e.g. "Major / Bright", "Minor / Melancholic"
    val icon: String,           // Material icon name
    val colorAccent: Long       // Compose Color as ARGB long
)

enum class ModeConstraint {
    STRICT_MAJOR,  // Only mode == 1 permitted in Phase 3 (Uplift, Energized, Confident)
    STRICT_MINOR,  // Only mode == 0 permitted in Phase 3 (Cathartic, Wind Down)
    ANY            // Flexible / Modal (Calm, Focus)
}
```

### 5.3 Journey

```kotlin
data class MoodJourney(
    val id: String = UUID.randomUUID().toString(),
    val startMood: MoodSnapshot,
    val targetMood: TargetMood,
    val phases: List<JourneyPhase>,
    val createdAt: Instant,
    val status: JourneyStatus = JourneyStatus.PENDING
)

data class JourneyPhase(
    val name: String,           // "Settle In", "Build Momentum", "Reach Target"
    val description: String,
    val tracks: List<JourneyTrack>,
    val targetEnergyRange: ClosedFloatingPointRange<Float>
)

data class JourneyTrack(
    val track: Track,
    val source: PlaybackSource,
    val estimatedEnergy: Float,
    val estimatedValence: Float,
    val reason: String          // "Familiar comfort track from your library"
)

enum class PlaybackSource { SPOTIFY_DEEPLINK, YOUTUBE_STREAM, LOCAL_FILE }
enum class JourneyStatus { PENDING, ACTIVE, PAUSED, COMPLETED, ABANDONED }
```

### 5.4 Track (Provider-Agnostic)

```kotlin
data class Track(
    val id: String,
    val title: String,
    val artist: String,
    val album: String?,
    val durationMs: Long,
    val artworkUrl: String?,
    val spotifyUri: String?,     // "spotify:track:xxxxx"
    val youtubeId: String?,      // YouTube video ID for stream resolution
    val tempoBpm: Float? = null, // Native BPM from Spotify audio features (for tempo guardrails)
    val musicalKey: Int? = null, // Pitch class: 0 = C, 1 = C#, ..., 11 = B
    val musicalMode: Int? = null,// Modality: 1 = Major, 0 = Minor
    val camelotCode: String? = null, // e.g. "8B" (C Major), "8A" (A Minor) for harmonic chaining
    val userVibeTag: String?,    // User-authored mood tag
    val playCount: Int = 0,
    val lastPlayedAt: Instant? = null
)
```

---

## 6. Signal Collection — Technical Details

### 6.1 Personal Face Calibration (Onboarding)

During onboarding, the user enrolls their face so the ML model learns **their specific expressions** — not generic FER-2013 averages. This is the single biggest accuracy multiplier in the entire system.

**Calibration Flow (30 seconds, 5 steps):**

```
┌──────────────────────────────────────────────────────┐
│  Let's learn your face ✨                            │
│                                                      │
│  "Your data never leaves this device."               │
│                                                      │
│        ┌───────────────────┐                         │
│        │                   │                         │
│        │  [Camera Preview  │  ← Face mesh overlay    │
│        │   + Guide Ring]   │     shows alignment     │
│        │                   │                         │
│        └───────────────────┘                         │
│                                                      │
│  Step 2 of 5: Give us a real smile 😊                │
│                                                      │
│  ████████████░░░░░░░░░░░░  40%                      │
│                                                      │
│  [Skip calibration →]                                │
└──────────────────────────────────────────────────────┘
```

| Step | Prompt | Captures | Duration |
|:---|:---|:---|:---|
| 1 | "Relax your face naturally" | **Neutral baseline** (most critical) | 3 sec, 15 frames |
| 2 | "Give us a real smile" | **Happy** expression features | 3 sec, 15 frames |
| 3 | "Think of something tiring" | **Low energy** expression | 3 sec, 15 frames |
| 4 | "Look surprised!" | **High arousal** expression | 3 sec, 15 frames |
| 5 | "Slowly rotate your head in a circle" | **3D face geometry** (468 mesh landmarks) | 8 sec, 40 frames |

**PersonalFaceProfile (stored encrypted in Room):**

```kotlin
data class PersonalFaceProfile(
    val userId: String,
    val calibratedAt: Instant,
    val baselineNeutral: FloatArray,      // 128-dim face embedding
    val baselineHappy: FloatArray,
    val baselineTired: FloatArray,
    val baselineSurprised: FloatArray,
    val faceMeshAnchors: List<FaceMeshAnchor>?,  // 3D mode (step 5)
    val lightingProfile: LightingProfile, // Ambient light during calibration
    val personalThreshold: Float,         // Personalized confidence floor
    val correctionCount: Int = 0          // How many times user corrected
)

data class LightingProfile(
    val avgBrightness: Float,
    val contrastRatio: Float,
    val isBacklit: Boolean
)
```

**PersonalizedEmotionClassifier:**

```kotlin
class PersonalizedEmotionClassifier(
    private val profile: PersonalFaceProfile?,
    private val genericModel: TFLiteEmotionClassifier
) {
    fun classify(faceEmbedding: FloatArray): EmotionResult {
        val genericResult = genericModel.classify(faceEmbedding)

        if (profile == null) return genericResult.copy(isPersonalized = false)

        val personalScores = mapOf(
            EmotionLabel.NEUTRAL   to cosineSimilarity(faceEmbedding, profile.baselineNeutral),
            EmotionLabel.HAPPY     to cosineSimilarity(faceEmbedding, profile.baselineHappy),
            EmotionLabel.SAD       to cosineSimilarity(faceEmbedding, profile.baselineTired),
            EmotionLabel.SURPRISED to cosineSimilarity(faceEmbedding, profile.baselineSurprised)
        )

        val blended = blendPredictions(personalScores, genericResult, personalWeight = 0.7f)
        return blended.copy(isPersonalized = true, confidence = blended.confidence * 1.3f)
    }
}
```

> [!IMPORTANT]
> **Calibration is recommended but skippable.** If skipped, the app falls back to the generic FER model with lower confidence weights. A nudge to calibrate appears after the 3rd mood correction by the user: "You've corrected me 3 times — want me to learn your face?"

**Continuous learning:** Every time the user corrects a mood prediction, the personal baseline is refined via exponential moving average:
```kotlin
fun refineBaseline(profile: PersonalFaceProfile, correction: MoodCorrection, currentEmbedding: FloatArray): PersonalFaceProfile {
    val alpha = 0.1f
    val targetBaseline = when (correction.impliedEmotion) {
        EmotionLabel.HAPPY -> profile.baselineHappy
        EmotionLabel.NEUTRAL -> profile.baselineNeutral
        // ... etc
    }
    val refined = targetBaseline.zip(currentEmbedding) { old, new -> old * (1 - alpha) + new * alpha }
    return profile.copy(/* updated baseline */)
}
```

**Re-calibration** is available in Settings → "Re-learn my face".

### 6.2 Face Expression Pipeline (Runtime)

```
Auto-Sense or Manual Scan:
CameraX → ML Kit FaceDetector → Crop bounding box →
Resize 48×48 grayscale → TFLite FER model → 7-emotion probabilities →
┌── IF personal profile exists:
│   Compare embedding against personal baselines (cosine similarity)
│   Blend: 70% personal + 30% generic → PERSONALIZED result (~90%+ accuracy)
└── ELSE:
    Use generic FER result → GENERIC result (~65% accuracy)
→ Map to (energy, valence, arousal) → Attach confidence
```

**Emotion → Mood Dimension Mapping:**

| FER Label | Energy | Valence | Arousal | Personal Override |
|:---|:---|:---|:---|:---|
| Happy | 0.7 | 0.9 | 0.6 | Calibrated from user's actual smile |
| Sad | 0.2 | 0.2 | 0.3 | Calibrated from user's tired expression |
| Angry | 0.8 | 0.1 | 0.9 | Generic (not captured in calibration) |
| Surprised | 0.7 | 0.6 | 0.8 | Calibrated from user's surprised face |
| Fearful | 0.5 | 0.2 | 0.8 | Generic |
| Disgusted | 0.4 | 0.1 | 0.5 | Generic |
| Neutral | 0.5 | 0.5 | 0.3 | Calibrated from user's resting face |

### 6.3 Device Usage Pipeline

```kotlin
data class DeviceUsageSignals(
    val unlockCountToday: Int,
    val totalScreenTimeMs: Long,
    val topAppsWithTime: Map<String, Long>,
    val socialMediaTimeMs: Long,
    val messagingTimeMs: Long,
    val pickupFrequencyPerHour: Float,
    val sessionDurationAvgMs: Long,
    val timeOfDay: TimeOfDay,
    val dayOfWeek: DayOfWeek
)
```

### 6.4 Signal Fusion Algorithm (Calibration-Aware)

```kotlin
class MoodFuser(private val hasPersonalProfile: Boolean) {
    fun fuse(signals: List<MoodSignal>): MoodSnapshot {
        val weights = if (hasPersonalProfile) mapOf(
            SignalType.SELF_REPORT     to 0.30f,
            SignalType.FACE_EXPRESSION to 0.35f,
            SignalType.DEVICE_USAGE    to 0.15f,
            SignalType.APP_FEEDBACK    to 0.15f,
            SignalType.MUSIC_HISTORY   to 0.05f
        ) else mapOf(
            SignalType.SELF_REPORT     to 0.40f,
            SignalType.FACE_EXPRESSION to 0.20f,
            SignalType.DEVICE_USAGE    to 0.18f,
            SignalType.APP_FEEDBACK    to 0.17f,
            SignalType.MUSIC_HISTORY   to 0.05f
        )

        val availableSignals = signals.filter { it.isAvailable }
        val totalWeight = availableSignals.sumOf { weights[it.type]!! }
        
        val energy = availableSignals.sumOf { it.energy * weights[it.type]!! } / totalWeight
        val valence = availableSignals.sumOf { it.valence * weights[it.type]!! } / totalWeight
        val arousal = availableSignals.sumOf { it.arousal * weights[it.type]!! } / totalWeight
        
        val confidence = calculateConfidence(availableSignals, totalWeight)
        
        return MoodSnapshot(
            energy = energy, valence = valence, arousal = arousal,
            confidence = confidence,
            isPersonalized = hasPersonalProfile,
            observedSignals = availableSignals.map { it.type }.toSet(),
            dominantEmotion = extractDominantEmotion(signals),
            timestamp = Instant.now()
        )
    }
}
```

---

## 6.5 Auto-Flow Controller

### Auto-Sense on App Open

```kotlin
class AutoSenseManager(
    private val faceSensor: PersonalizedFaceSensor,
    private val usageSensor: DeviceUsageSensor,
    private val fuser: MoodFuser,
    private val settings: UserPreferences
) {
    suspend fun autoSense(): MoodSnapshot? {
        if (!settings.autoSenseEnabled) return null

        return coroutineScope {
            val faceDeferred = async {
                if (settings.cameraPermissionGranted && settings.autoSenseCamera)
                    faceSensor.quickCapture(maxFrames = 5, maxDurationMs = 2000)
                else null
            }
            val usageDeferred = async {
                if (settings.usageStatsPermissionGranted)
                    usageSensor.collectCurrent()
                else null
            }

            val signals = listOfNotNull(faceDeferred.await(), usageDeferred.await())
            if (signals.isEmpty()) return@coroutineScope null

            fuser.fuse(signals)
        }
    }
}
```

### Smart Target Prediction

```kotlin
class SmartTargetPredictor(
    private val journeyRepo: JourneyRepository,
    private val feedbackRepo: FeedbackRepository
) {
    fun predict(currentMood: MoodSnapshot, context: TemporalContext): RankedTargets {
        val candidates = mutableListOf<Pair<TargetMood, Float>>()

        when (context.timeOfDay) {
            EARLY_MORNING -> candidates += TargetMood.ENERGIZED to 0.7f
            MORNING       -> candidates += TargetMood.FOCUS to 0.6f
            AFTERNOON     -> candidates += TargetMood.UPLIFT to 0.5f
            EVENING       -> candidates += TargetMood.WIND_DOWN to 0.6f
            LATE_NIGHT    -> candidates += TargetMood.CALM to 0.7f
        }

        if (currentMood.energy < 0.3f) candidates += TargetMood.ENERGIZED to 0.8f
        if (currentMood.valence < 0.3f) candidates += TargetMood.UPLIFT to 0.8f
        if (currentMood.arousal > 0.8f) candidates += TargetMood.CALM to 0.7f

        val pattern = journeyRepo.findRecurringPattern(context.dayOfWeek, context.timeOfDay)
        if (pattern != null) candidates += pattern to 0.9f

        feedbackRepo.getPositiveFeedback()
            .groupBy { it.targetMood }
            .forEach { (target, feedbacks) ->
                candidates += target to (0.5f + (feedbacks.size * 0.1f).coerceAtMost(0.4f))
            }

        val sorted = candidates.sortedByDescending { it.second }
        return RankedTargets(
            recommended = sorted.first().first,
            alternatives = sorted.take(3).map { it.first }
        )
    }
}
```

---

## 7. Journey Planner — The Core Differentiator

### 7.1 Transition Strategy

The journey is a **gradient walk** from current mood coordinates to target mood coordinates in 3 phases:

```
Phase 1: SETTLE IN (2-3 tracks)
├── Purpose: Acknowledge current state with familiar, comfortable music
├── Energy: Match current ±0.1
├── Valence: Match current ±0.1
└── Source: User's most-played tracks near current mood

Phase 2: BUILD MOMENTUM (3-5 tracks)
├── Purpose: Gradually shift toward target
├── Energy: Linear interpolation from current → target
├── Valence: Linear interpolation from current → target
└── Source: Mix of user library + discovery tracks

Phase 3: REACH TARGET (3-4 tracks)
├── Purpose: Arrive at desired state
├── Energy: Target ±0.1
├── Valence: Target ±0.1
└── Source: Tracks matching target mood profile
```

### 7.2 Track Scoring for Journey Placement

```kotlin
fun scoreTrackForPhase(
    track: Track,
    phase: JourneyPhase,
    targetMood: TargetMood,
    previousTrack: Track?,
    isFinalPhase: Boolean = false
): Float {
    // Phase 3 Strict Mode Filter: exclude conflicting modes if mode is known
    if (isFinalPhase && track.musicalMode != null) {
        when (targetMood.phase3ModeConstraint) {
            ModeConstraint.STRICT_MAJOR -> if (track.musicalMode != 1) return -1f
            ModeConstraint.STRICT_MINOR -> if (track.musicalMode != 0) return -1f
            ModeConstraint.ANY -> Unit
        }
    }

    val energyFit = 1f - abs(track.estimatedEnergy - phase.targetEnergyMidpoint)
    val valenceFit = 1f - abs(track.estimatedValence - phase.targetValenceMidpoint)
    
    // Camelot harmonic compatibility bonus (Circle of Fifths transition from previous track)
    val harmonicBonus = calculateHarmonicBonus(previousTrack?.camelotCode, track.camelotCode)
    
    // Mode affinity for intermediate phases
    val modeAffinityBonus = when {
        targetMood.phase3ModeConstraint == ModeConstraint.STRICT_MAJOR && track.musicalMode == 1 -> 0.10f
        targetMood.phase3ModeConstraint == ModeConstraint.STRICT_MINOR && track.musicalMode == 0 -> 0.10f
        else -> 0f
    }

    val familiarityBonus = if (track.playCount > 5) 0.15f else 0f
    val recencyPenalty = if (track.wasPlayedRecently()) -0.1f else 0f
    
    return (energyFit * 0.35f + valenceFit * 0.35f + harmonicBonus * 0.15f + modeAffinityBonus + familiarityBonus + recencyPenalty)
}
```

### 7.3 Predefined Target Moods

| Target | Energy | Valence | Arousal | Base Tempo | Ideal BPM | Phase 3 Mode | Tonality Character | Icon | Color |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| 🌊 **Calm** | 0.2 | 0.6 | 0.2 | `0.97x` | 65–85 | `ANY` | Modal / Pentatonic / Gentle | `waves` | `#06B6D4` Cyan |
| 🎯 **Focus** | 0.5 | 0.5 | 0.4 | `1.00x` | 90–115 | `ANY` | Harmonically Stable / Neutral | `target` | `#8B5CF6` Violet |
| ☀️ **Uplift** | 0.6 | 0.8 | 0.5 | `1.03x` | 115–128 | `STRICT_MAJOR` | Bright, Euphoric, Joyful | `sun` | `#F59E0B` Amber |
| ⚡ **Energized** | 0.9 | 0.7 | 0.8 | `1.04x` | 125–140 | `STRICT_MAJOR` | Driving, Optimistic, High-Power | `zap` | `#EF4444` Red |
| 💪 **Confident** | 0.7 | 0.7 | 0.6 | `1.02x` | 110–125 | `STRICT_MAJOR` | Bold, Resonant, Triumphant | `shield` | `#10B981` Emerald |
| 💧 **Cathartic** | 0.4 | 0.3 | 0.5 | `0.98x` | 70–95 | `STRICT_MINOR` | Introspective, Melancholic Beauty | `droplet` | `#6366F1` Indigo |
| 🌙 **Wind Down** | 0.1 | 0.6 | 0.1 | `0.96x` | 55–75 | `STRICT_MINOR` | Subdued, Ambient, Intimate | `moon` | `#1E293B` Slate |

---

### 7.4 Dynamic Track-Aware Tempo Controller (0.96x – 1.04x)

MoodShift modulates playback **tempo (speed)** dynamically upon target mood selection while **musical pitch is strictly locked at 1.0x** (ensuring natural vocal timbre and zero key transposition).

```kotlin
class DynamicTempoController {
    /**
     * Calculates the track-specific tempo multiplier based on target mood and track BPM guardrails.
     * Guaranteed bounds: [0.96f, 1.04f]. Pitch invariant: strictly 1.0f.
     */
    fun calculateTempo(target: TargetMood, track: Track, estimatedEnergy: Float): Float {
        val baseMultiplier = target.baseTempoMultiplier // e.g. 1.04f for Energized
        val nativeBpm = track.tempoBpm

        // Fallback to track's estimated mood energy if native Spotify BPM is unavailable
        if (nativeBpm == null) {
            val energyDelta = target.targetEnergy - estimatedEnergy
            val dampened = 1.0f + (energyDelta * 0.04f)
            return dampened.coerceIn(0.96f, 1.04f)
        }

        val idealRange = target.idealBpmRange ?: return baseMultiplier

        // BPM Guardrails: Prevent rushing already-fast tracks or dragging already-slow tracks
        return when {
            // Fast song in an upbeat mood -> dampen speed boost towards 1.0x so it doesn't sound rushed
            baseMultiplier > 1.0f && nativeBpm > idealRange.endInclusive -> {
                val overshoot = (nativeBpm - idealRange.endInclusive).coerceAtMost(30f) / 30f
                1.0f + ((baseMultiplier - 1.0f) * (1.0f - overshoot * 0.75f))
            }
            // Slow song in a relaxed mood -> dampen speed reduction towards 1.0x so it doesn't drag
            baseMultiplier < 1.0f && nativeBpm < idealRange.start -> {
                val undershoot = (idealRange.start - nativeBpm).coerceAtMost(30f) / 30f
                1.0f - ((1.0f - baseMultiplier) * (1.0f - undershoot * 0.75f))
            }
            // In optimal range -> apply full mood tempo boost/cut
            else -> baseMultiplier
        }.coerceIn(0.96f, 1.04f)
    }
}
```

**Modulation Dynamics & Crossfades:**
- **Immediate Target Shift**: Target mood tempo begins from Track 1 of the journey.
- **Dynamic Per-Track Crossfade Ramp**: Multipliers interpolate smoothly across a 1.5-second crossfade window between tracks, preventing audible tempo snapping.

---

### 7.5 Musical Key, Tonality & Harmonic Chaining Strategy

The Journey Sequencer eliminates jarring musical transitions by pairing **mode-driven emotional targeting** with **Camelot Circle-of-Fifths harmonic mixing**:

```
Phase 1: SETTLE IN ───[Soft Mode Affinity]───►
├── Reflects user's current emotional state (familiar comfort tracks)
│
Phase 2: BUILD MOMENTUM ───[Camelot Harmonic Chaining]───►
├── Transitions seamlessly between adjacent keys on the Circle of Fifths
├── Prevents dissonant key clashes between consecutive songs
│
Phase 3: REACH TARGET ───[Strict Mode Filter]───►
├── Uplift / Energized / Confident: Strict Major keys (Mode = 1)
├── Cathartic / Wind Down: Strict Minor keys (Mode = 0)
└── Calm / Focus: Harmonically flexible modal foundations
```

**Camelot Harmonic Compatibility Function:**

```kotlin
fun calculateHarmonicBonus(fromCode: String?, toCode: String?): Float {
    if (fromCode == null || toCode == null) return 0f // Unknown: neutral pass

    val (fromNum, fromLetter) = parseCamelot(fromCode) // e.g. 8, 'B'
    val (toNum, toLetter) = parseCamelot(toCode)       // e.g. 9, 'B'

    return when {
        // Exact harmonic key match (e.g. 8B -> 8B)
        fromNum == toNum && fromLetter == toLetter -> 0.15f

        // Adjacent key step on Circle of Fifths (e.g. 8B -> 9B or 8B -> 7B)
        abs(fromNum - toNum) == 1 && fromLetter == toLetter -> 0.10f
        (fromNum == 1 && toNum == 12 || fromNum == 12 && toNum == 1) && fromLetter == toLetter -> 0.10f

        // Relative Major <-> Minor shift (e.g. 8B <-> 8A)
        fromNum == toNum && fromLetter != toLetter -> 0.10f

        // Diagonal harmonic shift (e.g. 8B -> 9A)
        abs(fromNum - toNum) == 1 && fromLetter != toLetter -> 0.05f

        // Distant / clashing key
        else -> 0f
    }
}
```

> [!NOTE]
> **Missing Metadata Tolerance:**
> If a track's key or mode has not yet been resolved (e.g. YouTube stream pending Spotify matching), MoodShift permits the track into Phase 3 based on its energy/valence scores without blocking playback. A background worker resolves audio features asynchronously.


---

## 8. Playback Architecture

### 8.1 Provider Adapter Pattern

```kotlin
interface MusicProvider {
    suspend fun searchTrack(query: String): List<Track>
    suspend fun getPlaylistTracks(playlistId: String): List<Track>
    suspend fun resolveStreamUrl(track: Track): StreamResult
    fun getProviderType(): ProviderType
}

sealed class StreamResult {
    data class InAppStream(val url: String, val mimeType: String, val bitrate: Int) : StreamResult()
    data class DeepLink(val uri: String) : StreamResult()   // Spotify deep-link
    data class Unavailable(val reason: String) : StreamResult()
}

enum class ProviderType { SPOTIFY, YOUTUBE, LOCAL }
```

### 8.2 YouTube Audio via Piped/InnerTube

```
Track.youtubeId → Piped API: GET /streams/{videoId} →
Parse adaptiveFormats → Filter audio-only (audio/mp4, audio/webm) →
Select highest bitrate ≤ 256kbps → Feed URL to ExoPlayer Media3
```

### 8.3 Spotify Integration

| Capability | Implementation | Notes |
|:---|:---|:---|
| Auth | OAuth 2.0 PKCE (Authorization Code) | Android CustomTabs, no embedded WebView |
| Library Access | Web API `/me/playlists`, `/me/top/tracks` | Read-only, metadata only |
| Track Matching | Spotify track → search YouTube for same title+artist | For in-app playback |
| Direct Play | Deep-link `spotify:track:{id}` | Opens Spotify app |
| Queue Push | Optional: `POST /me/player/queue` | Requires Premium + active device |

### 8.4 ExoPlayer Media3 Setup

```kotlin
// Foreground playback service with notification controls & dynamic tempo DSP
@AndroidEntryPoint
class MoodShiftPlaybackService : MediaSessionService() {
    private var mediaSession: MediaSession? = null
    private lateinit var exoPlayer: ExoPlayer
    private val tempoController = DynamicTempoController()

    override fun onCreate() {
        super.onCreate()
        exoPlayer = ExoPlayer.Builder(this)
            .setAudioAttributes(AudioAttributes.Builder()
                .setContentType(C.AUDIO_CONTENT_TYPE_MUSIC)
                .setUsage(C.USAGE_MEDIA)
                .build(), true)
            .setHandleAudioBecomingNoisy(true)
            .build()
        
        mediaSession = MediaSession.Builder(this, exoPlayer).build()
    }

    /** Applies track-aware dynamic tempo while pitch remains strictly locked at 1.0f */
    fun applyMoodTempo(target: TargetMood, track: Track, estimatedEnergy: Float) {
        val speed = tempoController.calculateTempo(target, track, estimatedEnergy)
        // ExoPlayer native SonicAudioProcessor: speed varies [0.96f..1.04f], pitch locked at 1.0f
        exoPlayer.playbackParameters = PlaybackParameters(/* speed = */ speed, /* pitch = */ 1.0f)
    }

    override fun onGetSession(controllerInfo: MediaSession.ControllerInfo) = mediaSession
}
```

> [!IMPORTANT]
> **Spotify External Playback Fallback Gate:**
> Spotify's native external app cannot accept external DSP tempo parameters. When a track is queued via Spotify deep-link and Mood Tempo Control is active, MoodShift triggers an in-app notification prompt: *"Spotify external playback cannot adjust tempo. Switch to in-app YouTube stream to enable dynamic mood tempo?"*

---

## 9. UI Architecture & Design Language

### 9.1 Design System Tokens

```kotlin
object MoodShiftTheme {
    val bgPrimary = Color(0xFF0A0E1A)         // Near-black navy
    val bgSecondary = Color(0xFF111827)        // Dark slate
    val bgCard = Color(0xFF1A1F2E)             // Elevated card
    val bgGlass = Color(0x33FFFFFF)            // 20% white glass

    val textPrimary = Color(0xFFF8FAFC)        // Off-white
    val textSecondary = Color(0xFF94A3B8)       // Muted slate
    val textMuted = Color(0xFF475569)           // Deep muted

    val accentCyan = Color(0xFF06B6D4)
    val accentAmber = Color(0xFFF59E0B)
    val accentEmerald = Color(0xFF10B981)
    val accentRed = Color(0xFFEF4444)
    val accentViolet = Color(0xFF8B5CF6)
    val accentIndigo = Color(0xFF6366F1)

    val fontFamily = FontFamily(Font(R.font.plus_jakarta_sans))
    val headingFamily = FontFamily(Font(R.font.outfit))

    val glassBlur = 12.dp
    val cardRadius = 16.dp
    val elevation = 8.dp
}
```

### 9.2 Key Screens

| Screen | Purpose | Key Elements |
|:---|:---|:---|
| **Home Dashboard** | Normal music browsing + mood CTA | Greeting, recent playlists, quick-play, floating "Scan" FAB |
| **Mood Scan** | Camera + signal collection | Live camera preview, face overlay, progress indicators, self-report wheel |
| **Mood Result** | Show detected state | Animated mood orb, energy/valence/arousal gauges, explanation cards, "Correct" button |
| **Target Picker** | Choose destination mood | Mood grid with animated cards, recommended target highlighted, journey preview |
| **Journey Player** | Immersive playback | Phase progress bar, artwork, transition visualization, **discreet "Mood Tempo: 1.03x" badge**, bottom-sheet fine-tune slider (0.96x–1.04x) & toggle |
| **Insights** | Mood history & patterns | Weekly mood trend chart, journey completion rate, most effective transitions |

---

## 10. Implementation Roadmap (6 Phases)

### Phase 0: Foundation Lock (Week 1)
- [ ] Initialize Android project with Gradle module structure (incl. `onboarding/`, `autoflow/`, `ml/personal-calibrator/`)
- [ ] Set up Hilt DI, Compose Navigation, Room database schema
- [ ] Create design system (theme tokens, typography, common composables)
- [ ] Write ADRs for: architecture pattern, provider strategy, ML pipeline, data privacy, face calibration storage
- [ ] GitHub Actions CI: build + lint + unit test

### Phase 1: Onboarding + Home Dashboard + Spotify Connect (Week 2-3)
- [ ] Onboarding flow: permissions + face calibration enrollment
- [ ] Spotify OAuth PKCE flow (CustomTabs)
- [ ] Fetch user playlists, top tracks, recently played
- [ ] Home dashboard UI: greeting, ambient mood card, playlist grid, search

### Phase 2: Mood Intelligence Engine + Auto-Flow (Week 3-5)
- [ ] CameraX pipeline + ML Kit face detection
- [ ] TFLite FER model integration
- [ ] PersonalizedEmotionClassifier + continuous learning
- [ ] UsageStatsManager integration
- [ ] Self-report mood wheel composable
- [ ] Signal fusion algorithm + confidence scoring
- [ ] AutoSenseManager: passive background scan on app open
- [ ] SmartTargetPredictor: time + pattern + feedback based prediction
- [ ] FlowMode router (Auto / Guided / Manual)

### Phase 3: Journey Planner + Queue Builder (Week 5-7)
- [ ] Target mood definitions and picker UI
- [ ] Track mood-tagging system (heuristic + user-authored tags)
- [ ] **Musical key & mode extraction** (Spotify audio features API)
- [ ] **Camelot Wheel harmonic chaining engine** (Circle-of-Fifths transition scoring)
- [ ] **Phase 3 strict mode filter & unverified track background resolver**
- [ ] Journey phase builder (settle → build → arrive)
- [ ] Track scoring and ranking for phase placement
- [ ] Journey preview screen with drag-reorder queue

### Phase 4: In-App Playback & Dynamic Tempo (Week 7-9)
- [ ] Piped/InnerTube client: stream URL resolution
- [ ] ExoPlayer Media3 playback service
- [ ] **Dynamic Track-Aware Tempo Controller** (0.96x–1.04x time-stretch, pitch locked 1.0x, BPM guardrails, 1.5s crossfade ramp)
- [ ] **Spotify external playback fallback prompt** (notify user to switch to YouTube stream for tempo DSP)
- [ ] **Tempo fine-tune bottom sheet** (slider 0.96x–1.04x + dynamic guardrail toggle)
- [ ] Media notification with controls
- [ ] Spotify deep-link handoff for Spotify-only tracks
- [ ] YouTube ↔ Spotify track matching (title + artist search)
- [ ] Now Playing screen: artwork, progress, phase indicator, **discreet tempo badge**
- [ ] Mini-player bottom bar (persistent across navigation)
- [ ] Queue management: skip, save, remove, reorder

### Phase 5: Feedback Loop + Insights + Auto-Continue (Week 9-10)
- [ ] Per-track feedback: skip reason, vibe rating
- [ ] Journey completion feedback: "Did this help?"
- [ ] Journey auto-continue: suggest next journey when current ends
- [ ] Face calibration refinement from correction feedback
- [ ] Mood history timeline & weekly pattern visualization
- [ ] Re-calibration flow in Settings → "Re-learn my face"

### Phase 6: Hardening + Polish + Shortcuts (Week 10-12)
- [ ] Permission denial graceful degradation
- [ ] Offline mode & battery optimization testing
- [ ] Android home screen widget (mood estimate + one-tap journey)
- [ ] App shortcuts (Quick Energize, Quick Calm, Quick Focus)
- [ ] Morning/Evening routine scheduler

---

## 11. Testing Strategy

| Layer | What to Test | Framework |
|:---|:---|:---|
| **Unit** | MoodFuser, JourneyPlanner, TrackScorer, DynamicTempoController | JUnit 5 + Turbine |
| **Integration** | Room migrations, Spotify token refresh, Piped stream resolution | Robolectric + MockWebServer |
| **UI** | Scan flow, target selection, queue editing, tempo tuning controls | Compose UI Testing + Espresso |
| **Contract** | Provider adapters (Spotify 401/403/429, Piped 503) | MockWebServer + custom fakes |
| **E2E** | Full journey: scan → detect → pick → build → play → feedback | Maestro or manual |

---

## 12. Key Risks & Mitigations

| Risk | Impact | Mitigation |
|:---|:---|:---|
| Audio artifact from tempo shift | Robotic or stuttering audio | Strict clamping to `[0.96x, 1.04x]`, ExoPlayer Sonic time-stretch, and 1.5s crossfade ramp. |
| Vocal pitch distortion | Unnatural voice tonality | **Musical pitch is strictly locked at 1.0x.** No pitch transposition or harmonic shifting. |
| Over-accelerating fast songs | Frantic or chaotic playback | Dynamic BPM guardrails dampen tempo boosts for songs already above target zone. |
| External Spotify limitation | Cannot apply DSP in external app | Fallback prompt gates external playback, suggesting in-app YouTube stream match. |
| FER model accuracy is low | Mood detection unreliable | Personal face calibration boosts to ~90%+. Self-report fallback always available. |
| Auto-sense camera feels creepy | User distrust | Opt-in only during onboarding (default OFF). Subtle indicator dot. No raw images stored. |
| Piped instances go down | No in-app playback | Health-check + fallback chain (3+ instances). Direct InnerTube as last resort. |

---

## 13. What We're NOT Building (v1)

| Feature | Why Not |
|:---|:---|
| **Pitch shifting / Key modification** | **Strictly omitted** to prevent vocal distortion and maintain authentic musical keys. Only subtle time-stretch tempo modulation (0.96x–1.04x) is used. |
| Equalizer / multi-band FX | Out of scope. Media3 handles audio natively; tempo is handled via SonicAudioProcessor. |
| iOS / Web / Desktop | Android-first. Validate concept on one platform. |
| Social features | Personal tool. No sharing, no profiles, no leaderboards. |
| Cloud sync | Local-first. Data stays on device. |
| Continuous background mood monitoring | Privacy concern + battery drain. Auto-sense is brief (2 sec on open), not continuous. |
| AI-generated playlists (LLM) | Deterministic journey planner first. LLM enhancement is v2. |
| Lyrics display | Nice-to-have, not core. v2. |
| Music downloads / offline cache | Legal complexity. Stream-only for v1. |
| Mental health claims | Not a therapeutic tool. No clinical language. |
| Cloud-based face recognition | All face processing is on-device. No face data leaves the phone. |
| Multi-face calibration | Single user profile only. One face per device. |

---

> [!TIP]
> **Recommended next step:** Run `/spec` to formalize this into a PRD with acceptance criteria, then `/plan` to break Phase 0-1 into executable tasks with dependency ordering.
