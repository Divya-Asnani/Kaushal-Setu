import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:kaushalsetu/core/auth/auth_provider.dart';
import 'package:kaushalsetu/core/theme/app_theme.dart';
import 'package:kaushalsetu/models/worker_profile.dart';
import 'package:kaushalsetu/models/service_request.dart';
import 'package:kaushalsetu/models/job.dart';
import 'package:kaushalsetu/services/worker_service.dart';
import 'package:kaushalsetu/services/request_service.dart';
import 'package:kaushalsetu/services/job_service.dart';
import 'package:kaushalsetu/widgets/status_badge.dart';
import 'package:kaushalsetu/widgets/loading_view.dart';
import 'package:kaushalsetu/screens/worker/worker_requests_screen.dart';
import 'package:kaushalsetu/screens/worker/worker_job_completion_screen.dart';
import 'package:kaushalsetu/screens/worker/worker_profile_skills_screen.dart';
import 'package:kaushalsetu/screens/worker/knowledge_hub_screen.dart';
import 'package:kaushalsetu/screens/common/notifications_screen.dart';
import 'package:kaushalsetu/widgets/location_picker_sheet.dart';

class WorkerDashboardScreen extends StatefulWidget {
  const WorkerDashboardScreen({super.key});

  @override
  State<WorkerDashboardScreen> createState() => _WorkerDashboardScreenState();
}

class _WorkerDashboardScreenState extends State<WorkerDashboardScreen> {
  final WorkerService _workerService = WorkerService();
  final RequestService _requestService = RequestService();
  final JobService _jobService = JobService();

  bool _isLoading = true;
  WorkerProfile? _profile;
  List<ServiceRequestModel> _requests = [];
  List<JobModel> _jobs = [];
  final Set<String> _processingRequestIds = {};
  String _jobFilter = 'all'; // 'all', 'active', 'completed'

  @override
  void initState() {
    super.initState();
    _loadDashboardData();
  }

  Future<void> _loadDashboardData() async {
    setState(() => _isLoading = true);
    try {
      final results = await Future.wait([
        _workerService.getMyProfile(),
        _requestService.listServiceRequests(),
        _jobService.listJobs(),
      ]);
      _profile = results[0] as WorkerProfile;
      _requests = results[1] as List<ServiceRequestModel>;
      _jobs = results[2] as List<JobModel>;
    } catch (_) {}
    if (mounted) setState(() => _isLoading = false);
  }

