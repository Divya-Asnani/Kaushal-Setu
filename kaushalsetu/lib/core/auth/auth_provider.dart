import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:kaushalsetu/core/api/api_exception.dart';
import 'package:kaushalsetu/models/profile.dart';
import 'package:kaushalsetu/services/auth_service.dart';

class AuthProvider extends ChangeNotifier {
  final AuthService _authService = AuthService();

  UserProfile? _userProfile;
  bool _isLoading = false;
  String? _errorMessage;
  String? _activeMode; // 'customer' or 'worker'

  UserProfile? get userProfile => _userProfile;
  bool get isAuthenticated => _userProfile != null;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;

  String get activeMode => _activeMode ?? (_userProfile?.role ?? 'customer');
  bool get isCustomer => activeMode == 'customer';
  bool get isWorker => activeMode == 'worker';
  bool get isAdmin => _userProfile?.isAdmin ?? false;
  bool get hasWorkerProfile => _userProfile?.role == 'worker';

  void switchMode(String mode) {
    _activeMode = mode;
    notifyListeners();
  }

  Future<void> checkExistingAuth() async {
    _isLoading = true;
    notifyListeners();
    try {
      _userProfile = await _authService.getCurrentProfile();
    } catch (_) {
      _userProfile = null;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> login(String email, String password) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      _userProfile = await _authService.loginWithEmail(email, password);
      _isLoading = false;
      notifyListeners();
      return true;
    } on AuthException catch (e) {
      _errorMessage = e.message;
      _isLoading = false;
      notifyListeners();
      return false;
    } catch (e) {
      _errorMessage = e.toString().replaceAll('Exception: ', '');
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }


  Future<bool> register({
    required String email,
    required String password,
    required String fullName,
    required String role,
    String? phone,
    String? locality,
    String? city,
  }) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      _userProfile = await _authService.register(
        email: email,
        password: password,
        fullName: fullName,
        role: role,
        phone: phone,
        locality: locality,
        city: city,
      );
      _isLoading = false;
      notifyListeners();
      return true;
    } on AuthException catch (e) {
      _errorMessage = e.message;
      _isLoading = false;
      notifyListeners();
      return false;
    } on ApiException catch (e) {
      _errorMessage = e.message;
      _isLoading = false;
      notifyListeners();
      return false;
    } catch (e) {
      _errorMessage = e.toString().replaceAll('Exception: ', '');
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  Future<bool> becomeWorker({
    String serviceCategory = 'electronics',
    int experienceYears = 3,
    double hourlyRate = 450.0,
    String? locality,
    String? city,
    String? headline,
    String? bio,
  }) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      _userProfile = await _authService.becomeWorker(
        serviceCategory: serviceCategory,
        experienceYears: experienceYears,
        hourlyRate: hourlyRate,
        locality: locality,
        city: city,
        headline: headline,
        bio: bio,
      );
      _activeMode = 'worker';
      _isLoading = false;
      notifyListeners();
      return true;
    } on ApiException catch (e) {
      _errorMessage = e.message;
      _isLoading = false;
      notifyListeners();
      return false;
    } catch (e) {
      _errorMessage = e.toString().replaceAll('Exception: ', '');
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  Future<bool> updateProfile({
    String? fullName,
    String? phone,
    String? locality,
    String? city,
  }) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      _userProfile = await _authService.updateProfile(
        fullName: fullName,
        phone: phone,
        locality: locality,
        city: city,
      );
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _errorMessage = e.toString().replaceAll('Exception: ', '');
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  Future<void> logout() async {
    await _authService.logout();
    _userProfile = null;
    _activeMode = null;
    notifyListeners();
  }
}
