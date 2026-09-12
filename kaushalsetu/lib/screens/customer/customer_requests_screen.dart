import 'package:flutter/material.dart';
import 'package:kaushalsetu/core/theme/app_theme.dart';
import 'package:kaushalsetu/models/service_request.dart';
import 'package:kaushalsetu/models/job.dart';
import 'package:kaushalsetu/services/request_service.dart';
import 'package:kaushalsetu/services/job_service.dart';
import 'package:kaushalsetu/widgets/status_badge.dart';
import 'package:kaushalsetu/widgets/loading_view.dart';
import 'package:kaushalsetu/screens/customer/customer_job_details_screen.dart';
import 'package:kaushalsetu/screens/customer/rate_technician_sheet.dart';

class CustomerRequestsScreen extends StatefulWidget {
  const CustomerRequestsScreen({super.key});

  @override
  State<CustomerRequestsScreen> createState() => _CustomerRequestsScreenState();
}

class _CustomerRequestsScreenState extends State<CustomerRequestsScreen> {
  final RequestService _requestService = RequestService();
  final JobService _jobService = JobService();

  bool _isLoading = true;
  List<ServiceRequestModel> _requests = [];
  List<JobModel> _jobs = [];

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() => _isLoading = true);
    try {
      final results = await Future.wait([
        _requestService.listServiceRequests(),
        _jobService.listJobs(),
      ]);
      _requests = results[0] as List<ServiceRequestModel>;
      _jobs = results[1] as List<JobModel>;
    } catch (_) {}
    if (mounted) setState(() => _isLoading = false);
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return Scaffold(
        appBar: AppBar(title: const Text('My Service Requests')),
        body: const LoadingView(message: 'Loading requests and ongoing jobs...'),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Requests & Active Jobs'),
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _loadData),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _loadData,
        child: ListView(
          padding: const EdgeInsets.symmetric(vertical: 12),
          children: [
            // Active Jobs Section
            if (_jobs.isNotEmpty) ...[
              const Padding(
                padding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                child: Text(
                  'Confirmed & In-Progress Jobs',
                  style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                    color: AppTheme.secondaryNavy,
                  ),
                ),
              ),
              ..._jobs.map((job) {
                return Card(
                  margin: const EdgeInsets.only(bottom: 12),
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
                                job.problemTitle ?? 'Repair Job',
                                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15),
                              ),
                            ),
                            StatusBadge(status: job.status),
                          ],
                        ),
                        const SizedBox(height: 6),
                        Text('Technician: ${job.workerName ?? "Specialist"}'),
                        if (job.workerPhone != null) Text('Phone: ${job.workerPhone}', style: const TextStyle(fontSize: 12, color: Color(0xFF64748B))),
                        const SizedBox(height: 10),
                        if (job.isCompleted) ...[
                          if (job.hasFeedback)
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                              decoration: BoxDecoration(
                                color: const Color(0xFFF0FDF4),
                                borderRadius: BorderRadius.circular(8),
                                border: Border.all(color: const Color(0xFFBBF7D0)),
                              ),
                              child: const Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(Icons.check_circle_rounded, color: Colors.green, size: 16),
                                  SizedBox(width: 6),
                                  Text(
                                    'Reviewed ✓',
                                    style: TextStyle(color: Color(0xFF166534), fontWeight: FontWeight.bold, fontSize: 12),
                                  ),
                                ],
                              ),
                            )
                          else
                            Row(
                              children: [
                                ElevatedButton.icon(
                                  onPressed: () => showRateTechnicianSheet(
                                    context: context,
                                    job: job,
                                    onSubmitted: _loadData,
                                  ),
                                  icon: const Icon(Icons.star_rounded, size: 16, color: Colors.amber),
                                  label: const Text('Rate Technician'),
                                  style: ElevatedButton.styleFrom(
                                    backgroundColor: AppTheme.secondaryNavy,
                                    foregroundColor: Colors.white,
                                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                                  ),
                                ),
                                const SizedBox(width: 10),
                                OutlinedButton(
                                  onPressed: () async {
                                    await Navigator.push(
                                      context,
                                      MaterialPageRoute(builder: (_) => CustomerJobDetailsScreen(jobId: job.id)),
                                    );
                                    _loadData();
                                  },
                                  child: const Text('Verify & Details', style: TextStyle(fontSize: 12)),
                                ),
                              ],
                            ),
                        ] else ...[
                          OutlinedButton.icon(
                            onPressed: () async {
                              await Navigator.push(
                                context,
                                MaterialPageRoute(builder: (_) => CustomerJobDetailsScreen(jobId: job.id)),
                              );
                              _loadData();
                            },
                            icon: const Icon(Icons.arrow_forward_rounded, size: 14),
                            label: const Text('View Job Timeline', style: TextStyle(fontSize: 12)),
                          ),
                        ],
                      ],
                    ),
                  ),
                );
              }),
              const SizedBox(height: 16),
            ],

            // Pending / Handled Service Requests
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              child: Text(
                'Service Requests',
                style: TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.secondaryNavy,
                ),
              ),
            ),
            if (_requests.isEmpty)
              const Center(
                child: Padding(
                  padding: EdgeInsets.all(32),
                  child: Text('No service requests found.', style: TextStyle(color: Colors.grey)),
                ),
              )
            else
              ..._requests.map((req) {
                final isPending = req.isPending;
                final isAccepted = req.isAccepted;
                final isRejected = req.isRejected;

                return Card(
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
                                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15),
                              ),
                            ),
                            StatusBadge(status: req.status),
                          ],
                        ),
                        const SizedBox(height: 6),
                        Text('Technician: ${req.workerName ?? "Specialist"}${req.locality != null && req.locality!.isNotEmpty ? " • ${req.locality}" : ""}'),

                        // Step progress indicator matching Section 7
                        Container(
                          margin: const EdgeInsets.symmetric(vertical: 10),
                          padding: const EdgeInsets.all(10),
                          decoration: BoxDecoration(
                            color: const Color(0xFFF8FAFC),
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: AppTheme.borderSubtle),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text('Request Status Tracking:', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: Color(0xFF64748B))),
                              const SizedBox(height: 6),
                              const Row(
                                children: [
                                  Icon(Icons.check_circle, size: 14, color: Colors.green),
                                  SizedBox(width: 6),
                                  Text('Request submitted', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                                ],
                              ),
                              const SizedBox(height: 4),
                              Row(
                                children: [
                                  if (isPending) ...[
                                    const Icon(Icons.radio_button_checked, size: 14, color: AppTheme.primaryAmber),
                                    const SizedBox(width: 6),
                                    const Text('Waiting for technician: Pending', style: TextStyle(fontSize: 12, color: AppTheme.primaryAmber, fontWeight: FontWeight.w600)),
                                  ] else if (isAccepted) ...[
                                    const Icon(Icons.check_circle, size: 14, color: Colors.green),
                                    const SizedBox(width: 6),
                                    const Text('Technician accepted: Accepted', style: TextStyle(fontSize: 12, color: Colors.green, fontWeight: FontWeight.w600)),
                                  ] else if (isRejected) ...[
                                    const Icon(Icons.cancel, size: 14, color: Colors.red),
                                    const SizedBox(width: 6),
                                    const Text('Technician declined: Rejected', style: TextStyle(fontSize: 12, color: Colors.red, fontWeight: FontWeight.w600)),
                                  ] else ...[
                                    const Icon(Icons.radio_button_off, size: 14, color: Colors.grey),
                                    const SizedBox(width: 6),
                                    Text('Status: ${req.status.toUpperCase()}', style: const TextStyle(fontSize: 12, color: Colors.grey)),
                                  ],
                                ],
                              ),
                            ],
                          ),
                        ),

                        if (req.customerMessage != null) ...[
                          Text(
                            'Your message: "${req.customerMessage}"',
                            style: const TextStyle(fontSize: 12, color: Color(0xFF64748B), fontStyle: FontStyle.italic),
                          ),
                          const SizedBox(height: 6),
                        ],
                        if (req.workerResponse != null) ...[
                          Text(
                            'Technician response: "${req.workerResponse}"',
                            style: const TextStyle(fontSize: 12, color: AppTheme.primaryAmber, fontWeight: FontWeight.w600),
                          ),
                          const SizedBox(height: 6),
                        ],
                        if (req.createdJobId != null) ...[
                          const SizedBox(height: 8),
                          ElevatedButton.icon(
                            onPressed: () async {
                              await Navigator.push(
                                context,
                                MaterialPageRoute(
                                  builder: (_) => CustomerJobDetailsScreen(jobId: req.createdJobId!),
                                ),
                              );
                              _loadData();
                            },
                            icon: const Icon(Icons.play_circle_outline, size: 16),
                            label: const Text('Open Job Timeline & Details'),
                          ),
                        ],
                      ],
                    ),
                  ),
                );
              }),
            const SizedBox(height: 40),
          ],
        ),
      ),
    );
  }
}
