import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:webview_flutter/webview_flutter.dart';

import '../services/auth_store.dart';

/// Simple Iris app shell (explainer + 3 tabs) served by /app — not the full site.
class SiteShellScreen extends StatefulWidget {
  const SiteShellScreen({
    super.key,
    required this.store,
    this.initialPath = '/app',
  });

  final AuthStore store;
  final String initialPath;

  @override
  State<SiteShellScreen> createState() => _SiteShellScreenState();
}

class _SiteShellScreenState extends State<SiteShellScreen> {
  late final WebViewController _controller;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    SystemChrome.setSystemUIOverlayStyle(
      const SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.dark,
      ),
    );
    _controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(const Color(0xFFF5F5F7))
      ..setNavigationDelegate(
        NavigationDelegate(
          onPageStarted: (_) {
            if (mounted) setState(() => _loading = true);
          },
          onPageFinished: (_) {
            if (mounted) setState(() => _loading = false);
          },
        ),
      );
    _load(widget.initialPath);
  }

  Future<void> _load(String path) async {
    final base = await widget.store.baseUrl();
    final clean = path.startsWith('/') ? path : '/$path';
    final parsed = Uri.parse('$base$clean');
    final uri = parsed.replace(
      queryParameters: {
        ...parsed.queryParameters,
        'from': 'native_app',
      },
    );
    await _controller.loadRequest(uri);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5F5F7),
      body: SafeArea(
        bottom: false,
        child: Stack(
          fit: StackFit.expand,
          children: [
            WebViewWidget(controller: _controller),
            if (_loading)
              const ColoredBox(
                color: Color(0xFFF5F5F7),
                child: Center(
                  child: CircularProgressIndicator(color: Color(0xFF00B7FF)),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
