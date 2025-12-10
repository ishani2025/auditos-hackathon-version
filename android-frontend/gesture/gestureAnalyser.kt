import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import kotlin.math.sqrt

class GestureAnalyzer(
    private val context: Context,
    private val listener: GestureListener
) : SensorEventListener {

    interface GestureListener {
        fun onShakeDetected()
        fun onTiltDetected()
    }

    private val sensorManager = context.getSystemService(Context.SENSOR_SERVICE) as SensorManager
    private val accelerometer = sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)

    private var lastX = 0f
    private var lastY = 0f
    private var lastZ = 0f

    fun start() {
        sensorManager.registerListener(this, accelerometer, SensorManager.SENSOR_DELAY_UI)
    }

    fun stop() {
        sensorManager.unregisterListener(this)
    }

    override fun onSensorChanged(event: SensorEvent?) {
        if (event?.sensor?.type != Sensor.TYPE_ACCELEROMETER) return

        val x = event.values[0]
        val y = event.values[1]
        val z = event.values[2]

        if (lastX == 0f && lastY == 0f) {
            lastX = x; lastY = y; lastZ = z
            return
        }

        val deltaX = x - lastX
        val deltaY = y - lastY
        val deltaZ = z - lastZ

        lastX = x; lastY = y; lastZ = z

        val speed = sqrt(deltaX * deltaX + deltaY * deltaY + deltaZ * deltaZ)

        if (speed > 16f) listener.onShakeDetected()
        if (kotlin.math.abs(x) > 8f || kotlin.math.abs(y) > 8f) listener.onTiltDetected()
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {}
}