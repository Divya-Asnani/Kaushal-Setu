class ServiceRequestModel {
  final String id;
  final String problemId;
  final String workerId;
  final String? matchResultId;
  final String? customerMessage;
  final String? workerResponse;
  final String status; // pending, accepted, rejected, expired, cancelled
  final DateTime createdAt;
  final String? problemTitle;
  final String? problemDescription;
  final String? problemCategory;
  final String? customerName;
  final String? workerName;
  final String? locality;
  final String? createdJobId;

  ServiceRequestModel({
    required this.id,
    required this.problemId,
    required this.workerId,
    this.matchResultId,
    this.customerMessage,
    this.workerResponse,
    required this.status,
    required this.createdAt,
    this.problemTitle,
    this.problemDescription,
    this.problemCategory,
    this.customerName,
    this.workerName,
    this.locality,
    this.createdJobId,
  });

  factory ServiceRequestModel.fromJson(Map<String, dynamic> json) {
    return ServiceRequestModel(
      id: json['id'] as String,
      problemId: json['problem_id'] as String,
      workerId: json['worker_id'] as String,
      matchResultId: json['match_result_id'] as String?,
      customerMessage: json['customer_message'] as String?,
      workerResponse: json['worker_response'] as String?,
      status: json['status'] as String? ?? 'pending',
      createdAt: DateTime.tryParse(json['created_at']?.toString() ?? '') ?? DateTime.now(),
      problemTitle: json['problem_title'] as String?,
      problemDescription: json['problem_description'] as String?,
      problemCategory: json['problem_category'] as String?,
      customerName: json['customer_name'] as String?,
      workerName: json['worker_name'] as String?,
      locality: json['locality'] as String?,
      createdJobId: json['created_job_id'] as String?,
    );
  }

  bool get isPending => status.toLowerCase() == 'pending';
  bool get isAccepted => status.toLowerCase() == 'accepted';
  bool get isRejected => status.toLowerCase() == 'rejected';
}
