import 'package:flutter/material.dart';
import 'package:kaushalsetu/core/theme/app_theme.dart';
import 'package:kaushalsetu/models/problem.dart';
import 'package:kaushalsetu/services/problem_service.dart';
import 'package:kaushalsetu/widgets/loading_view.dart';
import 'package:kaushalsetu/widgets/error_view.dart';
import 'package:kaushalsetu/screens/customer/match_results_screen.dart';

class ProblemFingerprintScreen extends StatefulWidget {
  final CustomerProblem problem;

  const ProblemFingerprintScreen({super.key, required this.problem});

  @override
  State<ProblemFingerprintScreen> createState() => _ProblemFingerprintScreenState();
}

class _ProblemFingerprintScreenState extends State<ProblemFingerprintScreen> {
  final ProblemService _problemService = ProblemService();

  bool _isLoading = true;
  String? _errorMessage;
  ProblemFingerprint? _fingerprint;

  // Editable review controllers
  late TextEditingController _brandController;
  late TextEditingController _modelController;
  late TextEditingController _deviceTypeController;

  @override
  void initState() {
    super.initState();
    _brandController = TextEditingController();
    _modelController = TextEditingController();
    _deviceTypeController = TextEditingController();
    _fetchOrGenerateFingerprint();
  }

  @override
  void dispose() {
    _brandController.dispose();
    _modelController.dispose();
    _deviceTypeController.dispose();
    super.dispose();
  }

  Future<void> _fetchOrGenerateFingerprint() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final fp = await _problemService.generateFingerprint(widget.problem.id);
      _fingerprint = fp;
      _brandController.text = fp.brand ?? '';
      _modelController.text = fp.model ?? '';
      _deviceTypeController.text = fp.deviceType ?? '';
    } catch (e) {
      _errorMessage = e.toString();
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return Scaffold(
        appBar: AppBar(title: const Text('AI Problem Fingerprint')),
        body: const LoadingView(
          message: 'Extracting Problem Fingerprint...',
          subtitle: 'Analyzing fault symptoms, device specs, and required technician skills',
        ),
      );
    }

    if (_errorMessage != null) {
      return Scaffold(
        appBar: AppBar(title: const Text('AI Problem Fingerprint')),
        body: ErrorView(
          title: 'Fingerprint Extraction Failed',
          message: _errorMessage!,
          onRetry: _fetchOrGenerateFingerprint,
        ),
      );
    }

    final fp = _fingerprint!;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Review Extracted Fingerprint'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Regenerate Fingerprint',
            onPressed: _fetchOrGenerateFingerprint,
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Status Tag
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppTheme.accentIndigo.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(
                children: [
                  const Icon(Icons.auto_awesome, color: AppTheme.accentIndigo, size: 20),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      'AI Fingerprint v${fp.fingerprintVersion} • Knowledge Graph Ready',
                      style: const TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                        color: AppTheme.accentIndigo,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // AI Summary
            if (fp.aiSummary != null)
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'AI Diagnostic Assessment',
                        style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: AppTheme.secondaryNavy),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        fp.aiSummary!,
                        style: const TextStyle(fontSize: 13, color: Color(0xFF475569), height: 1.4),
                      ),
                    ],
                  ),
                ),
              ),
            const SizedBox(height: 12),

            // Suspected Component Box (with careful disclaimer)
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: const Color(0xFFFFFBEB),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFFFDE68A)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Row(
                    children: [
                      Icon(Icons.info_outline_rounded, size: 16, color: Color(0xFFB45309)),
                      SizedBox(width: 8),
                      Text(
                        'Hypothetical Suspected Component',
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w700,
                          color: Color(0xFF92400E),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Text(
                    fp.suspectedComponent ?? 'Pending on-site diagnostic review',
                    style: const TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                      color: Color(0xFF78350F),
                    ),
                  ),
                  const SizedBox(height: 4),
                  const Text(
                    'Note: This is an AI hypothesis based on reported symptoms. Final diagnosis is confirmed on-site with technician instrumentation.',
                    style: TextStyle(fontSize: 11, color: Color(0xFFB45309)),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Editable device parameters
            const Text(
              'Review & Verify Device Information',
              style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: AppTheme.secondaryNavy),
            ),
            const SizedBox(height: 10),

            TextField(
              controller: _deviceTypeController,
              decoration: const InputDecoration(labelText: 'Device Type / Category'),
            ),
            const SizedBox(height: 10),

            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _brandController,
                    decoration: const InputDecoration(labelText: 'Brand'),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: TextField(
                    controller: _modelController,
                    decoration: const InputDecoration(labelText: 'Model'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),

            // Symptoms List
            if (fp.symptoms.isNotEmpty) ...[
              const Text(
                'Identified Symptoms',
                style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: AppTheme.secondaryNavy),
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: fp.symptoms.map((s) {
                  return Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: AppTheme.borderSubtle),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.check_circle_outline, size: 14, color: Colors.green),
                        const SizedBox(width: 6),
                        Text(s, style: const TextStyle(fontSize: 12, color: Color(0xFF334155))),
                      ],
                    ),
                  );
                }).toList(),
              ),
              const SizedBox(height: 16),
            ],

            // Required Skills
            if (fp.extractedSkills.isNotEmpty) ...[
              const Text(
                'Required Technician Competencies',
                style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: AppTheme.secondaryNavy),
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: fp.extractedSkills.map((sk) {
                  return Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                    decoration: BoxDecoration(
                      color: AppTheme.primaryAmber.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text(
                      sk,
                      style: const TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                        color: AppTheme.primaryAmber,
                      ),
                    ),
                  );
                }).toList(),
              ),
              const SizedBox(height: 24),
            ],

            // Action Button -> Proceed to Matching
            ElevatedButton.icon(
              onPressed: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (_) => MatchResultsScreen(problem: widget.problem),
                  ),
                );
              },
              icon: const Icon(Icons.search_rounded),
              label: const Text('Confirm & Find Top Technician Matches'),
            ),
            const SizedBox(height: 30),
          ],
        ),
      ),
    );
  }
}
