import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:kaushalsetu/core/config/app_config.dart';
import 'package:kaushalsetu/core/api/api_exception.dart';

class ApiClient {
  static final ApiClient _instance = ApiClient._internal();
  factory ApiClient() => _instance;
  ApiClient._internal();

  String? _customAuthToken;

  void setCustomAuthToken(String? token) {
    _customAuthToken = token;
  }

  String? get currentToken {
    if (_customAuthToken != null) {
      return _customAuthToken;
    }
    try {
      final session = Supabase.instance.client.auth.currentSession;
      return session?.accessToken;
    } catch (_) {
      return null;
    }
  }

  Map<String, String> _buildHeaders() {
    final headers = <String, String>{
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
    final token = currentToken;
    if (token != null && token.isNotEmpty) {
      headers['Authorization'] = 'Bearer $token';
    }
    return headers;
  }

  Uri _resolveUri(String path, [Map<String, dynamic>? queryParams]) {
    final base = AppConfig.apiBaseUrl;
    final cleanPath = path.startsWith('/') ? path : '/$path';
    final fullUrl = '$base$cleanPath';
    final uri = Uri.parse(fullUrl);
    if (queryParams != null && queryParams.isNotEmpty) {
      final stringParams = queryParams.map(
        (key, value) => MapEntry(key, value.toString()),
      );
      return uri.replace(queryParameters: stringParams);
    }
    return uri;
  }

  dynamic _handleResponse(http.Response response) {
    if (response.statusCode >= 200 && response.statusCode < 300) {
      if (response.body.isEmpty) return null;
      try {
        return jsonDecode(utf8.decode(response.bodyBytes));
      } catch (e) {
        return response.body;
      }
    }

    try {
      final errorJson = jsonDecode(utf8.decode(response.bodyBytes));
      if (errorJson is Map<String, dynamic>) {
        throw ApiException.fromJson(errorJson, response.statusCode);
      }
    } catch (e) {
      if (e is ApiException) rethrow;
    }

    throw ApiException(
      code: 'HTTP_${response.statusCode}',
      message: 'Request failed with HTTP status ${response.statusCode}: ${response.body}',
      statusCode: response.statusCode,
    );
  }

  Future<dynamic> get(String path, {Map<String, dynamic>? queryParams}) async {
    final uri = _resolveUri(path, queryParams);
    final response = await http.get(uri, headers: _buildHeaders());
    return _handleResponse(response);
  }

  Future<dynamic> post(String path, {dynamic body}) async {
    final uri = _resolveUri(path);
    final response = await http.post(
      uri,
      headers: _buildHeaders(),
      body: body != null ? jsonEncode(body) : null,
    );
    return _handleResponse(response);
  }

  Future<dynamic> patch(String path, {dynamic body}) async {
    final uri = _resolveUri(path);
    final response = await http.patch(
      uri,
      headers: _buildHeaders(),
      body: body != null ? jsonEncode(body) : null,
    );
    return _handleResponse(response);
  }

  Future<dynamic> put(String path, {dynamic body}) async {
    final uri = _resolveUri(path);
    final response = await http.put(
      uri,
      headers: _buildHeaders(),
      body: body != null ? jsonEncode(body) : null,
    );
    return _handleResponse(response);
  }

  Future<dynamic> delete(String path) async {
    final uri = _resolveUri(path);
    final response = await http.delete(uri, headers: _buildHeaders());
    return _handleResponse(response);
  }
}
