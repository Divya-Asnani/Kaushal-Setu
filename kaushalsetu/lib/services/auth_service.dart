import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:kaushalsetu/core/api/api_client.dart';
import 'package:kaushalsetu/models/profile.dart';

class AuthService {
  final ApiClient _api = ApiClient();

  Future<UserProfile?> getCurrentProfile() async {
    final session = Supabase.instance.client.auth.currentSession;
    if (session == null) {
      return null;
    }
    try {
      final res = await _api.get('/me');
      if (res != null) {
        return UserProfile.fromJson(res as Map<String, dynamic>);
      }
    } catch (_) {
      return null;
    }
    return null;
  }

  Future<UserProfile> loginWithEmail(String email, String password) async {
    final authResponse = await Supabase.instance.client.auth.signInWithPassword(
      email: email.trim(),
      password: password,
    );

    if (authResponse.session == null) {
      throw Exception('Login succeeded but no valid Supabase session was returned.');
    }

    // Always use the real Supabase session JWT
    _api.setCustomAuthToken(null);

    final profile = await getCurrentProfile();
    if (profile == null) {
      throw Exception('Authenticated with Supabase, but profile could not be loaded from database.');
    }
    return profile;
  }

  Future<UserProfile> register({
    required String email,
    required String password,
    required String fullName,
    required String role,
    String? phone,
    String? locality,
    String? city,
  }) async {
    final cleanEmail = email.trim().toLowerCase();

    // 1. Provision user via backend with email_confirm=True in Supabase Auth & PostgreSQL
    // This avoids SMTP rate limits on free-tier Supabase and instantly provisions profiles
    final regRes = await _api.post('/auth/register', body: {
      'email': cleanEmail,
      'password': password,
      'full_name': fullName,
      'role': role,
      'phone': phone,
      'locality': locality,
      'city': city,
    });

    // 2. Sign in to Supabase Auth to establish the real client session and acquire JWT
    final authResponse = await Supabase.instance.client.auth.signInWithPassword(
      email: cleanEmail,
      password: password,
    );

    if (authResponse.session == null) {
      throw Exception('Account registered in Supabase, but failed to obtain a session.');
    }

    _api.setCustomAuthToken(null);

    final profile = await getCurrentProfile();
    if (profile != null) {
      return profile;
    }

    if (regRes != null && regRes is Map<String, dynamic>) {
      return UserProfile.fromJson(regRes);
    }

    throw Exception('Registration succeeded, but profile could not be loaded.');
  }

  Future<UserProfile> becomeWorker({
    String serviceCategory = 'electronics',
    int experienceYears = 3,
    double hourlyRate = 450.0,
    String? locality,
    String? city,
    String? headline,
    String? bio,
  }) async {
    final res = await _api.post('/become-worker', body: {
      'service_category': serviceCategory,
      'experience_years': experienceYears,
      'hourly_rate': hourlyRate,
      'locality': locality,
      'city': city,
      'headline': headline,
      'bio': bio,
    });
    if (res != null && res is Map<String, dynamic>) {
      return UserProfile.fromJson(res);
    }
    final updated = await getCurrentProfile();
    if (updated != null) return updated;
    throw Exception('Failed to upgrade to technician profile.');
  }

  Future<UserProfile> updateProfile({
    String? fullName,
    String? phone,
    String? locality,
    String? city,
  }) async {
    final body = <String, dynamic>{};
    if (fullName != null) body['full_name'] = fullName;
    if (phone != null) body['phone'] = phone;
    if (locality != null) body['locality'] = locality;
    if (city != null) body['city'] = city;

    final res = await _api.patch('/me', body: body);
    if (res != null && res is Map<String, dynamic>) {
      return UserProfile.fromJson(res);
    }
    final updated = await getCurrentProfile();
    if (updated != null) return updated;
    throw Exception('Failed to update profile.');
  }

  Future<void> logout() async {
    try {
      await Supabase.instance.client.auth.signOut();
    } catch (_) {}
    _api.setCustomAuthToken(null);
  }
}
