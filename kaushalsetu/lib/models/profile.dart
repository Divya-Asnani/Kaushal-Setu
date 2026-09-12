class UserProfile {
  final String id;
  final String email;
  final String role; // customer, worker, admin
  final String fullName;
  final String? phone;
  final String? locality;
  final String? city;
  final String? avatarUrl;

  UserProfile({
    required this.id,
    required this.email,
    required this.role,
    required this.fullName,
    this.phone,
    this.locality,
    this.city,
    this.avatarUrl,
  });

  factory UserProfile.fromJson(Map<String, dynamic> json) {
    return UserProfile(
      id: json['id'] as String,
      email: json['email'] as String? ?? '',
      role: json['role'] as String? ?? 'customer',
      fullName: json['full_name'] as String? ?? json['display_name'] as String? ?? 'User',
      phone: json['phone'] as String?,
      locality: json['locality'] as String?,
      city: json['city'] as String?,
      avatarUrl: json['avatar_url'] as String?,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'email': email,
        'role': role,
        'full_name': fullName,
        'phone': phone,
        'locality': locality,
        'city': city,
        'avatar_url': avatarUrl,
      };

  bool get isCustomer => role == 'customer';
  bool get isWorker => role == 'worker';
  bool get isAdmin => role == 'admin';

  String get formattedLocation {
    final loc = locality?.trim();
    final c = city?.trim();
    if (loc != null && loc.isNotEmpty && c != null && c.isNotEmpty) {
      return '$loc, $c';
    }
    if (loc != null && loc.isNotEmpty) return loc;
    if (c != null && c.isNotEmpty) return c;
    return '';
  }
}

