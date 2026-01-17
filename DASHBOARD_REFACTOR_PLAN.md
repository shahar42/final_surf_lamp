# Dashboard Template Refactoring Plan

**Current State**: JavaScript extraction complete, HTML template optimization pending
**File**: `web_and_database/templates/dashboard.html`
**Current Lines**: 1,392
**Target Lines**: ~800-900 (35-40% reduction)

---

## Core Problem

**Mobile/Desktop Duplication**: 9 major sections exist in duplicate with `block lg:hidden` / `hidden lg:block` pattern.

**Total Duplication**: ~500-600 lines of repeated HTML structure

---

## Completed Work ✅

### Phase 1: JavaScript Extraction (COMPLETE)
- ✅ All JavaScript extracted to feature modules in `static/js/features/`
- ✅ 12 feature modules created (location-update, wave-threshold, off-hours, etc.)
- ✅ Utility modules created (api-client, status-messages, modal-manager, theme-manager)
- ✅ CSS extracted to `static/css/dashboard.css`
- ✅ Configuration centralized in `static/js/config.js`

**Result**: Clean separation of JavaScript logic from HTML templates

---

## Remaining Work: HTML Template Optimization

### Priority 1: Create Reusable Macros (HIGH IMPACT)

**Problem**: Repeated button groups and UI patterns appear 4-6 times each

#### Macro 1: Preset Button Group
**File**: `templates/macros/preset_buttons.html`
**Target**: Off hours preset buttons (6 instances, 80+ lines of duplication)
**Lines 733-763 (mobile), 858-888 (desktop)**

```jinja
{# templates/macros/preset_buttons.html #}
{% macro preset_button(label, time_label, start, end, device_suffix='') %}
<button data-preset="{{ label|lower }}" data-start="{{ start }}" data-end="{{ end }}"
        class="preset-btn text-sm py-3 px-2 rounded transition-all border leading-tight
        {% if data.user.off_times_enabled and data.user.off_time_start == start %}
            bg-orange-600/80 border-orange-500 text-white font-semibold shadow-[0_0_15px_rgba(234,88,12,0.3)]
        {% else %}
            bg-white/10 hover:bg-white/20 text-white/80 border-white/20
        {% endif %}">
    <span class="whitespace-nowrap block font-normal">{{ label }}</span>
    <span class="opacity-60 text-base whitespace-nowrap block font-light">{{ time_label }}</span>
</button>
{% endmacro %}

{% macro preset_button_group(device_suffix='') %}
<div class="grid grid-cols-3 gap-2">
    {{ preset_button('Typical', '11pm-7am', '23:00', '07:00', device_suffix) }}
    {{ preset_button('Late Night', '1am-9am', '01:00', '09:00', device_suffix) }}
    {{ preset_button('Early Bird', '9pm-5am', '21:00', '05:00', device_suffix) }}
    {{ preset_button('Midnight', '12am-8am', '00:00', '08:00', device_suffix) }}
    {{ preset_button('Custom', 'Set your own', '', '', device_suffix) }}
    {{ preset_button('Disabled', 'Always on', 'disabled', 'disabled', device_suffix) }}
</div>
{% endmacro %}
```

**Usage**: `{{ preset_button_group() }}` (mobile) and `{{ preset_button_group() }}` (desktop)
**Reduction**: 80 lines → 2 lines

---

#### Macro 2: Brightness Button Group
**File**: `templates/macros/brightness_buttons.html`
**Target**: Brightness buttons (6 instances, 30+ lines)
**Lines 820-828 (mobile), 945-953 (desktop)**

```jinja
{# templates/macros/brightness_buttons.html #}
{% macro brightness_button_group(device_suffix='') %}
{% set brightness_levels = {'LOW': 0.3, 'MEDIUM': 0.6, 'HIGH': 1.0} %}
<div class="grid grid-cols-3 gap-2">
    {% for level, value in brightness_levels.items() %}
    <button data-brightness="{{ value }}"
            class="brightness-btn flex-1 bg-white/10 hover:bg-white/20 text-white font-semibold py-3 px-4 rounded-lg transition-all border border-white/20">
        {{ level|capitalize }}
    </button>
    {% endfor %}
</div>
{% endmacro %}
```

