#include <iostream>
#include <string>
#include <cstring>

// === Mock Serial (must be defined before including the header) ===
class SerialMock {
public:
    std::string output;
    void write(const char* buf, size_t len) {
        output.append(buf, len);
    }
    void clear() { output.clear(); }
} Serial;

#include "my_linear_buffer.hpp"

// === Test harness ===
int passed = 0;
int failed = 0;

void check(const char* name, bool condition) {
    if (condition) {
        std::cout << "  PASSED: " << name << std::endl;
        passed++;
    } else {
        std::cout << "  FAILED: " << name << std::endl;
        failed++;
    }
}

// === Tests ===

void test_single_message() {
    std::cout << "\n=== Test: Single Message ===" << std::endl;
    Serial.clear();
    AsyncSerialLogger logger;

    logger.Log("Hello");
    logger.Flush();

    check("Output contains 'Hello'", Serial.output.find("Hello") != std::string::npos);
    check("Output ends with newline", Serial.output.back() == '\n');
    check("Output length is 6", Serial.output.length() == 6); // "Hello\n"
}

void test_multiple_messages() {
    std::cout << "\n=== Test: Multiple Messages ===" << std::endl;
    Serial.clear();
    AsyncSerialLogger logger;

    logger.Log("First");
    logger.Log("Second");
    logger.Log("Third");
    logger.Flush();

    check("Contains 'First'", Serial.output.find("First") != std::string::npos);
    check("Contains 'Second'", Serial.output.find("Second") != std::string::npos);
    check("Contains 'Third'", Serial.output.find("Third") != std::string::npos);
    check("Correct order", Serial.output.find("First") < Serial.output.find("Second") &&
                            Serial.output.find("Second") < Serial.output.find("Third"));
}

void test_flush_empty() {
    std::cout << "\n=== Test: Flush Empty Buffer ===" << std::endl;
    Serial.clear();
    AsyncSerialLogger logger;

    logger.Flush();

    check("No output on empty flush", Serial.output.length() == 0);
}

void test_auto_flush() {
    std::cout << "\n=== Test: Auto-Flush on Overflow ===" << std::endl;
    Serial.clear();
    AsyncSerialLogger logger;

    // Each message: 100 chars + newline = 101 bytes in buffer
    // 2048 / 101 = 20.27 → flush triggers on message 21
    char msg[101];
    memset(msg, 'A', 100);
    msg[100] = '\0';

    for (int i = 0; i < 25; i++) {
        logger.Log(msg);
    }

    // Auto-flush should have fired (after msg 20 filled 2020 bytes, msg 21 triggered it)
    check("Auto-flush triggered", Serial.output.length() > 0);
    size_t after_auto = Serial.output.length();

    // Flush remaining
    logger.Flush();

    check("Total output is 25 messages", Serial.output.length() == 25 * 101);
    check("Auto-flush wrote partial, manual flush wrote rest",
          after_auto > 0 && Serial.output.length() > after_auto);
}

void test_boundary_message() {
    std::cout << "\n=== Test: Message Exactly Fills Buffer ===" << std::endl;
    Serial.clear();
    AsyncSerialLogger logger;

    // Fill buffer to exactly 2048 bytes: 2048 / 101 = 20 msgs (2020 bytes) + one 28-char msg
    char filler[101];
    memset(filler, 'B', 100);
    filler[100] = '\0';

    for (int i = 0; i < 20; i++) {
        logger.Log(filler); // 2020 bytes
    }

    // 2048 - 2020 = 28 bytes remaining. A 27-char message = 28 bytes (27 + newline)
    char exact[28];
    memset(exact, 'C', 27);
    exact[27] = '\0';

    logger.Log(exact); // Should fit exactly, no flush yet
    check("No auto-flush when message fits exactly", Serial.output.length() == 0);

    // Next message must trigger flush
    logger.Log("trigger");
    check("Flush triggered on next message", Serial.output.length() > 0);

    logger.Flush();
    check("All data written after final flush", Serial.output.find("trigger") != std::string::npos);
}

void test_single_char() {
    std::cout << "\n=== Test: Single Character Messages ===" << std::endl;
    Serial.clear();
    AsyncSerialLogger logger;

    logger.Log("A");
    logger.Log("B");
    logger.Log("C");
    logger.Flush();

    // Each single char: 1 char + newline = 2 bytes
    check("Output length is 6", Serial.output.length() == 6);
    check("Content is A\\nB\\nC\\n", Serial.output == "A\nB\nC\n");
}

int main() {
    std::cout << "========== TESTING AsyncSerialLogger ==========";

    test_single_message();
    test_multiple_messages();
    test_flush_empty();
    test_auto_flush();
    test_boundary_message();
    test_single_char();

    std::cout << "\n=========================================" << std::endl;
    std::cout << "Results: " << passed << " passed, " << failed << " failed" << std::endl;

    return failed > 0 ? 1 : 0;
}
