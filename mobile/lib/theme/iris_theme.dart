import 'dart:ui';

import 'package:flutter/material.dart';

import '../config.dart';

/// Liquid-glass look shared across phone / tablet layouts.
abstract final class IrisTheme {
  static const Color accent = Color(IrisConfig.accentBlue);
  static const Color deep = Color(0xFF0B1B33);
  static const Color mist = Color(0xFFE8F1FF);

  static ThemeData light() {
    final base = ColorScheme.fromSeed(
      seedColor: accent,
      brightness: Brightness.light,
      primary: accent,
    );
    return ThemeData(
      colorScheme: base,
      useMaterial3: true,
      scaffoldBackgroundColor: Colors.transparent,
      appBarTheme: AppBarTheme(
        backgroundColor: Colors.white.withValues(alpha: 0.28),
        foregroundColor: deep,
        elevation: 0,
        centerTitle: false,
        surfaceTintColor: Colors.transparent,
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: accent,
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: accent,
          side: BorderSide(color: accent.withValues(alpha: 0.4)),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white.withValues(alpha: 0.55),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.55)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.55)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: accent, width: 1.4),
        ),
      ),
    );
  }
}

class IrisGlassScaffold extends StatelessWidget {
  const IrisGlassScaffold({
    super.key,
    required this.child,
    this.appBar,
    this.floatingActionButton,
  });

  final Widget child;
  final PreferredSizeWidget? appBar;
  final Widget? floatingActionButton;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Color(0xFFD7E8FF),
            Color(0xFFF4F7FC),
            Color(0xFFC8E0FF),
          ],
        ),
      ),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: appBar,
        floatingActionButton: floatingActionButton,
        body: SafeArea(child: child),
      ),
    );
  }
}

class GlassPane extends StatelessWidget {
  const GlassPane({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(16),
    this.margin,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;
  final EdgeInsetsGeometry? margin;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: margin,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(22),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 18, sigmaY: 18),
          child: DecoratedBox(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(22),
              color: Colors.white.withValues(alpha: 0.42),
              border: Border.all(color: Colors.white.withValues(alpha: 0.65)),
              boxShadow: [
                BoxShadow(
                  color: IrisTheme.deep.withValues(alpha: 0.06),
                  blurRadius: 24,
                  offset: const Offset(0, 10),
                ),
              ],
            ),
            child: Padding(padding: padding, child: child),
          ),
        ),
      ),
    );
  }
}