**Reduction**: 30 lines → 1 line

---

#### Macro 3: Condition Display Card
**File**: `templates/macros/condition_card.html`
**Target**: Weather condition cards (4 instances, 50+ lines)
**Lines 537-591 (mobile), 609-655 (desktop)**

```jinja
{# templates/macros/condition_card.html #}
{% macro condition_card(icon_path, value, unit, label, scale=1.0) %}
<div class="text-center">
    <div class="mb-1 flex items-center justify-center h-16">
        <img src="{{ url_for('static', filename=icon_path) }}"
             alt="{{ label }}"
             class="max-h-full w-auto object-contain png-icon"
             style="transform: scale({{ scale }});">
    </div>
    <div class="text-white font-bold text-lg sm:text-xl">
        {% if value %}
            {{ "%.1f"|format(value) }}{{ unit }}
        {% else %}
            --
        {% endif %}
    </div>
</div>
{% endmacro %}
```

**Usage**:
```jinja
{{ condition_card(
    'icons/wave_height_new.png',
    wave_height_display,
    height_unit,
    'Wave Height',
    1.15
) }}
```

**Reduction**: 50 lines → 8 lines per 4 instances = 168 lines saved

---

#### Macro 4: Accordion/Drawer Header
**File**: `templates/macros/accordion_header.html`
**Target**: Accordion headers (4 instances, 40+ lines)

```jinja
{# templates/macros/accordion_header.html #}
{% macro accordion_header(title, content_id) %}
<button onclick="document.getElementById('{{ content_id }}').classList.toggle('hidden');
                 document.getElementById('{{ content_id }}-chevron').classList.toggle('rotate-180');"
        class="w-full text-left p-6 flex justify-between items-center bg-white/5 hover:bg-white/10 transition-colors">
    <h2 class="text-xl font-bold text-white">{{ title }}</h2>
    <svg id="{{ content_id }}-chevron" class="w-6 h-6 text-white transition-transform duration-300"
         fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
    </svg>
</button>
{% endmacro %}
```

**Reduction**: 40 lines → 4 lines

---

### Priority 2: Extract Large Sections to Partials (MEDIUM IMPACT)

**Problem**: Major dashboard sections duplicate mobile/desktop layouts

#### Partial 1: Light Configuration
**File**: `templates/partials/light_configuration.html`
**Lines**: 679-959 (281 lines → extract to ~140 lines with macros)
**Contains**: Off hours, quiet hours, brightness, theme selector

**Strategy**:
- Use `preset_button_group()` macro
- Use `brightness_button_group()` macro
- Single responsive implementation instead of mobile+desktop duplication

**Expected Reduction**: ~140 lines

---

#### Partial 2: Surf Conditions Card
**File**: `templates/partials/surf_conditions.html`
**Lines**: 529-676 (148 lines → extract to ~60 lines with macros)
**Contains**: Wave height, period, wind speed, direction display

**Strategy**:
- Use `condition_card()` macro for all 4 conditions
- Responsive grid layout (4 cols desktop, 2 cols mobile)
- Single implementation

**Expected Reduction**: ~88 lines

---

#### Partial 3: Lamp Configuration Card
**File**: `templates/partials/lamp_configuration.html`
**Lines**: 287-527 (241 lines → extract to ~120 lines)
**Contains**: Location selector, wave/wind sliders, unit toggle, Arduino management

**Strategy**:
- Extract location selector
- Extract Arduino form logic
- Responsive container

**Expected Reduction**: ~121 lines

---

#### Partial 4: Quick Actions
**File**: `templates/partials/quick_actions.html`
**Lines**: 961-1037 (77 lines → extract to ~40 lines)
**Contains**: Admin buttons, WiFi setup, error reporting, logout

**Strategy**:
- Responsive flex layout (drawer mobile, row desktop)
- Single implementation

**Expected Reduction**: ~37 lines

---

