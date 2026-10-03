# Debugging Case (Part 12)

## Bug Report
> "The assistant tells the user 'Your appointment has been rescheduled' but the downstream tool timed out."

## Reproduction

### Minimal Repro Steps
1. Book appointment APT-1001 for P1001 (cardiology, 2026-10-07 10:00)
2. Start reschedule flow: `POST /assistant/message` with `session_id="sess-1"`, message="Reschedule APT-1001 to 2026-10-07 14:00"
3. Assistant replies: "Move APT-1001 ... to 2026-10-07 14:00? Reply yes to confirm"
4. User replies "yes"
5. **During tool execution**, downstream scheduling system times out (5s)
6. **Bug**: Assistant replies "Appointment APT-1001 is now on 2026-10-07 at 14:00" (COMPLETED)

### Test That Catches This
```python
# tests/test_workflow.py::test_timeout_during_execution_is_not_reported_as_success
def test_timeout_during_execution_is_not_reported_as_success():
    store = AppointmentStore()
    appt_id, a, b = _setup(store)
    workflow.step("s6", E(patient_id="P1001", appointment_id=appt_id,
                          date=b["date"], time=b["time"]), "move", store)

    def broken(*args, **kwargs):
        raise TimeoutError("simulated")
    store.reschedule = broken
    r = workflow.step("s6", E(), "yes", store)
    assert r.status.value == "not_possible"
    assert "is now on" not in r.reply
```

## Diagnosis

### Root Cause (Hypothetical Bug)
In `workflow.py::_confirm()`, if the tool call succeeds but the **response parsing fails**, or if the tool returns `ok=True` incorrectly:

```python
# BUGGY VERSION (what the bug report describes)
res = reschedule_appointment(store, f["appointment_id"], f["patient_id"], f["date"], f["time"])
# Missing: if not res.ok: check
appt = res.data["appointment"]  # KeyError or stale data
return Result(Status.COMPLETED, f"Appointment {appt['appointment_id']} is now on...")
```

### Why Current Code Is Correct
```python
# CURRENT CORRECT VERSION (app/workflow.py:49-63)
res = reschedule_appointment(store, f["appointment_id"], f["patient_id"], f["date"], f["time"])
if not res.ok:                                    # ← Guard clause
    return Result(Status.NOT_POSSIBLE, res.message)  # ← Never claims success
appt = res.data["appointment"]
return Result(Status.COMPLETED, ...)              # ← Only after ok=True
```

The `_guarded` wrapper in `tools.py` converts **any exception** (including `TimeoutError`) to `ToolResult(ok=False, code="tool_failure", message="The system could not confirm this action, so nothing is confirmed.")`.

## Fix (If Bug Existed)

### 1. Add Guard Clause
```python
res = reschedule_appointment(...)
if not res.ok:
    return Result(Status.NOT_POSSIBLE, res.message)  # Safe failure
```

### 2. Ensure `_guarded` Catches All Exceptions
```python
def _guarded(fn):
    try:
        return fn()
    except Exception:  # Catches TimeoutError, ConnectionError, etc.
        log.exception("tool failed unexpectedly")
        return _fail("tool_failure", "The system could not confirm this action, so nothing is confirmed.")
```

### 3. Add Integration Test
```python
def test_reschedule_timeout_does_not_claim_success():
    # ... setup ...
    store.reschedule = lambda *a, **k: (_ for _ in ()).throw(TimeoutError())
    r = workflow.step(session_id, entities, "yes", store)
    assert r.status == Status.NOT_POSSIBLE
    assert "is now on" not in r.reply
    # Verify appointment unchanged in store
```

## Verification
- Run `pytest tests/test_workflow.py::test_timeout_during_execution_is_not_reported_as_success -v`
- Run `pytest tests/test_tools.py::test_unexpected_failure_is_never_success -v`
- Both pass → bug cannot occur in current code

## Prevention
- **Rule**: Never access `res.data` without checking `res.ok` first
- **Static check**: Add mypy rule or custom linter for `ToolResult` usage
- **Code review checklist**: "Does every tool call check `ok` before using `data`?"