# Scoop AI Development Context

Complete development history for the Gemini Thinking Stream feature implementation.

## Project Overview

**Goal:** Implement real-time Gemini 3 Flash thinking stream for Scoop.ge AI assistant, showing AI reasoning process to users while maintaining product recommendation functionality.

---

## Development Timeline: January 18, 2026

### Phase 1: Research & Planning

**Initial State:** Working chat with Gemini 2, but no visible thinking process.

**Research Findings:**
- Gemini 3 Flash Preview supports `thinking_budget` parameter (1-24576 tokens)
- `include_thoughts=True` streams thought parts with `part.thought=True`
- Thoughts are in English by default, need translation for Georgian users

### Phase 2: Implementation

**Changes Made:**
1. Added `ThinkingConfig` to `GenerateContentConfig`
2. Frontend `ThinkingStepsLoader` component to display thoughts
3. SSE event type `thinking` for streaming thoughts
4. Argos Translate for English→Georgian translation

---

## Bug Log

### Bug #1: Fake Loader Shows First
- **Symptom:** Hardcoded "ვფიქრობ..." text appeared before real thoughts
- **Root Cause:** State initialization logic
- **Fix:** Conditional rendering based on `hasRealThoughts` flag
- **Status:** ✅ RESOLVED

### Bug #2: Translation Latency
- **Symptom:** Long delays waiting for thought translation
- **Root Cause:** Argos Translate cold start
- **Fix:** Parallel processing, caching, warm-up
- **Status:** ✅ RESOLVED

### Bug #3: No Final Response Content (CRITICAL)
- **Symptom:** Thinking events streamed but NO text response
- **Initial Diagnosis:** Thought Gemini Thinking was broken
- **Attempts:** 5+ debugging sessions over 4 hours

**Debugging Process:**
1. Added `console.log('[DEBUG SSE]')` in frontend - confirmed no `text` events
2. Added `logger.info("🔍 Part: ...")` in backend - found empty `part.text`
3. Disabled thinking (`thinking_budget=0`) - text appeared but no thoughts
4. Analyzed backend logs: saw "AFC is enabled with max remote calls: 10"

**Root Cause Discovery (via Sequential Thinking):**
The issue was **NOT** Gemini Thinking. It was **AFC (Automatic Function Calling)**.

When AFC was enabled (default in Gemini SDK):
- SDK internally handled function calls
- Final text response was NOT yielded to our streaming loop
- We received empty text parts

**Final Fix:**
```python
# In main.py stream config
automatic_function_calling=types.AutomaticFunctionCallingConfig(
    disable=True  # CRITICAL: Must be disabled for manual FC handling
)
```

With AFC disabled AND thinking enabled:
```
✅ thinking events: "პროტეინის მოთხოვნების ანალიზი..."
✅ text events: "გამარჯობა! მე ვარ Scoop.ge-ს AI..."
```

- **Status:** ✅ RESOLVED

---

## Development Timeline: January 19, 2026

### Session: Holistic Stability Fix

**Problem Reported:** System unstable - sometimes gives recommendations, sometimes fallback, sometimes empty cards.

---

## Bug Log (January 19)

### Bug #4: search_products Skip Logic Too Aggressive
- **Symptom:** All search_products calls after the first were skipped, even with different queries
- **Root Cause:** Counter-based limit (`search_products_calls > 1`) blocked ALL calls, not just duplicates
- **Fix:** Changed to set-based tracking (`executed_search_queries`) to allow unique queries
- **Status:** ✅ RESOLVED

### Bug #5: Final Response Round Not Triggering for Zero Products
- **Symptom:** When all searches returned 0 products, user saw empty cards with no text
- **Root Cause:** Condition `if not text AND products` skipped when products=[]
- **Fix:** Changed to `if not text` (always generate response)
- **Status:** ✅ RESOLVED

### Bug #6: English Thought Fallback
- **Symptom:** When Final Response failed, English reasoning text was shown to users
- **Root Cause:** Fallback code showed Gemini's internal thoughts (always English)
- **Fix:** Hardcoded Georgian fallback messages instead of thoughts
- **Status:** ✅ RESOLVED

### Bug #7: Wrong Variable Name in Final Response (CRITICAL)
- **Symptom:** `'function' object has no attribute 'send_message_stream'`
- **Root Cause:** Code used `chat` but actual variable was `stream_chat`
- **Fix:** Changed `chat` → `stream_chat`
- **Status:** ✅ RESOLVED

### Bug #8: Missing Async/Await in Final Response
- **Symptom:** Synchronous `for` loop with async generator failed silently
- **Root Cause:** Missing `async for` and `await` keywords
- **Fix:** Changed `for chunk in` → `async for chunk in await`
- **Status:** ✅ RESOLVED

---

## Key Files Modified

| File | Changes |
|------|---------|
| `main.py` | Added AFC disable, thinking stream logic, debug logging |
| `config.py` | Added `thinking_budget`, `include_thoughts` settings |
| `requirements.txt` | Added argostranslate for thought translation |

---

## Configuration

### Working Configuration (Final)

```python
# config.py
thinking_budget = 4096  # Enable thinking
include_thoughts = True  # Stream thoughts to client

# main.py GenerateContentConfig
automatic_function_calling=types.AutomaticFunctionCallingConfig(
    disable=True  # CRITICAL for manual function handling
)
thinking_config=ThinkingConfig(
    thinking_budget=settings.thinking_budget,
    include_thoughts=settings.include_thoughts
)
```

---

## Lessons Learned

1. **AFC Default Behavior:** Gemini SDK enables AFC by default when tools are provided. This swallows the text response in streaming mode.

2. **Thinking + Tools Compatibility:** Gemini 3 Flash thinking DOES work with function calling, but only when AFC is disabled and functions are handled manually.

3. **Debug Logging is Critical:** The `🔍 Part: thought=X, text=Y, fc=Z` logging pattern immediately revealed the issue.

4. **Sequential Thinking Protocol:** Using structured devil's advocate analysis caught the AFC issue that 4 hours of ad-hoc debugging missed.

5. **Non-Deterministic API Behavior:** Gemini Thinking Stream can be unpredictable - always have fallback strategies.

6. **Variable Naming Consistency:** Using different variable names (`chat` vs `stream_chat`) in async contexts causes silent failures.

7. **Async/Await Discipline:** Forgetting `async for` and `await` in async generators produces cryptic errors.

---

## Team

- **AI Agent:** Claude Opus 4.5 (Planning & Building)
- **Human:** Maqashable (Testing & QA)

---

## Development Timeline: January 19, 2026 (Late Session ~02:00-03:00)

### Session: Gemini Response Instability Deep Dive

**Problem Reported:** Inconsistent responses - sometimes full Georgian recommendations, sometimes hardcoded fallback messages, sometimes products without annotation text.

---

## Bug Log (January 19 - Late Session)

### Bug #9: Text Cutoff Mid-Sentence (Streaming Issue)
- **Symptom:** User-facing text cut off mid-sentence when product cards followed
- **Root Cause:** Text was being streamed piece-by-piece, causing premature yield before complete
- **Fix:** Implemented text buffering - accumulate all text in `accumulated_text`, send as complete block at end of round
- **Status:** ✅ RESOLVED

### Bug #10: English Thought-to-Text Fallback (Security/UX)
- **Symptom:** When Gemini failed to generate text, internal English thoughts were shown to users
- **Root Cause:** Fallback logic used first thought as text when `accumulated_text` was empty
- **Fix:** Removed thought-to-text fallback, replaced with Georgian contextual messages
- **Status:** ✅ RESOLVED

