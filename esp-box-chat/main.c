/*
 * SPDX-FileCopyrightText: 2023 Espressif Systems (Shanghai) CO LTD
 *
 * SPDX-License-Identifier: CC0-1.0
 */

#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"
#include "esp_system.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "app_ui_ctrl.h"
#include "tts_api.h"
#include "app_sr.h"
#include "bsp/esp-bsp.h"
#include "bsp_board.h"
#include "app_audio.h"
#include "app_wifi.h"
#include "settings.h"
#include "esp_http_client.h"
#include "esp_timer.h"

#define SCROLL_START_DELAY_S      (1.5)
static char *TAG = "app_main";
static sys_param_t *sys_param = NULL;
QueueHandle_t ttsQueue = NULL;

static esp_err_t send_chat_request(const char *input_text) {
    const char *url = "http://43.134.56.232:80/chat";
    
    int64_t start_time = esp_timer_get_time();  // 获取请求开始的时间戳
    esp_http_client_config_t config = {
        .url = url,
        .method = HTTP_METHOD_POST,
        .timeout_ms = 60000
    };

    esp_http_client_handle_t client = esp_http_client_init(&config);
    if (!client) {
        ESP_LOGE(TAG, "Failed to initialize HTTP client");
        return ESP_FAIL;
    }

    char payload[1024];
    snprintf(payload, sizeof(payload), "{\"data\":\"%s\"}", input_text);
    // ESP_LOGI(TAG, "Constructed payload: %s", payload);

    esp_http_client_set_header(client, "Content-Type", "application/json");

    esp_err_t err = esp_http_client_open(client, strlen(payload));
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to open HTTP connection: %s", esp_err_to_name(err));
        esp_http_client_cleanup(client);
        return err;
    }

    int wlen = esp_http_client_write(client, payload, strlen(payload));
    if (wlen < 0) {
        ESP_LOGE(TAG, "Failed to write to HTTP client");
        esp_http_client_cleanup(client);
        return ESP_FAIL;
    }

    int content_length = esp_http_client_fetch_headers(client);
    if (content_length < 0) {
        ESP_LOGE(TAG, "Failed to fetch HTTP headers or content length is zero");
        esp_http_client_cleanup(client);
        return ESP_FAIL;
    }

    char response_chunk[256];  // 用于存放每个数据块的缓冲区
    int chunk_index = 0;  // 当前数据块的索引
    char c;  // 用于存储每次读取的字符

    // 循环逐字符地读取HTTP响应
    while (esp_http_client_read(client, &c, 1) > 0) {
        // 如果读到换行符或者response_chunk已满，处理该数据块
        if (c == '\n' || chunk_index == sizeof(response_chunk) - 1) {
            response_chunk[chunk_index] = '\0';  // 终止字符串

            if (strlen(response_chunk) > 0) {
                char *task_data = strdup(response_chunk);  // 为数据块分配新的内存空间
                if (!task_data) {
                    ESP_LOGE(TAG, "Failed to allocate memory for response_chunk");
                    continue;
                }
                if (xQueueSend(ttsQueue, &task_data, pdMS_TO_TICKS(1000)) != pdPASS) { // 等待最多1000毫秒
                    ESP_LOGE(TAG, "Failed to send data to TTS queue");
                    free(task_data);  // Free the memory if the send operation failed
                }
                chunk_index = 0;  // 重置数据块索引
            } else {
                ESP_LOGI(TAG, "Handling the last res mark here");

            }
        } else {
            response_chunk[chunk_index++] = c;  // 将字符加入数据块并增加索引
        }
    }

    int64_t end_time = esp_timer_get_time();  // 获取请求结束的时间戳
    ESP_LOGI(TAG, "Request duration: %lld ms", (end_time - start_time) / 1000);  // 打印请求的持续时间
    
    esp_http_client_close(client);
    esp_http_client_cleanup(client);

    return ESP_OK;
}

void tts_queue_handler_task(void *param) {
    ESP_LOGI(TAG, "start tts_queue_handler_task");
    char *task_data;
    while (1) {
        while (get_audio_playing()) {
            vTaskDelay(pdMS_TO_TICKS(100));
        }
        if (xQueueReceive(ttsQueue, &task_data, portMAX_DELAY) == pdTRUE ) {
            if (task_data != NULL && strcmp(task_data, "\nover") != 0) {
                ui_ctrl_label_show_text(UI_CTRL_LABEL_REPLY_CONTENT, task_data);
                ui_ctrl_show_panel(UI_CTRL_PANEL_REPLY, 0);

                esp_err_t tts_status = text_to_speech_request(task_data, AUDIO_CODECS_MP3);
                if (tts_status != ESP_OK) {
                    ESP_LOGE(TAG, "Error converting chunk to speech: %s\n", esp_err_to_name(tts_status));
                } else {
                    vTaskDelay(pdMS_TO_TICKS(SCROLL_START_DELAY_S * 1000));
                    ui_ctrl_reply_set_audio_start_flag(true);
                }
                free(task_data);
            } else {
                // 设置reply_audio_end ?
                ESP_LOGI(TAG,"seting audio_end_flag true");
                // ui_ctrl_reply_set_audio_end_flag(true);
            }
        }
    }
    ESP_LOGI(TAG, "exit tts_queue_handler_task");
}

