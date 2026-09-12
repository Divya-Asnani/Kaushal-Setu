class ApiException implements Exception {
  final String code;
  final String message;
  final Map<String, dynamic> details;
  final String? requestId;
  final int statusCode;

  ApiException({
    required this.code,
    required this.message,
    this.details = const {},
    this.requestId,
    this.statusCode = 400,
  });

  factory ApiException.fromJson(Map<String, dynamic> json, int statusCode) {
    final error = json['error'] as Map<String, dynamic>?;
    if (error != null) {
      return ApiException(
        code: error['code'] as String? ?? 'UNKNOWN_ERROR',
        message: error['message'] as String? ?? 'An unexpected error occurred.',
        details: (error['details'] as Map<String, dynamic>?) ?? {},
        requestId: json['request_id'] as String?,
        statusCode: statusCode,
      );
    }
    return ApiException(
      code: 'SERVER_ERROR',
      message: json['detail']?.toString() ?? 'Server returned error status $statusCode',
      statusCode: statusCode,
    );
  }

  @override
  String toString() => '$code: $message';
}
