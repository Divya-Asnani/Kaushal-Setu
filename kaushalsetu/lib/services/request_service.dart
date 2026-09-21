import 'package:kaushalsetu/core/api/api_client.dart';
import 'package:kaushalsetu/models/service_request.dart';

class RequestService {
  final ApiClient _api = ApiClient();

  Future<ServiceRequestModel> createServiceRequest({
    required String problemId,
    required String workerId,
    String? matchResultId,
    String? customerMessage,
  }) async {
    final res = await _api.post('/service-requests', body: {
      'problem_id': problemId,
      'worker_id': workerId,
      'match_result_id': matchResultId,
      'customer_message': customerMessage,
    });
    return ServiceRequestModel.fromJson(res as Map<String, dynamic>);
  }

  Future<List<ServiceRequestModel>> listServiceRequests() async {
    final res = await _api.get('/service-requests/me');
    if (res is List) {
      return res.map((e) => ServiceRequestModel.fromJson(e as Map<String, dynamic>)).toList();
    }
    return [];
  }

  Future<ServiceRequestModel> respondToRequest({
    required String requestId,
    required String status,
    String? workerResponse,
  }) async {
    final res = await _api.patch('/service-requests/$requestId', body: {
      'status': status,
      'worker_response': workerResponse,
    });
    return ServiceRequestModel.fromJson(res as Map<String, dynamic>);
  }
}
