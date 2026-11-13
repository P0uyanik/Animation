#include "core/core.h"

#include <algorithm>
#include <atomic>
#include <cstdio>
#include <fstream>
#include <mutex>
#include <sstream>
#include <thread>
#include <vector>

namespace plush {

namespace {
LogLevel gLevel = LogLevel::Info;
std::mutex gLogMutex;
unsigned gWorkers = 0;
}  // namespace

void setLogLevel(LogLevel level) { gLevel = level; }

void logMessage(LogLevel level, std::string_view text) {
  if (level < gLevel) return;
  static const char* names[] = {"debug", "info", "warn", "error"};
  std::lock_guard lock(gLogMutex);
  std::FILE* out = level >= LogLevel::Warn ? stderr : stdout;
  std::fprintf(out, "[%s] %.*s\n", names[int(level)], int(text.size()), text.data());
  std::fflush(out);
}

unsigned workerCount() {
  if (gWorkers == 0) gWorkers = std::max(1u, std::thread::hardware_concurrency());
  return gWorkers;
}
void setWorkerCount(unsigned n) { gWorkers = n; }

void parallelFor(size_t count, const std::function<void(size_t)>& fn, size_t grain) {
  if (count == 0) return;
  grain = std::max<size_t>(1, grain);
  unsigned threads = unsigned(std::min<size_t>(workerCount(), (count + grain - 1) / grain));
  if (threads <= 1) {
    for (size_t i = 0; i < count; ++i) fn(i);
    return;
  }
  std::atomic<size_t> next{0};
  auto worker = [&] {
    for (;;) {
      size_t begin = next.fetch_add(grain);
      if (begin >= count) break;
      size_t end = std::min(count, begin + grain);
      for (size_t i = begin; i < end; ++i) fn(i);
    }
  };
  std::vector<std::thread> pool;
  pool.reserve(threads - 1);
  for (unsigned t = 1; t < threads; ++t) pool.emplace_back(worker);
  worker();
  for (auto& t : pool) t.join();
}

Result<std::string> readTextFile(const std::filesystem::path& path) {
  std::ifstream in(path, std::ios::binary);
  if (!in) return fail(std::format("cannot open '{}' for reading", path.string()));
  std::ostringstream ss;
  ss << in.rdbuf();
  return ss.str();
}

Result<void> writeTextFile(const std::filesystem::path& path, std::string_view text) {
  std::error_code ec;
  if (path.has_parent_path()) std::filesystem::create_directories(path.parent_path(), ec);
  std::ofstream out(path, std::ios::binary);
  if (!out) return fail(std::format("cannot open '{}' for writing", path.string()));
  out.write(text.data(), std::streamsize(text.size()));
  if (!out) return fail(std::format("failed writing '{}'", path.string()));
  return {};
}

}  // namespace plush
