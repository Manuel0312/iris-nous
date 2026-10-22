import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:webview_flutter/webview_flutter.dart';

import '../services/auth_store.dart';
import '../services/call_control.dart';
import '../services/call_observer.dart';
import '../services/iris_api.dart';
import '../services/whatsapp_open.dart';
import 'permissions_screen.dart';

/// Stessa UI della preview sul sito (Connessioni / Iris / Account), a schermo intero.
/// Carica /app?from=native_app — sul browser /app reindirizza a /app/preview.
///
/// Bridge JS `IrisNative`: permessi OS + heartbeat/call observer per SÌ/NO sulle chiamate.
class SiteShellScreen extends StatefulWidget {
  const SiteShellScreen({
    super.key,
    required this.store,
    this.initialPath = '/app?from=native_app',
  });

  final AuthStore store;
  final String initialPath;

  @override
  State<SiteShellScreen> createState() => _SiteShellScreenState();
}

class _SiteShellScreenState extends State<SiteShellScreen> {
  late final WebViewController _controller;
  late final IrisApi _api = IrisApi(widget.store);
  late final CallObserverService _calls = CallObserverService(
    _api,
    onIncomingRing: (caller) => _ensureCallKit(caller),
    onCallIdle: () => _clearCallKitIfRinging(),
  );
  final CallControlService _callControl = CallControlService();
  Timer? _beat;
  bool _loading = true;
  bool _bridgeArmed = false;
  bool _callKitPresented = false;
  bool _callKitAnswered = false;

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
      ..addJavaScriptChannel(
        'IrisNative',
        onMessageReceived: _onNativeMessage,
      )
      ..setNavigationDelegate(
        NavigationDelegate(
          onPageStarted: (_) {
            if (mounted) setState(() => _loading = true);
          },
          onPageFinished: (_) {
            if (mounted) setState(() => _loading = false);
            _armBridgeIfPaired();
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

  void _onNativeMessage(JavaScriptMessage message) {
    Map<String, dynamic> body = {};
    try {
      final decoded = jsonDecode(message.message);
      if (decoded is Map<String, dynamic>) body = decoded;
    } catch (_) {
      body = {'action': message.message};
    }
    final action = (body['action'] ?? '').toString();
    if (action == 'openPermissions') {
      _openPermissions();
    } else if (action == 'ensureCallBridge') {
      _armBridgeIfPaired(force: true);
    } else if (action == 'savePairing') {
      final token = (body['token'] ?? '').toString();
      final username = (body['username'] ?? '').toString();
      if (token.isNotEmpty) {
        widget.store.savePairing(token: token, username: username).then((_) {
          _armBridgeIfPaired(force: true);
        });
      }
    }
  }

  Future<void> _openPermissions() async {
    if (!mounted) return;
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => PermissionsScreen(store: widget.store),
      ),
    );
  }

  Future<void> _armBridgeIfPaired({bool force = false}) async {
    if (_bridgeArmed && !force) return;
    final paired = await widget.store.isPaired();
    if (!paired) return;
    _bridgeArmed = true;
    _calls.start();
    _armHeartbeat();
    unawaited(_refreshBridge());
  }

  void _armHeartbeat({bool fast = false}) {
    _beat?.cancel();
    _beat = Timer.periodic(
      Duration(seconds: fast ? 4 : 15),
      (_) => _refreshBridge(),
    );
  }

  Future<void> _refreshBridge() async {
    try {
      final body = await _api.heartbeat();
      await _drainOsCommands(body);
      final ctxMap = body['context'] is Map ? body['context'] as Map : null;
      final incoming = ctxMap?['incoming_call'] == true;
      final callerName = (ctxMap?['caller_name']?.toString() ?? '').trim();
      if (incoming && !_callKitPresented && !_callKitAnswered) {
        await _ensureCallKit(callerName.isEmpty ? 'Chiamata Iris' : callerName);
      } else if (!incoming && _callKitPresented) {
        await _clearCallKitIfRinging();
      }
      final focus = ctxMap?['focus'];
      final kind = focus is Map ? focus['kind']?.toString() : null;
      final active = kind != null && kind != 'idle' && kind.isNotEmpty;
      _armHeartbeat(
        fast: active ||
            (ctxMap?['incoming_call'] == true) ||
            (ctxMap?['unread_message'] == true) ||
            (ctxMap?['music_playing'] == true),
      );
    } on IrisApiException catch (e) {
      if (e.statusCode == 401 || e.statusCode == 403) {
        await widget.store.clear();
        _bridgeArmed = false;
        _beat?.cancel();
        _calls.stop();
      }
    } catch (_) {}
  }

  Future<void> _ensureCallKit(String caller) async {
    if (_callKitAnswered) return;
    final r = await _callControl.presentIncoming(caller: caller);
    _callKitPresented = r['ok'] == true;
  }

  Future<void> _clearCallKitIfRinging() async {
    if (_callKitAnswered) {
      _callKitPresented = false;
      return;
    }
    if (_callKitPresented) {
      await _callControl.end();
      _callKitPresented = false;
    }
  }

  Future<void> _drainOsCommands(Map<String, dynamic> body) async {
    final raw = body['pending_commands'];
    if (raw is! List || raw.isEmpty) return;
    final ids = <String>[];
    for (final item in raw) {
      if (item is! Map) continue;
      final id = item['id']?.toString() ?? '';
      final action = item['action']?.toString() ?? '';
      if (id.isEmpty || action.isEmpty) continue;
      if (action == 'open_whatsapp' || action == 'open_url') {
        final url = item['url']?.toString() ?? 'whatsapp://';
        await openWhatsApp(url: url);
        ids.add(id);
        continue;
      }
      final result = await _callControl.runAction(action);
      ids.add(id);
      final ok = result['ok'] == true;
      if (ok && action.contains('answer')) {
        _callKitAnswered = true;
        _callKitPresented = true;
      }
      if (ok && action.contains('reject')) {
        _callKitAnswered = false;
        _callKitPresented = false;
      }
    }
    if (ids.isNotEmpty) {
      try {
        await _api.ackCommands(ids);
      } catch (_) {}
    }
  }

  @override
  void dispose() {
    _beat?.cancel();
    _calls.stop();
    super.dispose();
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
