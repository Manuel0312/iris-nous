import 'dart:async';

import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../config.dart';
import '../services/auth_store.dart';
import '../services/call_control.dart';
import '../services/call_observer.dart';
import '../services/iris_api.dart';
import '../services/notification_observer.dart';
import '../services/whatsapp_open.dart';
import '../theme/iris_theme.dart';
import 'permissions_screen.dart';
import 'site_shell_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key, required this.store});

  final AuthStore store;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  late final IrisApi _api = IrisApi(widget.store);
  late final CallObserverService _calls = CallObserverService(
    _api,
    onIncomingRing: (caller) => _ensureCallKit(caller),
    onCallIdle: () => _clearCallKitIfRinging(),
  );
  late final NotificationObserverService _notifs = NotificationObserverService(
    _api,
    onMessage: (p) async {
      if (!mounted) return;
      final who = (p['sender'] ?? 'Messaggio').toString();
      final preview = (p['preview'] ?? '').toString();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(preview.isEmpty ? who : '$who: $preview')),
      );
      await _refresh();
    },
  );
  final CallControlService _callControl = CallControlService();
  Timer? _beat;
  Map<String, dynamic>? _status;
  String? _error;
  String? _username;
  bool _busy = false;
  String? _lastOsAction;
  bool _callKitPresented = false;
  bool _callKitAnswered = false;

  @override
  void initState() {
    super.initState();
    widget.store.username().then((u) {
      if (mounted) setState(() => _username = u);
    });
    _refresh();
    _armHeartbeat();
    _calls.onChanged = () {
      if (mounted) setState(() {});
    };
    _calls.start();
    unawaited(_notifs.start());
  }

  Future<void> _ensureCallKit(String caller) async {
    if (_callKitAnswered) return;
    final r = await _callControl.presentIncoming(caller: caller);
    _callKitPresented = r['ok'] == true;
    if (mounted && _callKitPresented) {
      setState(() {
        _lastOsAction =
            'iPhone: schermata chiamata Iris (CallKit) — SÌ/NO rispondono qui';
      });
    }
  }

  Future<void> _clearCallKitIfRinging() async {
    // Non chiudere una CallKit già risposta con SÌ.
    if (_callKitAnswered) {
      _callKitPresented = false;
      return;
    }
    if (_callKitPresented) {
      await _callControl.end();
      _callKitPresented = false;
    }
  }

  void _armHeartbeat({bool fast = false}) {
    _beat?.cancel();
    _beat = Timer.periodic(
      Duration(seconds: fast ? 4 : 15),
      (_) => _refresh(),
    );
  }

  @override
  void dispose() {
    _beat?.cancel();
    _calls.stop();
    _notifs.stop();
    super.dispose();
  }

  Future<void> _refresh() async {
    try {
      final body = await _api.heartbeat();
      if (!mounted) return;
      setState(() {
        _status = body;
        _error = null;
        final u = body['username'] as String?;
        if (u != null && u.isNotEmpty) _username = u;
      });
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
      _armHeartbeat(fast: active || (_status?['context'] is Map &&
          (((_status!['context'] as Map)['incoming_call'] == true) ||
              ((_status!['context'] as Map)['unread_message'] == true) ||
              ((_status!['context'] as Map)['music_playing'] == true))));
    } on IrisApiException catch (e) {
      if (!mounted) return;
      if (e.statusCode == 401 || e.statusCode == 403) {
        await widget.store.clear();
        if (!mounted) return;
        Navigator.of(context).pushReplacement(
          MaterialPageRoute<void>(
            builder: (_) => SiteShellScreen(store: widget.store),
          ),
        );
        return;
      }
      setState(() => _error = e.message);
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = 'Errore rete: $e');
    }
  }

  Future<void> _demoCall(String event) async {
    setState(() => _busy = true);
    try {
      await _api.sendEvent(event, caller: 'Demo');
      if (event == 'call_incoming') {
        _callKitAnswered = false;
        await _ensureCallKit('Demo');
      } else if (event == 'call_ended') {
        _callKitAnswered = false;
        await _callControl.end();
        _callKitPresented = false;
      }
      await _refresh();
    } on IrisApiException catch (e) {
      setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _musicNext() async {
    setState(() => _busy = true);
    try {
      final r = await _api.musicNext();
      if (!mounted) return;
      final detail = r['detail']?.toString();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            r['status'] == 'ok'
                ? 'Prossima canzone inviata a Spotify'
                : (detail ?? 'Spotify non disponibile'),
          ),
        ),
      );
      await _refresh();
    } on IrisApiException catch (e) {
      setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _busy = false);
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
        final ok = await openWhatsApp(url: url);
        ids.add(id);
        _lastOsAction = ok
            ? 'WhatsApp aperto'
            : 'WhatsApp non trovato su questo telefono';
        if (mounted) setState(() {});
        continue;
      }
      final result = await _callControl.runAction(action);
      ids.add(id);
      final ok = result['ok'] == true;
      final mode = result['mode']?.toString() ?? '';
      if (ok && action.contains('answer')) {
        _callKitAnswered = true;
        _callKitPresented = true;
      }
      if (ok && action.contains('reject')) {
        _callKitAnswered = false;
        _callKitPresented = false;
      }
      _lastOsAction = ok
          ? (mode == 'callkit'
              ? 'iPhone CallKit: ${action.contains('answer') ? 'risposta' : 'rifiuto'}'
              : 'Telefono: ${action.contains('answer') ? 'risposta' : 'rifiuto'} inviato al sistema')
          : 'Telefono OS: ${result['reason'] ?? 'non riuscito'}';
      if (mounted) setState(() {});
    }
    if (ids.isNotEmpty) {
      try {
        await _api.ackCommands(ids);
      } catch (_) {}
    }
  }

  Future<void> _decide(String answer) async {
    setState(() => _busy = true);
    try {
      final r = await _api.decide(answer);
      if (!mounted) return;
      // Immediate OS action if server queued answer/reject (also drained from companion block).
      final companion = r['companion'];
      if (companion is Map<String, dynamic>) {
        await _drainOsCommands(companion);
      } else if (companion is Map) {
        await _drainOsCommands(companion.cast<String, dynamic>());
      }
      final exec = r['execution'];
      if (exec is Map && exec['os_command'] is Map) {
        final cmd = (exec['os_command'] as Map).cast<String, dynamic>();
        final action = cmd['action']?.toString() ?? '';
        if (action == 'open_whatsapp' || action == 'open_url') {
          final preview = exec['message_preview']?.toString() ?? '';
          if (preview.isNotEmpty && mounted) {
            await showDialog<void>(
              context: context,
              builder: (ctx) => AlertDialog(
                title: const Text('Messaggio'),
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
          final url = cmd['url']?.toString() ??
              exec['open_url']?.toString() ??
              'whatsapp://';
          final ok = await openWhatsApp(url: url);
          final id = cmd['id']?.toString();
          if (id != null && id.isNotEmpty) {
            try {
              await _api.ackCommands([id]);
            } catch (_) {}
          }
          _lastOsAction = ok
              ? 'WhatsApp aperto'
              : 'Non riesco ad aprire WhatsApp';
        } else if (action.isNotEmpty) {
          final result = await _callControl.runAction(action);
          final id = cmd['id']?.toString();
          if (id != null && id.isNotEmpty) {
            try {
              await _api.ackCommands([id]);
            } catch (_) {}
          }
          if (result['ok'] == true && action.contains('answer')) {
            _callKitAnswered = true;
            _callKitPresented = true;
          }
          if (result['ok'] == true && action.contains('reject')) {
            _callKitAnswered = false;
            _callKitPresented = false;
          }
          _lastOsAction = result['ok'] == true
              ? 'Chiamata: comando inviato al telefono'
              : 'Chiamata OS non eseguita: ${result['reason'] ?? 'blocco sistema'}';
        }
      }
      final fb = r['feedback']?.toString() ??
          r['message']?.toString() ??
          (answer == 'SI' ? 'SÌ inviato a Iris' : 'NO inviato a Iris');
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(_lastOsAction == null ? fb : '$fb\n$_lastOsAction')),
      );
      await _refresh();
    } on IrisApiException catch (e) {
      setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _openWeb(String path) async {
    final base = await widget.store.baseUrl();
    final uri = Uri.parse('$base$path');
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  Future<void> _logout() async {
    await widget.store.clear();
    if (!mounted) return;
    Navigator.of(context).pushReplacement(
      MaterialPageRoute<void>(
        builder: (_) => SiteShellScreen(store: widget.store),
      ),
    );
  }

  Future<void> _demoMessage() async {
    setState(() => _busy = true);
    try {
      await _api.sendEvent(
        'message_incoming',
        caller: 'Marco',
        sender: 'Marco',
        preview: 'Ciao, ci vediamo più tardi?',
        app: 'WhatsApp',
      );
      await _refresh();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Messaggio pronto (con anteprima). Tocca SÌ per leggerlo e aprire WhatsApp.',
          ),
        ),
      );
    } on IrisApiException catch (e) {
      setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Map<String, dynamic> _eco() {
    final raw = _status?['ecosystem'];
    if (raw is Map) return raw.cast<String, dynamic>();
    return {
      'cuffia': {
        'done': _status?['calibration_complete'] == true,
        'linked': _status?['headset_linked'] == true,
      },
      'telefono': {'done': _status?['phone_paired'] == true},
      'canali': {
        'done': _status?['spotify_linked'] == true,
        'spotify': _status?['spotify_linked'] == true,
      },
    };
  }

  @override
  Widget build(BuildContext context) {
    final ctx = (_status?['context'] as Map?)?.cast<String, dynamic>() ?? {};
    final focus = (ctx['focus'] as Map?)?.cast<String, dynamic>();
    final call = ctx['incoming_call'] == true;
    final music = ctx['music_playing'] == true;
    final caller = (ctx['caller_name'] as String?) ?? '';
    final track = (ctx['track_hint'] as String?) ?? '';
    final spotify = _status?['spotify_linked'] == true;
    final eco = _eco();
    final cuffiaDone = (eco['cuffia'] as Map?)?['done'] == true;
    final telefonoDone = (eco['telefono'] as Map?)?['done'] == true;
    final canaliDone = (eco['canali'] as Map?)?['done'] == true;
    final accent = Theme.of(context).colorScheme.primary;

    final media = MediaQuery.of(context);
    final padH = media.size.width >= 720 ? 32.0 : 20.0;
    final wideEco = media.size.width >= 560;

    Widget ecoSteps() {
      final cuffia = _EcoStepCard(
        mark: '1',
        title: 'Cuffia',
        done: cuffiaDone,
        subtitle: cuffiaDone ? 'Pronta' : 'Da configurare',
        onTap: () => _openWeb(IrisConfig.webCuffia),
      );
      final telefono = _EcoStepCard(
        mark: '2',
        title: 'Telefono',
        done: telefonoDone,
        subtitle: telefonoDone ? 'Collegato' : 'Da collegare',
        onTap: () => _openWeb(IrisConfig.webTelefonoSetup),
      );
      final canali = _EcoStepCard(
        mark: '3',
        title: 'Canali',
        done: canaliDone,
        subtitle: canaliDone ? 'Spotify pronto' : 'Collega Spotify',
        onTap: () => _openWeb(
          canaliDone ? IrisConfig.webEcosistema : IrisConfig.webSpotify,
        ),
      );
      if (!wideEco) {
        return Column(
          children: [
            cuffia,
            const SizedBox(height: 10),
            telefono,
            const SizedBox(height: 10),
            canali,
          ],
        );
      }
      return Column(
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(child: cuffia),
              const SizedBox(width: 10),
              Expanded(child: telefono),
            ],
          ),
          const SizedBox(height: 10),
          Align(
            alignment: Alignment.center,
            child: FractionallySizedBox(widthFactor: 0.5, child: canali),
          ),
        ],
      );
    }

    return IrisGlassScaffold(
      appBar: AppBar(
        title: const Text('Iris'),
        actions: [
          IconButton(
            tooltip: 'Aggiorna',
            onPressed: _refresh,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 720),
            child: ListView(
        padding: EdgeInsets.fromLTRB(
          padH,
          8,
          padH,
          28 + media.padding.bottom,
        ),
        children: [
          Text(
            _username == null ? 'Benvenuto' : 'Ciao, $_username',
            textAlign: wideEco ? TextAlign.left : TextAlign.center,
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w700,
                  letterSpacing: -0.4,
                ),
          ),
          const SizedBox(height: 6),
          Text(
            'Cuffia, telefono, musica: tutto in un posto.',
            textAlign: wideEco ? TextAlign.left : TextAlign.center,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Colors.black54,
                ),
          ),
          if (_error != null) ...[
            const SizedBox(height: 10),
            Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
          ],
          const SizedBox(height: 18),
          Text('Ecosistema', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
          const SizedBox(height: 10),
          ecoSteps(),
          const SizedBox(height: 8),
          TextButton.icon(
            onPressed: () => _openWeb(IrisConfig.webEcosistema),
            icon: Icon(Icons.open_in_browser, size: 18, color: accent),
            label: Text('Apri Ecosistema', style: TextStyle(color: accent)),
          ),
          const SizedBox(height: 16),
          Text('Stato live', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
          const SizedBox(height: 10),
          _StatusCard(
            title: 'Chiamata',
            value: call ? 'In arrivo${caller.isNotEmpty ? ' · $caller' : ''}' : 'Nessuna',
            tone: call ? const Color(0xFFFFE8CC) : const Color(0xFFF0F0F2),
            accent: accent,
          ),
          const SizedBox(height: 10),
          _StatusCard(
            title: 'Musica',
            value: music
                ? 'In riproduzione${track.isNotEmpty ? ' · $track' : ''}'
                : (spotify
                    ? 'Collegata — metti play su Spotify'
                    : 'Collega Spotify da Ecosistema'),
            tone: music ? const Color(0xFFE0F7FF) : const Color(0xFFF0F0F2),
            accent: accent,
          ),
          const SizedBox(height: 10),
          _StatusCard(
            title: 'Ora',
            value: (focus?['title'] as String?) ?? '—',
            tone: const Color(0xFFE8F6FF),
            accent: accent,
          ),
          const SizedBox(height: 12),
          Text(
            'SÌ / NO',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 6),
          Text(
            'Pensa SÌ o NO. Iris lo applica a ciò che sta succedendo ora.',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.black54),
          ),
          if (_lastOsAction != null) ...[
            const SizedBox(height: 6),
            Text(_lastOsAction!, style: TextStyle(color: accent, fontWeight: FontWeight.w600)),
          ],
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: FilledButton(
                  onPressed: _busy ? null : () => _decide('SI'),
                  child: Text((focus?['yes_label'] as String?) ?? 'Pensa SÌ'),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: OutlinedButton(
                  onPressed: _busy ? null : () => _decide('NO'),
                  child: Text((focus?['no_label'] as String?) ?? 'Pensa NO'),
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),
          Text('Azioni', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              OutlinedButton(
                onPressed: _busy ? null : () => _demoCall('call_incoming'),
                child: const Text('Prova una chiamata'),
              ),
              OutlinedButton(
                onPressed: _busy ? null : () => _demoCall('call_ended'),
                child: const Text('Chiudi chiamata'),
              ),
              OutlinedButton(
                onPressed: _busy ? null : _demoMessage,
                child: const Text('Prova un messaggio'),
              ),
              FilledButton(
                onPressed: _busy ? null : _musicNext,
                child: const Text('Canzone dopo'),
              ),
            ],
          ),
          const SizedBox(height: 8),
          if (_calls.lastSent != null)
            Text('Ultimo segnale: ${_calls.lastSent}',
                style: TextStyle(color: accent, fontWeight: FontWeight.w600)),
          if (_calls.lastError != null)
            Text(_calls.lastError!,
                style: TextStyle(color: Theme.of(context).colorScheme.error)),
          const SizedBox(height: 6),
          Text(
            _calls.listening
                ? 'Iris resta in ascolto anche in background.'
                : (!_calls.permitted
                    ? 'Attiva Chiamate e Notifiche nei Permessi, poi Aggiorna.'
                    : 'Tocca Aggiorna per riprendere.'),
            style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.black54),
          ),
          TextButton(
            onPressed: _busy
                ? null
                : () async {
                    await _calls.start();
                    await _refresh();
                  },
            child: const Text('Riprendi ascolto'),
          ),
          const SizedBox(height: 20),
          _LinkTile(
            icon: Icons.security,
            title: 'Permessi',
            subtitle: 'Solo ciò che serve, quando serve',
            onTap: () {
              Navigator.of(context).push(
                MaterialPageRoute<void>(
                  builder: (_) => PermissionsScreen(store: widget.store),
                ),
              );
            },
          ),
          _LinkTile(
            icon: Icons.hearing,
            title: 'In ascolto',
            subtitle: 'Vedi cosa Iris sta decidendo',
            onTap: () => _openWeb(IrisConfig.webContesto),
          ),
          _LinkTile(
            icon: Icons.person_outline,
            title: 'I tuoi dati',
            subtitle: 'Nome, foto, preferenze',
            onTap: () => _openWeb(IrisConfig.webAnagrafica),
          ),
          _LinkTile(
            icon: Icons.chat_bubble_outline,
            title: 'Chat',
            subtitle: 'Parla con Iris',
            onTap: () => _openWeb(IrisConfig.webChat),
          ),
          const SizedBox(height: 8),
          TextButton(
            onPressed: _logout,
            child: Text(
              'Esci da questo telefono',
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
          ),
        ],
            ),
          ),
        ),
    );
  }
}

