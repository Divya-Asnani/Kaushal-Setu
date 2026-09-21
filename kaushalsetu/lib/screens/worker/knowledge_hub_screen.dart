import 'package:flutter/material.dart';
import 'package:kaushalsetu/core/theme/app_theme.dart';
import 'package:kaushalsetu/models/knowledge_case.dart';
import 'package:kaushalsetu/services/knowledge_service.dart';
import 'package:kaushalsetu/widgets/loading_view.dart';
import 'package:kaushalsetu/widgets/error_view.dart';
import 'package:kaushalsetu/screens/worker/knowledge_case_detail_screen.dart';

class KnowledgeHubScreen extends StatefulWidget {
  const KnowledgeHubScreen({super.key});

  @override
  State<KnowledgeHubScreen> createState() => _KnowledgeHubScreenState();
}

class _KnowledgeHubScreenState extends State<KnowledgeHubScreen> {
  final KnowledgeService _knowledgeService = KnowledgeService();
  final _searchController = TextEditingController(text: 'Samsung S23 no power');

  bool _isLoading = true;
  String? _errorMessage;
  List<KnowledgeCase> _cases = [];

  @override
  void initState() {
    super.initState();
    _performSearch();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _performSearch() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final results = await _knowledgeService.searchSimilarCases(
        _searchController.text.trim().isNotEmpty ? _searchController.text.trim() : 'repair',
      );
      _cases = results;
    } catch (e) {
      _errorMessage = e.toString();
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  void _showCreateCaseModal() {
    final titleCtrl = TextEditingController();
    final summaryCtrl = TextEditingController();
    final diagCtrl = TextEditingController();
    final solutionCtrl = TextEditingController();
    final lessonCtrl = TextEditingController();

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
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const Text('Publish Knowledge Case', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 12),
                    TextField(controller: titleCtrl, decoration: const InputDecoration(labelText: 'Case Title *')),
                    const SizedBox(height: 10),
                    TextField(controller: summaryCtrl, decoration: const InputDecoration(labelText: 'Problem Summary *')),
                    const SizedBox(height: 10),
                    TextField(controller: diagCtrl, decoration: const InputDecoration(labelText: 'Diagnosis *')),
                    const SizedBox(height: 10),
                    TextField(controller: solutionCtrl, decoration: const InputDecoration(labelText: 'Solution / Repair Steps *')),
                    const SizedBox(height: 10),
                    TextField(controller: lessonCtrl, decoration: const InputDecoration(labelText: 'Key Lesson Learned')),
                    const SizedBox(height: 20),
                    ElevatedButton(
                      onPressed: isSubmitting
                          ? null
                          : () async {
                              if (titleCtrl.text.trim().isEmpty || solutionCtrl.text.trim().isEmpty) return;
                              setModalState(() => isSubmitting = true);
                              try {
                                await _knowledgeService.createCase(
                                  title: titleCtrl.text.trim(),
                                  problemSummary: summaryCtrl.text.trim(),
                                  diagnosis: diagCtrl.text.trim(),
                                  solution: solutionCtrl.text.trim(),
                                  lessonLearned: lessonCtrl.text.trim(),
                                );
                                if (ctx.mounted) Navigator.pop(ctx);
                                _performSearch();
                              } catch (e) {
                                setModalState(() => isSubmitting = false);
                              }
                            },
                      child: isSubmitting
                          ? const SizedBox(height: 18, width: 18, child: CircularProgressIndicator(color: Colors.white))
                          : const Text('Publish to Knowledge Hub'),
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Knowledge Hub'),
        actions: [
          IconButton(
            icon: const Icon(Icons.add_circle_outline),
            tooltip: 'Publish Case',
            onPressed: _showCreateCaseModal,
          ),
        ],
      ),
      body: Column(
        children: [
          // Semantic Search Bar
          Padding(
            padding: const EdgeInsets.all(16),
            child: TextField(
              controller: _searchController,
              decoration: InputDecoration(
                hintText: 'Search symptoms, models (e.g. Samsung S23, Inverter overload)...',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: IconButton(
                  icon: const Icon(Icons.arrow_forward),
                  onPressed: _performSearch,
                ),
              ),
              onSubmitted: (_) => _performSearch(),
            ),
          ),

          // Search Results
          Expanded(
            child: _isLoading
                ? const LoadingView(
                    message: 'Searching Knowledge Cases...',
                    subtitle: 'Semantic retrieval matching diagnostic patterns and component solutions',
                  )
                : _errorMessage != null
                    ? ErrorView(title: 'Search Error', message: _errorMessage!, onRetry: _performSearch)
                    : _cases.isEmpty
                        ? const Center(child: Text('No matching cases found.', style: TextStyle(color: Colors.grey)))
                        : ListView.builder(
                            padding: const EdgeInsets.symmetric(horizontal: 16),
                            itemCount: _cases.length,
                            itemBuilder: (context, idx) {
                              final c = _cases[idx];
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
                                              c.title,
                                              style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15),
                                            ),
                                          ),
                                          if (c.isVerified)
                                            const Icon(Icons.verified, color: Colors.green, size: 18),
                                        ],
                                      ),
                                      const SizedBox(height: 4),
                                      Text(
                                        'By ${c.workerName ?? "Specialist"} • ${c.deviceCategory ?? "General"}',
                                        style: const TextStyle(fontSize: 12, color: Color(0xFF64748B)),
                                      ),
                                      const SizedBox(height: 8),
                                      Text(
                                        c.problemSummary,
                                        style: const TextStyle(fontSize: 13, color: Color(0xFF334155)),
                                      ),
                                      const SizedBox(height: 10),
                                      Container(
                                        padding: const EdgeInsets.all(10),
                                        decoration: BoxDecoration(
                                          color: const Color(0xFFF1F5F9),
                                          borderRadius: BorderRadius.circular(8),
                                        ),
                                        child: Column(
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            Text(
                                              'Solution: ${c.solution}',
                                              style: const TextStyle(fontSize: 12, color: Color(0xFF475569)),
                                            ),
                                            if (c.lessonLearned != null) ...[
                                              const SizedBox(height: 4),
                                              Text(
                                                '💡 Lesson: ${c.lessonLearned}',
                                                style: const TextStyle(
                                                  fontSize: 11,
                                                  color: AppTheme.primaryAmber,
                                                  fontWeight: FontWeight.bold,
                                                ),
                                              ),
                                            ],
                                          ],
                                        ),
                                      ),
                                      const SizedBox(height: 12),
                                      Align(
                                        alignment: Alignment.centerRight,
                                        child: TextButton(
                                          onPressed: () {
                                            Navigator.push(
                                              context,
                                              MaterialPageRoute(
                                                builder: (_) => KnowledgeCaseDetailScreen(knowledgeCase: c),
                                              ),
                                            );
                                          },
                                          child: const Text('View Full Breakdown'),
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              );
                            },
                          ),
          ),
        ],
      ),
    );
  }
}
