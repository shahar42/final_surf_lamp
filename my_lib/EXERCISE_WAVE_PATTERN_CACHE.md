# Exercise: Wave Pattern Precomputation Cache

## Context & Problem

Your ESP32 animates LEDs at 60 FPS with easing functions. Every frame:
- 3 strips × 16-32 LEDs per strip
- For each LED: compute easing curve, map hue/saturation/brightness
- Compute trigonometric functions: `easeInOutSine()` uses `cos(PI * t)`
- 60 × 3 × 32 = 5,760 computations per second

**The Issue:**
Wave pattern is **deterministic** — same progress value (0.0 → 1.0) always produces same colors. Computing it 60 times/second is wasteful when you could precompute once.

---

## Learning Goals

- Understand **time-space tradeoff** (RAM for CPU)
- Implement **precomputation pattern** for animations
- Use **lookup tables** for expensive functions
- Manage **constrained memory** on ESP32 (520KB RAM)
- Apply **caching strategy** with cache invalidation

---

## Current Architecture

```
Main Loop (60 FPS)
    |
    v
animation.h: playSunset()
    |
    +-- easeInOutSine(progress)  [cos() call - EXPENSIVE]
    |
    +-- fillStripGradient()
    |   |
    |   +-- Compute HSV for each LED [repeated calculation]
    |
    v
FastLED.show() [Display to LEDs]
```

**Key Functions (from animation.h):**
- `easeInOutSine(float t)` — Smooth curve, uses `cos()` (~20 cycles each)
- `fillStripGradient()` — Builds HSV color for each LED position
- Animation loop runs 60 times/second for N seconds

---

## The Solution: Precomputation Cache

### Architecture

```
Animation Setup Phase (Once)
    |
    v
PrecomputedWaveCache
    |
    +-- frames[] array [FPS × DURATION]
    |       |
    |       +-- frame[0]: {hue=16, sat=255, val=255}
    |       +-- frame[1]: {hue=15.9, sat=250, val=250}
    |       +-- frame[N]: {hue=0, sat=225, val=60}
    |
    v
Main Loop (60 FPS)
    |
    +-- Get frame from cache [O(1) lookup]
    |
    +-- Apply to all strips [simple memcpy]
    |
    v
FastLED.show()
```

### What to Cache

Not the entire LED array — just the **animation parameters per frame**:

```cpp
struct AnimationFrame {
    uint8_t hue;           // 0-255
    uint8_t saturation;    // 0-255
    uint8_t brightness;    // 0-255
};

// For 30-second sunset at 60 FPS:
AnimationFrame cache[1800];  // 1800 bytes RAM
```

### When to Use Cache

**Build cache when:**
- Animation starts (playSunset called)
- Data changes that affects animation (theme, brightness)

**Use cache when:**
- Rendering each frame
- Just lookup → apply to strips → show

**Invalidate when:**
- Animation ends
- User changes theme mid-animation
- Settings change

---

## Implementation Tasks

### Task 1: Data Structure Design

**Define AnimationFrame:**
- What fields minimize memory while preserving animation quality?
- Should brightness be separate or merged with saturation?
- Is uint8_t precision enough, or need float?

**Define Cache Container:**
- How do you store variable-length frame sequences?
- Options: Static array (1800 bytes), dynamic allocation, circular buffer
- Trade-off: Memory usage vs flexibility

### Task 2: Precomputation Function

**Goal:** Generate cache without running animation

**Logic Flow:**
1. Accept: duration_seconds, starting_hue, easing_function
2. For each frame (0 to FPS × duration):
   - Calculate progress (0.0 → 1.0)
   - Apply easing: `easedProgress = easeFunc(progress)`
   - Compute HSV based on eased value
   - Store in cache[frame]
3. Return pointer to cache