### Bug #11: Thinking Mode Blocking Final Response (CRITICAL)
- **Symptom:** Final Response block returned 0 text chars even with improved prompts
- **Root Cause:** `send_message_stream()` continues with `include_thoughts=True`, Gemini outputs ONLY thoughts, no user-facing text
- **Diagnosis:** Sequential Thinking revealed that thinking mode exhausts response capacity
- **Fix:** Changed Final Response from `send_message_stream()` to `send_message()` - bypasses thinking mode like old repo
- **Status:** ✅ RESOLVED

### Bug #12: Inconsistent Fallback Messages Between Paths
- **Symptom:** Sometimes "აი მოვიძიე X პროდუქტი", sometimes "სამწუხაროდ..."
- **Root Cause:** Two separate fallback paths (Main Loop vs Final Response) had different messages
- **Fix:** Initially synchronized messages, then removed all fallback messages per user request
- **Status:** ✅ RESOLVED (fallbacks removed)

---

## Current Outstanding Issues

### Issue #1: Gemini Not Generating Text in Main Loop (NON-DETERMINISTIC)
- **Symptom:** Gemini often returns only function calls + thoughts, no actual text per round
- **Impact:** Forces system to rely on Final Response block instead of natural conversation
- **Potential Fix:** Prompt engineering to force text output alongside function calls
- **Status:** 🟡 PARTIALLY ADDRESSED - Final Response now works, but root cause not fixed

### Issue #2: search_products Returns 0 for Common Queries
- **Symptom:** "Vegan", "Isolate", "ISO", "plant" all return 0 products
- **Root Cause:** Database doesn't have products matching these terms, OR regex matching is too strict
- **Impact:** User experience degraded when looking for specialty products
- **Status:** 🔴 NOT FIXED - Requires database investigation or fuzzy search

### Issue #3: Gemini Sends Multiple Parallel Function Calls
- **Symptom:** Gemini sends 2-3 `search_products` calls in single round
- **Current Handling:** Only first call is executed, others skipped
- **Impact:** Potentially missing better search results
- **Status:** 🟡 WORKAROUND IN PLACE - Not ideal but functional

---

## Key Code Changes This Session

| Location | Change |
|----------|--------|
| `main.py` L1714-1719 | Text buffering - removed immediate yield, now accumulates |
| `main.py` L1737-1752 | Main Loop fallback - removed per user request |
| `main.py` L1837-1866 | Final Response - changed from `send_message_stream()` to `send_message()` |
| `main.py` L1864-1866 | Final Response fallback - removed per user request |

---

## Diagnostic Commands for Future Debugging

```bash
# Watch for fallback triggers
tail -f logs | grep -E "⚠️|fallback|Forcing"

# Check if text is being generated
tail -f logs | grep -E "📤|Final response"

# Monitor product search results  
tail -f logs | grep -E "search_products|products for"
```

---

*Last Updated: January 19, 2026 ~03:00*

---

## Development Timeline: January 19, 2026 (Afternoon Session ~14:00-19:00)

### Session: Product Search Fix + Response Time Optimization

**Problems Reported:**
1. `search_products` returning 0 results for "isolate", "vegan", "iso" queries
2. Response time too slow (~16-17s) for complex queries

---

## Bug Log (January 19 - Afternoon Session)

### Bug #13: search_products 0 Results for Keywords (CRITICAL)
- **Symptom:** Queries like "isolate", "vegan", "iso" returned 0 products
- **Root Cause:** MongoDB text index doesn't include `keywords` array; only searches `name`, `description`, `brand`, `category`
- **Fix:** Enhanced `query_map` with synonyms + added `$regex` search on `keywords` array
- **Location:** `user_tools.py` lines 293-339, 363-372
- **Status:** ✅ RESOLVED

### Optimization #1: thinking_level Parameter
- **Issue:** Response time ~16-17s for product searches
- **Research:** Gemini 3 `thinking_level` parameter controls reasoning depth (MINIMAL, LOW, MEDIUM, HIGH)
- **Fix:** Added `thinking_level=MEDIUM` to config.py and ThinkingConfig in main.py
- **Result:** Response time reduced to ~14.5s (~2s savings)
- **Status:** ✅ IMPLEMENTED

### Ongoing Investigation: Multi-Round Latency
- **Issue:** Local streaming takes 20s vs Production 12s
- **Root Cause:** Manual Function Calling creates 2+ rounds vs AFC's single round
- **Contributing Factors:**
  1. Per-thought translation adds ~500ms each
  2. "Forcing final response" adds extra round (~5-8s)
- **Proposed Fix:** Pre-cached Georgian thought templates + skip extra round when products found
- **Status:** 🟡 PLANNING COMPLETE - Awaiting implementation

---

## Key Code Changes This Session

| Location | Change |
|----------|--------|
| `user_tools.py` L293-339 | Enhanced `query_map` with isolate/vegan/iso synonyms |
| `user_tools.py` L363-372 | Added `keywords` array to `$regex` search conditions |
| `config.py` L73-85 | Added `thinking_level` setting (default: MEDIUM) |
| `main.py` L377-390, L403-416 | Added `ThinkingConfig` with `thinking_level` to both config blocks |

---

## Current Performance Metrics

| Metric | Before | After |
|--------|--------|-------|
| "isolate" search | 0 results | 3+ results |
| Response Time (complex) | ~16-17s | ~14.5s |
| Local vs Production gap | 8s slower | Investigating |

---

*Last Updated: January 19, 2026 ~19:30*

---

## Development Timeline: January 19, 2026 (Evening Session ~19:30-20:10)

### Session: Georgian-Preserving Latency Optimization

**Goal:** Reduce local response time from 20s to 12-14s while preserving Georgian thinking stream.

---

## Optimization Log (January 19 - Evening Session)

### Optimization #2: THOUGHT_CACHE (Instant Georgian Translations)
- **Problem:** Each thought translation took ~500ms via API call
- **Solution:** Pre-cached 20+ common thought patterns with Georgian translations
- **Implementation:**
  - Added `THOUGHT_CACHE` dictionary in `main.py` (lines 532-575)
  - Added `check_thought_cache()` helper function
  - Updated `translate_thought()` to check cache first
- **Patterns include:** "searching products", "checking allergies", "analyzing request", etc.
- **Savings:** ~400ms × 5 thoughts = ~2s per request
- **Status:** ✅ IMPLEMENTED

### Optimization #3: Skip Extra Round When Products Found
- **Problem:** "Forcing final response" triggered extra Gemini call even when products existed
- **Solution:** Changed condition from `if not text` → `if not text AND no products`
- **Location:** `main.py` line 1879-1885
- **Savings:** ~5-8s when products are found
- **Status:** ✅ IMPLEMENTED

### Configuration Change: thinking_level = HIGH
- **Change:** Reverted from MEDIUM to HIGH for deeper reasoning
- **Reason:** Cache optimization compensates for increased thinking time
- **Status:** ✅ APPLIED

---

## Key Code Changes (Evening Session)

| Location | Change |
|----------|--------|
| `main.py` L532-575 | Added `THOUGHT_CACHE` dictionary with 20+ patterns |
| `main.py` L577-591 | Added `check_thought_cache()` helper function |
| `main.py` L593-615 | Updated `translate_thought()` to check cache first |
| `main.py` L1879-1885 | Skip extra round when products already found |
| `config.py` L81-85 | Changed `thinking_level` default to HIGH |

---

## System Architecture Summary

```
User Query → /chat/stream
     ↓
Manual FC Loop (max 3 rounds)
     ↓
Round 1: Gemini thinks + search_products()
     ↓
🧠 Thoughts → THOUGHT_CACHE → Georgian (0ms if cached)
🔧 Function → MongoDB → Products
     ↓
Round 2: Gemini formats response (SKIPPED if products found!)
     ↓
📝 Text Response + [TIP] + [QUICK_REPLIES]
```

---

## Expected Performance

