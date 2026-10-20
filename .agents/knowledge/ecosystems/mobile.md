# 📱 Mobile Ecosystem Knowledge

Categorized mobile recipes, React Native / Flutter build flows, and gotchas.

---

## 🏗️ Verified Build Flows & Setup Recipes
- **React Native Expo Bare/Managed Init**:
  - Pattern: Clean TypeScript template with strict linting and Hermes engine enabled.

---

## 🛡️ Known Gotchas & Anti-Patterns
- **CocoaPods Ruby Version Mismatch**:
  - *Gotcha*: iOS pod install failing due to system Ruby vs rbenv version mismatch.
  - *Strategy*: Use `bundle exec pod install` with Gemfile-pinned CocoaPods.
