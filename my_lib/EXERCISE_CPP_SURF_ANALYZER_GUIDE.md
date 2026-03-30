# Exercise Guide: C++ Surf Data Analyzer

## Context & Overview

You have a file `/md_files/cpp_surf_exercises.md` that contains skeleton code for learning C++ through real surf lamp data. This guide provides **learning roadmap** without spoiling the code implementations.

**Standard:** C++98 (compatible with embedded and older systems)
**Concepts:** Abstract classes, virtual functions, polymorphism, inheritance
**Real Data:** Queries your actual Supabase database

---

## Exercise 1: Surf Data Analyzer (Abstract Classes & Polymorphism)

### What You're Building

An **analysis framework** where:
- `SurfAnalyzer` = abstract strategy interface
- `WavePatternAnalyzer` = analyzes wave heights
- `WindTrendAnalyzer` = analyzes wind patterns
- `OptimalSurfTimeAnalyzer` = finds best times to surf

**Key Principle:** Add new analyzer types WITHOUT modifying existing code (Open/Closed).

### Understanding the Architecture

```
Your Main Program
       |
       v
   Analyzer Manager (stores vector<SurfAnalyzer*>)
       |
       +---> WavePatternAnalyzer (concrete)
       +---> WindTrendAnalyzer (concrete)
       +---> OptimalSurfTimeAnalyzer (concrete)
```

**The Interface (SurfAnalyzer base class):**
- Pure virtual `analyze()` — each analyzer implements differently
- Pure virtual `getReport()` — return formatted analysis results
- Pure virtual `getAnalyzerName()` — human-readable name
- Virtual destructor — CRITICAL for proper cleanup

**Why This Design?**
- Polymorphism at runtime: `analyzer->analyze()` calls correct version
- Easy to add 10th analyzer without touching existing 9
- Main code doesn't need to know about specific analyzer types

---

## Task 1: WavePatternAnalyzer Implementation

### What Needs Implementation

The `.cpp` file has TODO markers for:

1. **`calculateAverage()`**
   - Goal: Sum all wave heights, divide by count
   - Concept: Loop through vector, accumulate values
   - Edge case: What if vector is empty?
   - Algorithm hint: Linear scan with running sum

2. **`findMax()`**
   - Goal: Find largest wave height in dataset
   - Approach options:
     - Manual loop with comparison
     - Use `std::max_element()` from `<algorithm>`
   - Edge case: Empty data
   - What does "largest" mean? (Compare `wave_height_m` field)

3. **`findMin()`**
   - Goal: Find smallest wave height
   - Similar approach to `findMax()` but opposite comparison
   - Edge case handling required

4. **`analyze()` — Trend Analysis Section**
   - Goal: Determine if conditions are improving or worsening
   - Logic: Compare first reading vs last reading
   - Output: Direction string ("Improving", "Worsening", "Stable")
   - Hint: Calculate difference, compare to threshold

5. **`analyze()` — Surfability Count**
   - Goal: Count readings where wave_height_m > 1.5m
   - Concept: Count-based loop through vector
   - Output: Integer count
   - Question: Should 1.5m be a constant or variable?

### Testing Strategy

**Unit Testing Approach:**
- Create small test datasets manually (3-5 readings)
- Call `analyze()` with known data
- Verify average/max/min calculations
- Check edge cases: empty data, single reading, all same values

**Integration Testing:**
- Connect to real database
- Query actual surf data from your lamps
- Run analysis on real conditions
- Verify reports are meaningful

**Verification Questions:**
- Does average make sense? (between min and max)
- Is trend analysis accurate?
- Does surfability count seem reasonable?

---

## Task 2: WindTrendAnalyzer Implementation

### What Needs Implementation

1. **`getWindDirectionName()`**
   - Input: Degrees (0-359)
   - Goal: Convert to cardinal direction string
   - Mapping logic:
     - 0° = North
     - 90° = East
     - 180° = South
     - 270° = West
     - Need intermediate directions (NE, SE, SW, NW)
   - Approach: Degree ranges → direction names
   - Question: How do you map continuous degrees to discrete directions?

2. **`isOffshore()`**
   - Input: Wind degrees, location string
   - Goal: Determine if wind is blowing FROM land TO ocean
   - Challenge: Different locations have different "offshore" directions
     - Tel Aviv: Westerly winds are offshore (blowing toward sea)
     - Maagan: Different direction offshore
   - Approach: Location-specific mappings
   - Hint: Build if/else or switch on location name

3. **`analyze()` — Wind Analysis**
   - Goal: Summarize wind conditions in report
   - What to include:
     - Average wind speed
     - Dominant wind direction
     - Count of offshore readings
     - Wind quality assessment (good/bad for conditions)
   - Question: Is strong offshore wind good or bad?

### Key Concept: Domain Knowledge

Wind analysis requires **understanding your sport:**
- Offshore winds blow from land toward water (generally good for surfing - cleaner waves)
- Strong winds might be bad for lamps (cause instability)
- Direction matters: same speed, different direction = different conditions

Your task: Encode this knowledge in the analyzer logic.

---

## Task 3: OptimalSurfTimeAnalyzer Implementation

### What Needs Implementation

This is the **hardest exercise** — requires combining concepts:

1. **Identify "Good" Surf Conditions**
   - What makes conditions optimal?
   - Thresholds: wave height range (1.0-3.0m?), wind speed limits, direction preferences
   - Question: Are these hardcoded or configurable?

