/*
 * SPDX-FileCopyrightText: 2023 Espressif Systems (Shanghai) CO LTD
 *
 * SPDX-License-Identifier: CC0-1.0
 */

#include <string.h>
#include"tts_api.h"
#include <stdio.h>
#include "esp_err.h"
#include "esp_log.h"
#include "esp_http_client.h"
#include "app_audio.h"
#include "app_ui_ctrl.h"
#include "audio_player.h"
#include "esp_crt_bundle.h"
#include "inttypes.h"
#include "cJSON.h"
#include "esp_system.h"
#include <stdint.h>

volatile bool isAudioPlaying = false;

void set_audio_playing(bool state) {
    isAudioPlaying = state;
}

bool get_audio_playing() {
    return isAudioPlaying;
}

static int base64_decode_char(char c) {
    if (c >= 'A' && c <= 'Z') return c - 'A';
    if (c >= 'a' && c <= 'z') return c - 'a' + 26;
    if (c >= '0' && c <= '9') return c - '0' + 52;
    if (c == '+') return 62;
    if (c == '/') return 63;
    return -1;
}

size_t base64_decode(const char *encoded, uint8_t *decoded) {
    size_t out_len = 0;
    int count = 0;
    uint32_t buffer = 0;

    for (size_t i = 0; encoded[i] != '\0'; ++i) {
        if (encoded[i] == '=' || (encoded[i] >= 'A' && encoded[i] <= 'Z') || 
            (encoded[i] >= 'a' && encoded[i] <= 'z') || 
            (encoded[i] >= '0' && encoded[i] <= '9') || 
            encoded[i] == '+' || encoded[i] == '/') {

            buffer = (buffer << 6) | base64_decode_char(encoded[i]);
            count += 6;

            if (count >= 8) {
                count -= 8;
                decoded[out_len++] = (buffer >> count) & 0xFF;
            }
        }
    }

    return out_len;
}

#define VOICE_ID CONFIG_VOICE_ID
#define VOLUME CONFIG_VOLUME_LEVEL

static const char *TAG = "TTS-Api";
// static char http_response_buffer[MAX_FILE_SIZE];
static uint32_t http_response_length = 0;

void generate_uuid(char *uuid_str) {
    uint32_t t1 = esp_random();
    uint16_t t2 = esp_random() & 0xFFFF;
    uint16_t t3 = esp_random() & 0xFFFF;
    uint16_t t4 = esp_random() & 0xFFFF;
    uint32_t t5 = esp_random();

    sprintf(uuid_str, "%08lx-%04x-%04x-%04x-%08lx%04lx", t1, t2, t3, t4, t5>>16, t5 & 0xFFFF);
}

/* Define a function to handle HTTP events during an HTTP request */

static esp_err_t http_event_handler(esp_http_client_event_t *evt)
{
    static char *http_response_buffer = NULL;
    switch (evt->event_id) {
    case HTTP_EVENT_ERROR:
        ESP_LOGE(TAG, "HTTP_EVENT_ERROR");
        break;
    case HTTP_EVENT_ON_CONNECTED:
        ESP_LOGI(TAG, "HTTP_EVENT_ON_CONNECTED");
        break;
    case HTTP_EVENT_HEADER_SENT:
        if (evt->header_key && evt->header_value) {
            ESP_LOGI(TAG, "HTTP Header -> %s: %s", evt->header_key, evt->header_value);
            if (strcmp(evt->header_key, "Content-Type") == 0 && strcmp(evt->header_value, "audio/mpeg") != 0) {
                ESP_LOGE(TAG, "Unexpected content type!");
            }
        } else {
            ESP_LOGE(TAG, "Received NULL header key or value!");
        }
        break;
    case HTTP_EVENT_ON_HEADER:
        // ESP_LOGI(TAG, "HTTP_EVENT_ON_HEADER");
        file_total_len = 0;
        break;
    case HTTP_EVENT_ON_DATA:
        // ESP_LOGI(TAG, "HTTP_EVENT_ON_DATA, len=(%"PRIu32" + %d) [%d]", http_response_length, evt->data_len, MAX_FILE_SIZE);
        
        // 在接收第一块数据时，动态分配内存
        if (http_response_length == 0) {
            http_response_buffer = malloc(MAX_FILE_SIZE);
            if (!http_response_buffer) {
                ESP_LOGE(TAG, "Failed to allocate memory for http_response_buffer");
                return ESP_FAIL; // or handle the error appropriately
            }
        }

        if ((http_response_length + evt->data_len) < MAX_FILE_SIZE) {
            memcpy(http_response_buffer + http_response_length, (char *)evt->data, evt->data_len);
            http_response_length += evt->data_len;
        } else {
            ESP_LOGE(TAG, "Data exceeds MAX_FILE_SIZE. Data might be truncated!");
        }
        break;
    case HTTP_EVENT_ON_FINISH:
        ESP_LOGI(TAG, "HTTP_EVENT_ON_FINISH. Processing received data.");

        cJSON *root = cJSON_Parse(http_response_buffer);
        if (root) {
            cJSON *data = cJSON_GetObjectItem(root, "data");
            if (data && cJSON_IsString(data) && data->valuestring != NULL) {
                size_t decoded_len = base64_decode(data->valuestring, (uint8_t *)audio_rx_buffer);
                if (decoded_len < MAX_FILE_SIZE) {
                    file_total_len = decoded_len;
                } else {
                    ESP_LOGE(TAG, "Decoded audio data exceeds MAX_FILE_SIZE. Data might be truncated!");
                }
            }
            cJSON_Delete(root);
        } else {
            ESP_LOGE(TAG, "Failed to parse JSON from HTTP response.");
        }

        audio_player_play(audio_rx_buffer, file_total_len);
        free(http_response_buffer);
        http_response_length = 0;
        break;
    case HTTP_EVENT_DISCONNECTED:
        ESP_LOGI(TAG, "HTTP_EVENT_DISCONNECTED");
        break;
    case HTTP_EVENT_REDIRECT:
        ESP_LOGI(TAG, "HTTP_EVENT_REDIRECT");
        break;
    }
    return ESP_OK;
}

