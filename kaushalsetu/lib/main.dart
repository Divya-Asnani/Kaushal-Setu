import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:kaushalsetu/core/config/app_config.dart';
import 'package:kaushalsetu/core/auth/auth_provider.dart';
import 'package:kaushalsetu/core/theme/app_theme.dart';
import 'package:kaushalsetu/widgets/loading_view.dart';
import 'package:kaushalsetu/screens/auth/login_screen.dart';
import 'package:kaushalsetu/screens/auth/register_screen.dart';
import 'package:kaushalsetu/screens/customer/customer_home_screen.dart';
import 'package:kaushalsetu/screens/customer/create_problem_screen.dart';
import 'package:kaushalsetu/screens/customer/customer_requests_screen.dart';
import 'package:kaushalsetu/screens/worker/worker_dashboard_screen.dart';
import 'package:kaushalsetu/screens/worker/worker_requests_screen.dart';
import 'package:kaushalsetu/screens/worker/knowledge_hub_screen.dart';
import 'package:kaushalsetu/screens/common/notifications_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize Supabase Flutter client safely
  try {
    await Supabase.initialize(
      url: AppConfig.supabaseUrl,
      publishableKey: AppConfig.supabaseAnonKey,
      authOptions: const FlutterAuthClientOptions(
        autoRefreshToken: true,
      ),
    );
  } catch (e) {
    debugPrint('Supabase initialisation notice (development fallback): $e');
  }

  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => AuthProvider()..checkExistingAuth()),
      ],
      child: const KaushalSetuApp(),
    ),
  );
}

class KaushalSetuApp extends StatelessWidget {
  const KaushalSetuApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: AppConfig.appName,
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      routes: {
        '/login': (_) => const LoginScreen(),
        '/register': (_) => const RegisterScreen(),
        '/customer': (_) => const CustomerHomeScreen(),
        '/customer/problems/new': (_) => const CreateProblemScreen(),
        '/customer/requests': (_) => const CustomerRequestsScreen(),
        '/worker': (_) => const WorkerDashboardScreen(),
        '/worker/requests': (_) => const WorkerRequestsScreen(),
        '/worker/knowledge': (_) => const KnowledgeHubScreen(),
        '/worker/notifications': (_) => const NotificationsScreen(),
      },
      home: const AuthGate(),
    );
  }
}

class AuthGate extends StatelessWidget {
  const AuthGate({super.key});

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();

    if (auth.isLoading) {
      return const Scaffold(
        body: LoadingView(
          message: 'Connecting to KaushalSetu...',
          subtitle: 'Restoring secure session and loading profile',
        ),
      );
    }

    if (!auth.isAuthenticated) {
      return const LoginScreen();
    }

    // Role-based root view dispatching
    if (auth.isWorker) {
      return const WorkerDashboardScreen();
    }

    return const CustomerHomeScreen();
  }
}