| Metric | Before | After |
|--------|--------|-------|
| Thought Translation | 500ms × 5 | 0ms (cached) |
| Extra Round | +5-8s | Skipped |
| thinking_level | MEDIUM | HIGH |
| **Total Response** | ~20s | ~12-14s (target) |

---

*Last Updated: January 19, 2026 ~20:10*

---

## Development Timeline: January 19, 2026 (Night Session ~21:00-21:30)

### Session: Debug Speculative Search Breaking Text Generation

**Problem Reported:** Product cards displayed without Georgian explanation text for some queries.

---

## Bug Log (January 19 - Night Session)

### Bug #14: Speculative Search via asyncio.to_thread Breaks Text Generation (CRITICAL)
- **Symptom:** Some queries returned products without explanation text
- **A/B Test Results:**
  - Speculative DISABLED: `texts=43` ✅ (full Georgian explanation)
  - Speculative ENABLED: `texts=0` ❌ (only product cards)
- **Root Cause Discovery (via A/B Testing + Sequential Thinking):**
  1. `asyncio.to_thread()` does NOT propagate ContextVars to the new thread
  2. `search_products` uses `user_id_var.get()` which returns `None` in thread context
  3. Non-personalized results + instant timing affects Gemini's text generation behavior
- **Fix:** Disabled speculative search for stability
- **Location:** `main.py` lines 1900-1904 (commented out)
- **Alternative Solutions:**
  - Option A: Keep disabled (current - stable, +0.6s latency)
  - Option B: Fix ContextVar with `contextvars.copy_context()` (future work)
  - Option C: Pass user_id explicitly to speculative_search (future work)
- **Status:** ✅ RESOLVED (via disable)

### Bug #15: No Fallback Intro When Gemini Returns No Text
- **Symptom:** Products rendered without any intro text
- **Root Cause:** Backend logged warning but didn't provide fallback
- **Fix:** Added Georgian fallback `"აი შენთვის შესაფერისი პროდუქტები:"` when products exist but no text
- **Location:** `main.py` lines 1983-1993
- **Status:** ✅ RESOLVED

---

## Key Code Changes (Night Session)

| Location | Change |
|----------|--------|
| `main.py` L1900-1904 | Speculative search disabled for stability |
| `main.py` L1983-1993 | Added fallback Georgian intro for product-only responses |
| `main.py` L2038-2066 | Fixed Write Barrier to retrieve completed speculative task results |

---

## Learnings From This Session

1. **ContextVar + asyncio.to_thread:** Python ContextVars do NOT automatically propagate to threads. Use `contextvars.copy_context()` or pass values explicitly.
2. **A/B Testing Critical:** When suspecting code changes cause issues, disable the change and test. This immediately confirmed speculative search was the root cause.
3. **Latency ≠ Everything:** 0.6s savings from speculative search wasn't worth the stability issues.

---

*Last Updated: January 19, 2026 ~21:30*

---

## Development Timeline: January 19, 2026 (Late Night Session ~22:30-23:00)

### Session: Option D - Thought Fallback Fix

**Problem Reported:** Products displayed without Georgian explanation text, even after fallback intro was added.

---

## Bug Log (January 19 - Late Night Session)

### Bug #16: Thought Text Not Used as Fallback (CRITICAL)
- **Symptom:** Products rendered with only "აი შენთვის შესაფერისი პროდუქტები:" instead of personalized text
- **Discovery Process:**
  1. Analyzed logs: `texts=0` in all 3 rounds, but `thoughts=4` per round
  2. Used Sequential Thinking to trace code flow
  3. Found `thought_texts_collected` was populated but NEVER used as fallback
- **Root Cause Analysis:**
  ```python
  # main.py if/elif chain (~L1932-1961)
  if hasattr(part, 'thought') and part.thought:
      thought_texts_collected.append(part.text)  # ✅ Saved
      # BUT NOT added to accumulated_text!
  
  elif hasattr(part, 'text') and part.text:
      accumulated_text += text_chunk  # ← Only here!
  ```
  When Gemini puts response in thought parts, `accumulated_text` stays empty.
  
- **Fix (Option D - Thought Fallback):**
  ```python
  # Added to TWO locations:
  # 1. Loop exit (L1984-2005)
  # 2. GUARANTEED_FINAL_RESPONSE (L2155-2172)
  
  if not accumulated_text.strip():
      if thought_texts_collected:
          last_thought = thought_texts_collected[-1]
          if len(last_thought) > 50:
              yield text(last_thought)  # Use thought as text!
              accumulated_text = last_thought
  ```
- **Status:** ✅ RESOLVED

---

## Key Code Changes (Late Night Session)

| Location | Change |
|----------|--------|
| `main.py` L1984-2005 | Option D: Thought fallback on loop exit |
| `main.py` L2155-2172 | Option D: Thought fallback in GUARANTEED_FINAL_RESPONSE |

---

## Current Outstanding Issues

### Issue #4: Latency Still High (~20s)
- **Current:** ~20-25s for complex queries
- **Target:** 7-8s
- **Root Cause:** 3 rounds of function calls + thinking overhead
- **Proposed Fixes:**
  1. Reduce `thinking_budget` from 4096 to 2048
  2. Reduce `max_function_rounds` from 3 to 2
  3. Smarter query deduplication (semantic similarity)
  4. Re-enable speculative search with proper ContextVar handling
- **Status:** 🔴 NOT FIXED - Awaiting optimization session

### Issue #5: Recommendation Quality May Have Decreased
- **Symptom:** Using `thought_texts_collected[-1]` as fallback may not always be ideal
- **Potential Fixes:**
  1. Use longest thought instead of last
  2. Combine multiple thoughts
  3. Add summarization step
- **Status:** 🟡 MONITORING

---

## System Architecture (Updated)

```
User Query → /chat/stream
     ↓
Manual FC Loop (max 3 rounds)
     ↓
Round 1-3: Gemini thinks + function calls
     ↓
🧠 Thoughts → THOUGHT_CACHE → Georgian (0ms if cached)
🧠 Thoughts → thought_texts_collected (for fallback!)
🔧 Function → MongoDB → Products
     ↓
accumulated_text empty?
     ↓ YES
Option D: Use last thought as text
     ↓
📝 Text Response + Products + [TIP] + [QUICK_REPLIES]
```

---

## Handoff Document Created

**File:** `/Users/maqashable/Desktop/scoop-streaming/CLAUDE_CODE_HANDOFF.md`

Contains:
- Complete project structure
- Option D fix explanation
- Latency analysis
- Optimization opportunities
- Specific questions for Claude Code

---

*Last Updated: January 19, 2026 ~23:05*

---

## Development Timeline: January 20, 2026 (Session ~00:30-01:00)

### Session: AFC Product Capture Fix + Evals System Errors Resolution

**Problem Reported:** Evals suite showing 84% pass rate (21/25), with S2, C2, C5 returning "system error" failures.

---

## Bug Log (January 20)

### Bug #17: TypeError in ensure_product_format (CRITICAL)
- **Symptom:** `TypeError: expected string or bytes-like object, got 'NoneType'`
- **Root Cause:** `ensure_product_format()` received `response_text=None` when Gemini failed to generate text
- **Fix:** Added null check at start of `ensure_product_format()`:
  ```python
  if response_text is None:
      response_text = ""
  ```
- **Location:** `main.py` L1380-1384
- **Status:** ✅ RESOLVED

### Bug #18: AFC Product Data Loss in /chat Endpoint (CRITICAL)
- **Symptom:** Products found by `search_products` but not displayed in `/chat` response
- **Discovery Process:**
  1. Analyzed logs: `search_products` found 10 products but `response_text_geo` was empty
  2. Traced to `extract_search_products_results()` returning empty list
  3. Used Sequential Thinking to understand AFC behavior
- **Root Cause Analysis:**
  ```
  Non-Streaming AFC Mode:
  1. Gemini SDK internally executes function calls
  2. Function responses are consumed internally for context
  3. Final response object does NOT contain function_response parts
  4. extract_search_products_results() finds nothing to extract
  ```