static esp_err_t send_transcription_request(const uint8_t *audio_data, size_t audio_len, char *transcription_buffer, size_t buffer_length) {
    const char *url = "http://43.134.56.232:80/whisper";
    const char *boundary = "----WebKitFormBoundary9HKFexBRLrf9dcpY";
    char *itemPrefix = NULL;
    // asprintf(&itemPrefix, "--%s\r\nContent-Disposition: form-data; audio=", boundary);
    asprintf(&itemPrefix, "--%s\r\nContent-Disposition: form-data; name=\"audio\"; filename=\"audio.wav\"\r\nContent-Type: audio/wav\r\n\r\n", boundary);

    
    char *reqEndBody = NULL;
    asprintf(&reqEndBody, "\r\n--%s--\r\n", boundary);

    size_t len = strlen(itemPrefix) + strlen(reqEndBody) + audio_len;
    uint8_t *data = (uint8_t *)malloc(len + 1);

    uint8_t *d = data;
    memcpy(d, itemPrefix, strlen(itemPrefix));
    d += strlen(itemPrefix);
    memcpy(d, audio_data, audio_len);
    d += audio_len;
    memcpy(d, reqEndBody, strlen(reqEndBody));
    d += strlen(reqEndBody);
    *d = 0;

    free(itemPrefix);
    free(reqEndBody);

    esp_http_client_config_t config = {
        .url = url,
        .method = HTTP_METHOD_POST,
        .timeout_ms = 60000,
    };
    esp_http_client_handle_t client = esp_http_client_init(&config);
    char *headers = NULL;
    asprintf(&headers, "multipart/form-data; boundary=%s", boundary);

    esp_http_client_set_header(client, "Content-Type", headers);
    free(headers);

    esp_err_t err = esp_http_client_open(client, len);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to open client!");
        free(data);
        return err;
    }

    int wlen = esp_http_client_write(client, (const char *)data, len);
    free(data);
    if (wlen < 0) {
        ESP_LOGE(TAG, "Failed to write client!");
        return ESP_FAIL;
    }

    int content_length = esp_http_client_fetch_headers(client);
    if (content_length >= 0) {
        if (content_length < buffer_length) {
            int read = esp_http_client_read_response(client, transcription_buffer, content_length);
            if (read == content_length) {
                transcription_buffer[content_length] = '\0';
                // ESP_LOGI(TAG, "Received response: %s", transcription_buffer);
                // 解析 input_text 来获取 'response' 的值
                cJSON *json_obj = cJSON_Parse(transcription_buffer);
                if (!json_obj) {
                    ESP_LOGE(TAG, "Failed to parse transcription_buffer");
                    return ESP_FAIL;
                }
                cJSON *response_item = cJSON_GetObjectItem(json_obj, "response");
                if (!response_item || !cJSON_IsString(response_item)) {
                    ESP_LOGE(TAG, "Failed to get 'response' from transcription_buffer");
                    cJSON_Delete(json_obj);
                    return ESP_FAIL;
                }
                strcpy(transcription_buffer, response_item->valuestring);
                // ESP_LOGI(TAG, "Updated transcription_buffer with: %s", transcription_buffer);
                return ESP_OK;
            } else {
                ESP_LOGE(TAG, "HTTP_ERROR: read=%d, length=%d", read, content_length);
                return ESP_FAIL;
            }
        } else {
            ESP_LOGE(TAG, "Buffer too small to hold response");
            return ESP_FAIL;
        }
    } else {
        ESP_LOGE(TAG, "Failed to get response from server");
        return ESP_FAIL;
    }
    // free(url);
    esp_http_client_close(client);
    esp_http_client_cleanup(client);

}

