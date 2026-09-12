import 'package:flutter/material.dart';
import 'package:kaushalsetu/core/theme/app_theme.dart';
import 'package:kaushalsetu/models/service_request.dart';
import 'package:kaushalsetu/services/request_service.dart';
import 'package:kaushalsetu/widgets/status_badge.dart';
import 'package:kaushalsetu/widgets/loading_view.dart';
import 'package:kaushalsetu/widgets/error_view.dart';

class WorkerRequestsScreen extends StatefulWidget {
  const WorkerRequestsScreen({super.key});

  @override
  State<WorkerRequestsScreen> createState() => _WorkerRequestsScreenState();
}

class _WorkerRequestsScreenState extends State<WorkerRequestsScreen> {
  final RequestService _requestService = RequestService();

  bool _isLoading = true;
  String? _errorMessage;
  List<ServiceRequestModel> _requests = [];

  @override
  void initState() {
    super.initState();
    _loadRequests();
  }

  Future<void> _loadRequests() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });
    try {
      final reqs = await _requestService.listServiceRequests();
      _requests = reqs;
    } catch (e) {
      _errorMessage = e.toString();
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _handleResponse(ServiceRequestModel req, String status) async {
    final responseController = TextEditingController(
      text: status == 'accepted' ? 'I can inspect this issue today.' : 'Currently unavailable.',
    );

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) {
        return AlertDialog(
          title: Text(status == 'accepted' ? 'Accept Service Request' : 'Decline Request'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Problem: ${req.problemTitle ?? "Repair"}'),
              const SizedBox(height: 12),
              TextField(
                controller: responseController,
                decoration: const InputDecoration(labelText: 'Message for Customer'),
              ),
            ],
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
            ElevatedButton(
              onPressed: () => Navigator.pop(ctx, true),
              style: ElevatedButton.styleFrom(
                backgroundColor: status == 'accepted' ? const Color(0xFF059669) : Colors.red,
              ),
              child: Text(status == 'accepted' ? 'Confirm Acceptance' : 'Decline'),
            ),
          ],
        );
      },
    );

    if (confirmed == true) {
      try {
        await _requestService.respondToRequest(
          requestId: req.id,
          status: status,
          workerResponse: responseController.text.trim(),
        );
        _loadRequests();
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(status == 'accepted' ? 'Request accepted! Job created.' : 'Request declined.'),
              backgroundColor: status == 'accepted' ? Colors.green : Colors.grey,
            ),
          );
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Failed: $e'), backgroundColor: Colors.red),
          );
        }
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return Scaffold(
        appBar: AppBar(title: const Text('Incoming Requests')),
        body: const LoadingView(message: 'Loading your customer requests...'),
      );
    }

    if (_errorMessage != null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Incoming Requests')),
        body: ErrorView(title: 'Error loading requests', message: _errorMessage!, onRetry: _loadRequests),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Incoming Service Requests'),
        actions: [IconButton(icon: const Icon(Icons.refresh), onPressed: _loadRequests)],
      ),
      body: _requests.isEmpty
          ? const Center(
              child: Padding(
                padding: EdgeInsets.all(32),
                child: Text('No service requests currently assigned to you.', style: TextStyle(color: Colors.grey)),
              ),
            )
          : ListView.builder(
              padding: const EdgeInsets.symmetric(vertical: 12),
              itemCount: _requests.length,
              itemBuilder: (context, idx) {
                final req = _requests[idx];
                return Card(
                  margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Expanded(
                              child: Text(
                                req.problemTitle ?? 'Repair Request',
                                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16),
                              ),
                            ),
                            StatusBadge(status: req.status),
                          ],
                        ),
                        if (req.problemCategory != null && req.problemCategory!.isNotEmpty) ...[
                          const SizedBox(height: 4),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: const Color(0xFFF1F5F9),
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: Text(
                              req.problemCategory!,
                              style: const TextStyle(fontSize: 11, color: Color(0xFF475569), fontWeight: FontWeight.w600),
                            ),
                          ),
                        ],
                        if (req.problemDescription != null && req.problemDescription!.isNotEmpty) ...[
                          const SizedBox(height: 6),
                          Text(
                            req.problemDescription!,
                            style: const TextStyle(fontSize: 13, color: Color(0xFF475569)),
                          ),
                        ],
                        const SizedBox(height: 6),
                        Row(
                          children: [
                            const Icon(Icons.location_on_outlined, size: 14, color: Color(0xFF64748B)),
                            const SizedBox(width: 4),
                            Text(
                              req.locality != null && req.locality!.isNotEmpty ? req.locality! : "Permitted locality",
                              style: const TextStyle(fontSize: 12, color: Color(0xFF64748B)),
                            ),
                            const SizedBox(width: 12),
                            const Icon(Icons.access_time, size: 14, color: Color(0xFF64748B)),
                            const SizedBox(width: 4),
                            Text(
                              req.createdAt.toLocal().toString().substring(0, 16),
                              style: const TextStyle(fontSize: 11, color: Color(0xFF94A3B8)),
                            ),
                          ],
                        ),
                        if (req.customerMessage != null) ...[
                          const SizedBox(height: 8),
                          Container(
                            width: double.infinity,
                            padding: const EdgeInsets.all(10),
                            decoration: BoxDecoration(
                              color: const Color(0xFFF8FAFC),
                              borderRadius: BorderRadius.circular(8),
                              border: Border.all(color: AppTheme.borderSubtle),
                            ),
                            child: Text(
                              'Customer Message: "${req.customerMessage}"',
                              style: const TextStyle(fontSize: 12, color: Color(0xFF475569)),
                            ),
                          ),
                        ],
                        if (req.isPending) ...[
                          const SizedBox(height: 16),
                          Row(
                            children: [
                              Expanded(
                                child: ElevatedButton.icon(
                                  onPressed: () => _handleResponse(req, 'accepted'),
                                  icon: const Icon(Icons.check, size: 16),
                                  label: const Text('Accept & Create Job'),
                                  style: ElevatedButton.styleFrom(
                                    backgroundColor: const Color(0xFF059669),
                                  ),
                                ),
                              ),
                              const SizedBox(width: 10),
                              OutlinedButton.icon(
                                onPressed: () => _handleResponse(req, 'rejected'),
                                icon: const Icon(Icons.close, size: 16, color: Colors.red),
                                label: const Text('Decline', style: TextStyle(color: Colors.red)),
                                style: OutlinedButton.styleFrom(
                                  side: const BorderSide(color: Colors.red),
                                ),
                              ),
                            ],
                          ),
                        ] else if (req.workerResponse != null) ...[
                          const SizedBox(height: 10),
                          Text(
                            'Your reply: "${req.workerResponse}"',
                            style: const TextStyle(fontSize: 12, color: Color(0xFF64748B), fontStyle: FontStyle.italic),
                          ),
                        ],
                      ],
                    ),
                  ),
                );
              },
            ),
    );
  }
}
