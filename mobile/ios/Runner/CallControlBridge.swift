import AVFoundation
import CallKit
import Flutter
import Foundation
import UIKit

/// Bypass iOS sul cellulare del gestore: Iris possiede una chiamata CallKit (VoIP UI nativa).
/// SÌ/NO rispondono/rifiutano *quella* schermata sistema — stesso aspetto di una chiamata vera.
final class CallControlBridge: NSObject, CXProviderDelegate {
  static let channelName = "com.irisnous.mobile/call_control"

  private var channel: FlutterMethodChannel?
  private let provider: CXProvider
  private let controller = CXCallController()
  private var activeUUID: UUID?
  private var ringing = false

  override init() {
    let config = CXProviderConfiguration(localizedName: "Iris Nous")
    config.supportsVideo = false
    config.maximumCallsPerCallGroup = 1
    config.maximumCallGroups = 1
    config.supportedHandleTypes = [.generic, .phoneNumber]
    if let icon = UIImage(systemName: "brain.head.profile") {
      config.iconTemplateImageData = icon.pngData()
    }
    provider = CXProvider(configuration: config)
    super.init()
    provider.setDelegate(self, queue: nil)
  }

  func attach(messenger: FlutterBinaryMessenger) {
    let ch = FlutterMethodChannel(name: Self.channelName, binaryMessenger: messenger)
    channel = ch
    ch.setMethodCallHandler { [weak self] call, result in
      guard let self else {
        result(FlutterError(code: "gone", message: nil, details: nil))
        return
      }
      switch call.method {
      case "capabilities":
        result([
          "platform": "ios",
          "canAnswerReject": true,
          "mode": "callkit",
          "hasPermission": true,
          "active": self.activeUUID != nil,
          "ringing": self.ringing,
        ])
      case "presentIncoming":
        let args = call.arguments as? [String: Any]
        let caller = (args?["caller"] as? String)?.trimmingCharacters(in: .whitespacesAndNewlines)
        self.presentIncoming(caller: (caller?.isEmpty == false) ? caller! : "Chiamata Iris") { map in
          result(map)
        }
      case "answer":
        self.answer { map in result(map) }
      case "reject":
        self.reject { map in result(map) }
      case "end":
        self.endCall { map in result(map) }
      default:
        result(FlutterMethodNotImplemented)
      }
    }
  }

  private func presentIncoming(caller: String, completion: @escaping ([String: Any]) -> Void) {
    if let existing = activeUUID, ringing {
      completion(["ok": true, "action": "already_ringing", "uuid": existing.uuidString])
      return
    }
    if activeUUID != nil {
      // Replace stale call.
      endCall { _ in
        self.startNewIncoming(caller: caller, completion: completion)
      }
      return
    }
    startNewIncoming(caller: caller, completion: completion)
  }

  private func startNewIncoming(caller: String, completion: @escaping ([String: Any]) -> Void) {
    let uuid = UUID()
    let update = CXCallUpdate()
    update.remoteHandle = CXHandle(type: .generic, value: caller)
    update.localizedCallerName = caller
    update.hasVideo = false
    update.supportsHolding = false
    update.supportsGrouping = false
    update.supportsUngrouping = false
    update.supportsDTMF = false

    provider.reportNewIncomingCall(with: uuid, update: update) { [weak self] error in
      guard let self else { return }
      if let error {
        completion([
          "ok": false,
          "reason": "callkit_report_failed",
          "detail": error.localizedDescription,
        ])
        return
      }
      self.activeUUID = uuid
      self.ringing = true
      completion([
        "ok": true,
        "action": "present_incoming",
        "uuid": uuid.uuidString,
        "mode": "callkit",
      ])
    }
  }

  private func answer(completion: @escaping ([String: Any]) -> Void) {
    guard let uuid = activeUUID else {
      // Nessuna CallKit attiva: presentiamo e rispondiamo subito (SÌ tardivo).
      presentIncoming(caller: "Iris") { [weak self] presented in
        guard let self else { return }
        if presented["ok"] as? Bool != true {
          completion(presented)
          return
        }
        self.requestAnswer(completion: completion)
      }
      return
    }
    _ = uuid
    requestAnswer(completion: completion)
  }

  private func requestAnswer(completion: @escaping ([String: Any]) -> Void) {
    guard let uuid = activeUUID else {
      completion(["ok": false, "reason": "no_active_call"])
      return
    }
    activateAudioSession()
    let action = CXAnswerCallAction(call: uuid)
    let tx = CXTransaction(action: action)
    controller.request(tx) { [weak self] error in
      if let error {
        completion([
          "ok": false,
          "reason": "answer_failed",
          "detail": error.localizedDescription,
        ])
        return
      }
      self?.ringing = false
      completion(["ok": true, "action": "answer", "mode": "callkit", "uuid": uuid.uuidString])
    }
  }

  private func reject(completion: @escaping ([String: Any]) -> Void) {
    guard let uuid = activeUUID else {
      completion(["ok": false, "reason": "no_active_call"])
      return
    }
    let action = CXEndCallAction(call: uuid)
    let tx = CXTransaction(action: action)
    controller.request(tx) { [weak self] error in
      if let error {
        completion([
          "ok": false,
          "reason": "reject_failed",
          "detail": error.localizedDescription,
        ])
        return
      }
      self?.ringing = false
      self?.activeUUID = nil
      completion(["ok": true, "action": "reject", "mode": "callkit", "uuid": uuid.uuidString])
    }
  }

  private func endCall(completion: @escaping ([String: Any]) -> Void) {
    guard let uuid = activeUUID else {
      completion(["ok": true, "action": "already_idle"])
      return
    }
    let action = CXEndCallAction(call: uuid)
    let tx = CXTransaction(action: action)
    controller.request(tx) { [weak self] error in
      self?.ringing = false
      self?.activeUUID = nil
      if let error {
        // Force-clear local state even if system rejects.
        self?.provider.reportCall(with: uuid, endedAt: Date(), reason: .remoteEnded)
        completion([
          "ok": false,
          "reason": "end_failed",
          "detail": error.localizedDescription,
        ])
        return
      }
      completion(["ok": true, "action": "end", "mode": "callkit"])
    }
  }

  private func activateAudioSession() {
    let session = AVAudioSession.sharedInstance()
    do {
      try session.setCategory(.playAndRecord, mode: .voiceChat, options: [.allowBluetooth])
      try session.setActive(true, options: [])
    } catch {
      // CallKit may still answer UI without audio — demo-safe.
    }
  }

  // MARK: - CXProviderDelegate

  func providerDidReset(_ provider: CXProvider) {
    activeUUID = nil
    ringing = false
  }

  func provider(_ provider: CXProvider, perform action: CXAnswerCallAction) {
    activateAudioSession()
    ringing = false
    action.fulfill()
    channel?.invokeMethod("onCallKit", arguments: ["event": "answered", "uuid": action.callUUID.uuidString])
  }

  func provider(_ provider: CXProvider, perform action: CXEndCallAction) {
    ringing = false
    activeUUID = nil
    action.fulfill()
    channel?.invokeMethod("onCallKit", arguments: ["event": "ended", "uuid": action.callUUID.uuidString])
  }

  func provider(_ provider: CXProvider, perform action: CXStartCallAction) {
    action.fulfill()
  }

  func provider(_ provider: CXProvider, didActivate audioSession: AVAudioSession) {
    activateAudioSession()
  }
}
