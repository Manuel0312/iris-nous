import 'package:flutter/material.dart';

import '../services/auth_store.dart';
import '../theme/iris_theme.dart';
import 'home_screen.dart';
import 'login_screen.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key, required this.store});

  final AuthStore store;

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  @override
  void initState() {
    super.initState();
    _go();
  }

  Future<void> _go() async {
    await Future<void>.delayed(const Duration(milliseconds: 600));
    if (!mounted) return;
    final paired = await widget.store.isPaired();
    Navigator.of(context).pushReplacement(
      MaterialPageRoute<void>(
        builder: (_) => paired
            ? HomeScreen(store: widget.store)
            : LoginScreen(store: widget.store),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return IrisGlassScaffold(
      child: Center(
        child: GlassPane(
          padding: const EdgeInsets.symmetric(horizontal: 36, vertical: 32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                'Iris Nous',
                style: TextStyle(
                  fontSize: 34,
                  fontWeight: FontWeight.w700,
                  letterSpacing: -0.6,
                  color: IrisTheme.accent,
                ),
              ),
              const SizedBox(height: 10),
              Text(
                'App companion · Ecosistema',
                style: TextStyle(color: IrisTheme.deep.withValues(alpha: 0.55)),
              ),
              const SizedBox(height: 28),
              const CircularProgressIndicator(color: IrisTheme.accent),
            ],
          ),
        ),
      ),
    );
  }
}
