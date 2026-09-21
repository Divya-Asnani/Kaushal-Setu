import 'package:flutter/foundation.dart';

class AppConfig {
  static const String appName = 'KaushalSetu';
  static const String appTagline = 'Intelligent Opportunity Matching for Technicians';

  // FastAPI Base URL
  // Uses 10.0.2.2 for Android Emulator, localhost for Web/Desktop/iOS
  static String get apiBaseUrl {
    if (kIsWeb) {
      return 'http://localhost:8000/api/v1';
    }
    switch (defaultTargetPlatform) {
      case TargetPlatform.android:
        return 'http://10.0.2.2:8000/api/v1';
      default:
        return 'http://localhost:8000/api/v1';
    }
  }

  // Supabase Configuration
  static const String supabaseUrl = 'https://nonhfclpamyovrrmgpfp.supabase.co';
  static const String supabaseAnonKey =
      'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5vbmhmY2xwYW15b3Zycm1ncGZwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODkxNDEyODUsImV4cCI6MjEwNDcxNzI4NX0.bBFnoTl2wtFoImt46h9T8ncgL2PktzOr_18qEx1I-3w';

  // Supabase Storage Buckets
  static const String problemMediaBucket = 'problem-media';
  static const String experienceMediaBucket = 'experience-media';
}