/* Create Text to Speech request */
#define APPID "bytedance appid"
#define ACCESS_TOKEN "bytedance access token"
#define CLUSTER "volcano_tts"
#define HOST "openspeech.bytedance.com"

esp_err_t text_to_speech_request(const char *message, AUDIO_CODECS_FORMAT code_format)
{
    // 在播放开始时
    set_audio_playing(true);
    char uuid[37];
    generate_uuid(uuid);

    char *api_url = "https://" HOST "/api/v1/tts";
    
    cJSON *request_json = cJSON_CreateObject();

    cJSON *app = cJSON_CreateObject();
    cJSON_AddStringToObject(app, "appid", APPID);
    cJSON_AddStringToObject(app, "token", ACCESS_TOKEN);
    cJSON_AddStringToObject(app, "cluster", CLUSTER);
    cJSON_AddItemToObject(request_json, "app", app);

    cJSON *user = cJSON_CreateObject();
    cJSON_AddStringToObject(user, "uid", "388808087185088");
    cJSON_AddItemToObject(request_json, "user", user);

    cJSON *audio = cJSON_CreateObject();
    cJSON_AddStringToObject(audio, "voice_type", "BV051_streaming");
    cJSON_AddStringToObject(audio, "encoding", "mp3");
    cJSON_AddNumberToObject(audio, "speed_ratio", 1.5);
    cJSON_AddNumberToObject(audio, "volume_ratio", 1.0);
    cJSON_AddNumberToObject(audio, "pitch_ratio", 1.0);
    cJSON_AddItemToObject(request_json, "audio", audio);

    cJSON *req = cJSON_CreateObject();
    cJSON_AddStringToObject(req, "reqid", uuid); // 你需要使用一个UUID库来生成这个
    cJSON_AddStringToObject(req, "text", message);
    cJSON_AddStringToObject(req, "text_type", "plain");
    cJSON_AddStringToObject(req, "operation", "query");
    cJSON_AddNumberToObject(req, "with_frontend", 1);
    cJSON_AddStringToObject(req, "frontend_type", "unitTson");
    cJSON_AddItemToObject(request_json, "request", req);

    char *request_payload = cJSON_Print(request_json);
    if (request_payload == NULL) {
        ESP_LOGE(TAG, "Failed to generate request payload.");
        cJSON_Delete(request_json);
        return ESP_FAIL;
    }
    ESP_LOGD(TAG, "Generated TTS request payload: %s", request_payload);
    cJSON_Delete(request_json);

    esp_http_client_config_t config = {
        .url = api_url,
        .method = HTTP_METHOD_POST,
        .event_handler = http_event_handler,
        .buffer_size = 128000,
        .buffer_size_tx = 4000,
        .timeout_ms = 40000,
        .crt_bundle_attach = esp_crt_bundle_attach,
    };
    
    uint32_t starttime = esp_log_timestamp();
    esp_http_client_handle_t client = esp_http_client_init(&config);
    
    // ESP_LOGI(TAG, "CURL EQUIVALENT REQUEST:");
    // ESP_LOGI(TAG, "curl -X POST '%s'", api_url);

    // Step 2: Log headers
    // ESP_LOGI(TAG, "-H 'Authorization: Bearer;%s'", ACCESS_TOKEN);
    
    // Step 3: Log the body
    // ESP_LOGI(TAG, "--data '%s'", request_payload);
    esp_http_client_set_header(client, "Authorization", "Bearer;" ACCESS_TOKEN);
    esp_http_client_set_post_field(client, request_payload, strlen(request_payload));
    esp_err_t err = esp_http_client_perform(client);

    int status = esp_http_client_get_status_code(client);
    // ESP_LOGI(TAG, "HTTP Response Status Code: %d", status);

    char buffer[512];
    int read_len = esp_http_client_read(client, buffer, sizeof(buffer) - 1);
    if (read_len > 0) {
        buffer[read_len] = '\0';
        // ESP_LOGI(TAG, "HTTP Response: %s", buffer);
    }

    if (err != ESP_OK) {
        ESP_LOGE(TAG, "HTTP GET request failed: %s", esp_err_to_name(err));
    }
    ESP_LOGE(TAG, "[End] create_TTS_request, + offset:%"PRIu32, esp_log_timestamp() - starttime);

    free(request_payload);
    esp_http_client_cleanup(client);
    return err;
}
