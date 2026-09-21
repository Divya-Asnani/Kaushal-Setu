import 'package:kaushalsetu/core/api/api_client.dart';
import 'package:kaushalsetu/models/problem.dart';

class ProblemService {
  final ApiClient _api = ApiClient();

  Future<CustomerProblem> createProblem({
    required String title,
    required String description,
    String? addressLine,
    String? locality,
    String? city,
    String? state,
    String? postalCode,
    required double latitude,
    required double longitude,
    List<String> mediaPaths = const [],
  }) async {
    final res = await _api.post('/problems', body: {
      'title': title,
      'description': description,
      'address_line': addressLine,
      'locality': locality,
      'city': city,
      'state': state,
      'postal_code': postalCode,
      'latitude': latitude,
      'longitude': longitude,
      'media_paths': mediaPaths,
    });
    return CustomerProblem.fromJson(res as Map<String, dynamic>);
  }

  Future<List<CustomerProblem>> listProblems() async {
    final res = await _api.get('/problems');
    if (res is List) {
      return res.map((e) => CustomerProblem.fromJson(e as Map<String, dynamic>)).toList();
    }
    return [];
  }

  Future<CustomerProblem> getProblem(String id) async {
    final res = await _api.get('/problems/$id');
    return CustomerProblem.fromJson(res as Map<String, dynamic>);
  }

  Future<ProblemFingerprint> generateFingerprint(String problemId, {bool regenerate = false}) async {
    final res = await _api.post('/problems/$problemId/fingerprint', body: {
      'regenerate': regenerate,
    });
    return ProblemFingerprint.fromJson(res as Map<String, dynamic>);
  }
}
