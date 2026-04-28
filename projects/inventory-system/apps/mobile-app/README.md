# Veratori Restock - Mobile App

Employee-facing mobile application for iOS and Android to document restocking actions.

## Setup

### Prerequisites
- Node.js 18+ and npm/yarn
- React Native CLI
- iOS: Xcode 14+ (for iOS development)
- Android: Android Studio (for Android development)

### Installation

```bash
cd mobile-app
npm install
# or
yarn install
```

### Configuration

Update `src/config/api.js` with your server URL:
```javascript
export const API_BASE_URL = 'http://your-server-ip:8080';
```

### Running

**iOS:**
```bash
cd ios
pod install
cd ..
npm run ios
```

**Android:**
```bash
npm run android
```

## Features

- Employee login with franchise-scoped access
- Photo capture (minimum 3 photos per submission)
- Real-time YOLO detection preview
- Submission management
- Notifications for manager reviews
- Account settings

## Architecture

- **React Native** for cross-platform support
- **React Navigation** for navigation
- **React Native Camera** for photo capture
- **Axios** for API communication
- **AsyncStorage** for local token storage


