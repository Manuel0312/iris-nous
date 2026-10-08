import 'package:flutter/material.dart';

import 'config.dart';
import 'screens/splash_screen.dart';
import 'services/auth_store.dart';

class IrisNousApp extends StatelessWidget {
  const IrisNousApp({super.key, required this.store});

  final AuthStore store;

  @override
  Widget build(BuildContext context) {
    const accent = Color(IrisConfig.accentBlue);
    final base = ColorScheme.fromSeed(
      seedColor: accent,
      brightness: Brightness.light,
      primary: accent,
    );
    return MaterialApp(
      title: 'Iris Nous',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: base,
        useMaterial3: true,
        scaffoldBackgroundColor: const Color(0xFFF5F5F7),
        appBarTheme: AppBarTheme(
          backgroundColor: const Color(0xFFF5F5F7),
          foregroundColor: base.onSurface,
          elevation: 0,
          centerTitle: false,
        ),
        filledButtonTheme: FilledButtonThemeData(
          style: FilledButton.styleFrom(
            backgroundColor: accent,
            foregroundColor: Colors.white,
            padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          ),
        ),
        outlinedButtonTheme: OutlinedButtonThemeData(
          style: OutlinedButton.styleFrom(
            foregroundColor: accent,
            side: BorderSide(color: accent.withOpacity(0.45)),
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          ),
        ),
      ),
      home: SplashScreen(store: store),
    );
  }
}
