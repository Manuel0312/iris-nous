import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:webview_flutter/webview_flutter.dart';

import '../services/auth_store.dart';
import '../services/call_control.dart';
import '../services/call_observer.dart';
import '../services/iris_api.dart';
import '../services/notification_observer.dart';
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
  late final NotificationObserverService _notifs = NotificationObserverService(
    _api,
    onMessage: _onIncomingMessageNotif,
  );
  final CallControlService _callControl = CallControlService();
  Timer? _beat;
  bool _loading = true;
  bool _bridgeArmed = false;
  bool _callKitPresented = false;
  bool _callKitAnswered = false;
  bool _bootstrapped = false;
  String _lastMsgPreview = '';
  String _lastMsgSender = '';

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
          onPageFinished: (_) async {
            if (mounted) setState(() => _loading = false);
            try {
              await _controller.runJavaScript('''
                (function(){
                  var s=document.getElementById('iris-no-tap-hl');
                  if(!s){
                    s=document.createElement('style');
                    s.id='iris-no-tap-hl';
                    s.textContent='*{ -webkit-tap-highlight-color:transparent!important; tap-highlight-color:transparent!important;} button,a,.btn,.chip,.tab{-webkit-tap-highlight-color:transparent!important;outline:none;}';
                    document.head.appendChild(s);
                  }
                  document.documentElement.style.webkitTapHighlightColor='transparent';
                  document.body && (document.body.style.webkitTapHighlightColor='transparent');
                })();
              ''');
            } catch (_) {}
            // Arm solo se già paired: niente request permessi / FGS agresivo.
            unawaited(_armBridgeIfPaired());
          },
        ),
      );
    unawaited(_bootLoad());
  }

  /// Se c’è un device_token salvato, ripristina la sessione web prima di /app
  /// (dopo crash/cache Samsung altrimenti sembra un logout).
  Future<void> _bootLoad() async {
    if (_bootstrapped) {
      await _load(widget.initialPath);
      return;
    }
    _bootstrapped = true;
    final token = await widget.store.deviceToken();
    if (token != null && token.isNotEmpty) {
      final q = Uri.encodeQueryComponent(token);
      await _load('/app/native-bootstrap?device_token=$q');
      return;
    }
    await _load(widget.initialPath);
  }

  Future<void> _load(String path) async {
    final base = await widget.store.baseUrl();
    final clean = path.startsWith('/') ? path : '/$path';
    final parsed = Uri.parse('$base$clean');
    final qp = Map<String, String>.from(parsed.queryParameters);
    qp.putIfAbsent('from', () => 'native_app');
    final uri = parsed.replace(queryParameters: qp);
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
      // Soft arm: non riparte FGS se già attivo.
      unawaited(_armBridgeIfPaired(force: false));
    } else if (action == 'flushPhoneCommands') {
      unawaited(_refreshBridge());
    } else if (action == 'runOsCommand') {
      unawaited(_runOsFromWeb(body));
    } else if (action == 'savePairing') {
      final token = (body['token'] ?? '').toString();
      final username = (body['username'] ?? '').toString();
      if (token.isNotEmpty) {
        widget.store.savePairing(token: token, username: username).then((_) {
          unawaited(_armBridgeIfPaired(force: false));
        });
      }
    }
  }

  Future<void> _runOsFromWeb(Map<String, dynamic> body) async {
    final osAction = (body['osAction'] ?? body['command'] ?? '').toString();
    if (osAction.isEmpty) {
      await _refreshBridge();
      return;
    }
    if (osAction == 'open_whatsapp' || osAction == 'open_url') {
      final preview = (body['messagePreview'] ?? '').toString();
      if (preview.isNotEmpty && mounted) {
        await showDialog<void>(
          context: context,
          builder: (ctx) => AlertDialog(
            title: Text(_lastMsgSender.isEmpty ? 'Messaggio' : _lastMsgSender),
            content: Text(preview),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(ctx).pop(),
                child: const Text('OK'),
              ),
            ],
          ),
        );
      }
      final url = (body['url'] ?? 'whatsapp://').toString();
      await openWhatsApp(url: url);
      final id = (body['id'] ?? '').toString();
      if (id.isNotEmpty) {
        try {
          await _api.ackCommands([id]);
        } catch (_) {}
      }
      return;
    }
    final result = await _callControl.runAction(osAction);
    final id = (body['id'] ?? '').toString();
    if (id.isNotEmpty) {
      try {
        await _api.ackCommands([id]);
      } catch (_) {}
    }
    final ok = result['ok'] == true;
    if (ok && osAction.contains('answer')) {
      _callKitAnswered = true;
      _callKitPresented = true;
    }
    if (ok && osAction.contains('reject')) {
      _callKitAnswered = false;
      _callKitPresented = false;
    }
    if (!ok && mounted) {
      final reason = (result['reason'] ?? 'blocco sistema').toString();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Chiamata non eseguita: $reason')),
      );
    }
  }

  Future<void> _openPermissions() async {
    if (!mounted) return;
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => PermissionsScreen(store: widget.store),
      ),
    );
    // Dopo Permessi: riparti listener solo se i permessi ci sono (request lì).
    unawaited(_armBridgeIfPaired(force: true, requestPermissions: true));
  }

  Future<void> _onIncomingMessageNotif(Map<String, dynamic> payload) async {
    _lastMsgSender = (payload['sender'] ?? '').toString();
    _lastMsgPreview = (payload['preview'] ?? '').toString();
    if (!mounted) return;
    final who = _lastMsgSender.isEmpty ? 'Messaggio' : _lastMsgSender;
    final body = _lastMsgPreview.isEmpty ? 'Nuova notifica verso Iris.' : _lastMsgPreview;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('$who: $body')),
    );
  }

  Future<void> _armBridgeIfPaired({
    bool force = false,
    bool requestPermissions = false,
  }) async {
    final paired = await widget.store.isPaired();
    if (!paired) return;
    if (_bridgeArmed && !force) {
      // Solo heartbeat più frequente se serve, niente restart servizi.
      if (_beat == null) _armHeartbeat();
      return;
    }
    _bridgeArmed = true;
    try {
      await _calls.start(requestPermissions: requestPermissions);
    } catch (_) {}
    try {
      unawaited(_notifs.start());
    } catch (_) {}
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
      // 401/403: NON cancellare il token né forzare logout web.
      // Un heartbeat fallito non deve buttare fuori dall’account.
      if (e.statusCode == 401 || e.statusCode == 403) {
        _beat?.cancel();
        _beat = Timer(const Duration(seconds: 30), () {
          _armHeartbeat();
          unawaited(_refreshBridge());
        });
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
        if (_lastMsgPreview.isNotEmpty && mounted) {
          await showDialog<void>(
            context: context,
            builder: (ctx) => AlertDialog(
              title: Text(_lastMsgSender.isEmpty ? 'Messaggio' : _lastMsgSender),
              content: Text(_lastMsgPreview),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(ctx).pop(),
                  child: const Text('OK'),
                ),
              ],
            ),
          );
        }
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
    _notifs.stop();
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
