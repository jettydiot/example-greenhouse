/**
 * Smart Greenhouse Monitor
 * https://github.com/jettydiot/example-greenhouse
 *
 * All driver configuration is in device.yaml — no editing needed here.
 * JettyScript rules are in jettyscript.json — push them via the platform API.
 */
#include "jettyd.h"

void app_main(void)
{
    jettyd_config_t config = {
        .device_type            = CONFIG_JETTYD_DEVICE_TYPE,
        .firmware_version       = CONFIG_JETTYD_FIRMWARE_VERSION,
        .heartbeat_interval_sec = 30,
        .mqtt_keepalive         = 60,
        .mqtt_qos               = 1,
        .mqtt_buffer_on_disconnect = true,
        .mqtt_max_buffer_size   = 16,
        .deep_sleep             = false,
        .has_battery            = false,
        .battery_adc_pin        = -1,
        .status_led_pin         = -1,   /* Managed by LED driver via JettyScript */
        .wake_on_pin            = -1,
    };

    ESP_ERROR_CHECK(jettyd_init(&config));
    ESP_ERROR_CHECK(jettyd_start());
}