esp_err_t start_openai(uint8_t *audio, int audio_len)
{
    ui_ctrl_show_panel(UI_CTRL_PANEL_GET, 0);
    char transcription[512];  // 设置一个适当的大小，根据服务器可能的响应长度
    esp_err_t err = send_transcription_request(audio, audio_len, transcription, sizeof(transcription));
    if (err != ESP_OK) {
        // 输出详细的错误信息到日志
        ESP_LOGE(TAG, "Error in send_transcription_request: %s", esp_err_to_name(err));
        // 处理错误，例如显示一个错误消息
        ui_ctrl_label_show_text(UI_CTRL_LABEL_LISTEN_SPEAK, "Sorry, I can't transcribe the audio.");
        ui_ctrl_show_panel(UI_CTRL_PANEL_SLEEP, 2000);
        return ESP_FAIL;
    }

    char *text = transcription;

    if (text == NULL){
        ui_ctrl_label_show_text(UI_CTRL_LABEL_LISTEN_SPEAK, "API Key is not valid");
        return ESP_FAIL;
    }

    if (strcmp(text, "invalid_request_error") == 0 || strcmp(text, "server_error") == 0) {
        ui_ctrl_label_show_text(UI_CTRL_LABEL_LISTEN_SPEAK, "Sorry, I can't understand.");
        ui_ctrl_show_panel(UI_CTRL_PANEL_SLEEP, 2000);
        return ESP_FAIL;
    }

    // UI listen success
    ui_ctrl_label_show_text(UI_CTRL_LABEL_REPLY_QUESTION, text);
    ui_ctrl_label_show_text(UI_CTRL_LABEL_LISTEN_SPEAK, text);

    char response[2048];  // 设置一个适当的大小，根据服务器可能的响应长度
    err = send_chat_request(text);
    if (err != ESP_OK) {
        // 处理错误，例如显示一个错误消息
        ui_ctrl_label_show_text(UI_CTRL_LABEL_LISTEN_SPEAK, "Sorry, I can't understand.");
        ui_ctrl_show_panel(UI_CTRL_PANEL_SLEEP, 2000);
        // ESP_LOGE(TAG, "Error Log for me:", err);
        return ESP_FAIL;
    }

    // UI listen success
    ui_ctrl_label_show_text(UI_CTRL_LABEL_REPLY_QUESTION, text);
    ui_ctrl_label_show_text(UI_CTRL_LABEL_LISTEN_SPEAK, response);

    if (strcmp(response, "invalid_request_error") == 0) {
        ui_ctrl_label_show_text(UI_CTRL_LABEL_LISTEN_SPEAK, "Sorry, I can't understand.");
        ui_ctrl_show_panel(UI_CTRL_PANEL_SLEEP, 2000);
        return ESP_FAIL;
    }

    return ESP_OK;
}

/* play audio function */

static void audio_play_finish_cb(void)
{
    ESP_LOGI(TAG, "replay audio end");
    // 在播放完成的回调函数中
    set_audio_playing(false);
    if (ui_ctrl_reply_get_audio_start_flag()) {
        ui_ctrl_reply_set_audio_end_flag(true);
        // ESP_LOGI(TAG, "skipping ui_ctrl_reply_set_audio_end_flag");
    }
}

void app_main()
{
    // 在程序初始化部分
    ttsQueue = xQueueCreate(10, sizeof(char *));
    if (ttsQueue == NULL) {
        ESP_LOGE(TAG, "Failed to create TTS queue");
    }

    // 初始化TTS处理任务
    if (xTaskCreate(tts_queue_handler_task, "TTS_Queue_Handler", 4096, NULL, 5, NULL) != pdPASS) {
        ESP_LOGE(TAG, "Failed to create TTS queue handler task");
    }

    //Initialize NVS
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);
    ESP_ERROR_CHECK(settings_read_parameter_from_nvs());
    sys_param = settings_get_parameter();

    bsp_spiffs_mount();
    bsp_i2c_init();
    bsp_display_start();
    bsp_board_init();

    ESP_LOGI(TAG, "Display LVGL demo");
    bsp_display_backlight_on();
    ui_ctrl_init();
    app_network_start();

    ESP_LOGI(TAG, "speech recognition start");
    app_sr_start(false);
    audio_register_play_finish_cb(audio_play_finish_cb);

    while (true) {
        ESP_LOGD(TAG, "\tDescription\tInternal\tSPIRAM");
        ESP_LOGD(TAG, "Current Free Memory\t%d\t\t%d",
                 heap_caps_get_free_size(MALLOC_CAP_8BIT | MALLOC_CAP_INTERNAL),
                 heap_caps_get_free_size(MALLOC_CAP_SPIRAM));
        ESP_LOGD(TAG, "Min. Ever Free Size\t%d\t\t%d",
                 heap_caps_get_minimum_free_size(MALLOC_CAP_8BIT | MALLOC_CAP_INTERNAL),
                 heap_caps_get_minimum_free_size(MALLOC_CAP_SPIRAM));
        vTaskDelay(pdMS_TO_TICKS(5 * 1000));
    }
}