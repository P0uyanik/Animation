// Engine core: errors, logging, time, threading, files.
#pragma once
#include <chrono>
#include <cmath>
#include <cstdint>
#include <expected>
#include <filesystem>
#include <format>
#include <functional>
#include <string>
#include <string_view>

namespace plush {

// ---------------------------------------------------------------- errors
struct Error {
  std::string message;
};
template <class T>
using Result = std::expected<T, Error>;
inline std::unexpected<Error> fail(std::string message) { return std::unexpected(Error{std::move(message)}); }

// ---------------------------------------------------------------- logging
enum class LogLevel { Debug = 0, Info, Warn, Error };
void setLogLevel(LogLevel level);
void logMessage(LogLevel level, std::string_view text);
template <class... A>
void logInfo(std::format_string<A...> f, A&&... a) { logMessage(LogLevel::Info, std::format(f, std::forward<A>(a)...)); }
template <class... A>
void logWarn(std::format_string<A...> f, A&&... a) { logMessage(LogLevel::Warn, std::format(f, std::forward<A>(a)...)); }
template <class... A>
void logError(std::format_string<A...> f, A&&... a) { logMessage(LogLevel::Error, std::format(f, std::forward<A>(a)...)); }
template <class... A>
void logDebug(std::format_string<A...> f, A&&... a) { logMessage(LogLevel::Debug, std::format(f, std::forward<A>(a)...)); }

// ---------------------------------------------------------------- time
// Time is integer ticks: 705,600,000 per second divides evenly into
// 23.976/24/25/30/48/50/60 fps and common audio rates (no float drift).
inline constexpr int64_t kTicksPerSecond = 705'600'000;
struct FrameRate {
  int num = 24;
  int den = 1;
  double fps() const { return double(num) / double(den); }
};
inline int64_t frameToTicks(double frame, FrameRate r) {
  return int64_t(std::llround(frame * double(kTicksPerSecond) * r.den / r.num));
}
inline double ticksToFrame(int64_t ticks, FrameRate r) {
  return double(ticks) * r.num / (double(kTicksPerSecond) * r.den);
}

class Stopwatch {
 public:
  Stopwatch() : start_(std::chrono::steady_clock::now()) {}
  double seconds() const { return std::chrono::duration<double>(std::chrono::steady_clock::now() - start_).count(); }
  void reset() { start_ = std::chrono::steady_clock::now(); }

 private:
  std::chrono::steady_clock::time_point start_;
};

// ---------------------------------------------------------------- threading
unsigned workerCount();
void setWorkerCount(unsigned n);  // 0 = all hardware threads
// Runs fn(i) for i in [0, count) on all workers. Blocks until done.
void parallelFor(size_t count, const std::function<void(size_t)>& fn, size_t grain = 1);

// ---------------------------------------------------------------- files
Result<std::string> readTextFile(const std::filesystem::path& path);
Result<void> writeTextFile(const std::filesystem::path& path, std::string_view text);

}  // namespace plush
