package com.example.something

import android.Manifest
import android.annotation.SuppressLint
import android.content.pm.PackageManager
import android.graphics.Color
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.location.Location
import android.os.Bundle
import android.os.CountDownTimer
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material3.Button
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color as ComposeColor
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import com.google.android.gms.location.FusedLocationProviderClient
import com.google.android.gms.location.LocationServices
import kotlin.math.abs
import kotlin.math.sqrt

class MainActivity : ComponentActivity() {

    // State
    private var currentLat by mutableDoubleStateOf(0.0)
    private var currentLon by mutableDoubleStateOf(0.0)
    private var showCameraScreen by mutableStateOf(false)
    private var isListening by mutableStateOf(false)
    private var livenessDone by mutableStateOf(false)
    private var gpsDone by mutableStateOf(false)
    private var statusText by mutableStateOf("Tap Start to verify")
    private var buttonText by mutableStateOf("Start Verification")

    private var timer: CountDownTimer? = null
    private lateinit var sensorManager: SensorManager
    private lateinit var fusedLocationClient: FusedLocationProviderClient

    // Keep reference to unregister properly
    private var accelerometerListener: SensorEventListener? = null

    companion object {
        private const val RECYCLER_LAT = 12.839728
        private const val RECYCLER_LNG = 80.155256
        private const val MAX_DISTANCE_KM = 0.15f
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        sensorManager = getSystemService(SENSOR_SERVICE) as SensorManager
        fusedLocationClient = LocationServices.getFusedLocationProviderClient(this)

        setContent {
            androidx.compose.material3.MaterialTheme {
                if (showCameraScreen) {
                    WasteCameraScreen(
                        latitude = currentLat,
                        longitude = currentLon,
                        onImageCaptured = { file, _, _ ->
                            Toast.makeText(this@MainActivity, "Photo saved: ${file.name}", Toast.LENGTH_LONG).show()
                            showCameraScreen = false
                            statusText = "Photo captured! Ready for upload."
                        },
                        onClose = {
                            showCameraScreen = false
                            statusText = "Verification cancelled"
                        }
                    )
                } else {
                    VerificationScreen()
                }
            }
        }
    }

    @Composable
    fun VerificationScreen() {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .background(ComposeColor(0xFFF5F5F5))
                .padding(32.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            Text(
                text = "Waste Recycler Verification",
                fontSize = 26.sp,
                fontWeight = FontWeight.Bold,
                color = ComposeColor.Black
            )

            Spacer(modifier = Modifier.height(40.dp))

            Text(
                text = statusText,
                fontSize = 18.sp,
                color = if (statusText.contains("success", ignoreCase = true) ||
                    statusText.contains("VERIFIED", ignoreCase = true)
                ) ComposeColor.Green else ComposeColor.Black,
                textAlign = TextAlign.Center
            )

            Spacer(modifier = Modifier.height(60.dp))

            Button(
                onClick = { startVerification() },
                enabled = !isListening,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(60.dp)
            ) {
                Text(buttonText, fontSize = 20.sp)
            }
        }
    }

    private fun startVerification() {
        if (isListening) return

        isListening = true
        livenessDone = false
        gpsDone = false
        statusText = "Checking location..."
        buttonText = "Verifying..."

        checkLocation()
    }

    private fun checkLocation() {
        if (!hasLocationPermission()) {
            permissionLauncher.launch(Manifest.permission.ACCESS_FINE_LOCATION)
            return
        }

        getCurrentLocation { location ->
            if (location == null) {
                endVerification(false, "Unable to get location")
                return@getCurrentLocation
            }

            val distance = distanceInKm(
                location.latitude, location.longitude,
                RECYCLER_LAT, RECYCLER_LNG
            )

            if (distance > MAX_DISTANCE_KM) {
                endVerification(false, "You are ${String.format("%.2f", distance)} km away.\nMust be within 150m!")
                return@getCurrentLocation
            }

            currentLat = location.latitude
            currentLon = location.longitude
            gpsDone = true
            statusText = "Location verified!\nNow SHAKE or TILT your phone"
            buttonText = "Detecting motion..."

            val gesture = if (System.currentTimeMillis() % 2 == 0L) "shake" else "tilt"
            startLivenessDetection(gesture)
            startTimer()
        }
    }

    private val permissionLauncher = registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted) {
            checkLocation()
        } else {
            endVerification(false, "Location permission denied")
        }
    }

    private fun hasLocationPermission() =
        ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED

    @SuppressLint("MissingPermission")
    private fun getCurrentLocation(callback: (Location?) -> Unit) {
        fusedLocationClient.lastLocation
            .addOnSuccessListener { location -> callback(location) }
            .addOnFailureListener { callback(null) }
    }

    private fun distanceInKm(lat1: Double, lon1: Double, lat2: Double, lon2: Double): Float {
        val results = FloatArray(1)
        Location.distanceBetween(lat1, lon1, lat2, lon2, results)
        return results[0] / 1000f
    }

    private fun startLivenessDetection(requiredGesture: String) {
        val sensor = sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)
            ?: run {
                endVerification(false, "Accelerometer not available")
                return
            }

        accelerometerListener = object : SensorEventListener {
            private var lastX = 0f
            private var lastY = 0f
            private var lastZ = 0f

            override fun onSensorChanged(event: SensorEvent?) {
                if (!isListening || livenessDone || event?.sensor?.type != Sensor.TYPE_ACCELEROMETER) return

                val x = event.values[0]
                val y = event.values[1]
                val z = event.values[2]

                if (lastX == 0f && lastY == 0f && lastZ == 0f) {
                    lastX = x; lastY = y; lastZ = z
                    return
                }

                val deltaX = abs(x - lastX)
                val deltaY = abs(y - lastY)
                val deltaZ = abs(z - lastZ)
                lastX = x; lastY = y; lastZ = z

                val acceleration = sqrt(deltaX * deltaX + deltaY * deltaY + deltaZ * deltaZ)
                val isShake = acceleration > 18f
                val isTilt = abs(x) > 9f || abs(y) > 9f

                if ((requiredGesture == "shake" && isShake) || (requiredGesture == "tilt" && isTilt)) {
                    livenessDone = true
                    endVerification(success = true)
                }
            }

            override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {}
        }

        sensorManager.registerListener(
            accelerometerListener,
            sensor,
            SensorManager.SENSOR_DELAY_UI
        )
    }

    private fun startTimer() {
        timer?.cancel()
        timer = object : CountDownTimer(30_000, 1_000) {
            override fun onTick(millisUntilFinished: Long) {
                statusText = "Time left: ${millisUntilFinished / 1000}s\nKeep moving!"
            }

            override fun onFinish() {
                if (!livenessDone) {
                    endVerification(false, "Time expired!")
                }
            }
        }.start()
    }

    private fun stopLivenessDetection() {
        accelerometerListener?.let {
            sensorManager.unregisterListener(it)
            accelerometerListener = null
        }
    }

    private fun endVerification(success: Boolean, reason: String = "") {
        isListening = false
        timer?.cancel()
        stopLivenessDetection()

        if (success && gpsDone) {
            statusText = "VERIFIED SUCCESSFULLY!\nOpening camera..."
            buttonText = "Verified"
            showCameraScreen = true
        } else {
            statusText = "Verification Failed\n$reason"
            buttonText = "Try Again"
        }
    }

    override fun onDestroy() {
        timer?.cancel()
        stopLivenessDetection()
        super.onDestroy()
    }
}