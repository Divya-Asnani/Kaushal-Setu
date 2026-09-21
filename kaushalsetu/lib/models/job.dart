class JobAction {
  final int stepNumber;
  final String actionType;
  final String actionDescription;
  final List<String> toolsUsed;

  JobAction({
    required this.stepNumber,
    required this.actionType,
    required this.actionDescription,
    this.toolsUsed = const [],
  });

  factory JobAction.fromJson(Map<String, dynamic> json) {
    final tools = json['tools_used'] as List<dynamic>? ?? [];
    return JobAction(
      stepNumber: json['step_number'] as int? ?? 1,
      actionType: json['action_type'] as String? ?? 'repair',
      actionDescription: json['action_description'] as String? ?? '',
      toolsUsed: tools.map((e) => e.toString()).toList(),
    );
  }

  Map<String, dynamic> toJson() => {
        'step_number': stepNumber,
        'action_type': actionType,
        'action_description': actionDescription,
        'tools_used': toolsUsed,
      };
}

class JobOutcome {
  final String outcomeType;
  final String outcomeDescription;
  final String successStatus;
  final String? lessonsLearned;

  JobOutcome({
    required this.outcomeType,
    required this.outcomeDescription,
    this.successStatus = 'successful',
    this.lessonsLearned,
  });

  factory JobOutcome.fromJson(Map<String, dynamic> json) {
    return JobOutcome(
      outcomeType: json['outcome_type'] as String? ?? 'repair_result',
      outcomeDescription: json['outcome_description'] as String? ?? '',
      successStatus: json['success_status'] as String? ?? 'successful',
      lessonsLearned: json['lessons_learned'] as String?,
    );
  }

  Map<String, dynamic> toJson() => {
        'outcome_type': outcomeType,
        'outcome_description': outcomeDescription,
        'success_status': successStatus,
        'lessons_learned': lessonsLearned,
      };
}

class JobEvidence {
  final String storagePath;
  final String mediaType;
  final String mediaRole; // before, during, after, diagnostic
  final bool isVerified;

  JobEvidence({
    required this.storagePath,
    this.mediaType = 'image',
    this.mediaRole = 'after',
    this.isVerified = false,
  });

  factory JobEvidence.fromJson(Map<String, dynamic> json) {
    return JobEvidence(
      storagePath: json['storage_path'] as String? ?? '',
      mediaType: json['media_type'] as String? ?? 'image',
      mediaRole: json['media_role'] as String? ?? 'after',
      isVerified: json['is_verified'] as bool? ?? false,
    );
  }

  Map<String, dynamic> toJson() => {
        'storage_path': storagePath,
        'media_type': mediaType,
        'media_role': mediaRole,
        'is_verified': isVerified,
      };
}

class JobTimelineEvent {
  final String id;
  final String? fromStatus;
  final String toStatus;
  final String? changedByName;
  final String? notes;
  final DateTime createdAt;

  JobTimelineEvent({
    required this.id,
    this.fromStatus,
    required this.toStatus,
    this.changedByName,
    this.notes,
    required this.createdAt,
  });

  factory JobTimelineEvent.fromJson(Map<String, dynamic> json) {
    return JobTimelineEvent(
      id: json['id'] as String,
      fromStatus: json['from_status'] as String?,
      toStatus: json['to_status'] as String? ?? '',
      changedByName: json['changed_by_name'] as String?,
      notes: json['notes'] as String?,
      createdAt: DateTime.tryParse(json['created_at']?.toString() ?? '') ?? DateTime.now(),
    );
  }
}

class JobModel {
  final String id;
  final String serviceRequestId;
  final String problemId;
  final String customerId;
  final String workerId;
  final String? experienceId;
  final String status; // confirmed, in_progress, completed, cancelled, disputed
  final String? notes;
  final DateTime? startedAt;
  final DateTime? completedAt;
  final DateTime createdAt;
  final String? problemTitle;
  final String? problemDescription;
  final String? customerName;
  final String? customerPhone;
  final String? workerName;
  final String? workerPhone;
  final String? locality;
  final String? diagnosis;
  final List<JobAction> actions;
  final List<JobOutcome> outcomes;
  final List<JobEvidence> evidence;
  final List<JobTimelineEvent> timeline;
  final bool hasFeedback;
  final bool isVerified;

  JobModel({
    required this.id,
    required this.serviceRequestId,
    required this.problemId,
    required this.customerId,
    required this.workerId,
    this.experienceId,
    required this.status,
    this.notes,
    this.startedAt,
    this.completedAt,
    required this.createdAt,
    this.problemTitle,
    this.problemDescription,
    this.customerName,
    this.customerPhone,
    this.workerName,
    this.workerPhone,
    this.locality,
    this.diagnosis,
    this.actions = const [],
    this.outcomes = const [],
    this.evidence = const [],
    this.timeline = const [],
    this.hasFeedback = false,
    this.isVerified = false,
  });

  factory JobModel.fromJson(Map<String, dynamic> json) {
    final aList = json['actions'] as List<dynamic>? ?? [];
    final oList = json['outcomes'] as List<dynamic>? ?? [];
    final eList = json['evidence'] as List<dynamic>? ?? [];
    final tList = json['timeline'] as List<dynamic>? ?? [];

    return JobModel(
      id: json['id'] as String,
      serviceRequestId: json['service_request_id'] as String,
      problemId: json['problem_id'] as String,
      customerId: json['customer_id'] as String,
      workerId: json['worker_id'] as String,
      experienceId: json['experience_id'] as String?,
      status: json['status'] as String? ?? 'confirmed',
      notes: json['notes'] as String?,
      startedAt: json['started_at'] != null ? DateTime.tryParse(json['started_at']) : null,
      completedAt: json['completed_at'] != null ? DateTime.tryParse(json['completed_at']) : null,
      createdAt: DateTime.tryParse(json['created_at']?.toString() ?? '') ?? DateTime.now(),
      problemTitle: json['problem_title'] as String?,
      problemDescription: json['problem_description'] as String?,
      customerName: json['customer_name'] as String?,
      customerPhone: json['customer_phone'] as String?,
      workerName: json['worker_name'] as String?,
      workerPhone: json['worker_phone'] as String?,
      locality: json['locality'] as String?,
      diagnosis: json['diagnosis'] as String?,
      actions: aList.map((e) => JobAction.fromJson(e as Map<String, dynamic>)).toList(),
      outcomes: oList.map((e) => JobOutcome.fromJson(e as Map<String, dynamic>)).toList(),
      evidence: eList.map((e) => JobEvidence.fromJson(e as Map<String, dynamic>)).toList(),
      timeline: tList.map((e) => JobTimelineEvent.fromJson(e as Map<String, dynamic>)).toList(),
      hasFeedback: json['has_feedback'] as bool? ?? false,
      isVerified: json['is_verified'] as bool? ?? false,
    );
  }

  bool get isConfirmed => status.toLowerCase() == 'confirmed';
  bool get isInProgress => status.toLowerCase() == 'in_progress';
  bool get isCompleted => status.toLowerCase() == 'completed';
  bool get isDisputed => status.toLowerCase() == 'disputed';
  bool get isCancelled => status.toLowerCase() == 'cancelled';
}
