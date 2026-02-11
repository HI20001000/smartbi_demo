# LLM JSON Completion Prompt Contract

## Purpose
Single-pass JSON completion enriches a normalization draft while preserving protected data and schema integrity.

## Input Payload
A JSON object with:
- `draft` (object): current normalized draft.
- `time_resolved` (object|null): resolved time information.
- `risk_flags` (array[string]): detected risk flags.
- `allowed_fields` (array[string]): only these fields may be changed or added.
- `protected_fields` (array[string]): these fields are immutable when present in `draft`.

## Model Output
Strict JSON object:
- `completed` (object, required): candidate enriched draft.
- `explanations` (object, optional): short reason per changed field.

## Allowed and Forbidden Edits
- Allowed:
  - Fill missing or improve values for fields in `allowed_fields`.
- Forbidden:
  - Overwrite protected fields.
  - Modify fields outside `allowed_fields`.
  - Emit markdown, prose, code fences, or non-JSON wrappers.

## Enforcement (Post-LLM)
1. Parse output as JSON.
2. Read `completed` object only.
3. Revert any protected-field overwrite to original draft value.
4. Revert any non-allowed field changes to original draft value.
5. Run schema validator; on failure fallback to original draft.
