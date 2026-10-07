package com.irisnous.mobile

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.telephony.PhoneStateListener
import android.telephony.TelephonyCallback
import android.telephony.TelephonyManager
import androidx.core.content.ContextCompat
import io.flutter.embedding.engine.plugins.FlutterPlugin
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel

/**
 * Osserva lo stato chiamata (squillo / attiva / idle) e lo invia a Flutter
 * sullo stesso canale iOS: com.irisnous.mobile/call_observer
 *
 * Non risponde né rifiuta la tipica chiamata cellulare.
 */
class CallObserverPlugin : FlutterPlugin, MethodChannel.MethodCallHandler {
    private lateinit var channel: MethodChannel
    private var appContext: Context? = null
    private var telephony: TelephonyManager? = null
    private var modernCallback: TelephonyCallback? = null
    private var legacyListener: PhoneStateListener? = null
    private var listening = false
    private var lastState: Int = TelephonyManager.CALL_STATE_IDLE

    override fun onAttachedToEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        appContext = binding.applicationContext
        telephony = binding.applicationContext.getSystemService(Context.TELEPHONY_SERVICE) as TelephonyManager
        channel = MethodChannel(binding.binaryMessenger, CHANNEL)
        channel.setMethodCallHandler(this)
    }

    override fun onDetachedFromEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        stopListening()
        channel.setMethodCallHandler(null)
        appContext = null
        telephony = null
    }

    override fun onMethodCall(call: MethodCall, result: MethodChannel.Result) {
        when (call.method) {
            "start" -> {
                val ok = startListening()
                result.success(ok)
            }
            "stop" -> {
                stopListening()
                result.success(true)
            }
            "snapshot" -> result.success(snapshotMap(lastState))
            else -> result.notImplemented()
        }
    }

    private fun hasPhonePermission(): Boolean {
        val ctx = appContext ?: return false
        return ContextCompat.checkSelfPermission(ctx, Manifest.permission.READ_PHONE_STATE) ==
            PackageManager.PERMISSION_GRANTED
    }

    private fun startListening(): Boolean {
        if (listening) {
            emit(lastState, force = true)
            return true
        }
        if (!hasPhonePermission()) {
            emit(TelephonyManager.CALL_STATE_IDLE, force = true, permitted = false)
            return false
        }
        val tm = telephony ?: return false
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            val cb = object : TelephonyCallback(), TelephonyCallback.CallStateListener {
                override fun onCallStateChanged(state: Int) {
                    lastState = state
                    emit(state)
                }
            }
            modernCallback = cb
            tm.registerTelephonyCallback(appContext!!.mainExecutor, cb)
        } else {
            @Suppress("DEPRECATION")
            val listener = object : PhoneStateListener() {
                @Deprecated("Deprecated in Java")
                override fun onCallStateChanged(state: Int, phoneNumber: String?) {
                    lastState = state
                    emit(state)
                }
            }
            legacyListener = listener
            @Suppress("DEPRECATION")
            tm.listen(listener, PhoneStateListener.LISTEN_CALL_STATE)
        }
        listening = true
        // Stato iniziale non sempre notificato: emetti idle.
        emit(TelephonyManager.CALL_STATE_IDLE, force = true)
        return true
    }

    private fun stopListening() {
        val tm = telephony
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            modernCallback?.let { cb ->
                try {
                    tm?.unregisterTelephonyCallback(cb)
                } catch (_: Exception) {
                }
            }
            modernCallback = null
        } else {
            @Suppress("DEPRECATION")
            legacyListener?.let { tm?.listen(it, PhoneStateListener.LISTEN_NONE) }
            legacyListener = null
        }
        listening = false
    }

    private fun snapshotMap(state: Int, permitted: Boolean = true): Map<String, Any> {
        val ringing = state == TelephonyManager.CALL_STATE_RINGING
        val connected = state == TelephonyManager.CALL_STATE_OFFHOOK
        val anyActive = ringing || connected
        return mapOf(
            "callCount" to if (anyActive) 1 else 0,
            "incomingRinging" to ringing,
            "connected" to connected,
            "anyActive" to anyActive,
            "hasOutgoing" to false,
            "platform" to "android",
            "permitted" to permitted,
            "rawState" to state,
        )
    }

    private fun emit(state: Int, force: Boolean = false, permitted: Boolean = true) {
        channel.invokeMethod("onCallState", snapshotMap(state, permitted))
    }

    companion object {
        const val CHANNEL = "com.irisnous.mobile/call_observer"
    }
}
