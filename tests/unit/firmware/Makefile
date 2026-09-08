# Native (g++) tests for the pure-logic parts of the ESP32 firmware.
#
#   make test        build and run everything
#   make clean
#
# Requires only g++ (>= C++17). No Arduino core, no FastLED, no board.

CXX      ?= g++
CXXFLAGS ?= -std=c++17 -O1 -Wall -Wextra -Wno-unused-parameter
FW       := ../../../arduino_code/lamp_refractored/lamp_template
INCLUDES := -I shim -I $(FW) -I .
BUILD    := build

BINS := $(BUILD)/test_protocol $(BUILD)/test_led_mapping $(BUILD)/test_arduino_id $(BUILD)/test_jitter $(BUILD)/test_themes

.PHONY: all test clean
all: $(BINS)

$(BUILD):
	mkdir -p $(BUILD)

$(BUILD)/test_protocol: test_protocol.cpp check.h $(FW)/esp_Server_encoding.hpp | $(BUILD)
	$(CXX) $(CXXFLAGS) $(INCLUDES) $< -o $@

$(BUILD)/test_led_mapping: test_led_mapping.cpp check.h $(FW)/Config.h shim/Arduino.h | $(BUILD)
	$(CXX) $(CXXFLAGS) $(INCLUDES) $< -o $@

$(BUILD)/test_arduino_id: test_arduino_id.cpp check.h $(FW)/Config.h shim/Arduino.h | $(BUILD)
	$(CXX) $(CXXFLAGS) $(INCLUDES) $< -o $@

$(BUILD)/test_jitter: test_jitter.cpp check.h $(FW)/Config.h $(FW)/JitterManager.h shim/Arduino.h | $(BUILD)
	$(CXX) $(CXXFLAGS) $(INCLUDES) $< -o $@

$(BUILD)/test_themes: test_themes.cpp check.h $(FW)/Themes.h $(FW)/Themes.cpp shim/FastLED.h | $(BUILD)
	$(CXX) $(CXXFLAGS) $(INCLUDES) $< $(FW)/Themes.cpp -o $@

test: $(BINS)
	@set -e; \
	$(BUILD)/test_protocol fixtures/v3_sample.bin fixtures/v3_sample.txt; \
	$(BUILD)/test_led_mapping; \
	$(BUILD)/test_arduino_id 0x00112233445566 1122867; \
	$(BUILD)/test_arduino_id 0x00000000445566 1; \
	$(BUILD)/test_arduino_id 0x00FFFFFF445566 16777215; \
	$(BUILD)/test_jitter; \
	$(BUILD)/test_themes; \
	echo "firmware tests: all suites passed"

clean:
	rm -rf $(BUILD)
