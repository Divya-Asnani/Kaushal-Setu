# KaushalSetu Flutter Frontend

Cross-platform client application for **KaushalSetu (कौशल सेतु)** built with Flutter.

## Architecture

* **State Management**: `Provider` (`AuthProvider`)
* **Styling & Theme**: Custom design system in `lib/core/theme/app_theme.dart` (Urban Company / Uber inspired warm amber and slate palette)
* **Backend API Client**: `ApiClient` (`lib/core/api/api_client.dart`) communicating with FastAPI at `http://localhost:8000/api/v1`
* **Authentication & Media**: Supabase Auth and Supabase Storage buckets (`problem-media`, `experience-media`)

## Getting Started

1. **Install dependencies**:
   ```bash
   flutter pub get
   ```

2. **Run in development mode**:
   ```bash
   # Web (Google Chrome)
   flutter run -d chrome

   # Mobile (Android emulator or physical device)
   flutter run
   ```

For backend setup, database migration, and full system documentation, refer to the root [README.md](../README.md).
