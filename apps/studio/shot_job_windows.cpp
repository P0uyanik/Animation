#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>

#include <algorithm>
#include <chrono>
#include <map>
#include <memory>
#include <thread>

#include "shot_workflow.h"

namespace plush::workflow {
namespace {
struct Close {
  void operator()(HANDLE h) const { if (h != INVALID_HANDLE_VALUE) CloseHandle(h); }
};
using Handle = std::unique_ptr<void, Close>;
using Clock = std::chrono::steady_clock;

// CreateProcessW takes a single command line. Quote each argv element using the CRT's
// backslash rules, including trailing backslashes before the closing quote.
std::wstring commandLine(const std::vector<std::string>& argv) {
  std::wstring line;
  for (const auto& arg : argv) {
    if (!line.empty()) line += L' ';
    line += L'"';
    size_t slashes = 0;
    for (wchar_t c : fs::path(arg).wstring()) {
      if (c == L'\\') {
        ++slashes;
      } else {
        line.append(c == L'"' ? 2 * slashes + 1 : slashes, L'\\');
        line += c;
        slashes = 0;
      }
    }
    line.append(2 * slashes, L'\\');
    line += L'"';
  }
  return line;
}

bool groupEmpty(HANDLE job) {
  JOBOBJECT_BASIC_ACCOUNTING_INFORMATION info{};
  return QueryInformationJobObject(job, JobObjectBasicAccountingInformation, &info, sizeof(info), nullptr)
      && info.ActiveProcesses == 0;
}
}  // namespace

RunStatus readStatus(const fs::path& statusFile) {
  // The producer atomically replaces status.json while the studio polls it.
  // MSVC's ifstream permits concurrent reads and writes but denies this rename.
  Handle file(CreateFileW(statusFile.c_str(), GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                          nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr));
  if (file.get() == INVALID_HANDLE_VALUE) return {};
  std::string text;
  char buffer[4096];
  DWORD bytes;
  do {
    if (!ReadFile(file.get(), buffer, sizeof(buffer), &bytes, nullptr)) return {};
    text.append(buffer, bytes);
  } while (bytes != 0);
  return parseStatus(Json::parse(text, nullptr, false));
}

Job::~Job() {
  if (job_ && !groupEmpty(job_)) cancel(2.0);
  if (job_) CloseHandle(job_);
  if (process_) CloseHandle(process_);
}

Result<void> Job::start(const std::vector<std::string>& argv, const fs::path& logFile) {
  if (job_ && !groupEmpty(job_)) return fail("a job is already running");
  if (argv.empty() || argv.front().empty()) return fail("empty command");
  std::error_code ec;
  if (!logFile.parent_path().empty()) fs::create_directories(logFile.parent_path(), ec);
  SECURITY_ATTRIBUTES sa{sizeof(sa), nullptr, TRUE};
  Handle log(CreateFileW(logFile.c_str(), FILE_APPEND_DATA, FILE_SHARE_READ | FILE_SHARE_WRITE, &sa,
                         OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr));
  Handle input(CreateFileW(L"NUL", GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE, &sa,
                           OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr));
  if (log.get() == INVALID_HANDLE_VALUE || input.get() == INVALID_HANDLE_VALUE)
    return fail("cannot open job streams for " + logFile.string());

  Handle job(CreateJobObjectW(nullptr, nullptr));
  JOBOBJECT_EXTENDED_LIMIT_INFORMATION limits{};
  limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
  if (!job || !SetInformationJobObject(job.get(), JobObjectExtendedLimitInformation, &limits, sizeof(limits)))
    return fail(std::format("cannot create Windows job ({})", GetLastError()));

  // Limit inherited handles to the redirected streams, including when studios run jobs concurrently.
  SIZE_T bytes = 0;
  InitializeProcThreadAttributeList(nullptr, 1, 0, &bytes);
  std::vector<std::byte> storage(bytes);
  auto* attributes = reinterpret_cast<LPPROC_THREAD_ATTRIBUTE_LIST>(storage.data());
  if (!InitializeProcThreadAttributeList(attributes, 1, 0, &bytes))
    return fail(std::format("cannot initialize process attributes ({})", GetLastError()));
  std::unique_ptr<_PROC_THREAD_ATTRIBUTE_LIST, decltype(&DeleteProcThreadAttributeList)>
      cleanup(attributes, DeleteProcThreadAttributeList);
  HANDLE streams[] = {input.get(), log.get()};
  if (!UpdateProcThreadAttribute(attributes, 0, PROC_THREAD_ATTRIBUTE_HANDLE_LIST, streams, sizeof(streams), nullptr, nullptr))
    return fail(std::format("cannot redirect job streams ({})", GetLastError()));

  // Console control events require a shared console. Redirected CI runners can start without one.
  if (!GetConsoleCP() && AllocConsole()) ShowWindow(GetConsoleWindow(), SW_HIDE);
  STARTUPINFOEXW si{};
  si.StartupInfo.cb = sizeof(si);
  si.StartupInfo.dwFlags = STARTF_USESTDHANDLES;
  si.StartupInfo.hStdInput = input.get();
  si.StartupInfo.hStdOutput = si.StartupInfo.hStdError = log.get();
  si.lpAttributeList = attributes;
  PROCESS_INFORMATION pi{};
  auto cmd = commandLine(argv);
  if (!CreateProcessW(nullptr, cmd.data(), nullptr, nullptr, TRUE,
                      CREATE_SUSPENDED | CREATE_NEW_PROCESS_GROUP | EXTENDED_STARTUPINFO_PRESENT,
                      nullptr, nullptr, &si.StartupInfo, &pi))
    return fail(std::format("cannot start {} ({})", argv.front(), GetLastError()));
  Handle process(pi.hProcess), thread(pi.hThread);
  // Assign before executing any user code so even the first grandchild is contained.
  if (!AssignProcessToJobObject(job.get(), process.get()) || ResumeThread(thread.get()) == DWORD(-1)) {
    DWORD error = GetLastError();
    TerminateProcess(process.get(), 1);
    WaitForSingleObject(process.get(), INFINITE);
    return fail(std::format("cannot start process in Windows job ({})", error));
  }
  if (job_) CloseHandle(job_);
  if (process_) CloseHandle(process_);
  job_ = job.release();
  process_ = process.release();
  pid_ = pgid_ = pi.dwProcessId;
  exited_ = false;
  exitCode_ = -1;
  return {};
}

bool Job::running() {
  if (exited_) return false;
  if (WaitForSingleObject(process_, 0) == WAIT_TIMEOUT) return true;
  DWORD code;
  if (GetExitCodeProcess(process_, &code)) exitCode_ = static_cast<int>(code);
  exited_ = true;
  return false;
}

Job::CancelResult Job::cancel(double graceSeconds) {
  CancelResult r;
  if (!job_) return r;
  const auto start = Clock::now();
  r.wasRunning = !groupEmpty(job_);
  if (r.wasRunning) {
    // ActiveProcesses can reach zero before TerminateJobObject finishes closing child
    // handles (including the log). Wait for the actual processes to signal as well.
    std::map<ProcessId, Handle> observed;
    auto observe = [&] {
      for (const auto& member : members()) {
        if (observed.contains(member.pid)) continue;
        Handle child(OpenProcess(SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION, FALSE, member.pid));
        BOOL belongs = FALSE;
        if (child && IsProcessInJob(child.get(), job_, &belongs) && belongs)
          observed.emplace(member.pid, std::move(child));
      }
    };
    auto finished = [&] {
      return groupEmpty(job_) && WaitForSingleObject(process_, 0) == WAIT_OBJECT_0 &&
             std::all_of(observed.begin(), observed.end(), [](const auto& entry) {
               return WaitForSingleObject(entry.second.get(), 0) == WAIT_OBJECT_0;
             });
    };
    auto waitForGroup = [&](double seconds) {
      const auto deadline = Clock::now() + std::chrono::duration<double>(seconds);
      while (!finished() && Clock::now() < deadline) std::this_thread::sleep_for(std::chrono::milliseconds(25));
      return finished();
    };
    observe();
    GenerateConsoleCtrlEvent(CTRL_BREAK_EVENT, pgid_);
    r.graceful = waitForGroup(graceSeconds);
    r.groupGone = r.graceful;
    if (!r.graceful) {
      observe();
      r.forced = TerminateJobObject(job_, 1) != FALSE;
      r.groupGone = waitForGroup(10.0);
    }
  } else {
    r.groupGone = true;
  }
  running();
  r.seconds = std::chrono::duration<double>(Clock::now() - start).count();
  return r;
}

std::vector<ProcInfo> Job::members() const {
  std::vector<ProcInfo> out;
  if (!job_) return out;
  std::vector<ULONG_PTR> buffer(64);
  while (true) {
    auto* info = reinterpret_cast<JOBOBJECT_BASIC_PROCESS_ID_LIST*>(buffer.data());
    if (QueryInformationJobObject(job_, JobObjectBasicProcessIdList, info,
                                  static_cast<DWORD>(buffer.size() * sizeof(ULONG_PTR)), nullptr)) {
      for (DWORD i = 0; i < info->NumberOfProcessIdsInList; ++i) {
        auto pid = static_cast<DWORD>(info->ProcessIdList[i]);
        Handle process(OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pid));
        wchar_t path[32768];
        DWORD size = static_cast<DWORD>(std::size(path));
        out.push_back({pid, process && QueryFullProcessImageNameW(process.get(), 0, path, &size)
                                ? fs::path(path).string() : ""});
      }
      return out;
    }
    if (GetLastError() != ERROR_MORE_DATA) return out;
    buffer.resize(buffer.size() * 2);
  }
}

bool processExists(ProcessId pid) {
  Handle process(OpenProcess(SYNCHRONIZE, FALSE, pid));
  if (!process) return GetLastError() == ERROR_ACCESS_DENIED;
  return WaitForSingleObject(process.get(), 0) == WAIT_TIMEOUT;
}
}  // namespace plush::workflow
