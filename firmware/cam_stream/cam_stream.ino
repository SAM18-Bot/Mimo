/*
  ESP32-CAM MJPEG Stream Server
  ─────────────────────────────
  Board:  AI-Thinker ESP32-CAM (or any ESP32-CAM module)
  Flash:  4MB
  Output: MJPEG stream on http://<device-ip>:81/stream

  SETUP:
  1. Install ESP32 board package in Arduino IDE
  2. Set board to "AI Thinker ESP32-CAM"
  3. Set partition scheme to "Huge APP (3MB No OTA)"
  4. Fill in your WiFi credentials below
  5. Flash and check Serial Monitor (115200 baud) for the IP address
  6. Put the IP in your .env: ESP32_STREAM_URL=http://<IP>:81/stream
*/

#include "esp_camera.h"
#include <WiFi.h>
#include "esp_http_server.h"
#include "soc/soc.h"           // Disable brownout problems
#include "soc/rtc_cntl_reg.h"  // Disable brownout problems

// ─── CONFIGURE THESE ─────────────────────────────────────────
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
// ─────────────────────────────────────────────────────────────

// AI-Thinker ESP32-CAM pin map
#define PWDN_GPIO_NUM   32
#define RESET_GPIO_NUM  -1
#define XCLK_GPIO_NUM    0
#define SIOD_GPIO_NUM   26
#define SIOC_GPIO_NUM   27
#define Y9_GPIO_NUM     35
#define Y8_GPIO_NUM     34
#define Y7_GPIO_NUM     39
#define Y6_GPIO_NUM     36
#define Y5_GPIO_NUM     21
#define Y4_GPIO_NUM     19
#define Y3_GPIO_NUM     18
#define Y2_GPIO_NUM      5
#define VSYNC_GPIO_NUM  25
#define HREF_GPIO_NUM   23
#define PCLK_GPIO_NUM   22

#define LED_BUILTIN     33   // onboard LED (active LOW)
#define FLASH_LED       4    // flash LED

httpd_handle_t stream_httpd = NULL;

// ── MJPEG streaming handler ───────────────────────────────────
static esp_err_t stream_handler(httpd_req_t *req) {
  camera_fb_t  *fb     = NULL;
  esp_err_t     res    = ESP_OK;
  char          part_buf[128];

  res = httpd_resp_set_type(req, "multipart/x-mixed-replace; boundary=frame");
  if (res != ESP_OK) return res;

  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  httpd_resp_set_hdr(req, "X-Framerate", "10");

  while (true) {
    fb = esp_camera_fb_get();
    if (!fb) {
      Serial.println("[WARN] Camera frame capture failed");
      res = ESP_FAIL;
      break;
    }

    size_t hlen = snprintf(
      part_buf, sizeof(part_buf),
      "--frame\r\n"
      "Content-Type: image/jpeg\r\n"
      "Content-Length: %zu\r\n\r\n",
      fb->len
    );

    res = httpd_resp_send_chunk(req, part_buf, hlen);
    if (res == ESP_OK) res = httpd_resp_send_chunk(req, (const char *)fb->buf, fb->len);
    if (res == ESP_OK) res = httpd_resp_send_chunk(req, "\r\n", 2);

    esp_camera_fb_return(fb);
    fb = NULL;

    if (res != ESP_OK) break;   // client disconnected
  }

  return res;
}

// ── status handler (useful for health checks) ─────────────────
static esp_err_t status_handler(httpd_req_t *req) {
  httpd_resp_set_type(req, "application/json");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  char json[128];
  snprintf(json, sizeof(json),
    "{\"status\":\"ok\",\"ip\":\"%s\",\"rssi\":%d}",
    WiFi.localIP().toString().c_str(),
    WiFi.RSSI()
  );
  return httpd_resp_sendstr(req, json);
}

// ── start HTTP server ──────────────────────────────────────────
void startCameraServer() {
  httpd_config_t config  = HTTPD_DEFAULT_CONFIG();
  config.server_port     = 81;
  config.max_open_sockets = 3;

  httpd_uri_t stream_uri = {
    .uri      = "/stream",
    .method   = HTTP_GET,
    .handler  = stream_handler,
    .user_ctx = NULL
  };
  httpd_uri_t status_uri = {
    .uri      = "/status",
    .method   = HTTP_GET,
    .handler  = status_handler,
    .user_ctx = NULL
  };

  if (httpd_start(&stream_httpd, &config) == ESP_OK) {
    httpd_register_uri_handler(stream_httpd, &stream_uri);
    httpd_register_uri_handler(stream_httpd, &status_uri);
  }

  Serial.printf("[INFO] Stream:  http://%s:81/stream\n", WiFi.localIP().toString().c_str());
  Serial.printf("[INFO] Status:  http://%s:81/status\n", WiFi.localIP().toString().c_str());
}

