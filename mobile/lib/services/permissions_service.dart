import 'dart:io' show Platform;

import 'package:flutter/foundation.dart';
import 'package:permission_handler/permission_handler.dart';

class IrisPermissionItem {
  const IrisPermissionItem({
    required this.id,
    required this.title,
    required this.why,
    required this.permission,
    this.androidOnly = false,
    this.iosOnly = false,
    this.planned = false,
    this.note = '',
  });

  final String id;
  final String title;
  final String why;
  final Permission? permission;
  final bool androidOnly;
  final bool iosOnly;
  final bool planned;
  final String note;
}

class PermissionsService {
  List<IrisPermissionItem> catalog() {
    final items = <IrisPermissionItem>[
      const IrisPermissionItem(
        id: 'phone',
        title: 'Chiamate',
        why: 'Così Iris sa quando squilla e può aiutarti a rispondere o rifiutare.',
        permission: Permission.phone,
        androidOnly: true,
        note: 'Solo su Android. Tu resti sempre in controllo.',
      ),
      const IrisPermissionItem(
        id: 'notification',
        title: 'Notifiche',
        why: 'Per restare con te anche con lo schermo spento.',
        permission: Permission.notification,
        note: 'Brevi avvisi, niente spam.',
      ),
      const IrisPermissionItem(
        id: 'camera',
        title: 'Fotocamera',
        why: 'Solo per leggere il codice e collegarti in un attimo.',
        permission: Permission.camera,
        note: 'Niente foto salvate senza che lo chiedi tu.',
      ),
      const IrisPermissionItem(
        id: 'ignore_battery',
        title: 'Sempre attiva',
        why: 'Evita che il telefono spenga Iris mentre non guardi.',
        permission: Permission.ignoreBatteryOptimizations,
        androidOnly: true,
        note: 'Consigliato per le chiamate in background.',
      ),
      const IrisPermissionItem(
        id: 'ios_callkit',
        title: 'Chiamate (iPhone)',
        why: 'Iris può avvisarti quando arriva una chiamata.',
        permission: null,
        iosOnly: true,
        note: 'Su iPhone rispondere al gestore resta a te.',
      ),
      const IrisPermissionItem(
        id: 'sms',
        title: 'Messaggi',
        why: 'Presto Iris potrà avvisarti anche qui.',
        permission: null,
        planned: true,
        note: 'Non ancora attivo.',
      ),
    ];

    if (kIsWeb) return items;
    if (Platform.isAndroid) {
      return items.where((e) => !e.iosOnly).toList();
    }
    if (Platform.isIOS) {
      return items.where((e) => !e.androidOnly).toList();
    }
    return items;
  }

  Future<PermissionStatus> statusOf(IrisPermissionItem item) async {
    if (item.permission == null || item.planned) {
      return PermissionStatus.denied;
    }
    return item.permission!.status;
  }

  Future<PermissionStatus> request(IrisPermissionItem item) async {
    if (item.planned || item.permission == null) {
      return PermissionStatus.denied;
    }
    return item.permission!.request();
  }

  String labelFor(PermissionStatus s) {
    switch (s) {
      case PermissionStatus.granted:
      case PermissionStatus.limited:
        return 'Attivo';
      case PermissionStatus.denied:
        return 'Da attivare';
      case PermissionStatus.permanentlyDenied:
        return 'Apri Impostazioni';
      case PermissionStatus.restricted:
        return 'Limitato';
      case PermissionStatus.provisional:
        return 'Provvisorio';
    }
  }
}
