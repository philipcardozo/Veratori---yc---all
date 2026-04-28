# Veratori Restock - Flutter Mobile App

Employee-facing mobile application for documenting restock actions through structured photo submissions.

## Features

- **Authentication**: Integrates with existing Veratori backend authentication system
- **Photo Capture**: Capture minimum 3 photos (front, left, right) with optional additional angles
- **YOLO Detection**: Real-time product detection with visual bounding boxes before submission
- **Submission Management**: View all your submissions with status tracking
- **Notifications**: Receive push notifications when managers review your submissions
- **Role-Based Access**: Employees can only access their franchise data

## Setup

### Prerequisites

- Flutter SDK (3.0.0 or higher)
- Dart SDK
- iOS: Xcode (for iOS builds)
- Android: Android Studio (for Android builds)

### Installation

1. Navigate to the app directory:
```bash
cd veratori_restock_flutter
```

2. Install dependencies:
```bash
flutter pub get
```

3. Configure API endpoint:
   - Edit `lib/services/api_service.dart`
   - Update `_baseUrl` to point to your Veratori backend server
   - Default: `http://localhost:8080` (change to your server IP/domain)

4. Run the app:
```bash
flutter run
```

## Configuration

### Backend URL

Update the base URL in `lib/services/api_service.dart`:

```dart
_baseUrl = baseUrl ?? 'http://YOUR_SERVER_IP:8080';
```

For production, use HTTPS:
```dart
_baseUrl = baseUrl ?? 'https://your-domain.com';
```

### Permissions

The app requires the following permissions:
- **Camera**: For capturing restock photos
- **Storage/Photos**: For selecting photos from gallery

These are automatically requested when needed.

## Building for Production

### Android

```bash
flutter build apk --release
```

### iOS

```bash
flutter build ios --release
```

## Architecture

- **State Management**: Provider pattern
- **Networking**: Dio HTTP client with cookie-based session management
- **Storage**: SharedPreferences for session persistence
- **Image Handling**: Image Picker for camera/gallery access

## API Integration

The app integrates with the following backend endpoints:

- `POST /api/restock/login` - Employee login
- `POST /api/restock/validate` - Session validation
- `POST /api/restock/logout` - Logout
- `POST /api/restock/detect` - YOLO detection on photo
- `POST /api/restock/upload` - Submit restock with photos
- `GET /api/restock/submissions` - Get employee submissions
- `GET /api/restock/notifications` - Get notifications
- `GET /api/restock/notifications/count` - Get unread count
- `POST /api/restock/notifications/read` - Mark notification as read

## Troubleshooting

### Connection Issues

- Ensure the backend server is running and accessible
- Check firewall settings if connecting to remote server
- Verify the API base URL is correct

### Camera Not Working

- Check app permissions in device settings
- Ensure camera hardware is available
- Try restarting the app

### Authentication Issues

- Verify credentials are correct
- Check backend authentication is enabled
- Ensure session cookies are being stored properly


