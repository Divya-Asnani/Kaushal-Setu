import 'package:flutter/material.dart';
import 'package:kaushalsetu/core/theme/app_theme.dart';
import 'package:kaushalsetu/models/knowledge_case.dart';

class KnowledgeCaseDetailScreen extends StatelessWidget {
  final KnowledgeCase knowledgeCase;

  const KnowledgeCaseDetailScreen({super.key, required this.knowledgeCase});

  @override
  Widget build(BuildContext context) {
    final c = knowledgeCase;

    return Scaffold(
      appBar: AppBar(title: const Text('Knowledge Case Breakdown')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              c.title,
              style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800, color: AppTheme.secondaryNavy),
            ),
            const SizedBox(height: 6),
            Text(
              'Author: ${c.workerName ?? "Specialist"} • Difficulty: ${c.difficulty.toUpperCase()}',
              style: const TextStyle(color: Color(0xFF64748B), fontSize: 13),
            ),
            const SizedBox(height: 16),

            // Problem Summary
            const Text('Problem Summary', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
            const SizedBox(height: 6),
            Text(c.problemSummary, style: const TextStyle(fontSize: 13, height: 1.4)),
            const SizedBox(height: 16),

            // Diagnosis
            const Text('Technical Diagnosis', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
            const SizedBox(height: 6),
            Text(c.diagnosis, style: const TextStyle(fontSize: 13, height: 1.4)),
            const SizedBox(height: 16),

            // Solution
            const Text('Repair Solution & Method', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
            const SizedBox(height: 6),
            Text(c.solution, style: const TextStyle(fontSize: 13, height: 1.4)),
            const SizedBox(height: 16),

            // Lesson Learned
            if (c.lessonLearned != null) ...[
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: const Color(0xFFFFFBEB),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: const Color(0xFFFDE68A)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Technical Lesson Learned',
                      style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13, color: Color(0xFF92400E)),
                    ),
                    const SizedBox(height: 6),
                    Text(c.lessonLearned!, style: const TextStyle(fontSize: 13, color: Color(0xFF78350F))),
                  ],
                ),
              ),
              const SizedBox(height: 16),
            ],
          ],
        ),
      ),
    );
  }
}
