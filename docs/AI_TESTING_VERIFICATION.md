# AI Testing & Verification Documentation
## Campus Resource Hub - Resource Concierge

**Document Version:** 1.0  
**Last Updated:** 2024-11-15  
**Status:** ✅ Implemented

---

## Overview

This document describes the comprehensive testing and verification framework for the AI Resource Concierge feature. These tests ensure that AI-generated outputs behave predictably, align with factual project data, and never return fabricated or unverifiable results.

## Requirements Met

✅ **Automated tests** verifying AI-generated outputs behave predictably  
✅ **Data alignment verification** - AI outputs align with factual project data  
✅ **Fabrication prevention** - AI components never return fabricated or unverifiable results  
✅ **Functional validation** - AI outputs validated for correct data  
✅ **Ethical validation** - AI outputs validated for appropriate, non-biased responses

---

## Test Suite Location

All AI verification tests are located in: `tests/test_concierge.py`

---

## Test Coverage

### 1. Resource Existence Verification
**Test:** `test_ai_outputs_only_mention_existing_resources`

**Purpose:** Ensures AI responses only mention resources that actually exist in the database, preventing fabrication of non-existent resources.

**What it tests:**
- Verifies that all resources in AI response results exist in the database
- Ensures no fabricated resource names appear in the resources list
- Validates that resource titles can be verified against database records

**Key Assertions:**
- All resources in `result['resources']` must exist in database
- Resource titles must match database records exactly
- No non-existent resources can appear in results

---

### 2. Factual Data Alignment
**Test:** `test_ai_outputs_align_with_factual_data`

**Purpose:** Verifies that AI responses contain accurate information matching database records. Tests functional correctness.

**What it tests:**
- Resource attributes (title, location, capacity, category) match database
- All returned resource data is verifiable against database records
- No discrepancies between AI response and actual data

**Key Assertions:**
- `returned_resource['title'] == db_resource.title`
- `returned_resource['location'] == db_resource.location`
- `returned_resource['capacity'] == db_resource.capacity`
- All attributes match database exactly

---

### 3. Fabrication Prevention
**Test:** `test_ai_outputs_no_fabricated_information`

**Purpose:** Ensures AI does not fabricate information about resources. All details must come from actual database records.

**What it tests:**
- Resource attributes in responses match database exactly
- No fabricated equipment, descriptions, or attributes
- Even if LLM mentions fabricated info in answer text, resource data must be accurate

**Key Assertions:**
- Resource data in response matches database exactly
- No fabricated attributes (equipment, capacity, etc.)
- Resource objects are source of truth, not LLM text

---

### 4. Ethical Appropriateness
**Test:** `test_ai_outputs_appropriate_and_non_biased_responses`

**Purpose:** Verifies AI responses are appropriate, non-biased, and professional. Tests ethical correctness.

**What it tests:**
- Response does not contain inappropriate terms
- Response is professional and helpful
- Response mentions actual resources (not fabricated)
- No discriminatory or biased language

**Key Assertions:**
- No inappropriate terms in response (discriminate, exclude, prefer, etc.)
- Response is non-empty and helpful
- Response mentions actual resources from database

---

### 5. Context Retrieval Verification
**Test:** `test_ai_context_retrieval_uses_actual_database_data`

**Purpose:** Verifies that the context retrieval system uses actual database data, not fabricated information.

**What it tests:**
- Context sent to LLM contains actual resource data
- Context includes verifiable resource attributes (title, location, capacity)
- Context does not contain fabricated data

**Key Assertions:**
- Context contains actual resource titles from database
- Context contains actual resource locations from database
- Context contains actual resource capacities from database
- No fabricated resource names or locations in context

---

### 6. Fallback Response Verification
**Test:** `test_ai_fallback_responses_use_actual_data`

**Purpose:** Verifies that fallback responses (when LLM unavailable) use actual database data and do not fabricate information.

**What it tests:**
- Fallback responses return actual database resources
- All returned resources exist in database
- Resource attributes match database exactly
- Fallback answer mentions actual resources

**Key Assertions:**
- All resources in fallback results exist in database
- Resource titles, locations, capacities match database
- Fallback answer mentions actual resource titles

---