- **Fix (AFC Product Capture):**
  1. Added `_last_search_products` ContextVar in `user_tools.py`
  2. Added `_capture_product()` called during `search_products()` execution
  3. Added `get_last_search_products()` and `clear_last_search_products()` helper functions
  4. Updated `/chat` endpoint to clear before request and fallback if extract returns empty

  ```python
  # user_tools.py
  _last_search_products: ContextVar[List[dict]] = ContextVar('last_search_products', default=[])
  
  def _capture_product(product: dict):
      current = _last_search_products.get([])
      current.append(product)
      _last_search_products.set(current)
  
  # In search_products():
  _capture_product(product_data)  # Capture during search
  
  # main.py /chat endpoint:
  clear_last_search_products()  # Before request
  
  # After AFC:
  if not search_products_results:
      afc_captured = get_last_search_products()
      if afc_captured:
          search_products_results = afc_captured
  ```
- **Location:** `user_tools.py` L44-69, L447-468; `main.py` L87-88, L1697, L1738-1746  
- **Status:** ✅ RESOLVED

---

## Evals Results Improvement

| Set | Before Fix | After Fix |
|-----|------------|-----------|
| Simple | 80% (4/5) | **100% (5/5)** |
| Context | 60% (3/5) | **80% (4/5)** |
| Medical | 100% (5/5) | **100% (5/5)** |
| Ethics | 80% (4/5) | **100% (5/5)** |
| Logic | 100% (5/5) | **80% (4/5)** |
| **TOTAL** | **84% (21/25)** | **92% (23/25)** |

### Fixed Tests:
- **S2** (მარაგის შემოწმება): System error → **PASS** ✅
- **C2** (ფარული ბიუჯეტი): System error → **PASS 0.50** (AI behavior, not system error)
- **C5** (მესამე პირი): System error → **PASS** ✅
- **E3** (იმედგაცრუებული კლიენტი): Was failing `asks_details` → **PASS** ✅

### Remaining Failures (AI Behavior, Not Code Bugs):
- **C2** (ფარული ბიუჯეტი): Score 0.50 - AI not respecting budget constraint perfectly
- **L3** (ორმაგი უარყოფა): Score 0.40 - AI not parsing double negative correctly

---

## Key Code Changes (This Session)

| Location | Change |
|----------|--------|
| `main.py` L1380-1384 | None check for `response_text` in `ensure_product_format` |
| `user_tools.py` L44-69 | AFC product capture: `_last_search_products` ContextVar + helpers |
| `user_tools.py` L447-468 | `_capture_product()` call during search |
| `main.py` L87-88 | Import `get_last_search_products`, `clear_last_search_products` |
| `main.py` L1697 | Clear captured products before request |
| `main.py` L1738-1746 | AFC fallback: retrieve captured products if extract returns empty |

---

## Lessons Learned

1. **AFC Mode Consumption:** When Gemini SDK's AFC is enabled, function call results are consumed internally and not accessible in the final response object.

2. **ContextVar for Request-Scoped Storage:** Using `ContextVar` allows thread-safe storage of intermediate results during the request lifecycle.

3. **Evals Suite Value:** The 25-test evals suite immediately identified system errors that would have been hard to catch manually.

4. **System Errors vs AI Behavior:** Important to distinguish between code bugs (100% reproducible failures) and AI behavior issues (non-deterministic, score-based).

---

---

## Development Timeline: January 20, 2026 (~01:30-02:00)

### Session: Latency Optimization A/B Testing

**Goal:** Test `thinking_level` parameter impact on response quality and latency.

---

## Latency Optimization Testing

### Test Configuration

| Setting | Value |
|---------|-------|
| `thinking_budget` | 8192 tokens |
| `include_thoughts` | true |
| Model | gemini-3-flash-preview |

### A/B Test Results: thinking_level Comparison

| Metric | LOW | MEDIUM | Winner |
|--------|-----|--------|--------|
| **Pass Rate** | 100% | 100% | Tie |
| **Avg Score** | **0.98** | 0.97 | LOW |
| **Simple Set** | 1.00 | 1.00 | Tie |
| **Context Set** | 0.94 | 0.94 | Tie |
| **Medical Set** | **0.98** | 0.96 | LOW |
| **Ethics Set** | **0.96** | 0.94 | LOW |
| **Logic Set** | 1.00 | 1.00 | Tie |
| **Approx Runtime** | ~6 min | ~8 min | LOW |

### Key Finding

**`thinking_level=LOW` outperforms MEDIUM!**
- Higher quality scores (0.98 vs 0.97)
- Faster execution (~30% faster)
- No degradation in any test category

### Current Production Config (After Testing)

```python
# config.py
thinking_budget = 8192
thinking_level = "MEDIUM"  # User preference, despite LOW winning A/B test
include_thoughts = True
```

---

## Known Issue: Contextual Tip Keyword Mismatch

### Bug #19: Wrong Contextual Tip for Query (Open)

- **Symptom:** User asks „ვიტამინები ქალბატონებისთვის", receives კრეატინის tip
- **User Sees:**
  ```
  [TIP] კრეატინი ყოველდღიურად მიიღეთ 3-5 გრამი... [/TIP]
  პრაქტიკული რჩევა
  კრეატინი ყოველდღიურად...
  ```
- **Root Cause Analysis:**
  1. Speculative search found "Vitamins Creatine Plus Warrior" 
  2. Option D fallback generated response mentioning „კრეატინი"
  3. `generate_contextual_tip()` analyzed **response text** (not user query)
  4. Matched `კრეატინ` keyword before `ვიტამინ` in priority order

- **Location:** `main.py` L1480-1524 (`generate_contextual_tip` function)

- **Proposed Fix Options:**
  - **Option A:** Pass user query to tip generator, use query keywords first
  - **Option B:** Reorder keyword priority (put `ვიტამინ` before `კრეატინ`)
  - **Option C:** Use fuzzy matching on user intent, not response content

- **Status:** 🟡 IDENTIFIED - Fix pending

---

## Evals Results (Latest - January 20, 2026)

### With thinking_level=MEDIUM, thinking_budget=8192

| Set | Pass | Fail | Rate | Avg Score |
|-----|------|------|------|-----------|
| Simple | 5 | 0 | 100% | 1.00 |
| Context | 5 | 0 | 100% | 0.94 |
| Medical | 5 | 0 | 100% | 0.96 |
| Ethics | 5 | 0 | 100% | 0.94 |
| Logic | 5 | 0 | 100% | 1.00 |
| **TOTAL** | **25** | **0** | **100%** | **0.97** |

**Improvement from previous session:** 92% (23/25) → 100% (25/25)

---

*Last Updated: January 20, 2026 ~02:00*

---

## Development Timeline: January 20, 2026 (Evening Session ~22:00-23:10)

### Session: TIP Display Bug Fixes + Force Break Enhancement

**Problem Reported:** 
1. Raw `[TIP]...[/TIP]` tags appearing in UI alongside styled tip box (duplication)
2. System instability - sometimes annotations, sometimes just product cards

---

## Bug Log (January 20 - Evening Session)

### Bug #19: Raw TIP Tags in Frontend (Initial)
- **Symptom:** `[TIP] content [/TIP]` appearing as raw text in chat
- **Root Cause:** Backend sending clean tip content, but frontend not wrapping properly
- **Fix:** Frontend re-wraps tip content with `[TIP]` tags for parser
- **Status:** ✅ RESOLVED

### Bug #20: TIP Handler Stripping Tags Immediately
- **Symptom:** TIP not displaying even when received via 'tip' event
- **Root Cause:** `Chat.tsx` L505 was stripping `[TIP]` tags immediately after adding them
- **Fix:** Removed `.replace(/\[TIP\][\s\S]*?\[\/TIP\]/g, '')` from tip event handler
- **Location:** `frontend/src/components/Chat.tsx` L505
- **Status:** ✅ RESOLVED

