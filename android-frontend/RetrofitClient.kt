package com.example.something.network

import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

/**
 * Singleton object that creates and provides Retrofit instance
 * Using 'object' means only one instance exists in the app
 */
object RetrofitClient {

    // ============ CONFIGURATION ============
    // ⚠️ VERY IMPORTANT: Change this to your computer's actual IP address!
    // Find your IP:
    // - Windows: ipconfig (look for IPv4)
    // - Mac/Linux: ifconfig
    // Format: "http://192.168.1.100:5000/"
    private const val BASE_URL = "http://172.16.44.191:5000/"

    // ============ LOGGING INTERCEPTOR ============
    /**
     * This interceptor logs all network requests and responses
     * Helpful for debugging - shows what's being sent/received
     */
    private val loggingInterceptor = HttpLoggingInterceptor().apply {
        // Choose logging level:
        // NONE = no logs
        // BASIC = request method, URL, response code
        // HEADERS = BASIC + headers
        // BODY = HEADERS + request/response body (shows JSON)
        level = HttpLoggingInterceptor.Level.BODY
    }

    // ============ HTTP CLIENT CONFIGURATION ============
    /**
     * OkHttpClient handles the actual HTTP requests
     * We configure timeouts and add interceptors here
     */
    private val okHttpClient = OkHttpClient.Builder()
        .addInterceptor(loggingInterceptor)  // Add logging
        .connectTimeout(60, TimeUnit.SECONDS) // Max time to connect to server
        .readTimeout(60, TimeUnit.SECONDS)    // Max time to read response
        .writeTimeout(60, TimeUnit.SECONDS)   // Max time to send request
        .build()

    // ============ RETROFIT INSTANCE ============
    /**
     * Retrofit is the main library that converts our interface into network calls
     * Using 'by lazy' means it's created only when first needed
     */
    private val retrofit: Retrofit by lazy {
        Retrofit.Builder()
            .baseUrl(BASE_URL)  // All requests start with this base URL
            .client(okHttpClient)  // Use our configured HTTP client
            .addConverterFactory(GsonConverterFactory.create()) // Convert JSON ↔ Kotlin objects
            .build()
    }

    // ============ API SERVICE ACCESS ============
    /**
     * Provides access to our ApiService interface
     * Retrofit automatically implements the interface for us
     */
    val apiService: ApiService by lazy {
        retrofit.create(ApiService::class.java)
    }

    // ============ HELPER FUNCTIONS ============
    /**
     * Call this to check if server is reachable
     */
    fun testConnection() {
        // Implementation would go here
        println("Testing connection to: $BASE_URL")
    }
}