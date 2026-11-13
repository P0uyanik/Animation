// CPU path tracer (Embree kernels). Runs on any machine; no GPU required.
#pragma once
#include <functional>
#include <memory>

#include "geom/geometry.h"

namespace plush {

struct ImageRGB {
  int width = 0, height = 0;
  std::vector<vec3> pixels;
  void resize(int w, int h) { width = w; height = h; pixels.assign(size_t(w) * size_t(h), vec3(0)); }
};

struct RenderOutput {
  ImageRGB color;   // linear scene-referred radiance
  ImageRGB albedo;  // first-hit albedo (denoiser guide)
  ImageRGB normal;  // first-hit world normal (denoiser guide)
  int samples = 0;
  double seconds = 0;
};

class PathTracer {
 public:
  PathTracer();
  ~PathTracer();
  PathTracer(const PathTracer&) = delete;
  PathTracer& operator=(const PathTracer&) = delete;

  // Builds acceleration structures for this snapshot and resets accumulation.
  void setScene(std::shared_ptr<const FrameSnapshot> snapshot);
  // Adds `count` samples per pixel to the accumulation buffers (progressive).
  // `cancel` may be polled from worker threads; return true to stop early.
  void accumulate(const RenderSettings& settings, int count, const std::function<bool()>& cancel = {});
  int accumulatedSamples() const;
  RenderOutput output() const;  // averaged buffers

  // Convenience: setScene + accumulate(spp) + output, with progress logging.
  RenderOutput render(std::shared_ptr<const FrameSnapshot> snapshot, const RenderSettings& settings,
                      const std::function<void(float)>& progress = {});

 private:
  struct Impl;
  std::unique_ptr<Impl> impl_;
};

}  // namespace plush
