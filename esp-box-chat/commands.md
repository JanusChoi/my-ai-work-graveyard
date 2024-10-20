- 查询串口（Mac）
```ll /dev/cu*```

- 刷环境
```. ~/esp/esp-idf/export.sh```

- 烧录前配置
```idf.py menuconfig```

```idf.py build```

- 注意查看串口编号，下面是两个不同串口的烧录命令

```python -m esptool -p /dev/cu.usbmodem21201 --chip esp32s3 -b 460800 --before default_reset --after hard_reset write_flash --flash_mode dio --flash_size 16MB --flash_freq 80m 0x0 build/bootloader/bootloader.bin 0x8000 build/partition_table/partition-table.bin 0xd000 build/ota_data_initial.bin 0x10000 build/chatgpt_demo.bin 0x900000 build/storage.bin 0xb00000 build/srmodels/srmodels.bin 0x700000 factory_nvs/build/factory_nvs.bin```

```python -m esptool -p /dev/cu.usbmodem11201 --chip esp32s3 -b 460800 --before default_reset --after hard_reset write_flash --flash_mode dio --flash_size 16MB --flash_freq 80m 0x0 build/bootloader/bootloader.bin 0x8000 build/partition_table/partition-table.bin 0xd000 build/ota_data_initial.bin 0x10000 build/chatgpt_demo.bin 0x900000 build/storage.bin 0xb00000 build/srmodels/srmodels.bin 0x700000 factory_nvs/build/factory_nvs.bin```

python -m esptool -p /dev/cu.usbmodem11301 --chip esp32s3 -b 460800 --before default_reset --after hard_reset write_flash --flash_mode dio --flash_size 16MB --flash_freq 80m 0x0 build/bootloader/bootloader.bin 0x8000 build/partition_table/partition-table.bin 0xd000 build/ota_data_initial.bin 0x10000 build/chatgpt_demo.bin 0x900000 build/storage.bin 0xb00000 build/srmodels/srmodels.bin 0x700000 factory_nvs/build/factory_nvs.bin

- 编译前，需配置一下menuconfig，把HMI Board Config中的Select BSP board选项，默认是BSP_BOARD_ESP32_S3_BOX，选为BSP_BOARD_ESP32_S3_BOX_Lite，就可以正常编译烧录运行。

- 一般的example烧录通过以下指令即可
```idf.py flash monitor```



I (1385) gpio: GPIO[4]| InputEn: 0| OutputEn: 1| OpenDrain: 0| Pullup: 0| Pulldown: 0| Intr:0 
I (1393) gpio: GPIO[48]| InputEn: 0| OutputEn: 1| OpenDrain: 0| Pullup: 0| Pulldown: 0| Intr:0 
I (1523) gpio: GPIO[3]| InputEn: 1| OutputEn: 0| OpenDrain: 0| Pullup: 0| Pulldown: 0| Intr:2 
E (1524) lcd_panel.io.i2c: panel_io_i2c_rx_buffer(135): i2c transaction failed
E (1530) TT21100: esp_lcd_touch_tt21100_read_data(198): I2C read error!
E (1537) TT21100: esp_lcd_touch_new_i2c_tt21100(110): TT21100 init failed
E (1544) TT21100: Error (0xffffffff)! Touch controller TT21100 initialization failed!
I (1553) gpio: GPIO[3]| InputEn: 0| OutputEn: 0| OpenDrain: 0| Pullup: 1| Pulldown: 0| Intr:0 
ESP_ERROR_CHECK failed: esp_err_t 0xffffffff (ESP_FAIL) at 0x420397df
0x420397df: bsp_display_indev_init at /Users/januswing/code/esp-box/examples/chatgpt_demo/components/espressif__esp-box/esp-box.c:424
 (inlined by) bsp_display_start_with_config at /Users/januswing/code/esp-box/examples/chatgpt_demo/components/espressif__esp-box/esp-box.c:453