#### Partial 5: Chat Modal
**File**: `templates/partials/chat_modal.html`
**Lines**: 1046-1087 (42 lines)
**Standalone modal**

**Benefit**: Organizational clarity, reduce main template noise

---

#### Partial 6: LED Error Codes Drawer
**File**: `templates/partials/led_error_codes.html`
**Lines**: 1092-1192 (101 lines)
**Admin-only feature**

**Benefit**: Conditional loading, cleaner separation of concerns

---

#### Partial 7: Error Report Modal
**File**: `templates/partials/error_report_modal.html`
**Lines**: 1221-1263 (43 lines)
**Standalone modal**

**Benefit**: Organizational clarity

---

#### Partial 8: LED Visualization
**File**: `templates/partials/led_visualization.html`
**Lines**: 47-185 (139 lines)
**Contains**: Canvas, legend, wind compass

**Benefit**: Isolates complex rendering logic

---

#### Partial 9: Underlayer Control Panel
**File**: `templates/partials/underlayer_control_panel.html`
**Lines**: 187-282 (96 lines)
**Dev-only tool**

**Benefit**: Completely separate development code from production template

---

### Priority 3: Responsive Consolidation (LOW EFFORT, HIGH IMPACT)

**Problem**: Many sections duplicate identical logic for mobile/desktop

**Strategy**: Use Tailwind responsive utilities instead of separate blocks

**Example - Before**:
```html
<!-- Mobile -->
<div class="block lg:hidden">
    <div class="card">...</div>
</div>

<!-- Desktop -->
<div class="hidden lg:block">
    <div class="card">...</div>
</div>
```

**Example - After**:
```html
<!-- Single responsive version -->
<div class="card">
    <div class="flex flex-col lg:flex-row">
        <!-- Content adapts with Tailwind -->
    </div>
</div>
```

**Targets**:
- Surf Conditions grid (4 cols → 2 cols)
- Quick Actions (drawer → row)
- Brightness buttons (already same markup, just consolidate wrapper)

---

## Implementation Order

### Stage 1: Create Macro Library (2-3 hours)
1. Create `templates/macros/` directory
2. Implement `preset_buttons.html` macro
3. Implement `brightness_buttons.html` macro
4. Implement `condition_card.html` macro
5. Implement `accordion_header.html` macro
6. Test each macro in isolation

**Impact**: Foundation for template reduction

---

### Stage 2: Extract High-Duplication Partials (3-4 hours)
1. Extract `partials/light_configuration.html` (use preset/brightness macros)
2. Extract `partials/surf_conditions.html` (use condition_card macro)
3. Extract `partials/lamp_configuration.html`
4. Test after each extraction

**Expected Reduction**: ~350 lines

---

### Stage 3: Extract Standalone Sections (2-3 hours)
1. Extract `partials/led_visualization.html`
2. Extract `partials/underlayer_control_panel.html`
3. Extract `partials/chat_modal.html`
4. Extract `partials/led_error_codes.html`
5. Extract `partials/error_report_modal.html`
6. Extract `partials/quick_actions.html`

**Expected Reduction**: ~260 lines (organizational, not just duplication removal)

---

### Stage 4: Final Consolidation (1-2 hours)
1. Consolidate remaining mobile/desktop duplicates
2. Review for any missed macro opportunities
3. Final testing and validation

---

## Expected Results

### Before Refactoring:
```
dashboard.html: 1,392 lines
├── Duplicated mobile/desktop code: ~500-600 lines (40%)
├── Extractable standalone sections: ~300 lines (20%)
├── Unique content: ~492-592 lines (40%)
└── Maintenance effort: HIGH (2x edits for mobile+desktop)
```

### After Refactoring:
```
templates/
├── dashboard.html: ~800-900 lines (orchestration + unique logic)
├── macros/ (4 files): ~150 lines (reusable components)
├── partials/ (9 files): ~800 lines (extracted sections)
└── Total template code: ~1,750-1,850 lines

Actual reduction: ~400-500 lines (30-35%)
Maintenance effort: LOW (1 edit, 1 location)
```

