class KnowledgeCaseMedia {
  final String id;
  final String storagePath;
  final String mediaType;
  final String? caption;

  KnowledgeCaseMedia({
    required this.id,
    required this.storagePath,
    this.mediaType = 'image',
    this.caption,
  });

  factory KnowledgeCaseMedia.fromJson(Map<String, dynamic> json) {
    return KnowledgeCaseMedia(
      id: json['id'] as String,
      storagePath: json['storage_path'] as String? ?? '',
      mediaType: json['media_type'] as String? ?? 'image',
      caption: json['caption'] as String?,
    );
  }
}

class KnowledgeCase {
  final String id;
  final String workerId;
  final String? workerName;
  final String? experienceId;
  final String title;
  final String problemSummary;
  final String diagnosis;
  final String solution;
  final String? lessonLearned;
  final String difficulty;
  final String? deviceCategory;
  final String? brand;
  final String? model;
  final bool isPublished;
  final bool isVerified;
  final int viewCount;
  final DateTime createdAt;
  final List<KnowledgeCaseMedia> media;

  KnowledgeCase({
    required this.id,
    required this.workerId,
    this.workerName,
    this.experienceId,
    required this.title,
    required this.problemSummary,
    required this.diagnosis,
    required this.solution,
    this.lessonLearned,
    this.difficulty = 'intermediate',
    this.deviceCategory,
    this.brand,
    this.model,
    this.isPublished = true,
    this.isVerified = false,
    this.viewCount = 0,
    required this.createdAt,
    this.media = const [],
  });

  factory KnowledgeCase.fromJson(Map<String, dynamic> json) {
    final mList = json['media'] as List<dynamic>? ?? [];
    return KnowledgeCase(
      id: json['id'] as String,
      workerId: json['worker_id'] as String,
      workerName: json['worker_name'] as String?,
      experienceId: json['experience_id'] as String?,
      title: json['title'] as String? ?? 'Knowledge Case',
      problemSummary: json['problem_summary'] as String? ?? '',
      diagnosis: json['diagnosis'] as String? ?? '',
      solution: json['solution'] as String? ?? '',
      lessonLearned: json['lesson_learned'] as String?,
      difficulty: json['difficulty'] as String? ?? 'intermediate',
      deviceCategory: json['device_category'] as String?,
      brand: json['brand'] as String?,
      model: json['model'] as String?,
      isPublished: json['is_published'] as bool? ?? true,
      isVerified: json['is_verified'] as bool? ?? false,
      viewCount: json['view_count'] as int? ?? 0,
      createdAt: DateTime.tryParse(json['created_at']?.toString() ?? '') ?? DateTime.now(),
      media: mList.map((e) => KnowledgeCaseMedia.fromJson(e as Map<String, dynamic>)).toList(),
    );
  }
}
