// Minimal Arduino/ESP32 core stand-in so pure-logic firmware headers compile
// natively with g++. Only what Config.h, JitterManager.h, Themes.* and
// esp_Server_encoding.hpp actually touch. Nothing here talks to hardware.
#pragma once

#include <cstdint>
#include <cstddef>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cmath>
#include <string>
#include <algorithm>

// ---- Arduino.h macro family (defined AFTER the std headers on purpose) ----
#define abs(x) ((x) > 0 ? (x) : -(x))
#define constrain(amt, low, high) ((amt) < (low) ? (low) : ((amt) > (high) ? (high) : (amt)))
#define min(a, b) ((a) < (b) ? (a) : (b))
#define max(a, b) ((a) > (b) ? (a) : (b))

// ---- clock ----
inline unsigned long& shim_millis() { static unsigned long ms = 0; return ms; }
inline unsigned long millis() { return shim_millis(); }
inline void delay(unsigned long) {}

// ---- String (just enough) ----
class String {
public:
    String() {}
    String(const char* s) : v_(s ? s : "") {}
    String(const std::string& s) : v_(s) {}
    String(int n) : v_(std::to_string(n)) {}
    String(unsigned n) : v_(std::to_string(n)) {}
    String(unsigned long n) : v_(std::to_string(n)) {}
    const char* c_str() const { return v_.c_str(); }
    size_t length() const { return v_.size(); }
    String operator+(const String& o) const { return String(v_ + o.v_); }
    String& operator+=(const String& o) { v_ += o.v_; return *this; }
    bool operator==(const String& o) const { return v_ == o.v_; }
private:
    std::string v_;
};
inline String operator+(const char* a, const String& b) { return String(a) + b; }

// ---- Serial (swallows output unless SHIM_VERBOSE) ----
struct SerialShim {
    template <typename... Args>
    void printf(const char* fmt, Args... args) {
#ifdef SHIM_VERBOSE
        std::printf(fmt, args...);
#else
        (void)fmt; (void)sizeof...(args);
#endif
    }
    void println(const char* = "") {}
    void println(const String&) {}
    void println(int) {}
    void println(unsigned) {}
    void println(unsigned long) {}
    void println(double) {}
    void print(const char*) {}
    void print(const String&) {}
    void print(int) {}
    void print(unsigned) {}
    void print(double) {}
};
inline SerialShim Serial;

// ---- ESP (only the eFuse MAC, settable by tests) ----
struct EspClass {
    uint64_t efuseMac = 0;
    uint64_t getEfuseMac() const { return efuseMac; }
    void restart() {}
};
inline EspClass ESP;
