class ProblemMedia {
  final String id;
  final String storagePath;
  final String mediaType;

  ProblemMedia({
    required this.id,
    required this.storagePath,
    required this.mediaType,
  });

  factory ProblemMedia.fromJson(Map<String, dynamic> json) {
    return ProblemMedia(
      id: json['id'] as String,
      storagePath: json['storage_path'] as String? ?? '',
      mediaType: json['media_type'] as String? ?? 'image',
    );
  }
}

class ProblemFingerprint {
  final String id;
  final String problemId;
  final String? deviceType;
  final String? brand;
  final String? model;
  final String? category;
  final String? issue;
  final List<String> symptoms;
  final String? suspectedComponent;
  final String? repairType;
  final List<String> extractedSkills;
  final String? aiSummary;
  final int fingerprintVersion;

  ProblemFingerprint({
    required this.id,
    required this.problemId,
    this.deviceType,
    this.brand,
    this.model,
    this.category,
    this.issue,
    this.symptoms = const [],
    this.suspectedComponent,
    this.repairType,
    this.extractedSkills = const [],
    this.aiSummary,
    this.fingerprintVersion = 1,
  });

  factory ProblemFingerprint.fromJson(Map<String, dynamic> json) {
    final sym = json['symptoms'] as List<dynamic>? ?? [];
    final skl = json['extracted_skills'] as List<dynamic>? ?? [];

    return ProblemFingerprint(
      id: json['id'] as String,
      problemId: json['problem_id'] as String,
      deviceType: json['device_type'] as String?,
      brand: json['brand'] as String?,
      model: json['model'] as String?,
      category: json['category'] as String?,
      issue: json['issue'] as String?,
      symptoms: sym.map((e) => e.toString()).toList(),
      suspectedComponent: json['suspected_component'] as String?,
      repairType: json['repair_type'] as String?,
      extractedSkills: skl.map((e) => e.toString()).toList(),
      aiSummary: json['ai_summary'] as String?,
      fingerprintVersion: json['fingerprint_version'] as int? ?? 1,
    );
  }
}

class CustomerProblem {
  final String id;
  final String customerId;
  final String title;
  final String description;
  final String? addressLine;
  final String? locality;
  final String? city;
  final String? state;
  final String? postalCode;
  final double latitude;
  final double longitude;
  final String status;
  final DateTime createdAt;
  final List<ProblemMedia> media;
  final ProblemFingerprint? fingerprint;

  CustomerProblem({
    required this.id,
    required this.customerId,
    required this.title,
    required this.description,
    this.addressLine,
    this.locality,
    this.city,
    this.state,
    this.postalCode,
    required this.latitude,
    required this.longitude,
    this.status = 'open',
    required this.createdAt,
    this.media = const [],
    this.fingerprint,
  });

  factory CustomerProblem.fromJson(Map<String, dynamic> json) {
    final mList = json['media'] as List<dynamic>? ?? [];
    final fpJson = json['fingerprint'] as Map<String, dynamic>?;

    return CustomerProblem(
      id: json['id'] as String,
      customerId: json['customer_id'] as String,
      title: json['title'] as String,
      description: json['description'] as String,
      addressLine: json['address_line'] as String?,
      locality: json['locality'] as String?,
      city: json['city'] as String?,
      state: json['state'] as String?,
      postalCode: json['postal_code'] as String?,
      latitude: (json['latitude'] as num?)?.toDouble() ?? 19.0760,
      longitude: (json['longitude'] as num?)?.toDouble() ?? 72.8777,
      status: json['status'] as String? ?? 'open',
      createdAt: DateTime.tryParse(json['created_at']?.toString() ?? '') ?? DateTime.now(),
      media: mList.map((e) => ProblemMedia.fromJson(e as Map<String, dynamic>)).toList(),
      fingerprint: fpJson != null ? ProblemFingerprint.fromJson(fpJson) : null,
    );
  }
}
