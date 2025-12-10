package com.example.something.viewmodel

import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.something.network.ApiService
import com.example.something.network.RetrofitClient
import com.example.something.network.UploadResponse
import kotlinx.coroutines.launch
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response
import java.io.File

sealed class UploadResult {
    object Loading : UploadResult()
    data class Success(val data: UploadResponse) : UploadResult()
    data class Error(val message: String) : UploadResult()
}

class UploadViewModel : ViewModel() {
    private val apiService: ApiService = RetrofitClient.apiService
    private val _uploadResult = MutableLiveData<UploadResult>()
    val uploadResult: LiveData<UploadResult> = _uploadResult

    fun uploadImage(imageFile: File, latitude: Double, longitude: Double) {
        viewModelScope.launch {
            println("🚀 DEBUG: Upload STARTED - ${imageFile.name}")
            _uploadResult.postValue(UploadResult.Loading)

            try {
                println("📱 DEBUG: Creating multipart request...")

                // Prepare image part
                val requestFile = imageFile.asRequestBody("image/*".toMediaTypeOrNull())
                val imagePart = MultipartBody.Part.createFormData(
                    "image",
                    imageFile.name,
                    requestFile
                )

                // Prepare text parts
                val latPart = latitude.toString().toRequestBody("text/plain".toMediaTypeOrNull())
                val lonPart = longitude.toString().toRequestBody("text/plain".toMediaTypeOrNull())
                val deviceId = "android_${android.os.Build.MODEL}".toRequestBody("text/plain".toMediaTypeOrNull())
                val timestamp = System.currentTimeMillis().toString().toRequestBody("text/plain".toMediaTypeOrNull())

                println("📤 DEBUG: Making API call to upload endpoint")
                println("📤 DEBUG: Image size: ${imageFile.length()} bytes")
                println("📤 DEBUG: Latitude: $latitude, Longitude: $longitude")

                // Make the API call with enqueue (non-blocking)
                apiService.uploadImage(
                    image = imagePart,
                    latitude = latPart,
                    longitude = lonPart,
                    deviceId = deviceId,
                    timestamp = timestamp
                ).enqueue(object : Callback<UploadResponse> {
                    override fun onResponse(
                        call: Call<UploadResponse>,
                        response: Response<UploadResponse>
                    ) {
                        println("📥 DEBUG: Response code: ${response.code()}")
                        println("📥 DEBUG: Response message: ${response.message()}")

                        if (response.isSuccessful && response.body() != null) {
                            println("✅ DEBUG: Upload SUCCESS!")
                            println("✅ DEBUG: Response: ${response.body()}")
                            _uploadResult.postValue(UploadResult.Success(response.body()!!))
                        } else {
                            val errorBody = response.errorBody()?.string()
                            println("❌ DEBUG: Server error body: $errorBody")
                            println("❌ DEBUG: Server error code: ${response.code()}")
                            _uploadResult.postValue(
                                UploadResult.Error(
                                    "Server error: ${response.code()} - ${response.message()}"
                                )
                            )
                        }
                    }

                    override fun onFailure(call: Call<UploadResponse>, t: Throwable) {
                        println("💥 DEBUG: Network failure: ${t.message}")
                        println("💥 DEBUG: Failure type: ${t.javaClass.simpleName}")
                        t.printStackTrace()
                        _uploadResult.postValue(UploadResult.Error("Network error: ${t.message}"))
                    }
                })

            } catch (e: Exception) {
                println("💥 DEBUG: Exception caught in try block: ${e.javaClass.simpleName}")
                println("💥 DEBUG: Exception message: ${e.message}")
                e.printStackTrace()
                _uploadResult.postValue(UploadResult.Error("Setup error: ${e.message}"))
            }
        }
    }

    fun testConnection() {
        viewModelScope.launch {
            try {
                val response = apiService.testConnection().execute()
                if (response.isSuccessful) {
                    println("✅ Connection successful: ${response.body()}")
                } else {
                    println("❌ Connection failed: ${response.code()}")
                }
            } catch (e: Exception) {
                println("❌ Network error: ${e.message}")
            }
        }
    }
}