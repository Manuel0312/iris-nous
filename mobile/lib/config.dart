/// Configurazione Iris Nous companion.
class IrisConfig {
  IrisConfig._();

  /// Backend pubblico (Render). Override in debug se serve locale.
  static const String defaultBaseUrl = 'https://iris-nous.onrender.com';

  static const String pairPath = '/api/companion/pair';
  static const String heartbeatPath = '/api/companion/heartbeat';
  static const String statusPath = '/api/companion/status';
  static const String eventPath = '/api/companion/event';
  static const String musicNextPath = '/api/companion/music/next';

  static const String webTelefonoSetup = '/telefono-setup';
  static const String webContesto = '/contesto';
  static const String webCuffia = '/cuffia';
}
