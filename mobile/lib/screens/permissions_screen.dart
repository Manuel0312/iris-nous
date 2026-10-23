import 'dart:io' show Platform;

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:permission_handler/permission_handler.dart';

import '../services/auth_store.dart';
import '../services/iris_api.dart';
import '../services/notification_observer.dart';
import '../services/permissions_service.dart';

class PermissionsScreen extends StatefulWidget {
  const PermissionsScreen({super.key, required this.store});

  final AuthStore store;

  @override
  State<PermissionsScreen> createState() => _PermissionsScreenState();
}

class _PermissionsScreenState extends State<PermissionsScreen> {
  final _svc = PermissionsService();
  final Map<String, PermissionStatus> _statuses = {};
  late final NotificationObserverService _notif =
      NotificationObserverService(IrisApi(widget.store));
  bool _notifEnabled = false;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  Future<void> _reload() async {
    for (final item in _svc.catalog()) {
      if (item.permission != null && !item.planned) {
        _statuses[item.id] = await _svc.statusOf(item);
      }
    }
    if (!kIsWeb && Platform.isAndroid) {
      _notifEnabled = await _notif.refreshEnabled();
    }
    if (mounted) setState(() {});
  }

  Future<void> _request(IrisPermissionItem item) async {
    if (item.planned) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Questo permesso non è richiesto in questa versione.')),
      );
      return;
    }
    if (item.id == 'notification_access') {
      await _notif.openSettings();
      await Future<void>.delayed(const Duration(milliseconds: 600));
      await _reload();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            _notifEnabled
                ? 'Accesso alle notifiche attivo.'
                : 'Attiva Iris Nous nell’elenco «Accesso alle notifiche», poi torna qui.',
          ),
        ),
      );
      return;
    }
    if (item.permission == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(item.note.isEmpty ? item.why : item.note)),
      );
      return;
    }
    final status = await _svc.request(item);
    setState(() => _statuses[item.id] = status);
    if (status.isPermanentlyDenied) {
      await openAppSettings();
    }
  }

  @override
  Widget build(BuildContext context) {
    final items = _svc.catalog();
    return Scaffold(
      appBar: AppBar(title: const Text('Permessi')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            'Pochi permessi, solo quelli che servono. Tu scegli quando.',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(height: 1.35),
          ),
          const SizedBox(height: 16),
          ...items.map((item) {
            final st = _statuses[item.id];
            String label;
            if (item.planned) {
              label = 'Non in questa versione';
            } else if (item.id == 'notification_access') {
              label = _notifEnabled ? 'Attivo' : 'Da attivare';
            } else if (item.permission == null) {
              label = 'Informativo';
            } else {
              label = _svc.labelFor(st ?? PermissionStatus.denied);
            }
            return Card(
              margin: const EdgeInsets.only(bottom: 12),
              child: Padding(
                padding: const EdgeInsets.all(14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(item.title, style: const TextStyle(fontWeight: FontWeight.w600)),
                    const SizedBox(height: 6),
                    Text(item.why, style: const TextStyle(height: 1.35)),
                    if (item.note.isNotEmpty) ...[
                      const SizedBox(height: 6),
                      Text(
                        item.note,
                        style: TextStyle(
                          fontSize: 12,
                          color: Colors.black.withOpacity(0.55),
                          height: 1.3,
                        ),
                      ),
                    ],
                    const SizedBox(height: 10),
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            label,
                            style: TextStyle(
                              color: Theme.of(context).colorScheme.primary,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ),
                        FilledButton.tonal(
                          onPressed: item.planned ? null : () => _request(item),
                          child: Text(
                            item.planned
                                ? 'Più avanti'
                                : (item.id == 'notification_access' ? 'Apri impostazioni' : 'Richiedi'),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            );
          }),
        ],
      ),
    );
  }
}
