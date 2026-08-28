# resolve / price / mark

**Current contract:** [public.md](public.md). Leftovers: [gaps.md](gaps.md).

```text
intent + zone + services
  → resolve(ResolutionRequest)
  → Porto
  → PortoMarkRequest
  → mark(one | many)
  → PortoMark
```

`Porto` is the frozen execution identity. `mark` must not re-resolve from letter type + weight.

`price` is an optional catalog lookup. It is not required before `mark`, and it is not execution identity.

Address is execution input only when `Porto.requires` contains `ADDRESS_SENDER` and/or `ADDRESS_RECIPIENT`. Registered mail does not imply address by itself.
