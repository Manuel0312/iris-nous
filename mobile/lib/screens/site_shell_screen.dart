import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';

import '../config.dart';
import '../services/auth_store.dart';
import '../theme/iris_theme.dart';

/// Full Iris website inside the app (same UI / 3D as PC).
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
  String _title = 'Iris Nous';

  @override
  void initState() {
    super.initState();
    _controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setNavigationDelegate(
        NavigationDelegate(
          onPageStarted: (_) {
            if (mounted) setState(() => _loading = true);
          },
          onPageFinished: (url) async {
            if (!mounted) return;
            final t = await _controller.getTitle();
            setState(() {
              _loading = false;
              if (t != null && t.isNotEmpty) _title = t;
            });
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
    final uri = Uri.parse('$base$path');
    await _controller.loadRequest(uri);
  }

  @override
  Widget build(BuildContext context) {
    return IrisGlassScaffold(
      appBar: AppBar(
        title: Text(_title, maxLines: 1, overflow: TextOverflow.ellipsis),
        actions: [
          IconButton(
            tooltip: 'Home Iris',
            onPressed: () async {
              final base = await widget.store.baseUrl();
              await _controller.loadRequest(Uri.parse(base));
            },
            icon: const Icon(Icons.home_outlined),
          ),
          IconButton(
            tooltip: 'Ecosistema',
            onPressed: () async {
              final base = await widget.store.baseUrl();
              await _controller.loadRequest(
                Uri.parse('$base${IrisConfig.webEcosistema}'),
              );
            },
            icon: const Icon(Icons.hub_outlined),
          ),
        ],
      ),
      child: Stack(
        children: [
          WebViewWidget(controller: _controller),
          if (_loading)
            const Center(
              child: CircularProgressIndicator(color: IrisTheme.accent),
            ),
        ],
      ),
    );
  }
}
