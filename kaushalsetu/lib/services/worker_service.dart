import 'package:kaushalsetu/core/api/api_client.dart';
import 'package:kaushalsetu/models/worker_profile.dart';

class WorkerService {
  final ApiClient _api = ApiClient();

  Future<WorkerProfile> getMyProfile() async {
    final res = await _api.get('/workers/me');
    return WorkerProfile.fromJson(res as Map<String, dynamic>);
  }

  Future<WorkerProfile> updateAvailability(bool isAvailable) async {
    final res = await _api.patch('/workers/me', body: {
      'is_available': isAvailable,
    });
    return WorkerProfile.fromJson(res as Map<String, dynamic>);
  }

  Future<WorkerProfile> getWorker(String workerId) async {
    final res = await _api.get('/workers/$workerId');
    return WorkerProfile.fromJson(res as Map<String, dynamic>);
  }

  Future<List<Map<String, dynamic>>> listAllSkills() async {
    final res = await _api.get('/skills');
    if (res is List) {
      return res.cast<Map<String, dynamic>>();
    }
    return [];
  }

  Future<void> addCertificate({
    required String title,
    required String issuingOrganization,
    String? issueDate,
    String? expiryDate,
    String? credentialUrl,
    String? storagePath,
  }) async {
    await _api.post('/workers/me/certificates', body: {
      'title': title,
      'issuing_organization': issuingOrganization,
      'issue_date': issueDate,
      'expiry_date': expiryDate,
      'credential_url': credentialUrl,
      'storage_path': storagePath,
    });
  }

  Future<void> updateSkills(List<Map<String, dynamic>> skillsList) async {
    await _api.put('/workers/me/skills', body: skillsList);
  }
}
