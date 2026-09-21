import 'package:kaushalsetu/core/api/api_client.dart';
import 'package:kaushalsetu/models/knowledge_case.dart';

class KnowledgeService {
  final ApiClient _api = ApiClient();

  Future<List<KnowledgeCase>> searchSimilarCases(String query, {int limit = 5}) async {
    final res = await _api.get('/knowledge-cases/similar', queryParams: {
      'q': query,
      'limit': limit,
    });
    if (res is List) {
      return res.map((e) => KnowledgeCase.fromJson(e as Map<String, dynamic>)).toList();
    }
    return [];
  }

  Future<KnowledgeCase> getCase(String caseId) async {
    final res = await _api.get('/knowledge-cases/$caseId');
    return KnowledgeCase.fromJson(res as Map<String, dynamic>);
  }

  Future<KnowledgeCase> createCase({
    required String title,
    required String problemSummary,
    required String diagnosis,
    required String solution,
    String? lessonLearned,
    String difficulty = 'intermediate',
    String? deviceCategory,
    String? brand,
    String? model,
    List<String> mediaPaths = const [],
  }) async {
    final res = await _api.post('/knowledge-cases', body: {
      'title': title,
      'problem_summary': problemSummary,
      'diagnosis': diagnosis,
      'solution': solution,
      'lesson_learned': lessonLearned,
      'difficulty': difficulty,
      'device_category': deviceCategory,
      'brand': brand,
      'model': model,
      'media_paths': mediaPaths,
    });
    return KnowledgeCase.fromJson(res as Map<String, dynamic>);
  }
}