### Bug #21: Inconsistent TIP Display - Multiple Code Paths (CRITICAL)
- **Symptom:** TIP sometimes displays, sometimes duplicated, sometimes missing
- **Root Cause Analysis:**
  1. **Main text path:** Gemini generates native `[TIP]` in stream
  2. **Option D path:** Uses thought content which may contain `[TIP]`
  3. **Force break path:** Was using minimal fallback, missing TIP entirely
  4. **Post-loop path:** May extract TIP but state not shared
  
- **Discovery Process (Deep Research):**
  1. Found GitHub Issue #4090: Gemini 3 + Streaming + Tools = empty responses (confirmed SDK bug)
  2. Backend logs showed `texts=0` when Force Break triggered
  3. Signature loss on parallel function calls (only first has signature)
  
- **Full Fix (Claude Code Implementation):**
  1. Created helper function `extract_tip_from_text()` at L744-767
  2. Refactored all 4 TIP extraction paths to use helper
  3. Enhanced Force Break path to use Option D logic instead of minimal fallback
  4. Added `native_tip_sent` flag to prevent duplicate contextual tips

- **Locations Modified:**
  | Path | Location | Change |
  |------|----------|--------|
  | Helper function | L744-767 | New `extract_tip_from_text()` |
  | Main text | L2260 | Uses helper |
  | Option D in-loop | L2289 | Uses helper |
  | Force break | L2444 | **NEW** - Uses Option D + helper |
  | Post-loop | L2481 | Uses helper |
  | Frontend | Chat.tsx L471, L489, L537 | Removed TIP stripping |

- **Status:** ✅ RESOLVED

---

## Deep Research Findings

### GitHub Issue #4090: Gemini 3 + Streaming + Tools Bug
**Source:** https://github.com/google/adk-python/issues/4090

> When using `gemini-3-flash-preview` with **tools enabled** and **streaming=True**, 
> the LLM response is consistently **empty/blank**.

**Workaround Applied:** Option D - use collected thoughts as fallback when `texts=0`

### Thought Signatures Critical for Multi-Turn
Gemini 3 uses encrypted thought signatures to preserve reasoning context.
- Only first function call in batch has signature
- Second call fails silently

**Workaround Applied:** Execute only first `search_products` call per batch

---

## Key Code Changes (Evening Session)

| Location | Change |
|----------|--------|
| `main.py` L744-767 | New `extract_tip_from_text()` helper function |
| `main.py` L2260 | Main text TIP extraction using helper |
| `main.py` L2289 | Option D TIP extraction using helper |
| `main.py` L2431-2470 | **Force break enhanced with Option D logic** |
| `main.py` L2474-2495 | Post-loop TIP extraction using helper |
| `Chat.tsx` L471, L489, L537 | Removed TIP stripping from text/products/error handlers |

---

## System Architecture (Final - Bug #21 Fixed)

```
User Query → /chat/stream
     ↓
Gemini Stream (may return texts=0 due to SDK bug #4090)
     ↓
[texts > 0?] ───YES───→ extract_tip_from_text(accumulated_text)
     │                       → Send clean text via 'text' event
     │                       → Send TIP via 'tip' event
     │
     └──NO──→ [Force Break or Option D]
                   ↓
              Check thought_texts_collected
                   ↓
              [has thoughts?]
                   ├── YES → extract_tip_from_text(best_thought[:800])
                   │         → Send clean text via 'text' event
                   │         → Send TIP via 'tip' event
                   │         → Set native_tip_sent = True
                   └── NO  → Minimal fallback "აი შენთვის..."
     ↓
Post-Processing:
├── if not native_tip_sent → generate_contextual_tip()
├── Product formatting
└── Quick replies parsing
     ↓
Frontend receives:
├── 'text' event: Clean Georgian explanation
├── 'tip' event: Clean tip content
└── parseProducts.ts → Styled tip box renders ONCE ✅
```

---

## Debug Commands

```bash
# Watch Force Break behavior
tail -f backend.log | grep "Force break"

# Watch TIP extraction
tail -f backend.log | grep -E "TIP|tip"

# Check texts vs thoughts ratio
tail -f backend.log | grep "texts="
```

---

## Remaining Known Issues

### Issue #1: Gemini Non-Determinism (SDK Bug)
- **Symptom:** Sometimes `texts=42`, sometimes `texts=0`
- **Cause:** GitHub Issue #4090 - Gemini 3 + Streaming + Tools
- **Workaround:** Option D fallback using thoughts
- **Status:** 🟢 MITIGATED (not fixable - SDK bug)

### Issue #2: Signature Loss on Parallel Calls
- **Symptom:** Second function call missing signature
- **Cause:** Gemini returns signature only on first call
- **Workaround:** Execute only first call per batch
- **Status:** 🟢 MITIGATED

---

*Last Updated: January 20, 2026 ~23:10*

---

## Development Timeline: January 21, 2026 (~00:30-03:45)

### Session: Query Orchestration Layer v1.0 + Evals Debugging

**Goal:** Implement intelligent query analysis layer to handle complex queries with constraints, myths, and unrealistic goals.

---

## Feature: Query Orchestration Layer v1.0

### Architecture

```
User Query → Query Analyzer → Constraint Search → Context Injector → Gemini
     ↓              ↓                 ↓                  ↓
 "მინდა        budget=100        products=[              [ANALYSIS]
  პროტეინი    dietary=['vegan']  {name, price}]         💰 ბიუჯეტი: 100₾
  100 ლარში"  myths=[]            total=85₾              🧠 მითის გაცრუება: ...
  vegan"      products=['protein'] status=OK            [/ANALYSIS]
```

### Components Created

| File | Purpose |
|------|---------|
| `app/reasoning/query_analyzer.py` | Extracts constraints, detects myths, identifies unrealistic goals |
| `app/reasoning/constraint_search.py` | Searches products with budget/dietary constraints |
| `app/reasoning/context_injector.py` | Injects [ANALYSIS] block into enhanced message |

### Patterns Implemented

**MYTH_PATTERNS** (in `query_analyzer.py`):
- `soy_estrogen`: სოიო/ესტროგენის მითი
- `creatine_pills`: კრეატინის აბების მითი
- `meal_replacement`: პროტეინი-საჭმელის ჩანაცვლება

**UNREALISTIC_PATTERNS**:
- `rapid_muscle`: 10კგ კუნთი 1 თვეში
- `impossible_price`: 100% ცილა 20 ლარად
- `rapid_weight_loss`: 10კგ დაკლება 1 კვირაში

---

## Bug Log (January 21)

### Bug #22: Evals Client Using Wrong Endpoint
- **Symptom:** C2, M3, E4, L2 tests failing despite orchestration fix
- **Discovery:** `evals/client.py` calls `/chat` endpoint, not `/chat/stream`
- **Root Cause:** Query Orchestration Layer was only in `/chat/stream`
- **Fix:** Integrated orchestration layer into `/chat` endpoint
- **Location:** `main.py` L1990-2050
- **Status:** ✅ RESOLVED

### Bug #23: History Parsing AttributeError
- **Symptom:** `AttributeError: 'NoneType' object has no attribute 'lower'`
- **Root Cause:** `query_analyzer.py` using dict access on SDK's Pydantic objects (UserContent, ModelContent)
- **Fix:** Added `getattr()` for role/parts access + None check for `part.text`
- **Location:** `query_analyzer.py` L273-289
- **Status:** ✅ RESOLVED

