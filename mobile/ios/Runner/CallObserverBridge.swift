import Flutter
import Foundation
import CallKit

/// Osserva lo stato delle chiamate cellulari (squillo / attiva / fine)
/// e lo inoltra a Flutter → API companion Iris.
///
/// Limite Apple: non possiamo rispondere o rifiutare la tipica chiamata cellulare.
final class CallObserverBridge: NSObject, CXCallObserverDelegate {
  static let channelName = "com.irisnous.mobile/call_observer"

  private let observer = CXCallObserver()
  private var channel: FlutterMethodChannel?
  private var lastSignature: String = ""

  func attach(messenger: FlutterBinaryMessenger) {
    let ch = FlutterMethodChannel(name: Self.channelName, binaryMessenger: messenger)
    channel = ch
    observer.setDelegate(self, queue: nil)
    ch.setMethodCallHandler { [weak self] call, result in
      guard let self else {
        result(FlutterError(code: "gone", message: nil, details: nil))
        return
      }
      switch call.method {
      case "start":
        self.emit(force: true)
        result(true)
      case "stop":
        result(true)
      case "snapshot":
        result(self.snapshotDict())
      default:
        result(FlutterMethodNotImplemented)
      }
    }
    emit(force: true)
  }

  func callObserver(_ callObserver: CXCallObserver, callChanged call: CXCall) {
    emit(force: false)
  }

  private func snapshotDict() -> [String: Any] {
    let calls = observer.calls
    // isOutgoing == true → uscita; false → entrata (squillo in arrivo se non connessa)
    let hasOutgoing = calls.contains { $0.isOutgoing && !$0.hasEnded }
    let ringing = calls.contains { !$0.hasConnected && !$0.hasEnded && !$0.isOutgoing }
    let connected = calls.contains { $0.hasConnected && !$0.hasEnded }
    let anyActive = calls.contains { !$0.hasEnded }
    return [
      "callCount": calls.count,
      "incomingRinging": ringing,
      "connected": connected,
      "anyActive": anyActive,
      "hasOutgoing": hasOutgoing,
    ]
  }

  private func emit(force: Bool) {
    let snap = snapshotDict()
    let signature = "\(snap["incomingRinging"]!)|\(snap["connected"]!)|\(snap["anyActive"]!)|\(snap["callCount"]!)"
    if !force && signature == lastSignature { return }
    lastSignature = signature
    channel?.invokeMethod("onCallState", arguments: snap)
  }
}