**Key Wins**:
- ✅ Single Source of Truth for all UI patterns
- ✅ DRY compliance: No mobile/desktop duplication
- ✅ Better organization: Clear file structure
- ✅ Easier maintenance: Change once, apply everywhere
- ✅ Testability: Partials can be tested in isolation

---

## Migration Checklist

### Before Starting:
- [ ] Create feature branch: `refactor/dashboard-templates`
- [ ] Tag current state: `git tag pre-template-refactor`
- [ ] Ensure all tests pass
- [ ] Screenshot current dashboard for visual regression testing

### During Refactoring:
- [ ] One commit per macro/partial extraction
- [ ] Test after each extraction
- [ ] Update this plan with actual results
- [ ] Note any unexpected dependencies or issues

### After Completion:
- [ ] Full regression testing (all features work identically)
- [ ] Visual comparison (screenshots match)
- [ ] Performance check (page load time)
- [ ] Code review
- [ ] Merge to development
- [ ] Deploy and monitor

---

## Anti-Patterns to Avoid

### ❌ Don't: Over-Abstract
```jinja
{# BAD: Too many parameters, unmaintainable #}
{% macro generic_card(title, subtitle, icon, color, size, spacing, ...) %}
```

### ✅ Do: Purpose-Specific Macros
```jinja
{# GOOD: Clear purpose, appropriate parameters #}
{% macro condition_card(icon_path, value, unit, label) %}
```

### ❌ Don't: Break Working Features
- Test after EVERY extraction
- Keep commits small and atomic
- Deploy to dev environment frequently

### ✅ Do: Incremental Improvement
- Extract one section at a time
- Verify functionality before moving to next
- Use git tags to mark checkpoints

---

## Risk Mitigation

**Risk**: Breaking existing functionality
**Mitigation**: Test after each extraction, small atomic commits, easy rollback

**Risk**: Visual regressions
**Mitigation**: Screenshot comparison, visual testing before/after

**Risk**: JavaScript initialization failures
**Mitigation**: Maintain ID/class naming conventions, test all features

**Risk**: Mobile/desktop layout issues
**Mitigation**: Test on multiple screen sizes after responsive consolidation

---

## Success Criteria

1. ✅ dashboard.html reduced to 800-900 lines (30-35% reduction)
2. ✅ Zero mobile/desktop duplication for identical logic
3. ✅ All UI patterns defined in macros (preset buttons, brightness, condition cards)
4. ✅ Major sections extracted to partials
5. ✅ All features work identically before/after
6. ✅ No visual regressions
7. ✅ Maintainability improved (1 edit instead of 2-4)

---

## Lessons from CLAUDE.md Applied

1. **Single Source of Truth**: Each UI pattern exists in exactly one place (macros)
2. **Open-Closed Principle**: Macros open to extension, closed to modification
3. **DRY Principle**: "Smart" extraction (macros/partials), not "naive" (copy-paste)
4. **Surgical Edits**: Small atomic commits, test after each change
5. **Root Cause Fix**: Address mobile/desktop duplication at architectural level

---

## Decision Log

### Why Jinja Macros Over Custom Components?
- Already using Flask/Jinja stack
- No build step required
- Server-side rendering preserved
- Progressive enhancement maintained

### Why Phased Approach?
- Reduces risk of breaking changes
- Allows testing at each stage
- Easy to pause/resume
- Smaller, reviewable commits

### Why Not Unify All Mobile/Desktop?
- Some patterns genuinely need different UX (drawers vs cards)
- Keep separate wrappers, share internal content via macros
- Responsive utilities where layouts are truly identical

---

## Next Steps

1. Review and approve this plan
2. Create feature branch: `refactor/dashboard-templates`
3. Begin Stage 1: Create macro library
4. Proceed incrementally through stages 2-4
5. Test thoroughly at each checkpoint
6. Merge after full regression testing

---

**Status**: Ready to begin
**Estimated Effort**: 8-12 hours (can be spread across multiple sessions)
**Expected Outcome**: Cleaner, more maintainable dashboard template with 30-35% reduction in code
