import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:kaushalsetu/main.dart';
import 'package:kaushalsetu/core/auth/auth_provider.dart';

void main() {
  testWidgets('KaushalSetu smoke test renders title and login', (WidgetTester tester) async {
    await tester.pumpWidget(
      MultiProvider(
        providers: [
          ChangeNotifierProvider(create: (_) => AuthProvider()),
        ],
        child: const KaushalSetuApp(),
      ),
    );

    expect(find.text('KaushalSetu'), findsWidgets);
    expect(find.text('Sign In'), findsOneWidget);
  });
}