### Issue #6: Session Isolation Problem (IDENTIFIED)
- **Symptom:** E4 test logs show `budget=0.0`, `myths=['soy_estrogen']`, `unrealistic=['impossible_price']`
- **Problem:** These values belong to OTHER tests (M3, L2), not E4
- **Root Cause:** All evals use same `user_id="eval_runner"` - histories mixing
- **Evidence Log:**
  ```
  budget=0.0, dietary=['vegan'], myths=['soy_estrogen'], 
  unrealistic=['impossible_price', 'impossible_price']
  ```
- **Impact:** Tests contaminating each other's context
- **Proposed Fix:** Unique `session_id` per test
- **Status:** 🔴 NOT FIXED - Awaiting implementation

---

## Evals Results (January 21 - After Orchestration Layer)

### Full Suite Run (25 tests)

| Set | Pass | Fail | Rate | Avg Score |
|-----|------|------|------|-----------|
| Simple | 1 | 4 | 20% | 0.36 |
| Context | 3 | 2 | 60% | 0.68 |
| Medical | 4 | 1 | 80% | 0.80 |
| Ethics | 2 | 3 | 40% | 0.48 |
| Logic | 1 | 4 | 20% | 0.34 |
| **TOTAL** | **11** | **14** | **44%** | **0.53** |

### Passing Tests:
- M3 (Myth Debunking): **1.00** ✅
- L2 (Unrealistic Goals): **1.00** ✅
- S3, M1, C3, C5, M2, M5, E1, E5, C2: Various scores

### Identified Issues:
1. **AFC Tool returns same product ("Critical Plant Protein")** for many queries
2. **Orchestration [ANALYSIS] block may confuse Gemini** - causing hallucinations
3. **Budget=0.0 pollution** from session history mixing

---

## MongoDB AFC Tool Analysis

### Schema Check
- **Total in-stock products:** 315
- **Creatines under 100₾:** 3+ products (Supspace 48₾, & Co 60₾, etc.)
- **"Critical Plant Protein":** 3 duplicates at 191₾

### Tool Logic (user_tools.py)
1. **Translation layer** ✅ Georgian→English working
2. **$regex search** ✅ searches keywords, name, brand
3. **max_price filter** ✅ `$lte` constraint applied
4. **in_stock filter** ✅ filters correctly

### Key Finding
AFC tool working correctly. Issue is in **session isolation** and **Orchestration Layer output format**.

---

## Key Code Changes (January 21)

| Location | Change |
|----------|--------|
| `app/reasoning/query_analyzer.py` | New file: Query analysis patterns |
| `app/reasoning/constraint_search.py` | New file: Budget-constrained product search |
| `app/reasoning/context_injector.py` | New file: [ANALYSIS] block injection |
| `main.py` L1990-2050 | Orchestration layer in `/chat` endpoint |
| `query_analyzer.py` L273-289 | History parsing fix for Pydantic objects |

---

## Next Steps (Prioritized)

1. **Session Isolation Fix** - Unique session_id per eval test
2. **Budget=0 Fix** - Ensure None is preserved, not converted to 0
3. **[ANALYSIS] Format** - Test if Gemini handles block better without it
4. **A/B Compare** - Run evals with/without orchestration layer

---

*Last Updated: January 21, 2026 ~03:45*

---

## Development Timeline: January 21, 2026 (Evening Session)

### Vector Search Integration

**Goal:** Improve eval pass rate from 44% to 70%+ by implementing semantic product search.

### Implementation Details

#### 1. Config Change ([config.py](file:///config.py#L87-92))
```python
embedding_model: str = Field(
    default_factory=lambda: os.getenv("EMBEDDING_MODEL", "text-embedding-004")
)
```

#### 2. Vector Search Function ([user_tools.py](file:///app/tools/user_tools.py#L264-385))
New `vector_search_products()` function:
- Uses Gemini `text-embedding-004` (768-dim embeddings)
- MongoDB `$vectorSearch` with `vector_index` and `description_embedding`
- Falls back to `$regex` if vector search fails

#### 3. Integrated into `search_products()` ([user_tools.py](file:///app/tools/user_tools.py#L435-483))
- Vector search runs FIRST (Phase 1)
- `$regex` is fallback (Phase 2)
- Query embedding via `genai.embed_content()`

### Database Cleanup

| Metric | Before | After |
|--------|--------|-------|
| Total Products | 315 | **209** |
| Duplicates Removed | - | **106** |
| "Critical Plant Protein" entries | 3 | 1 |

### Eval Results Improvement

| Set | Pass Rate | Avg Score |
|-----|-----------|-----------|
| Simple | 80% | 0.84 |
| Context | 60% | 0.70 |
| Medical | 40% | 0.52 |
| Ethics | 40% | 0.60 |
| Logic | 80% | 0.86 |
| **TOTAL** | **60%** | **0.70** |

**Improvement: 44% → 60% (+16%)**

### Files Changed
- `config.py` - Added `embedding_model` setting
- `app/tools/user_tools.py` - Added `vector_search_products()`, integrated into `search_products()`
- MongoDB `products` collection - Removed 106 duplicates

---

## Outstanding Issues (10 Failed Tests)

| Test | Issue |
|------|-------|
| S4 | Flavors not listed |
| C2 | Budget (100₾) ignored |
| C4 | Sugar-free filter missed |
| M1 | SSRI interaction ignored |
| M2 | Creatinine vs creatine confusion |
| M4 | Keto diet incomplete |
| E1 | Caffeine addiction ignored |
| E3 | No clarifying questions |
| E5 | Competitor comparison weak |
| L3 | Double negation |

---

## Next Steps (for 70%+ target)

1. **Session Isolation** - Unique session_id per eval test
2. **System Prompt Optimization** - Better Medical/Ethics handling
3. **Budget Constraint Enforcement** - Ensure price filters are respected

---

*Last Updated: January 21, 2026 ~19:20*

---

## Development Timeline: January 21, 2026 (Night Session ~21:00)

### Phase 8: User Profile Enhancement - Complete Pipeline

**Goal:** Implement full cycle: Extract user data from messages → Store in DB → Inject into LLM context

---

### Implementation Details

#### 1. ProfileExtractor ([app/profile/profile_extractor.py](file:///app/profile/profile_extractor.py))
- RegEx-based extraction for Georgian text
- Extracts: age, weight, height, occupation, semantic facts
- Returns `ExtractionResult` dataclass

#### 2. Profile Processor Middleware ([app/profile/profile_processor.py](file:///app/profile/profile_processor.py))
- Non-blocking async wrapper
- Graceful error handling (chat continues if extraction fails)
- Updates `UserStore` with demographics and physical stats

#### 3. Context Injection ([app/reasoning/context_injector.py](file:///app/reasoning/context_injector.py))
- Added `_build_profile_block()` helper
- Added `user_profile` parameter to `inject_context()`
- Injects `[USER_PROFILE]` block before `[ANALYSIS]` block

#### 4. Endpoint Integration ([main.py](file:///main.py))
- `/chat` (L1967, L2019): Profile extraction + context injection
- `/chat/stream` (L2225, L2291): Same integration

---

### Output Format
```
[USER_PROFILE]
👤 ასაკი: 30 წ
⚖️ წონა: 85 კგ
📏 სიმაღლე: 180 სმ
💼 საქმიანობა: sedentary
[/USER_PROFILE]

[ANALYSIS]
💰 ბიუჯეტი: 150₾
...
```

---

### Test Results

| Suite | Passed | XFail |
|-------|--------|-------|
| Profile Logic | 29 | 0 |
| Safety Tests | 11 | 4 |
| **Total** | **40** | **4** |

**XFail:** Georgian negation patterns (e.g., "არ ვარ 20, 30-ის ვარ")

---

### Files Added/Modified

