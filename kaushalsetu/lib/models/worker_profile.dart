class WorkerSkill {
  final String id;
  final String skillId;
  final String skillName;
  final String category;
  final String proficiencyLevel;
  final bool verified;

  WorkerSkill({
    required this.id,
    required this.skillId,
    required this.skillName,
    required this.category,
    required this.proficiencyLevel,
    required this.verified,
  });

  factory WorkerSkill.fromJson(Map<String, dynamic> json) {
    return WorkerSkill(
      id: (json['id'] ?? json['skill_id'] ?? '').toString(),
      skillId: (json['skill_id'] ?? '').toString(),
      skillName: json['skill_name'] as String? ?? 'General Skill',
      category: json['category'] as String? ?? 'General',
      proficiencyLevel: json['proficiency_level'] as String? ?? 'intermediate',
      verified: json['verified'] as bool? ?? false,
    );
  }
}

class WorkerCertificate {
  final String id;
  final String title;
  final String issuingOrganization;
  final String? issueDate;
  final bool isVerified;

  WorkerCertificate({
    required this.id,
    required this.title,
    required this.issuingOrganization,
    this.issueDate,
    required this.isVerified,
  });

  factory WorkerCertificate.fromJson(Map<String, dynamic> json) {
    return WorkerCertificate(
      id: (json['id'] ?? '').toString(),
      title: json['title'] as String? ?? json['certificate_name'] as String? ?? 'Certification',
      issuingOrganization: json['issuing_organization'] as String? ?? 'Authorized Body',
      issueDate: json['issue_date'] as String?,
      isVerified: json['is_verified'] as bool? ?? (json['verification_status'] == 'verified'),
    );
  }
}

class WorkerProfile {
  final String id;
  final String userId;
  final String fullName;
  final String email;
  final String? phone;
  final String? headline;
  final String? bio;
  final int experienceYears;
  final double? hourlyRate;
  final double serviceRadiusKm;
  final String? locality;
  final String? city;
  final bool isAvailable;
  final bool isVerified;
  final double rating;
  final int totalReviews;
  final List<WorkerSkill> skills;
  final List<WorkerCertificate> certificates;

  WorkerProfile({
    required this.id,
    required this.userId,
    required this.fullName,
    required this.email,
    this.phone,
    this.headline,
    this.bio,
    this.experienceYears = 0,
    this.hourlyRate,
    this.serviceRadiusKm = 15.0,
    this.locality,
    this.city,
    this.isAvailable = true,
    this.isVerified = false,
    this.rating = 5.0,
    this.totalReviews = 0,
    this.skills = const [],
    this.certificates = const [],
  });

  factory WorkerProfile.fromJson(Map<String, dynamic> json) {
    final skillsRaw = json['skills'] as List<dynamic>? ?? [];
    final certsRaw = json['certificates'] as List<dynamic>? ?? [];

    return WorkerProfile(
      id: json['id'] as String,
      userId: json['user_id'] as String,
      fullName: json['full_name'] as String? ?? 'Technician',
      email: json['email'] as String? ?? '',
      phone: json['phone'] as String?,
      headline: json['headline'] as String?,
      bio: json['bio'] as String?,
      experienceYears: json['experience_years'] as int? ?? 0,
      hourlyRate: (json['hourly_rate'] as num?)?.toDouble(),
      serviceRadiusKm: (json['service_radius_km'] as num?)?.toDouble() ?? 15.0,
      locality: json['locality'] as String?,
      city: json['city'] as String?,
      isAvailable: json['is_available'] as bool? ?? true,
      isVerified: json['is_verified'] as bool? ?? false,
      rating: (json['rating'] as num?)?.toDouble() ?? 5.0,
      totalReviews: json['total_reviews'] as int? ?? 0,
      skills: skillsRaw.map((e) => WorkerSkill.fromJson(e as Map<String, dynamic>)).toList(),
      certificates: certsRaw.map((e) => WorkerCertificate.fromJson(e as Map<String, dynamic>)).toList(),
    );
  }
}