**Questions to answer:**
- How do you avoid recomputing easing? (Hint: it's the only expensive part)
- Should easing be computed once and reused?
- How do you handle different animation types (sunset vs startup)?

### Task 3: Cache Lookup in Loop

**Current code (animation.h, line 64):**
```
float easedProgress = easeInOutSine(progress);
uint8_t hue = 16 - (uint8_t)(16.0 * easedProgress);
uint8_t sat = 255 - (30 * easedProgress);
uint8_t val = 255 - (195 * easedProgress);
```

**Your task:**
- Replace with cache lookup
- Access cache[currentFrame] to get precomputed HSV
- Apply to all three strips

**Considerations:**
- What if animation ends mid-frame?
- How do you handle frame index out of bounds?
- Should you bounds-check or assume valid?

### Task 4: Memory Management

**Challenge:** ESP32 has ~520KB usable RAM

**Your constraints:**
- 30-second sunset = 1,800 frames
- Each frame = 3 bytes
- Total = 5.4KB (acceptable)

**But what about:**
- Multiple simultaneous animations? (Can't have two sunsets at once - probably OK)
- Startup animation? (Much shorter, <10KB)
- User profiles with different animations? (Load one at a time)

**Questions:**
- Should cache be global or local to function?
- How do you deallocate after animation ends?
- What happens if user changes theme during animation?

### Task 5: Integration Points

**Where to add caching:**

1. **playSunset()** — Build cache on entry, use during loop
2. **playStartupAnimation()** — Similar pattern
3. **Other animations** — Pattern replicates

**Code change locations:**
- Add cache structure at top of function
- Call precomputation before animation loop
- Replace easing/HSV computation with cache lookup
- Cleanup after animation completes

---

## Testing Strategy

### Unit Test: Precomputation Correctness

**Verify cache matches direct computation:**
- Build cache for 5-second animation
- Manually compute frame[500] using easing function
- Compare: cached HSV vs computed HSV
- Acceptable error: <1 unit (imperceptible to human eye)

### Integration Test: Animation Smoothness

**Verify animation still runs smoothly:**
- Run cached animation on actual device
- Watch sunset — does it look smooth?
- Check FPS: should be steady 60
- No stuttering or color banding

### Performance Test: CPU Usage

**Measure savings:**
- Profile original: easing() calls per frame
- Profile cached: lookup operations per frame
- Expected savings: 50-70% CPU reduction in animation loop

### Edge Cases

- What if duration = 0? (Empty cache)
- What if cache allocation fails? (Fallback to direct computation)
- What if animation interrupted mid-loop? (Cleanup dangling pointer)

---

## Implementation Hints (No Code!)

| Task | Concept | Hint |
|------|---------|------|
| Data structure | Memory layout | Use smallest types that preserve quality |
| Precomputation | Loop structure | Mimic animation loop, store results instead of displaying |
| Cache lookup | Array indexing | currentFrame maps directly to cache index |
| Memory mgmt | Lifetime | Allocate at animation start, free at animation end |
| Integration | Code replacement | Exact same HSV values, just different source |

---

## Expected Performance Impact

### Before (Direct Computation)
```
60 FPS animation loop:
  - cos() call: ~20 cycles
  - HSV computation: ~10 cycles per LED
  - Per frame: 200 + (3 strips × 32 LEDs × 10) = ~1,160 cycles
  - Total: 60 FPS × 1,160 = 69,600 cycles/sec
```

### After (Cached)
```
60 FPS animation loop:
  - Array lookup: ~5 cycles
  - HSV apply: ~3 cycles per LED
  - Per frame: 5 + (3 strips × 32 LEDs × 3) = ~293 cycles
  - Total: 60 FPS × 293 = 17,580 cycles/sec

Improvement: 4x reduction (~75% savings)
```

---

## Architecture Considerations

### Design Decisions

1. **Single animation at a time?**
   - Yes: Simple cache, one allocation
   - No: Multiple caches, complex management

2. **Precompute all animations upfront?**
   - Yes: Fast startup, uses RAM upfront
   - No: Lazy compute, saves RAM but adds latency

3. **Cache persistence?**
   - Yes: Reuse sunset animation if called multiple times
   - No: Compute fresh each time (simpler memory mgmt)

### What to Document

After implementation, explain:
- Why this cache size for this animation?
- How does invalidation work?
- What's the fallback if allocation fails?
- Performance before/after numbers

---

## Common Mistakes to Avoid

1. **Caching entire LED array** — Too much memory (512 bytes per frame)
2. **Forgetting to deallocate** — Memory leak across animations
3. **Cache index out of bounds** — Access garbage after animation ends
4. **Not handling easing separately** — Still computing expensive functions
5. **Hardcoding frame count** — Breaks for different durations

---

## Extension Challenges

After basic caching works:

1. **Adaptive cache resolution** — Reduce cache size for short animations
2. **Easing function abstraction** — Support multiple easing types
3. **Cache warming** — Precompute common animations at startup
4. **LRU cache strategy** — Keep only recent animations in RAM

---

## Professional Skills You'll Gain

- **Performance optimization** — RAM/CPU tradeoff
- **Memory management** — Allocation/deallocation patterns
- **Embedded systems** — Work within 520KB RAM constraint
- **Code integration** — Minimal changes, maximum impact
- **Testing** — Verify optimization doesn't break functionality

---

**This is production-quality optimization.** You can show this work to Rafael as an example of embedded systems problem-solving.

Good luck! 🎨

