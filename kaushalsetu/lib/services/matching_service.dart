import 'package:kaushalsetu/core/api/api_client.dart';
import 'package:kaushalsetu/models/match_result.dart';

class MatchingService {
  final ApiClient _api = ApiClient();

  Future<List<MatchResultItem>> getProblemMatches(String problemId, {int limit = 5}) async {
    final res = await _api.get('/problems/$problemId/matches', queryParams: {
      'limit': limit,
    });
    if (res is Map<String, dynamic>) {
      final matchesList = res['matches'] as List<dynamic>? ?? [];
      return matchesList.map((e) => MatchResultItem.fromJson(e as Map<String, dynamic>)).toList();
    }
    return [];
  }
}