// ── camera init ────────────────────────────────────────────────
bool initCamera() {
  camera_config_t config;
  config.ledc_channel  = LEDC_CHANNEL_0;
  config.ledc_timer    = LEDC_TIMER_0;
  config.pin_d0        = Y2_GPIO_NUM;
  config.pin_d1        = Y3_GPIO_NUM;
  config.pin_d2        = Y4_GPIO_NUM;
  config.pin_d3        = Y5_GPIO_NUM;
  config.pin_d4        = Y6_GPIO_NUM;
  config.pin_d5        = Y7_GPIO_NUM;
  config.pin_d6        = Y8_GPIO_NUM;
  config.pin_d7        = Y9_GPIO_NUM;
  config.pin_xclk      = XCLK_GPIO_NUM;
  config.pin_pclk      = PCLK_GPIO_NUM;
  config.pin_vsync     = VSYNC_GPIO_NUM;
  config.pin_href      = HREF_GPIO_NUM;
  config.pin_sscb_sda  = SIOD_GPIO_NUM;
  config.pin_sscb_scl  = SIOC_GPIO_NUM;
  config.pin_pwdn      = PWDN_GPIO_NUM;
  config.pin_reset     = RESET_GPIO_NUM;
  config.xclk_freq_hz  = 20000000;
  config.pixel_format  = PIXFORMAT_JPEG;
  config.frame_size    = FRAMESIZE_VGA;    // 640x480 — good balance
  config.jpeg_quality  = 15;               // 0–63, lower = better quality
  config.fb_count      = 2;               // double-buffer for smoother stream
  config.grab_mode     = CAMERA_GRAB_WHEN_EMPTY;
  config.fb_location   = CAMERA_FB_IN_PSRAM;

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("[ERROR] Camera init failed: 0x%x\n", err);
    return false;
  }

  // Sensor tweaks for better indoor detection
  sensor_t *s = esp_camera_sensor_get();
  if (s) {
    s->set_brightness(s, 1);   // -2 to 2
    s->set_contrast(s, 1);     // -2 to 2
    s->set_saturation(s, 0);
    s->set_special_effect(s, 0);
    s->set_whitebal(s, 1);
    s->set_awb_gain(s, 1);
    s->set_wb_mode(s, 0);
    s->set_exposure_ctrl(s, 1);
    s->set_aec2(s, 0);
    s->set_ae_level(s, 0);
    s->set_aec_value(s, 300);
    s->set_gain_ctrl(s, 1);
    s->set_agc_gain(s, 0);
    s->set_gainceiling(s, (gainceiling_t)0);
    s->set_bpc(s, 0);
    s->set_wpc(s, 1);
    s->set_raw_gma(s, 1);
    s->set_lenc(s, 1);
    s->set_hmirror(s, 0);
    s->set_vflip(s, 0);
    s->set_dcw(s, 1);
    s->set_colorbar(s, 0);
  }

  Serial.println("[INFO] Camera initialized OK.");
  return true;
}

// ── WiFi connect with retry ────────────────────────────────────
void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.printf("[INFO] Connecting to %s", WIFI_SSID);

  int retries = 0;
  while (WiFi.status() != WL_CONNECTED && retries < 30) {
    delay(500);
    Serial.print(".");
    retries++;
    digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));  // blink while connecting
  }
  Serial.println();

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[ERROR] WiFi connection failed — restarting in 5s");
    delay(5000);
    ESP.restart();
  }

  digitalWrite(LED_BUILTIN, LOW);   // LED off = connected
  Serial.printf("[INFO] Connected! IP: %s  Signal: %d dBm\n",
    WiFi.localIP().toString().c_str(), WiFi.RSSI());
}

// ── setup ─────────────────────────────────────────────────────────────
void setup() {
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0); // Disable brownout detector

  Serial.begin(115200);
  Serial.println("\n\n[INFO] ESP32-CAM Accountability System Node");

  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(FLASH_LED,   OUTPUT);
  digitalWrite(LED_BUILTIN, HIGH);   // LED on = starting
  digitalWrite(FLASH_LED,   LOW);    // Flash off

  if (!initCamera()) {
    Serial.println("[ERROR] Camera init failed — halting.");
    while (true) { delay(1000); }
  }

  connectWiFi();
  startCameraServer();

  // Quick flash to signal ready
  for (int i = 0; i < 3; i++) {
    digitalWrite(FLASH_LED, HIGH); delay(100);
    digitalWrite(FLASH_LED, LOW);  delay(100);
  }

  Serial.println("[INFO] Ready. Streaming...");
}

// ── loop ───────────────────────────────────────────────────────
void loop() {
  // Watchdog: reconnect WiFi if it drops
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[WARN] WiFi lost — reconnecting...");
    WiFi.reconnect();
    delay(5000);
    if (WiFi.status() != WL_CONNECTED) {
      Serial.println("[ERROR] Reconnect failed — restarting");
      ESP.restart();
    }
  }
  delay(5000);
}
