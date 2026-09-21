class MatchResultItem {
  final String? matchResultId;
  final String problemId;
  final String workerId;
  final int rankPosition;
  final double matchScore;
  final double problemSimilarity;
  final double contextSimilarity;
  final double verifiedExperienceConfidence;
  final double proximityScore;
  final List<String> explanations;
  final String workerName;
  final String? headline;
  final String? locality;
  final String? city;
  final double? hourlyRate;
  final double rating;
  final int totalReviews;
  final bool isAvailable;
  final int relevantSolvedCases;
  final List<String> skills;

  MatchResultItem({
    this.matchResultId,
    required this.problemId,
    required this.workerId,
    required this.rankPosition,
    required this.matchScore,
    required this.problemSimilarity,
    required this.contextSimilarity,
    required this.verifiedExperienceConfidence,
    required this.proximityScore,
    this.explanations = const [],
    required this.workerName,
    this.headline,
    this.locality,
    this.city,
    this.hourlyRate,
    this.rating = 5.0,
    this.totalReviews = 0,
    this.isAvailable = true,
    this.relevantSolvedCases = 0,
    this.skills = const [],
  });

  factory MatchResultItem.fromJson(Map<String, dynamic> json) {
    final expList = json['explanations'] as List<dynamic>? ?? [];
    final skList = json['skills'] as List<dynamic>? ?? [];

    return MatchResultItem(
      matchResultId: json['match_result_id'] as String?,
      problemId: json['problem_id'] as String,
      workerId: json['worker_id'] as String,
      rankPosition: json['rank_position'] as int? ?? 1,
      matchScore: (json['match_score'] as num?)?.toDouble() ?? 0.0,
      problemSimilarity: (json['problem_similarity'] as num?)?.toDouble() ?? 0.0,
      contextSimilarity: (json['context_similarity'] as num?)?.toDouble() ?? 0.0,
      verifiedExperienceConfidence: (json['verified_experience_confidence'] as num?)?.toDouble() ?? 0.0,
      proximityScore: (json['proximity_score'] as num?)?.toDouble() ?? 0.0,
      explanations: expList.map((e) => e.toString()).toList(),
      workerName: json['worker_name'] as String? ?? 'Technician',
      headline: json['headline'] as String?,
      locality: json['locality'] as String?,
      city: json['city'] as String?,
      hourlyRate: (json['hourly_rate'] as num?)?.toDouble(),
      rating: (json['rating'] as num?)?.toDouble() ?? 5.0,
      totalReviews: json['total_reviews'] as int? ?? 0,
      isAvailable: json['is_available'] as bool? ?? true,
      relevantSolvedCases: json['relevant_solved_cases'] as int? ?? 0,
      skills: skList.map((e) => e.toString()).toList(),
    );
  }

  String get matchScorePercentage => '${(matchScore * 100).toStringAsFixed(1)}%';
}