class _EcoStepCard extends StatelessWidget {
  const _EcoStepCard({
    required this.mark,
    required this.title,
    required this.subtitle,
    required this.done,
    required this.onTap,
  });

  final String mark;
  final String title;
  final String subtitle;
  final bool done;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final accent = Theme.of(context).colorScheme.primary;
    return GlassPane(
      padding: EdgeInsets.zero,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(22),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(12, 14, 12, 14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      width: 28,
                      height: 28,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: accent.withValues(alpha: 0.14),
                        border: Border.all(color: accent.withValues(alpha: 0.35)),
                      ),
                      child: Text(
                        mark,
                        style: TextStyle(
                          fontWeight: FontWeight.w700,
                          color: accent,
                          fontSize: 13,
                        ),
                      ),
                    ),
                    const Spacer(),
                    if (done) Icon(Icons.check_circle, size: 18, color: accent),
                  ],
                ),
                const SizedBox(height: 10),
                Text(title, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
                const SizedBox(height: 2),
                Text(subtitle, style: const TextStyle(color: Colors.black54, fontSize: 12.5)),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _StatusCard extends StatelessWidget {
  const _StatusCard({
    required this.title,
    required this.value,
    required this.tone,
    required this.accent,
  });

  final String title;
  final String value;
  final Color tone;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return GlassPane(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: TextStyle(fontWeight: FontWeight.w600, color: accent)),
          const SizedBox(height: 4),
          Text(value, style: const TextStyle(height: 1.3)),
        ],
      ),
    );
  }
}

class _LinkTile extends StatelessWidget {
  const _LinkTile({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      contentPadding: EdgeInsets.zero,
      leading: Icon(icon, color: Theme.of(context).colorScheme.primary),
      title: Text(title),
      subtitle: Text(subtitle),
      onTap: onTap,
    );
  }
}