  Future<void> _handleRequestResponse(ServiceRequestModel req, String status) async {
    final responseController = TextEditingController(
      text: status == 'accepted' ? 'I can take this request.' : 'Currently unavailable.',
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
              Text('Problem: ${req.problemTitle ?? "Repair Request"}', style: const TextStyle(fontWeight: FontWeight.bold)),
              if (req.customerMessage != null && req.customerMessage!.isNotEmpty) ...[
                const SizedBox(height: 6),
                Text('Customer Note: "${req.customerMessage}"', style: const TextStyle(fontSize: 12, color: Color(0xFF64748B))),
              ],
              const SizedBox(height: 12),
              TextField(
                controller: responseController,
                decoration: InputDecoration(
                  labelText: status == 'accepted' ? 'Confirmation Note' : 'Decline Reason',
                ),
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
              child: Text(status == 'accepted' ? 'Accept Request' : 'Reject'),
            ),
          ],
        );
      },
    );

    if (confirmed == true) {
      setState(() => _processingRequestIds.add(req.id));
      try {
        await _requestService.respondToRequest(
          requestId: req.id,
          status: status,
          workerResponse: responseController.text.trim(),
        );
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(status == 'accepted' ? 'Service request accepted! Job created.' : 'Service request declined.'),
              backgroundColor: status == 'accepted' ? Colors.green : Colors.grey,
            ),
          );
        }
        await _loadDashboardData();
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Action failed: $e'), backgroundColor: Colors.red),
          );
        }
      } finally {
        if (mounted) setState(() => _processingRequestIds.remove(req.id));
      }
    }
  }

  Future<void> _toggleAvailability(bool value) async {
    try {
      final updated = await _workerService.updateAvailability(value);
      setState(() => _profile = updated);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(value ? 'You are now marked Available for jobs.' : 'You are now marked Offline.'),
            backgroundColor: value ? Colors.green : Colors.grey,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to update availability: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();

    if (_isLoading) {
      return Scaffold(
        appBar: AppBar(title: const Text('Technician Dashboard')),
        body: const LoadingView(message: 'Loading technician profile and active jobs...'),
      );
    }

    final p = _profile;
    final pendingRequests = _requests.where((r) => r.isPending).toList();
    final activeJobs = _jobs.where((j) => j.isConfirmed || j.isInProgress).toList();
    final completedJobs = _jobs.where((j) => j.isCompleted).toList();
    final filteredJobs = _jobFilter == 'active'
        ? activeJobs
        : (_jobFilter == 'completed' ? completedJobs : _jobs);

    return Scaffold(
      appBar: AppBar(
        title: const Row(
          children: [
            Icon(Icons.build_circle_rounded, color: AppTheme.primaryAmber, size: 22),
            SizedBox(width: 8),
            Text('Technician Dashboard'),
          ],
        ),
        actions: [
          TextButton.icon(
            icon: const Icon(Icons.person_pin_rounded, size: 16, color: AppTheme.secondaryNavy),
            label: const Text('Customer Mode', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AppTheme.secondaryNavy)),
            style: TextButton.styleFrom(
              backgroundColor: const Color(0xFFF1F5F9),
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
            ),
            onPressed: () => auth.switchMode('customer'),
          ),
          const SizedBox(width: 4),
          IconButton(
            icon: const Icon(Icons.notifications_none_rounded),
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const NotificationsScreen()),
              );
            },
          ),
          IconButton(
            icon: const Icon(Icons.logout_rounded),
            onPressed: () => auth.logout(),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _loadDashboardData,
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Technician Profile Card + Availability Toggle
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          CircleAvatar(
                            radius: 26,
                            backgroundColor: AppTheme.primaryAmber.withValues(alpha: 0.15),
                            child: const Icon(Icons.person, color: AppTheme.primaryAmber, size: 32),
                          ),
                          const SizedBox(width: 14),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    Text(
                                      p?.fullName ?? auth.userProfile?.fullName ?? 'Technician',
                                      style: const TextStyle(
                                        fontSize: 17,
                                        fontWeight: FontWeight.w800,
                                        color: AppTheme.secondaryNavy,
                                      ),
                                    ),
                                    if (p?.isVerified == true) ...[
                                      const SizedBox(width: 6),
                                      const Icon(Icons.verified, color: Colors.blue, size: 16),
                                    ],
                                  ],
                                ),
                                if (p?.headline != null)
                                  Text(
                                    p!.headline!,
                                    style: const TextStyle(fontSize: 12, color: Color(0xFF64748B)),
                                  ),
                                const SizedBox(height: 4),
                                Row(
                                  children: [
                                    const Icon(Icons.star, size: 15, color: Colors.amber),
                                    const SizedBox(width: 4),
                                    Text(
                                      (p?.rating ?? 5.0).toStringAsFixed(1),
                                      style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
                                    ),
                                    Text(
                                      ' (${p?.totalReviews ?? 0} reviews)',
                                      style: const TextStyle(fontSize: 12, color: Colors.grey),
                                    ),
                                    const SizedBox(width: 8),
                                    const Text('•', style: TextStyle(color: Colors.grey)),
                                    const SizedBox(width: 8),
                                    Text(
                                      '${p?.experienceYears ?? 0} yrs exp',
                                      style: const TextStyle(fontSize: 12, color: Color(0xFF64748B)),
                                    ),
                                  ],
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                        decoration: BoxDecoration(
                          color: const Color(0xFFF8FAFC),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: const Color(0xFFE2E8F0)),
                        ),
                        child: Row(
                          children: [
                            const Icon(Icons.location_on, size: 16, color: AppTheme.primaryAmber),
                            const SizedBox(width: 6),
                            Expanded(
                              child: Text(
                                (auth.userProfile?.formattedLocation.isNotEmpty == true)
                                    ? auth.userProfile!.formattedLocation
                                    : (p?.city != null ? '${p?.locality ?? ""}, ${p?.city}' : 'Location Not Set'),
                                style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppTheme.secondaryNavy),
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                            InkWell(
                              onTap: () async {
                                final updated = await showChangeLocationSheet(context);
                                if (updated == true) {
                                  _loadDashboardData();
                                }
                              },
                              child: const Padding(
                                padding: EdgeInsets.symmetric(horizontal: 4, vertical: 2),
                                child: Text(
                                  'Change Location',
                                  style: TextStyle(
                                    fontSize: 12,
                                    fontWeight: FontWeight.bold,
                                    color: AppTheme.primaryAmber,
                                  ),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                      if (p != null) ...[
                        const SizedBox(height: 12),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(
                              'Technical Skills (${p.skills.length})',
                              style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AppTheme.secondaryNavy),
                            ),
                            InkWell(
                              onTap: () async {
                                await Navigator.push(
                                  context,
                                  MaterialPageRoute(builder: (_) => WorkerProfileSkillsScreen(profile: p)),
                                );
                                _loadDashboardData();
                              },
                              child: const Text(
                                '+ Add / Edit Skills',
                                style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: AppTheme.primaryAmber),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 6),
                        if (p.skills.isEmpty)
                          InkWell(
                            onTap: () async {
                              await Navigator.push(
                                context,
                                MaterialPageRoute(builder: (_) => WorkerProfileSkillsScreen(profile: p)),
                              );
                              _loadDashboardData();
                            },
                            child: Container(
                              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                              decoration: BoxDecoration(
                                color: const Color(0xFFFEF3C7),
                                borderRadius: BorderRadius.circular(6),
                              ),
                              child: const Row(
                                children: [
                                  Icon(Icons.add_circle_outline, size: 14, color: Color(0xFFB45309)),
                                  SizedBox(width: 6),
                                  Text(
                                    'No skills listed yet. Tap to add your technical skills.',
                                    style: TextStyle(fontSize: 11, color: Color(0xFFB45309), fontWeight: FontWeight.w500),
                                  ),
                                ],
                              ),
                            ),
                          )
                        else
                          Wrap(
                            spacing: 6,
                            runSpacing: 6,
                            children: p.skills.map((s) {
                              return Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                decoration: BoxDecoration(
                                  color: const Color(0xFFEFF6FF),
                                  borderRadius: BorderRadius.circular(6),
                                  border: Border.all(color: const Color(0xFFBFDBFE)),
                                ),
                                child: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Text(
                                      s.skillName,
                                      style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: Color(0xFF1D4ED8)),
                                    ),
                                    const SizedBox(width: 4),
                                    Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
                                      decoration: BoxDecoration(
                                        color: const Color(0xFFDBEAFE),
                                        borderRadius: BorderRadius.circular(4),
                                      ),
                                      child: Text(
                                        s.proficiencyLevel.toUpperCase(),
                                        style: const TextStyle(fontSize: 8, fontWeight: FontWeight.w700, color: Color(0xFF1E40AF)),
                                      ),
                                    ),
                                  ],
                                ),
                              );
                            }).toList(),
                          ),
                        if (p.certificates.isNotEmpty) ...[
                          const SizedBox(height: 10),
                          Wrap(
                            spacing: 6,
                            runSpacing: 4,
                            children: p.certificates.map((c) {
                              return Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                decoration: BoxDecoration(
                                  color: const Color(0xFFF0FDF4),
                                  borderRadius: BorderRadius.circular(6),
                                  border: Border.all(color: const Color(0xFFBBF7D0)),
                                ),
                                child: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    const Icon(Icons.workspace_premium, size: 13, color: Color(0xFF15803D)),
                                    const SizedBox(width: 4),
                                    Text(
                                      c.title,
                                      style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: Color(0xFF15803D)),
                                    ),
                                  ],
                                ),
                              );
                            }).toList(),
                          ),
                        ],
                      ],
                      const Divider(height: 24),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Row(
                            children: [
                              Container(
                                width: 10,
                                height: 10,
                                decoration: BoxDecoration(
                                  color: (p?.isAvailable ?? true) ? Colors.green : Colors.grey,
                                  shape: BoxShape.circle,
                                ),
                              ),
                              const SizedBox(width: 8),
                              Text(
                                (p?.isAvailable ?? true) ? 'Available for New Jobs' : 'Marked Offline',
                                style: TextStyle(
                                  fontWeight: FontWeight.w600,
                                  fontSize: 13,
                                  color: (p?.isAvailable ?? true) ? Colors.green : Colors.grey,
                                ),
                              ),
                            ],
                          ),
                          Switch(
                            value: p?.isAvailable ?? true,
                            activeThumbColor: AppTheme.primaryAmber,
                            onChanged: _toggleAvailability,
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),

              // Quick Access Grid: Incoming Requests, Skills & Certifications, Knowledge Hub
              Row(
                children: [
                  Expanded(
                    child: InkWell(
                      onTap: () async {
                        await Navigator.push(
                          context,
                          MaterialPageRoute(builder: (_) => const WorkerRequestsScreen()),
                        );
                        _loadDashboardData();
                      },
                      borderRadius: BorderRadius.circular(14),
                      child: Container(
                        padding: const EdgeInsets.all(14),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(color: AppTheme.borderSubtle),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                const Icon(Icons.inbox_outlined, color: AppTheme.primaryAmber),
                                if (pendingRequests.isNotEmpty)
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                                    decoration: BoxDecoration(
                                      color: Colors.red,
                                      borderRadius: BorderRadius.circular(10),
                                    ),
                                    child: Text(
                                      '${pendingRequests.length} NEW',
                                      style: const TextStyle(color: Colors.white, fontSize: 9, fontWeight: FontWeight.bold),
                                    ),
                                  ),
                              ],
                            ),
                            const SizedBox(height: 8),
                            const Text(
                              'Requests',
                              style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13),
                            ),
                            Text(
                              '${_requests.length} total',
                              style: const TextStyle(fontSize: 11, color: Color(0xFF64748B)),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: InkWell(
                      onTap: () async {
                        if (_profile != null) {
                          await Navigator.push(
                            context,
                            MaterialPageRoute(builder: (_) => WorkerProfileSkillsScreen(profile: _profile!)),
                          );
                          _loadDashboardData();
                        }
                      },
                      borderRadius: BorderRadius.circular(14),
                      child: Container(
                        padding: const EdgeInsets.all(14),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(color: AppTheme.borderSubtle),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Icon(Icons.verified_outlined, color: Color(0xFF2563EB)),
                            const SizedBox(height: 8),
                            const Text(
                              'Skills & Certs',
                              style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13),
                            ),
                            Text(
                              '${p?.skills.length ?? 0} skills, ${p?.certificates.length ?? 0} certs',
                              style: const TextStyle(fontSize: 11, color: Color(0xFF64748B)),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: InkWell(
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(builder: (_) => const KnowledgeHubScreen()),
                        );
                      },
                      borderRadius: BorderRadius.circular(14),
                      child: Container(
                        padding: const EdgeInsets.all(14),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(color: AppTheme.borderSubtle),
                        ),
                        child: const Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Icon(Icons.menu_book_outlined, color: AppTheme.accentIndigo),
                            SizedBox(height: 8),
                            Text(
                              'Knowledge',
                              style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13),
                            ),
                            Text(
                              'Search cases',
                              style: TextStyle(fontSize: 11, color: Color(0xFF64748B)),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 20),

              // Incoming Requests Section (Section 4)
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      const Text(
                        'Incoming Requests',
                        style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: AppTheme.secondaryNavy),
                      ),
                      if (pendingRequests.isNotEmpty) ...[
                        const SizedBox(width: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                          decoration: BoxDecoration(
                            color: Colors.red,
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: Text(
                            '${pendingRequests.length} PENDING',
                            style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold),
                          ),
                        ),
                      ],
                    ],
                  ),
                  TextButton(
                    onPressed: () async {
                      await Navigator.push(
                        context,
                        MaterialPageRoute(builder: (_) => const WorkerRequestsScreen()),
                      );
                      _loadDashboardData();
                    },
                    child: const Text('View All'),
                  ),
                ],
              ),
              const SizedBox(height: 8),

              if (pendingRequests.isEmpty)
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(16),
                  margin: const EdgeInsets.only(bottom: 12),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: AppTheme.borderSubtle),
                  ),
                  child: const Center(
                    child: Text(
                      'No pending requests. Newly assigned customer requests will appear here.',
                      style: TextStyle(color: Color(0xFF94A3B8), fontSize: 13),
                    ),
                  ),
                )
              else
                ...pendingRequests.map((req) {
                  final isProcessing = _processingRequestIds.contains(req.id);
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
                                  req.problemTitle ?? 'Repair Request',
                                  style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15),
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
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
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
                          if (req.customerMessage != null && req.customerMessage!.isNotEmpty) ...[
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
                                'Customer Note: "${req.customerMessage}"',
                                style: const TextStyle(fontSize: 12, color: Color(0xFF334155), fontStyle: FontStyle.italic),
                              ),
                            ),
                          ],
                          const SizedBox(height: 14),
                          if (isProcessing)
                            const Center(
                              child: Padding(
                                padding: EdgeInsets.symmetric(vertical: 8),
                                child: SizedBox(
                                  height: 20,
                                  width: 20,
                                  child: CircularProgressIndicator(strokeWidth: 2),
                                ),
                              ),
                            )
                          else
                            Row(
                              children: [
                                Expanded(
                                  child: ElevatedButton.icon(
                                    onPressed: () => _handleRequestResponse(req, 'accepted'),
                                    icon: const Icon(Icons.check, size: 16),
                                    label: const Text('Accept Request'),
                                    style: ElevatedButton.styleFrom(
                                      backgroundColor: const Color(0xFF059669),
                                      foregroundColor: Colors.white,
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 10),
                                OutlinedButton.icon(
                                  onPressed: () => _handleRequestResponse(req, 'rejected'),
                                  icon: const Icon(Icons.close, size: 16, color: Colors.red),
                                  label: const Text('Reject', style: TextStyle(color: Colors.red)),
                                  style: OutlinedButton.styleFrom(
                                    side: const BorderSide(color: Colors.red),
                                  ),
                                ),
                              ],
                            ),
                        ],
                      ),
                    ),
                  );
                }),
              const SizedBox(height: 16),

              // Active & Ongoing Jobs Section
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      const Text(
                        'Active Engagements',
                        style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: AppTheme.secondaryNavy),
                      ),
                      if (activeJobs.isNotEmpty) ...[
                        const SizedBox(width: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                          decoration: BoxDecoration(
                            color: AppTheme.primaryAmber,
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: Text(
                            '${activeJobs.length} ONGOING',
                            style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold),
                          ),
                        ),
                      ] else if (_jobs.isNotEmpty) ...[
                        const SizedBox(width: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                          decoration: BoxDecoration(
                            color: const Color(0xFFE2E8F0),
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: Text(
                            '${_jobs.length} TOTAL',
                            style: const TextStyle(color: Color(0xFF475569), fontSize: 10, fontWeight: FontWeight.bold),
                          ),
                        ),
                      ],
                    ],
                  ),
                  IconButton(
                    icon: const Icon(Icons.refresh, size: 20, color: Color(0xFF64748B)),
                    tooltip: 'Refresh Jobs',
                    onPressed: _loadDashboardData,
                  ),
                ],
              ),
              if (_jobs.isNotEmpty) ...[
                const SizedBox(height: 6),
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: [
                      _buildJobFilterChip('all', 'All (${_jobs.length})'),
                      const SizedBox(width: 8),
                      _buildJobFilterChip('active', 'Active (${activeJobs.length})'),
                      const SizedBox(width: 8),
                      _buildJobFilterChip('completed', 'Completed (${completedJobs.length})'),
                    ],
                  ),
                ),
              ],
              const SizedBox(height: 10),

              if (filteredJobs.isEmpty)
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 28),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: AppTheme.borderSubtle),
                  ),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Container(
                        width: 56,
                        height: 56,
                        decoration: BoxDecoration(
                          color: AppTheme.primaryAmber.withValues(alpha: 0.12),
                          shape: BoxShape.circle,
                        ),
                        child: const Icon(Icons.handyman_outlined, color: AppTheme.primaryAmber, size: 28),
                      ),
                      const SizedBox(height: 12),
                      Text(
                        _jobs.isEmpty
                            ? 'No Active Engagements'
                            : 'No ${_jobFilter == "active" ? "Active" : "Completed"} Jobs',
                        style: const TextStyle(
                          fontSize: 15,
                          fontWeight: FontWeight.w700,
                          color: AppTheme.secondaryNavy,
                        ),
                      ),
                      const SizedBox(height: 6),
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 16),
                        child: Text(
                          _jobs.isEmpty
                              ? 'No active repair jobs right now. Accept incoming customer requests to start diagnostic repairs and record verified outcomes.'
                              : 'You have no repair jobs categorized under this filter.',
                          style: const TextStyle(color: Color(0xFF64748B), fontSize: 13, height: 1.4),
                          textAlign: TextAlign.center,
                        ),
                      ),
                      if (_jobs.isEmpty && pendingRequests.isNotEmpty) ...[
                        const SizedBox(height: 16),
                        ElevatedButton.icon(
                          onPressed: () async {
                            await Navigator.push(
                              context,
                              MaterialPageRoute(builder: (_) => const WorkerRequestsScreen()),
                            );
                            _loadDashboardData();
                          },
                          icon: const Icon(Icons.inbox_outlined, size: 16),
                          label: Text('Review ${pendingRequests.length} Pending Request${pendingRequests.length > 1 ? "s" : ""}'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppTheme.primaryAmber,
                            foregroundColor: AppTheme.secondaryNavy,
                            elevation: 0,
                            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                          ),
                        ),
                      ],
                    ],
                  ),
                )
              else
                ...filteredJobs.map((job) => _buildJobCard(job)),
              const SizedBox(height: 40),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildJobFilterChip(String key, String label) {
    final isSelected = _jobFilter == key;
    return ChoiceChip(
      label: Text(label),
      selected: isSelected,
      onSelected: (_) => setState(() => _jobFilter = key),
      selectedColor: AppTheme.primaryAmber.withValues(alpha: 0.2),
      backgroundColor: const Color(0xFFF1F5F9),
      labelStyle: TextStyle(
        fontSize: 12,
        fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
        color: isSelected ? AppTheme.secondaryNavy : const Color(0xFF64748B),
      ),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(20),
        side: BorderSide(
          color: isSelected ? AppTheme.primaryAmber : Colors.transparent,
        ),
      ),
      showCheckmark: false,
      visualDensity: VisualDensity.compact,
    );
  }

  Widget _buildProgressStep({
    required int step,
    required String label,
    required bool isActive,
    required bool isDone,
  }) {
    final color = isDone
        ? Colors.green
        : (isActive ? AppTheme.primaryAmber : const Color(0xFF94A3B8));

    return Column(
      children: [
        Container(
          width: 22,
          height: 22,
          decoration: BoxDecoration(
            color: isDone
                ? Colors.green
                : (isActive ? AppTheme.primaryAmber : const Color(0xFFF1F5F9)),
            shape: BoxShape.circle,
            border: Border.all(color: color, width: 1.5),
          ),
          child: Center(
            child: isDone
                ? const Icon(Icons.check, size: 13, color: Colors.white)
                : Text(
                    '$step',
                    style: TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.bold,
                      color: isActive ? Colors.white : const Color(0xFF94A3B8),
                    ),
                  ),
          ),
        ),
        const SizedBox(height: 3),
        Text(
          label,
          style: TextStyle(
            fontSize: 10,
            fontWeight: isActive || isDone ? FontWeight.w700 : FontWeight.w500,
            color: color,
          ),
        ),
      ],
    );
  }

  Widget _buildJobCard(JobModel job) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
        side: const BorderSide(color: AppTheme.borderSubtle),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          color: AppTheme.primaryAmber.withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: const Icon(Icons.build_rounded, size: 18, color: AppTheme.primaryAmber),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              job.problemTitle ?? 'Repair Job',
                              style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15, color: AppTheme.secondaryNavy),
                            ),
                            Text(
                              'Started ${job.createdAt.toLocal().toString().substring(0, 10)}',
                              style: const TextStyle(fontSize: 11, color: Color(0xFF94A3B8)),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                StatusBadge(status: job.status),
              ],
            ),
            const SizedBox(height: 12),

            // Customer Info Box
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              decoration: BoxDecoration(
                color: const Color(0xFFF8FAFC),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: const Color(0xFFE2E8F0)),
              ),
              child: Column(
                children: [
                  Row(
                    children: [
                      const Icon(Icons.person_outline, size: 15, color: Color(0xFF64748B)),
                      const SizedBox(width: 6),
                      Text(
                        job.customerName ?? 'Customer',
                        style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 12, color: AppTheme.secondaryNavy),
                      ),
                      const Spacer(),
                      const Icon(Icons.phone_outlined, size: 14, color: Color(0xFF64748B)),
                      const SizedBox(width: 4),
                      Text(
                        job.customerPhone ?? 'N/A',
                        style: const TextStyle(fontSize: 12, color: Color(0xFF475569)),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Row(
                    children: [
                      const Icon(Icons.location_on_outlined, size: 15, color: Color(0xFF64748B)),
                      const SizedBox(width: 6),
                      Expanded(
                        child: Text(
                          job.locality != null && job.locality!.isNotEmpty ? job.locality! : 'Location not specified',
                          style: const TextStyle(fontSize: 12, color: Color(0xFF64748B)),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),

            if (job.problemDescription != null && job.problemDescription!.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text(
                job.problemDescription!,
                style: const TextStyle(fontSize: 12, color: Color(0xFF64748B)),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ],

            const SizedBox(height: 12),

            // Step timeline representation
            Row(
              children: [
                _buildProgressStep(
                  step: 1,
                  label: 'Confirmed',
                  isActive: true,
                  isDone: job.isInProgress || job.isCompleted,
                ),
                Expanded(
                  child: Container(
                    height: 2,
                    color: (job.isInProgress || job.isCompleted) ? Colors.green : const Color(0xFFCBD5E1),
                  ),
                ),
                _buildProgressStep(
                  step: 2,
                  label: 'Repairing',
                  isActive: job.isInProgress,
                  isDone: job.isCompleted,
                ),
                Expanded(
                  child: Container(
                    height: 2,
                    color: job.isCompleted ? Colors.green : const Color(0xFFCBD5E1),
                  ),
                ),
                _buildProgressStep(
                  step: 3,
                  label: 'Verified',
                  isActive: job.isCompleted,
                  isDone: job.isVerified,
                ),
              ],
            ),

            const SizedBox(height: 14),

            // Lifecycle buttons
            if (job.isConfirmed) ...[
              Row(
                children: [
                  Expanded(
                    child: ElevatedButton.icon(
                      onPressed: () async {
                        await _jobService.updateJobStatus(
                          job.id,
                          'in_progress',
                          notes: 'Technician started on-site diagnostic investigation.',
                        );
                        _loadDashboardData();
                      },
                      icon: const Icon(Icons.play_arrow_rounded, size: 16),
                      label: const Text('Start Diagnostic / Repair'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppTheme.primaryAmber,
                        foregroundColor: AppTheme.secondaryNavy,
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  OutlinedButton(
                    onPressed: () => _showJobDetails(job),
                    child: const Text('Details'),
                  ),
                ],
              ),
            ] else if (job.isInProgress) ...[
              Row(
                children: [
                  Expanded(
                    child: ElevatedButton.icon(
                      onPressed: () async {
                        final completed = await Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => WorkerJobCompletionScreen(job: job),
                          ),
                        );
                        if (completed == true) _loadDashboardData();
                      },
                      icon: const Icon(Icons.check_circle_outline, size: 16),
                      label: const Text('Submit Completion'),
                      style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF059669)),
                    ),
                  ),
                  const SizedBox(width: 8),
                  OutlinedButton(
                    onPressed: () => _showJobDetails(job),
                    child: const Text('Details'),
                  ),
                ],
              ),
            ] else if (job.isCompleted) ...[
              Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                margin: const EdgeInsets.only(bottom: 8),
                decoration: BoxDecoration(
                  color: Colors.green.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.verified, color: Colors.green, size: 16),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text(
                        job.isVerified
                            ? 'Verified & recorded in Experience Vault'
                            : 'Completed • Awaiting customer verification',
                        style: const TextStyle(color: Colors.green, fontSize: 12, fontWeight: FontWeight.bold),
                      ),
                    ),
                  ],
                ),
              ),
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  onPressed: () => _showJobDetails(job),
                  icon: const Icon(Icons.receipt_long_outlined, size: 16),
                  label: const Text('View Job Summary & Evidence'),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  void _showJobDetails(JobModel job) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) {
        return Container(
          decoration: const BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
          ),
          padding: EdgeInsets.only(
            left: 20,
            right: 20,
            top: 20,
            bottom: MediaQuery.of(ctx).viewInsets.bottom + 24,
          ),
          constraints: BoxConstraints(
            maxHeight: MediaQuery.of(context).size.height * 0.85,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  margin: const EdgeInsets.only(bottom: 16),
                  decoration: BoxDecoration(
                    color: Colors.grey.shade300,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Text(
                      job.problemTitle ?? 'Repair Job Details',
                      style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: AppTheme.secondaryNavy),
                    ),
                  ),
                  StatusBadge(status: job.status),
                ],
              ),
              const SizedBox(height: 12),
              Expanded(
                child: ListView(
                  children: [
                    // Customer info card
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: const Color(0xFFF8FAFC),
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(color: AppTheme.borderSubtle),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              const Icon(Icons.person_outline, size: 16, color: Color(0xFF64748B)),
                              const SizedBox(width: 8),
                              Text('Customer: ${job.customerName ?? "Customer"}', style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                            ],
                          ),
                          const SizedBox(height: 6),
                          Row(
                            children: [
                              const Icon(Icons.phone_outlined, size: 16, color: Color(0xFF64748B)),
                              const SizedBox(width: 8),
                              Text('Phone: ${job.customerPhone ?? "Not provided"}', style: const TextStyle(fontSize: 13)),
                            ],
                          ),
                          const SizedBox(height: 6),
                          Row(
                            children: [
                              const Icon(Icons.location_on_outlined, size: 16, color: Color(0xFF64748B)),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text('Location: ${job.locality ?? "Not specified"}', style: const TextStyle(fontSize: 13)),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 16),

                    // Problem description
                    if (job.problemDescription != null && job.problemDescription!.isNotEmpty) ...[
                      const Text('Problem Description', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13, color: AppTheme.secondaryNavy)),
                      const SizedBox(height: 6),
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: AppTheme.borderSubtle),
                        ),
                        child: Text(job.problemDescription!, style: const TextStyle(fontSize: 13, color: Color(0xFF334155))),
                      ),
                      const SizedBox(height: 16),
                    ],

                    // Diagnosis if present
                    if (job.diagnosis != null && job.diagnosis!.isNotEmpty) ...[
                      const Text('Technician Diagnosis', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13, color: AppTheme.secondaryNavy)),
                      const SizedBox(height: 6),
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: const Color(0xFFEFF6FF),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: const Color(0xFFBFDBFE)),
                        ),
                        child: Text(job.diagnosis!, style: const TextStyle(fontSize: 13, color: Color(0xFF1E3A8A))),
                      ),
                      const SizedBox(height: 16),
                    ],

                    // Repair Actions if present
                    if (job.actions.isNotEmpty) ...[
                      Text('Repair Actions (${job.actions.length})', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13, color: AppTheme.secondaryNavy)),
                      const SizedBox(height: 6),
                      ...job.actions.map((act) => Container(
                        margin: const EdgeInsets.only(bottom: 8),
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: const Color(0xFFF8FAFC),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: AppTheme.borderSubtle),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                  decoration: BoxDecoration(
                                    color: AppTheme.primaryAmber.withValues(alpha: 0.2),
                                    borderRadius: BorderRadius.circular(4),
                                  ),
                                  child: Text('Step ${act.stepNumber} • ${act.actionType}', style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: AppTheme.secondaryNavy)),
                                ),
                              ],
                            ),
                            const SizedBox(height: 4),
                            Text(act.actionDescription, style: const TextStyle(fontSize: 12)),
                            if (act.toolsUsed.isNotEmpty) ...[
                              const SizedBox(height: 4),
                              Text('Tools: ${act.toolsUsed.join(", ")}', style: const TextStyle(fontSize: 11, color: Color(0xFF64748B))),
                            ],
                          ],
                        ),
                      )),
                      const SizedBox(height: 16),
                    ],

                    // Outcomes if present
                    if (job.outcomes.isNotEmpty) ...[
                      Text('Outcomes & Learnings (${job.outcomes.length})', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13, color: AppTheme.secondaryNavy)),
                      const SizedBox(height: 6),
                      ...job.outcomes.map((out) => Container(
                        margin: const EdgeInsets.only(bottom: 8),
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: const Color(0xFFF0FDF4),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: const Color(0xFFBBF7D0)),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(out.outcomeDescription, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Color(0xFF166534))),
                            if (out.lessonsLearned != null && out.lessonsLearned!.isNotEmpty) ...[
                              const SizedBox(height: 4),
                              Text('Lesson: ${out.lessonsLearned!}', style: const TextStyle(fontSize: 11, color: Color(0xFF15803D), fontStyle: FontStyle.italic)),
                            ],
                          ],
                        ),
                      )),
                      const SizedBox(height: 16),
                    ],

                    // Evidence items
                    if (job.evidence.isNotEmpty) ...[
                      Text('Submitted Evidence (${job.evidence.length})', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13, color: AppTheme.secondaryNavy)),
                      const SizedBox(height: 6),
                      Wrap(
                        spacing: 8,
                        children: job.evidence.map((ev) => Container(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                          decoration: BoxDecoration(
                            color: const Color(0xFFF1F5F9),
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(color: const Color(0xFFCBD5E1)),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Icon(Icons.image_outlined, size: 14, color: Color(0xFF475569)),
                              const SizedBox(width: 6),
                              Text(ev.mediaRole.toUpperCase(), style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Color(0xFF334155))),
                            ],
                          ),
                        )).toList(),
                      ),
                      const SizedBox(height: 16),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: () => Navigator.pop(ctx),
                  child: const Text('Close'),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

