import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:webview_flutter/webview_flutter.dart';

import '../config.dart';
import '../services/auth_store.dart';
import 'home_screen.dart';
import 'permissions_screen.dart';

/// The whole app = the Iris website (same graphics, 3D, flows as PC).
class SiteShellScreen extends StatefulWidget {
  const SiteShellScreen({
    super.key,
    required this.store,
    this.initialPath = '/',
  });

  final AuthStore store;
  final String initialPath;

  @override
  State<SiteShellScreen> createState() => _SiteShellScreenState();
}

class _SiteShellScreenState extends State<SiteShellScreen> {
  late final WebViewController _controller;
  bool _loading = true;
  bool _menuOpen = false;

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
    _load();
  }

  Future<void> _load() async {
    final base = await widget.store.baseUrl();
    final path = widget.initialPath.startsWith('/')
        ? widget.initialPath
        : '/${widget.initialPath}';
    // Mark traffic as native app so the site can tweak chrome if needed.
    final uri = Uri.parse('$base$path').replace(
      queryParameters: {
        ...Uri.parse('$base$path').queryParameters,
        'from': 'native_app',
      },
    );
    await _controller.loadRequest(uri);
  }

  Future<void> _goHome() async {
    final base = await widget.store.baseUrl();
    await _controller.loadRequest(
      Uri.parse(base).replace(queryParameters: {'from': 'native_app'}),
    );
  }

  @override
  Widget build(BuildContext context) {
    final bottom = MediaQuery.paddingOf(context).bottom;
    return Scaffold(
      backgroundColor: const Color(0xFFF5F5F7),
      body: Stack(
        fit: StackFit.expand,
        children: [
          SafeArea(
            top: true,
            bottom: false,
            child: WebViewWidget(controller: _controller),
          ),
          if (_loading)
            const ColoredBox(
              color: Color(0xFFF5F5F7),
              child: Center(
                child: CircularProgressIndicator(color: Color(0xFF00B7FF)),
              ),
            ),
          // Tiny overflow menu — site stays full-bleed; permissions stay reachable.
          Positioned(
            right: 12,
            bottom: 12 + bottom,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                if (_menuOpen) ...[
                  _MiniAction(
                    label: 'Torna all’inizio',
                    onTap: () {
                      setState(() => _menuOpen = false);
                      _goHome();
                    },
                  ),
                  const SizedBox(height: 8),
                  _MiniAction(
                    label: 'Permessi',
                    onTap: () {
                      setState(() => _menuOpen = false);
                      Navigator.of(context).push(
                        MaterialPageRoute<void>(
                          builder: (_) =>
                              PermissionsScreen(store: widget.store),
                        ),
                      );
                    },
                  ),
                  const SizedBox(height: 8),
                  _MiniAction(
                    label: 'Il tuo telefono',
                    onTap: () {
                      setState(() => _menuOpen = false);
                      Navigator.of(context).push(
                        MaterialPageRoute<void>(
                          builder: (_) => HomeScreen(store: widget.store),
                        ),
                      );
                    },
                  ),
                  const SizedBox(height: 8),
                ],
                FloatingActionButton.small(
                  heroTag: 'iris-app-menu',
                  backgroundColor: const Color(0xFF00B7FF),
                  foregroundColor: Colors.white,
                  onPressed: () => setState(() => _menuOpen = !_menuOpen),
                  child: Icon(_menuOpen ? Icons.close : Icons.phone_iphone),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _MiniAction extends StatelessWidget {
  const _MiniAction({required this.label, required this.onTap});

  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      elevation: 3,
      borderRadius: BorderRadius.circular(16),
      color: Colors.white.withValues(alpha: 0.94),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          child: Text(
            label,
            style: const TextStyle(
              color: Color(0xFF0B1B33),
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
      ),
    );
  }
}
