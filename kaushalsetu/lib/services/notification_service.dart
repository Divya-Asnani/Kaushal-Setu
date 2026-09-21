import 'package:kaushalsetu/core/api/api_client.dart';
import 'package:kaushalsetu/models/app_notification.dart';

class NotificationService {
  final ApiClient _api = ApiClient();

  Future<List<AppNotification>> listNotifications() async {
    final res = await _api.get('/notifications');
    if (res is List) {
      return res.map((e) => AppNotification.fromJson(e as Map<String, dynamic>)).toList();
    }
    return [];
  }

  Future<void> markAsRead(String id) async {
    await _api.patch('/notifications/$id/read');
  }
}