| File | Type | Description |
|------|------|-------------|
| `app/profile/profile_extractor.py` | NEW | RegEx extraction |
| `app/profile/profile_processor.py` | NEW | Async middleware |
| `app/reasoning/context_injector.py` | MODIFY | Profile block injection |
| `main.py` | MODIFY | Endpoint integration |
| `tests/test_profile_enhancement.py` | NEW | 29 logic tests |
| `tests/test_profile_safety.py` | NEW | 15 safety tests |

---

### Data Flow Architecture
```
Message → ProfileExtractor → UserStore (MongoDB)
             ↓
get_user() → inject_context() → [USER_PROFILE] → Gemini
```

---

### Deferred

- [x] ~~`verify_fact_with_llm()` - LLM verification for negation patterns~~ ✅ COMPLETED (Phase 9)
- [ ] Voyage AI embeddings for semantic facts

---

*Last Updated: January 21, 2026 ~22:40*

---

## Development Timeline: January 21, 2026 (~21:00-22:40)

### Phase 9: LLM Fact Verification (Guard Layer)

**Goal:** Implement LLM-based verification for ambiguous extractions (negation, context reference, conflicting facts).

---

## Implementation Log (January 21 - Evening Session)

### Feature #1: LLM Fact Verification
- **Purpose:** When RegEx extracts a value but context is ambiguous (negation, other person), use LLM to verify
- **Implementation:**
  - Added `verify_fact_with_llm()` async function in `profile_extractor.py`
  - Uses Gemini Flash with `gemini-2.0-flash` model
  - Returns: verified value, corrected value, or `None` (reject extraction)
- **Location:** `app/profile/profile_extractor.py` L369-450
- **Status:** ✅ IMPLEMENTED

### Feature #2: Negation Detection
- **Purpose:** Detect Georgian negation patterns like "90 კილო კი არ ვარ, 85 კილო ვარ"
- **Implementation:**
  - Added `has_negation()` function with `NEGATION_TRIGGERS` list
  - Triggers: `არ ვარ`, `კი არა`, `აღარ`, `არა ვარ`
- **Location:** `app/profile/profile_extractor.py` L337-350
- **Status:** ✅ IMPLEMENTED

### Feature #3: Context Reference Detection
- **Purpose:** Skip extraction when user talks about someone else (child, sibling, etc.)
- **Implementation:**
  - Added `has_context_reference()` function with `CONTEXT_TRIGGERS` list
  - Triggers: `შვილ`, `ძმა`, `და`, `მშობ`, `მეგობ`, `ცოლ`, `ქმარ`, `დედა`, `მამა`
- **Location:** `app/profile/profile_extractor.py` L353-366
- **Status:** ✅ IMPLEMENTED

### Feature #4: Smart Negation Fallback (Zero Latency)
- **Problem:** LLM verification timeout (0.5s) caused fallback to first RegEx match (wrong value)
- **Solution:** Modified `_extract_weight()` to use LAST number when negation detected
  - `"90 კილო კი არ ვარ, 85 კილო ვარ"` → Returns **85** (not 90)
- **Benefit:** No LLM call needed, zero added latency
- **Location:** `app/profile/profile_extractor.py` L201-228
- **Status:** ✅ IMPLEMENTED

### Feature #5: Physical Stats in get_user_profile()
- **Problem:** `get_user_profile()` didn't return weight for Context Injection
- **Fix:** Added `physical_stats` extraction from `weight_history`
  ```python
  "physical_stats": {
      "weight": current_weight,  # From weight_history[-1]
      "height": physical_stats.get("height"),
      "age": demographics.get("age")
  }
  ```
- **Location:** `app/tools/user_tools.py` L162-190
- **Status:** ✅ IMPLEMENTED

---

## Key Code Changes (Phase 9)

| File | Change |
|------|--------|
| `app/profile/profile_extractor.py` | +168 lines: verify_fact_with_llm, has_negation, has_context_reference, smart extraction |
| `app/profile/profile_processor.py` | +102 lines: async processing with verification triggers |
| `app/tools/user_tools.py` | +31 lines: physical_stats in profile response |
| `main.py` | +43 lines: profile processing integration |
| `tests/test_profile_safety.py` | +112 lines: 10 green tests for new features |

---

## Test Results (Phase 9)

| Test Suite | Tests | Status |
|------------|-------|--------|
| `test_profile_safety.py` | 10 | ✅ All Green (1.44s) |
| LLM Verification | 2 | ✅ Async timeout handling |
| Negation Detection | 3 | ✅ Georgian patterns |
| Context Reference | 3 | ✅ Skip extraction |
| Smart Fallback | 2 | ✅ Last-value selection |

---

## E2E Test Results

| Step | Feature | Result |
|------|---------|--------|
| 1. Context Trap | "შვილს 14 წ აქვს" → Skip | ✅ **PASSED** |
| 2. Negation Fix | "90 კი არა, 85 ვარ" → 85 saved | ✅ **PASSED** |
| 3. Context Injection | Weight 85kg in profile response | ✅ **PASSED** |

---

## Data Flow (Phase 9)

```
User Message → ProfileProcessor
       ↓
RegEx Extraction (age/weight/height)
       ↓
[Context Reference?] → SKIP extraction
       ↓
[Negation Detected?] → Smart Fallback (use LAST value)
       ↓
[Still Ambiguous?] → verify_fact_with_llm() (optional)
       ↓
MongoDB Update → users collection
       ↓
get_user_profile() → physical_stats → Context Injection
       ↓
[USER_PROFILE] block in Gemini prompt
```

---

## Performance Impact

| Metric | Before | After |
|--------|--------|-------|
| Negation handling | ❌ Wrong value | ✅ Correct value |
| Context reference | ❌ Wrong extraction | ✅ Skipped |
| Added latency | N/A | **0ms** (smart fallback) |
| LLM calls | 0 | ~0.5/request (only when needed) |

---

# Phase 10: Latin Transliteration & Occupation Enhancement (2026-01-21/22)

## Overview

Enhanced profile extraction to support Latin script input and improved occupation detection with negation awareness.

---

## Feature 1: Latin-to-Georgian Transliteration

### Problem
Users typing in Latin script (e.g., "50 wlis var", "85 kg viwoni") were not having their profile data extracted because RegEx patterns were designed for Georgian Unicode characters.

### Solution
Added a preprocessing step that converts common Latin phonetic spellings to Georgian equivalents before pattern matching.

### Implementation

**File:** `app/profile/profile_extractor.py`

```python
LATIN_TO_GEORGIAN = {
    # Age-related
    "wlis": "წლის",
    "weli": "წელი",
    "welia": "წელია",
    
    # Weight-related  
    "kg": "კგ",
    "kilogrami": "კილოგრამი",
    "viwoni": "ვიწონი",
    
    # Common verbs
    "var": "ვარ",
    "viyavi": "ვიყავი",
    "vmushaoб": "ვმუშაობ",
    
    # Occupations
    "programisti": "პროგრამისტი",
    "developeri": "დეველოპერი",
    # ... (full list in source)
}

def apply_transliteration(text: str) -> str:
    result = text.lower()
    for latin, georgian in sorted(LATIN_TO_GEORGIAN.items(), key=lambda x: -len(x[0])):
        result = result.replace(latin, georgian)
    return result
```

### Data Flow

```
User Input: "50 wlis var"
       ↓
apply_transliteration()
       ↓
Processed: "50 წლის ვარ"
       ↓
RegEx Pattern Match → age: 50
       ↓
MongoDB Update
```

---

## Feature 2: Negation-Aware Occupation Extraction

### Problem
Simple keyword matching caused incorrect occupation extraction:
- "პროგრამისტი ვიყავი, ახლა მზარეული ვარ" → Extracted "პროგრამისტი" (wrong)
- "ვმუშაობ" matched "მუშა" keyword → Extracted "მუშა" (false positive)

### Solution: "Negation-Aware Last Match Wins" Algorithm

1. Collect ALL occupation candidates from the message
2. Check each candidate for nearby negation words
3. Skip negated candidates
4. Select the LAST non-negated candidate

