import 'package:flutter/material.dart';
import 'package:kaushalsetu/core/theme/app_theme.dart';
import 'package:kaushalsetu/models/problem.dart';
import 'package:kaushalsetu/models/match_result.dart';
import 'package:kaushalsetu/services/matching_service.dart';
import 'package:kaushalsetu/services/request_service.dart';
import 'package:kaushalsetu/widgets/loading_view.dart';
import 'package:kaushalsetu/widgets/error_view.dart';
import 'package:kaushalsetu/widgets/match_card.dart';
import 'package:kaushalsetu/screens/customer/customer_requests_screen.dart';

class MatchResultsScreen extends StatefulWidget {
  final CustomerProblem problem;

  const MatchResultsScreen({super.key, required this.problem});

  @override
  State<MatchResultsScreen> createState() => _MatchResultsScreenState();
}

class _MatchResultsScreenState extends State<MatchResultsScreen> {
  final MatchingService _matchingService = MatchingService();
  final RequestService _requestService = RequestService();

  bool _isLoading = true;
  String? _errorMessage;
  List<MatchResultItem> _matches = [];

  @override
  void initState() {
    super.initState();
    _fetchMatches();
  }

  Future<void> _fetchMatches() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final results = await _matchingService.getProblemMatches(widget.problem.id, limit: 5);
      _matches = results;
    } catch (e) {
      _errorMessage = e.toString();
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  void _showRequestModal(MatchResultItem match) {
    final messageController = TextEditingController(
      text: 'Hello ${match.workerName}, I would like to request your diagnostic service for my ${widget.problem.title}.',
    );

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) {
        bool isSubmitting = false;
        return StatefulBuilder(
          builder: (context, setModalState) {
            return Padding(
              padding: EdgeInsets.only(
                left: 20,
                right: 20,
                top: 20,
                bottom: MediaQuery.of(context).viewInsets.bottom + 20,
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'Request ${match.workerName}',
                        style: const TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.w700,
                          color: AppTheme.secondaryNavy,
                        ),
                      ),
                      IconButton(
                        icon: const Icon(Icons.close),
                        onPressed: () => Navigator.pop(ctx),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Text(
                    'Match Confidence: ${match.matchScorePercentage}${match.locality != null && match.locality!.isNotEmpty ? " • ${match.locality}" : ""}',
                    style: const TextStyle(fontSize: 13, color: AppTheme.primaryAmber, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 16),
                  TextField(
                    controller: messageController,
                    maxLines: 3,
                    decoration: const InputDecoration(
                      labelText: 'Message for Technician',
                      hintText: 'Preferred time, urgency or access instructions...',
                    ),
                  ),
                  const SizedBox(height: 20),
                  ElevatedButton(
                    onPressed: isSubmitting
                        ? null
                        : () async {
                            setModalState(() => isSubmitting = true);
                            final messenger = ScaffoldMessenger.of(context);
                            final navigator = Navigator.of(context);
                            try {
                              await _requestService.createServiceRequest(
                                problemId: widget.problem.id,
                                workerId: match.workerId,
                                matchResultId: match.matchResultId,
                                customerMessage: messageController.text.trim(),
                              );
                              if (ctx.mounted) Navigator.pop(ctx);
                              if (mounted) {
                                messenger.showSnackBar(
                                  SnackBar(
                                    content: Text('Service request sent to ${match.workerName}!'),
                                    backgroundColor: Colors.green,
                                  ),
                                );
                                navigator.pushReplacement(
                                  MaterialPageRoute(builder: (_) => const CustomerRequestsScreen()),
                                );
                              }
                            } catch (e) {
                              setModalState(() => isSubmitting = false);
                              if (ctx.mounted) {
                                ScaffoldMessenger.of(ctx).showSnackBar(
                                  SnackBar(content: Text('Failed to send request: $e'), backgroundColor: Colors.red),
                                );
                              }
                            }
                          },
                    child: isSubmitting
                        ? const SizedBox(
                            height: 20,
                            width: 20,
                            child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                          )
                        : const Text('Send Service Request'),
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return Scaffold(
        appBar: AppBar(title: const Text('Matching Technicians')),
        body: const LoadingView(
          message: 'Finding Specialist Technicians...',
          subtitle: 'Calculating problem similarity, real-world verified experience, and locality proximity',
        ),
      );
    }

    if (_errorMessage != null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Matching Technicians')),
        body: ErrorView(
          title: 'Matching Failed',
          message: _errorMessage!,
          onRetry: _fetchMatches,
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Top Technician Matches'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _fetchMatches,
          ),
        ],
      ),
      body: _matches.isEmpty
          ? Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.person_search_outlined, size: 48, color: Colors.grey),
                    const SizedBox(height: 12),
                    const Text(
                      'No available technicians found in your area.',
                      style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      'Technicians may currently be busy on active jobs.',
                      style: TextStyle(color: Colors.grey, fontSize: 13),
                    ),
                    const SizedBox(height: 20),
                    ElevatedButton(onPressed: _fetchMatches, child: const Text('Check Again')),
                  ],
                ),
              ),
            )
          : ListView(
              padding: const EdgeInsets.symmetric(vertical: 12),
              children: [
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'Found ${_matches.length} Verified Specialists',
                        style: const TextStyle(
                          fontSize: 15,
                          fontWeight: FontWeight.w700,
                          color: AppTheme.secondaryNavy,
                        ),
                      ),
                      const Text(
                        'Ranked by AI Experience',
                        style: TextStyle(fontSize: 12, color: Color(0xFF64748B)),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 6),
                ..._matches.map((match) {
                  return MatchCard(
                    match: match,
                    onRequest: () => _showRequestModal(match),
                  );
                }),
                const SizedBox(height: 30),
              ],
            ),
    );
  }
}
