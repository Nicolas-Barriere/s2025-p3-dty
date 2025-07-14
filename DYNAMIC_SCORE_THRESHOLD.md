# Dynamic Score Threshold Enhancement

## Overview
Enhanced the score filtering system to use a **dynamic threshold based on the highest score** rather than a fixed threshold. This makes filtering adaptive and intelligent across different query qualities.

## Problem with Fixed Threshold
### Before Enhancement:
```
Query A: "urgent meeting documents" 
Results: [0.95, 0.88, 0.75, 0.42, 0.28, 0.15]
Fixed threshold: 0.3
→ Shows: [0.95, 0.88, 0.75, 0.42] (4 results)

Query B: "blue email yesterday"
Results: [0.45, 0.38, 0.31, 0.25, 0.18, 0.12] 
Fixed threshold: 0.3
→ Shows: [0.45, 0.38, 0.31] (3 results, but all are mediocre)
```

**Issues:**
- ❌ Query A: Good results mixed with mediocre ones (0.42 shown despite much better options)
- ❌ Query B: All results are mediocre, but some still shown due to fixed threshold
- ❌ Not adaptive: Same threshold regardless of result quality

## Solution: Dynamic Percentage-Based Threshold
### After Enhancement:
```
Query A: "urgent meeting documents"
Results: [0.95, 0.88, 0.75, 0.42, 0.28, 0.15]
Highest score: 0.95
Dynamic threshold: 0.95 × 60% = 0.57
→ Shows: [0.95, 0.88, 0.75] (3 results, all high quality)

Query B: "blue email yesterday"  
Results: [0.45, 0.38, 0.31, 0.25, 0.18, 0.12]
Highest score: 0.45
Dynamic threshold: 0.45 × 60% = 0.27
→ Shows: [0.45, 0.38, 0.31] (3 results, best available for this query)
```

**Benefits:**
- ✅ Query A: Only excellent results shown, mediocre 0.42 filtered out
- ✅ Query B: Shows best available results relative to the query quality
- ✅ Adaptive: Threshold adjusts to each query's result quality

## Technical Implementation

### 1. Configuration Change
**File**: `src/backend/chatbot/config.py`
```python
# OLD (fixed threshold)
min_relevance_score: float = 0.3

# NEW (percentage-based)  
min_relevance_score_percentage: float = 0.6  # 60% of highest score
```

### 2. Dynamic Threshold Calculation
**File**: `src/backend/chatbot/email_service.py`
```python
# Calculate dynamic threshold based on highest score
if relevant_contents:
    scores = [result.get("score", 0.0) for result in relevant_contents]
    highest_score = max(scores) if scores else 0.0
    dynamic_threshold = highest_score * rag_system.config.min_relevance_score_percentage
    self.logger.info(f"Dynamic threshold: {dynamic_threshold:.3f} ({rag_system.config.min_relevance_score_percentage:.1%} of highest score {highest_score:.3f})")
else:
    dynamic_threshold = 0.0
```

### 3. Adaptive Filtering
```python
# Apply dynamic score threshold filtering
if relevance_score < dynamic_threshold:
    self.logger.debug(f"Filtered out email {matched_email_id} with score {relevance_score:.3f} (below dynamic threshold: {dynamic_threshold:.3f})")
    continue
```

## Configuration Options

### Percentage Values & Their Effects

#### **60% (Default - Balanced)**
- **Use case**: General purpose, good balance of quality vs quantity
- **Effect**: Shows top-tier and good results, filters weak matches
- **Example**: If best score is 0.8, shows emails scoring ≥ 0.48

#### **80% (Strict - High Quality)**
- **Use case**: When precision is more important than recall
- **Effect**: Only shows excellent results, very few but highly relevant
- **Example**: If best score is 0.8, shows emails scoring ≥ 0.64

#### **40% (Permissive - More Results)**
- **Use case**: When you want more results, willing to accept some noise
- **Effect**: Shows more results including moderate matches
- **Example**: If best score is 0.8, shows emails scoring ≥ 0.32

#### **100% (Extreme - Only Best)**
- **Use case**: Show only the absolute best match(es)
- **Effect**: Typically shows 1-2 results maximum
- **Example**: If best score is 0.8, shows only emails scoring ≥ 0.8

## Real-World Examples

### Scenario 1: Excellent Query Match
```
Query: "quarterly budget review meeting"
RAG Results: [0.92, 0.89, 0.81, 0.45, 0.32, 0.19]
Dynamic Threshold (60%): 0.92 × 0.6 = 0.55
Results Shown: [0.92, 0.89, 0.81] ✅ Perfect!
Filtered Out: [0.45, 0.32, 0.19] (weak matches removed)
```

### Scenario 2: Poor Query Match  
```
Query: "something about email from yesterday"
RAG Results: [0.35, 0.28, 0.22, 0.18, 0.14, 0.09]
Dynamic Threshold (60%): 0.35 × 0.6 = 0.21
Results Shown: [0.35, 0.28, 0.22] ✅ Best available
Filtered Out: [0.18, 0.14, 0.09] (very poor matches)
```

### Scenario 3: Mixed Quality Results
```
Query: "project deadline extension request"
RAG Results: [0.78, 0.71, 0.43, 0.39, 0.25, 0.12]
Dynamic Threshold (60%): 0.78 × 0.6 = 0.47
Results Shown: [0.78, 0.71] ✅ Only the strong matches
Filtered Out: [0.43, 0.39, 0.25, 0.12] (mediocre results removed)
```

## Enhanced API Response

The API now returns comprehensive threshold information:
```json
{
    "success": true,
    "results": [...],
    "total_searched": 500,
    "total_matched": 10,
    "results_after_filtering": 3,
    "dynamic_score_threshold": 0.552,
    "highest_score": 0.92,
    "score_threshold_percentage": 0.6,
    "processing_time": 2.1
}
```

## Advantages Over Fixed Threshold

### 1. **Query-Adaptive Quality**
- **High-quality queries**: Strict filtering, only excellent results
- **Medium-quality queries**: Moderate filtering, good results shown
- **Low-quality queries**: Lenient filtering, best available results

### 2. **Consistent User Experience**
- **Always shows relative best**: Users always see the top results for their query
- **No empty results**: Even poor queries show something useful
- **Quality scaling**: Result quality scales with query precision

### 3. **Better Search Satisfaction**
- **Higher precision**: Dramatically reduces irrelevant results
- **Contextual relevance**: Results are always relevant relative to what's available
- **Predictable behavior**: Users understand they get "top X%" of matches

## Logging Enhancement

Enhanced debugging with dynamic threshold information:
```
INFO: Dynamic threshold: 0.552 (60.0% of highest score 0.920)
DEBUG: Filtered out email abc123 with score 0.451 (below dynamic threshold: 0.552)
DEBUG: Added result for email def456 with score 0.782 (threshold: 0.552)
INFO: Step 6 completed: Matched and formatted 3 email results (after dynamic score filtering with threshold 0.552)
```

This dynamic approach ensures users **always get the most relevant results relative to their query quality** - excellence when possible, best available when necessary! 🎯
