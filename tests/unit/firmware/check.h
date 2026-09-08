// Tiny assertion framework: no dependencies, one binary per test file.
// Exit code = number of failed checks, so `make test` fails loudly.
#pragma once
#include <cstdio>
#include <cstdlib>
#include <string>

namespace check {
inline int& failures() { static int n = 0; return n; }
inline int& passes() { static int n = 0; return n; }
inline const char*& current() { static const char* c = ""; return c; }

inline void fail(const char* expr, const char* file, int line, const std::string& detail = "") {
    ++failures();
    std::fprintf(stderr, "  FAIL [%s] %s:%d: %s %s\n", current(), file, line, expr, detail.c_str());
}
inline void pass() { ++passes(); }

inline int summary(const char* suite) {
    std::printf("%s: %d passed, %d failed\n", suite, passes(), failures());
    return failures() > 99 ? 99 : failures();
}
}  // namespace check

#define TEST(name) check::current() = #name; std::printf("- %s\n", #name);

#define CHECK(cond) \
    do { if (cond) check::pass(); else check::fail(#cond, __FILE__, __LINE__); } while (0)

#define CHECK_EQ(a, b) \
    do { auto _a = (a); auto _b = (b); \
         if (_a == _b) check::pass(); \
         else check::fail(#a " == " #b, __FILE__, __LINE__, \
                          "(got " + std::to_string(_a) + ", want " + std::to_string(_b) + ")"); } while (0)

#define CHECK_NEAR(a, b, eps) \
    do { double _a = (a), _b = (b); \
         if (std::fabs(_a - _b) <= (eps)) check::pass(); \
         else check::fail(#a " ~= " #b, __FILE__, __LINE__, \
                          "(got " + std::to_string(_a) + ", want " + std::to_string(_b) + ")"); } while (0)
