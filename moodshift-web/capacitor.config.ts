import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.moodshift.app',
  appName: 'MoodShift',
  webDir: 'dist',
  android: {
    allowMixedContent: true
  }
};

export default config;
