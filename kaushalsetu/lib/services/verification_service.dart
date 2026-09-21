import 'package:kaushalsetu/core/api/api_client.dart';

class VerificationService {
  final ApiClient _api = ApiClient();

  Future<void> verifyJob(String jobId, {String? comments}) async {
    await _api.post('/jobs/$jobId/verify', body: {
      'verification_status': 'verified',
      'comments': comments ?? 'Confirmed repair working properly.',
    });
  }

  Future<void> disputeJob(String jobId, {required String comments}) async {
    await _api.post('/jobs/$jobId/dispute', body: {
      'comments': comments,
    });
  }

  Future<void> submitFeedback({
    required String jobId,
    required double rating,
    String? feedbackText,
  }) async {
    await _api.post('/feedback', body: {
      'job_id': jobId,
      'rating': rating,
      'feedback_text': feedbackText,
    });
  }
}