2. **Track Time Ranges**
   - Find consecutive time periods with good conditions
   - Approach: Scan through chronologically ordered data
   - Output: Time windows when surfer should go out
   - Challenge: Data might have gaps (no readings for 1 hour)

3. **Score Quality**
   - Assign quality score to each time window
   - Factors: wave height, wind direction, consistency
   - Question: How do you weight these factors?

4. **Generate Report**
   - Best time to surf (time window + score)
   - Why it's optimal (explanation)
   - Alternative windows (if conditions allow multiple sessions)

### Algorithm Outline (Not Code!)

High-level approach:
1. Define what "good conditions" means (your thresholds)
2. Loop through chronological data
3. For each reading: is it "good"?
4. Track consecutive good readings as a potential session
5. Score each session based on data quality
6. Report best session with reasoning

### Testing Strategy

**Manual Test:**
- Create synthetic dataset:
  - Morning: bad conditions
  - Midday: excellent conditions
  - Evening: marginal conditions
- Run analyzer
- Does it correctly identify midday as best time?

**Real Data Test:**
- Query last 24 hours of your lamp
- Does recommended time make sense?
- Can you verify by checking weather that day?

---

## Task 4: Compiler & Linking

### Common Issues & How to Debug

**Issue: "undefined reference to WavePatternAnalyzer::analyze()"**
- Cause: `.cpp` file not compiled
- Fix: Add file to compile command: `g++ main.cpp wave_pattern_analyzer.cpp ...`

**Issue: "virtual function ... has no overrider"**
- Cause: Pure virtual function not implemented in derived class
- Fix: Check all three pure virtuals are declared in .h and defined in .cpp

**Issue: "SurfAnalyzer: cannot instantiate abstract class"**
- This is CORRECT behavior!
- Fix: Don't try to create `SurfAnalyzer` object directly
- Instead: Create `WavePatternAnalyzer`, cast to `SurfAnalyzer*`

**Issue: "Segmentation fault in destructor"**
- Cause: Missing virtual destructor in base class
- Fix: Add `virtual ~SurfAnalyzer() {}` to base class header

### Compilation Command

```bash
# Single file (all implementations in .cpp)
g++ -Wall -o analyzer main.cpp surf_analyzer.cpp wave_pattern_analyzer.cpp wind_trend_analyzer.cpp optimal_surf_analyzer.cpp database.cpp -lpqxx -lpq

# Or use a Makefile for larger projects
```

---

## Learning Checkpoints

After completing each analyzer, ask yourself:

**Concept Understanding:**
- [ ] Can I explain why we use pure virtual functions?
- [ ] Why does base class need virtual destructor?
- [ ] How does polymorphism work here?

**Code Quality:**
- [ ] Is my implementation correct for edge cases?
- [ ] Did I follow the naming conventions?
- [ ] Are my algorithms efficient?

**System Integration:**
- [ ] Does my analyzer produce meaningful output?
- [ ] Can I add a 4th analyzer type without modifying existing code?
- [ ] Do reports make sense for real data?

---

## Extension Challenges (After Base Exercises)

Once you finish the three analyzers, try:

1. **Template Specialization**
   - Create `DataAnalyzer<T>` template
   - Specialize for different data types
   - Reference: `/md_files/cpp_surf_exercises.md` Exercise 2

2. **Configuration System**
   - Move hardcoded thresholds to config file
   - Allow custom "good conditions" per user
   - Demonstrate polymorphism + flexibility

3. **Database Queries**
   - Learn libpqxx library
   - Query different time ranges
   - Analyze historical trends

4. **Performance Analysis**
   - Profile your analyzers
   - Which is slowest?
   - Can you optimize vector operations?

---

## Resources & References

**C++ Concepts:**
- Virtual functions: https://en.cppreference.com/w/cpp/language/virtual
- Abstract classes: https://en.cppreference.com/w/cpp/language/abstract_class
- Polymorphism: https://cplusplus.com/doc/tutorial/polymorphism/

**STL Algorithms:**
- `std::max_element`: https://en.cppreference.com/w/cpp/algorithm/max_element
- `std::min_element`: https://en.cppreference.com/w/cpp/algorithm/min_element
- `std::accumulate`: https://en.cppreference.com/w/cpp/algorithm/accumulate

**Your Database:**
- Query real data from Supabase dashboard
- Check data types and ranges
- Understand what "good" means for your location

---

## Common Mistakes to Avoid

1. **Forgetting virtual destructors** — causes memory leaks
2. **Not handling empty data** — crashes on edge cases
3. **Hardcoding all thresholds** — inflexible, hard to test
4. **Not ordering data by time** — invalid trend analysis
5. **Mixing concerns** — analyzer does analysis AND database queries
6. **Not testing edge cases** — single reading, all same value, gaps in data

---

## Hints Summary (No Code!)

| Task | Concept | Hint |
|------|---------|------|
| calculateAverage() | Loop + accumulate | Sum / Count |
| findMax/Min() | Comparison | Start with first element, compare others |
| Trend analysis | Direction | Earlier vs later = improving? |
| Surfability count | Filtering | Count how many meet criteria |
| Wind direction | Mapping | Degree ranges → cardinal directions |
| Offshore detection | Domain knowledge | Different for each location |
| Optimal time | Algorithm | Find consecutive good readings, score them |

---

**Good luck with the implementation! The concepts you learn here apply to many real systems.** 🏄‍♂️

