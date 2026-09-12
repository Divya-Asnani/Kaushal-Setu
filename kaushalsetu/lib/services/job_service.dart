import 'package:kaushalsetu/core/api/api_client.dart';
import 'package:kaushalsetu/models/job.dart';

class JobService {
  final ApiClient _api = ApiClient();

  Future<JobModel> getJob(String jobId) async {
    final res = await _api.get('/jobs/$jobId');
    return JobModel.fromJson(res as Map<String, dynamic>);
  }

  Future<List<JobModel>> listJobs() async {
    final res = await _api.get('/jobs/me');
    if (res is List) {
      return res.map((e) => JobModel.fromJson(e as Map<String, dynamic>)).toList();
    }
    return [];
  }

  Future<JobModel> updateJobStatus(String jobId, String status, {String? notes}) async {
    final res = await _api.patch('/jobs/$jobId/status', body: {
      'status': status,
      'notes': notes,
    });
    return JobModel.fromJson(res as Map<String, dynamic>);
  }

  Future<JobModel> submitCompletion({
    required String jobId,
    required String diagnosis,
    required List<JobAction> actions,
    required List<JobOutcome> outcomes,
    required List<JobEvidence> evidence,
  }) async {
    final res = await _api.post('/jobs/$jobId/completion', body: {
      'diagnosis': diagnosis,
      'actions': actions.map((a) => a.toJson()).toList(),
      'outcomes': outcomes.map((o) => o.toJson()).toList(),
      'evidence': evidence.map((e) => e.toJson()).toList(),
    });
    return JobModel.fromJson(res as Map<String, dynamic>);
  }
}