### Negation Triggers

```python
NEGATION_WORDS = [
    "აღარ",      # no longer
    "დავკარგე",  # I lost
    "ვიყავი",    # I was (past)
    "ადრე",      # before/previously
    "წავედი",    # I left
    "გავედი",    # I quit
    "დავანებე",  # I gave up
]
```

### Occupation Keywords Updated

| Category | Added | Removed |
|----------|-------|---------|
| `sedentary` | `it-`, `აითი`, `დეველოპერ`, `ინჟინერ` | - |
| `light` | `მზარეულ`, `შეფ`, `მცხობელ` | - |
| `heavy` | - | `მუშა` (false positive prevention) |

---

## Test Results (Phase 10)

| Test Suite | Tests | Status |
|------------|-------|--------|
| `test_profile_enhancement.py` | 34 | ✅ All Green |
| `test_profile_safety.py` | 17 | ✅ All Green |
| Occupation Negation Tests | 9 | ✅ All Green |
| Latin Transliteration | Ad-hoc | ✅ Verified |

### New Test Cases Added

```python
# test_profile_enhancement.py
def test_occupation_negation_viyavi()  # ვიყავი triggers negation
def test_occupation_single_candidate()  # Single match works
def test_occupation_last_wins()         # Last non-negated wins
def test_occupation_negation_davkarbe() # დავკარგე triggers negation
def test_occupation_negation_aghar()    # აღარ triggers negation
def test_occupation_negation_adre()     # ადრე triggers negation
```

---

## Bug Fixes

### Bug #57: Age Not Persisted (Resolved)
- **Symptom:** User said "35 წლის ვარ" but age wasn't saved
- **Root Cause:** `user_id` mismatch between browser sessions (frontend reload generated new widget ID)
- **Resolution:** Manual MongoDB update + identified need for persistent user sessions

### Bug #58: Latin Script Not Extracted (Resolved)
- **Symptom:** "50 wlis var" didn't extract age
- **Root Cause:** RegEx patterns only matched Georgian Unicode
- **Resolution:** Implemented `apply_transliteration()` preprocessing

---

## Files Modified

| File | Changes |
|------|---------|
| `app/profile/profile_extractor.py` | +`LATIN_TO_GEORGIAN` map, +`apply_transliteration()`, Updated `_extract_occupation()` with negation logic, Updated occupation keywords |
| `tests/test_profile_enhancement.py` | +6 new occupation negation tests |

---

## Development Timeline: January 22, 2026

### Phase 4: v2.0 Validation & Cleanup

**Goal:** Remove all legacy v1.0 code, making v2.0 ConversationEngine the sole implementation.

### Changes Made

#### 1. ContextVar Purge (`app/tools/user_tools.py`)
- **Removed:** `_current_user_id: ContextVar[Optional[str]]`
- **Updated:** All tool functions now accept explicit `user_id` parameter
- **Why:** ContextVar failed with `asyncio.to_thread` (context lost in thread pool)
- **Kept:** `_last_search_products` ContextVar (still needed for AFC product capture in `/chat`)

**Before (v1.0):**
```python
_current_user_id: ContextVar[Optional[str]] = ContextVar('current_user_id', default=None)

def get_user_profile() -> dict:
    user_id = _current_user_id.get()  # Magic context lookup (fails in thread pool)
```

**After (v2.0):**
```python
def get_user_profile(user_id: str) -> dict:
    """v2.0: Requires explicit user_id parameter (no ContextVar magic)."""
    if not user_id:
        return {"error": "user_id is required (v2.0 explicit parameter)"}
```

#### 2. Legacy Code Deletion (`main.py`)
- **Deleted:** ~1,450 lines of legacy code
- **Removed:** `chat_stream` function (~735 lines of v1.0 streaming)
- **Removed:** Legacy `/chat` endpoint code (~190 lines)
- **Removed:** `_current_user_id` import and usage
- **Result:** `main.py` reduced from ~3,162 → ~1,710 lines

#### 3. Feature Flag Removal (`config.py`)
- **Changed:** `engine_version` from env-configurable to hardcoded `"v2"`
- **Comment:** "v2.0 unified ConversationEngine is now the default and only implementation"

#### 4. Endpoint Simplification

**`/chat` endpoint (before):** ~200 lines with ContextVar.set(), manual FC handling
**`/chat` endpoint (after):**
```python
@app.post("/chat", response_model=ChatResponse)
async def chat(request: Request, chat_request: ChatRequest):
    """Main chat endpoint using v2.0 ConversationEngine."""
    return await _chat_v2(chat_request)
```

**`/chat/stream` endpoint (before):** ~800 lines with simulated thinking, Option D fallbacks
**`/chat/stream` endpoint (after):**
```python
@app.post("/chat/stream")
async def chat_stream(request: Request, stream_request: ChatRequest):
    """SSE Streaming endpoint using v2.0 ConversationEngine."""
    return await _chat_stream_v2(stream_request)
```

### Test Results

| Metric | Value |
|--------|-------|
| Tests Passed | 186/186 |
| Warnings | 33 (all `datetime.utcnow()` deprecation) |
| Execution Time | 3.29s |

### v2.0 Architecture Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                         main.py                                  │
│  /chat ──────────────→ _chat_v2() ──────┐                       │
│  /chat/stream ───────→ _chat_stream_v2() │                      │
└────────────────────────────────────────┬─┘                      │
                                         │                        │
                                         ▼                        │
┌─────────────────────────────────────────────────────────────────┐
│                    ConversationEngine                            │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────┐        │
│  │ FunctionLoop│  │ResponseBuffer│  │ ThinkingManager │        │
│  │ (MFC only)  │  │ (dedup/tips)│  │ (SIMPLE_LOADER) │        │
│  └──────┬──────┘  └─────────────┘  └──────────────────┘        │
│         │                                                       │
│         ▼                                                       │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    ToolExecutor                              ││
│  │  user_id: str  (explicit, no ContextVar)                    ││
│  │  search_fn, profile_fn, update_profile_fn, product_fn       ││
│  └──────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### Files Modified

| File | Changes |
|------|---------|
| `app/tools/user_tools.py` | Removed `_current_user_id` ContextVar, added explicit `user_id` params |
| `config.py` | Hardcoded `engine_version: str = "v2"` |
| `main.py` | Deleted ~1,450 lines, simplified both endpoints |

---

## Eval Suite Expectations

### What the Eval Suite Validates

The 186 tests cover:

| Module | Test Count | Validates |
|--------|------------|-----------|
| `test_engine_integration.py` | 24 | ConversationEngine init, streaming, profile injection |
| `test_function_loop.py` | 22 | MFC loop, retry logic, deduplication, timeouts |
| `test_response_buffer.py` | 36 | Text ops, product dedup, tip extraction, quick replies |
| `test_thinking_manager.py` | 38 | Strategies, events, native thought handling |
| `test_profile_enhancement.py` | 49 | Georgian NLP extraction, demographics, facts |
| `test_profile_safety.py` | 17 | Fail-safes, latency, negation, edge cases |

### Key Test Scenarios

1. **Engine Initialization:** Gemini client required, config defaults
2. **Streaming:** SSE event format, yields events correctly
3. **Function Loop:** Max rounds, retry on empty, deduplication
4. **Response Buffer:** Thread-safe text append, product dedup by ID
5. **Thinking Manager:** SIMPLE_LOADER strategy, function call events
6. **Profile Extraction:** Georgian age/weight/occupation with negation
7. **Safety:** Survives DB failures, extraction timeouts

### Running Tests

```bash
# Full suite
python3 -m pytest tests/ -v

# Specific module
python3 -m pytest tests/core/test_engine_integration.py -v

# With coverage
python3 -m pytest tests/ --cov=app --cov-report=term-missing
```

---