### 7. Attribute Verification
**Test:** `test_ai_outputs_verifiable_resource_attributes`

**Purpose:** Verifies that all resource attributes in AI responses can be verified against the database. Ensures no attributes are fabricated.

**What it tests:**
- Every resource attribute matches database exactly
- resource_id, title, description, category, location, capacity, equipment, is_restricted, status all verified

**Key Assertions:**
- Every attribute in returned resource matches database:
  - `returned_resource['resource_id'] == db_resource.resource_id`
  - `returned_resource['title'] == db_resource.title`
  - `returned_resource['description'] == db_resource.description`
  - `returned_resource['category'] == db_resource.category`
  - `returned_resource['location'] == db_resource.location`
  - `returned_resource['capacity'] == db_resource.capacity`
  - `returned_resource['equipment'] == db_resource.equipment`
  - `returned_resource['is_restricted'] == db_resource.is_restricted`
  - `returned_resource['status'] == db_resource.status`

---

## Testing Strategy

### Database-First Approach
All tests create known resources in the database first, then verify that AI responses only reference those resources. This ensures:
- **Predictability:** We know exactly what resources exist
- **Verifiability:** Every resource can be verified against database
- **No Fabrication:** AI cannot invent resources that don't exist

### Mock LLM Responses
Tests use mocked LLM responses to simulate various scenarios:
- LLM mentioning fabricated resources (test verifies they're filtered out)
- LLM providing correct information (test verifies accuracy)
- LLM unavailable (test verifies fallback uses real data)

### Resource Data as Source of Truth
The `result['resources']` list is the authoritative source. Even if LLM text mentions fabricated information, the resource objects must match the database exactly.

---

## Running the Tests

### Run All AI Verification Tests
```bash
pytest tests/test_concierge.py -v
```

### Run Specific Test
```bash
pytest tests/test_concierge.py::test_ai_outputs_only_mention_existing_resources -v
```

### Run with Coverage
```bash
pytest tests/test_concierge.py --cov=src.services.concierge_service --cov-report=html
```

---

## Test Results Interpretation

### ✅ Passing Tests
- All resources in responses exist in database
- All resource attributes match database exactly
- No fabricated information in resource data
- Responses are appropriate and non-biased
- Context retrieval uses actual database data

### ❌ Failing Tests Indicate
- **Resource fabrication:** AI returned non-existent resources
- **Data mismatch:** Resource attributes don't match database
- **Fabricated attributes:** Equipment, capacity, or other attributes are invented
- **Inappropriate content:** Response contains biased or unprofessional language
- **Context issues:** Context sent to LLM contains fabricated data

---

## Continuous Verification

These tests should be run:
- ✅ Before every commit
- ✅ In CI/CD pipeline
- ✅ Before production deployment
- ✅ After any changes to ConciergeService
- ✅ After any changes to resource data structure

---

## Architecture Safeguards

### 1. Resource Retrieval Layer
The `ConciergeService._resource_matches()` method only queries the database. It cannot return resources that don't exist.

### 2. Serialization Layer
The `ConciergeService._serialize_resource()` method only serializes actual Resource objects from the database.

### 3. Context Formatting
The `ConciergeService._format_context_block()` method only formats resources that were retrieved from the database.

### 4. Response Structure
The service returns:
- `result['resources']` - List of actual database resources (source of truth)
- `result['answer']` - LLM-generated text (may contain errors, but resources list is accurate)

---

## Future Enhancements

Potential additional tests:
- [ ] Test for hallucinated resource availability times
- [ ] Test for fabricated booking information
- [ ] Test for inappropriate resource recommendations
- [ ] Test for bias in resource ranking/scoring
- [ ] Integration tests with real LLM (with validation)

---

## Related Documentation

- **AI Feature Documentation:** `docs/AI_FEATURE_DOCUMENTATION.md`
- **Architecture Documentation:** `docs/ARCHITECTURE_DOCUMENTATION.md`
- **Test Suite:** `tests/test_concierge.py`
- **Concierge Service:** `src/services/concierge_service.py`

---

**Maintained By:** Campus Resource Hub Development Team  
**Last Updated:** 2024-11-15  
**Next Review:** As needed when AI features are modified

