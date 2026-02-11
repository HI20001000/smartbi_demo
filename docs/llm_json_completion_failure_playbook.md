# LLM JSON Completion Failure Playbook

## Failure Modes and Fallback

### 1) Timeout / client call error
- Condition: LLM call raises timeout or transport error.
- Action: do not retry indefinitely (respect `max_attempts`); fallback to original draft.

### 2) Parse failure
- Condition: response is not valid JSON.
- Action: record failure hook and fallback to original draft.

### 3) Contract failure
- Condition: parsed JSON missing `completed` object.
- Action: record failure hook and fallback to original draft.

### 4) Protected-field overwrite attempt
- Condition: candidate changes a protected field present in original draft.
- Action: force protected field back to original value; continue.

### 5) Non-allowed-field edit attempt
- Condition: candidate modifies any field not in `allowed_fields`.
- Action: force field back to original value; continue.

### 6) Schema validation failure
- Condition: post-enforcement candidate fails schema validation.
- Action: record failure hook and fallback to original draft.
