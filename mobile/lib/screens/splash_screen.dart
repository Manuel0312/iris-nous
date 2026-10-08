import 'package:flutter/material.dart';

import '../config.dart';
import '../services/auth_store.dart';
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
    const accent = Color(IrisConfig.accentBlue);
    return Scaffold(
      backgroundColor: const Color(0xFFF5F5F7),
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              'Iris Nous',
              style: TextStyle(
                fontSize: 34,
                fontWeight: FontWeight.w700,
                letterSpacing: -0.6,
                color: accent,
              ),
            ),
            const SizedBox(height: 10),
            const Text(
              'App companion · Ecosistema',
              style: TextStyle(color: Colors.black54),
            ),
            const SizedBox(height: 28),
            CircularProgressIndicator(color: accent),
          ],
        ),
      ),
    );
  }
}
