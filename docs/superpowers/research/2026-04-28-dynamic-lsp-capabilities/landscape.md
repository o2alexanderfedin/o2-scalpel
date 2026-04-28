# Solidlsp Current State + LSP-Client Landscape

**Researcher**: Agent B (landscape)
**Date**: 2026-04-28

---

## TL;DR (3 bullets)

- Solidlsp captures the initialize response only for ad-hoc `assert` checks in individual adapters; the full `ServerCapabilities` dict is never stored on the server object and is inaccessible after `_start_server` returns.
- `DynamicCapabilityRegistry` (v0.2.0 followup-01) records method names from `client/registerCapability` events correctly, but stores only method strings — not `registerOptions`, not the document-selector scope, and not the `id` needed to handle `client/unregisterCapability`. It is a shallow list, not a queryable capability map.
- Every mature LSP client (VSCode, Neovim, Helix, eglot) stores `ServerCapabilities` as a first-class field on the client object, then provides a single `supports_method(method)` / `supports_feature(feature)` predicate that checks both static init-response caps and dynamic registrations. Per-method param schemas are always hardcoded in client code — no client introspects them at runtime.

---

## Part 1 — Solidlsp today

### 1.1 ServerCapabilities handling

**File**: `vendor/serena/src/solidlsp/ls.py` (base class `SolidLanguageServer`)

The base class does NOT store the initialize response. `_start_server` is an abstract hook implemented per-adapter; most adapters discard the result entirely:

```python
# basedpyright_server.py:144
self.server.send.initialize(initialize_params)
self.server.notify.initialized({})
# return value dropped — no capture
```

The exceptions are a handful of adapters that capture `init_response` for narrow assertion checks then let it fall out of scope:

```python
# rust_analyzer.py:780–783
init_response = self.server.send.initialize(initialize_params)
assert init_response["capabilities"]["textDocumentSync"]["change"] == 2
assert "completionProvider" in init_response["capabilities"]
# ... then init_response is never stored on self
```

The same one-shot pattern appears in `nixd_ls.py`, `kotlin_language_server.py`, `typescript_language_server.py`, `luau_lsp.py`, and `perl_language_server.py`. In every case the capabilities dict is used for a startup sanity-check, not persisted.

**Consequence**: there is no `self._server_capabilities` field anywhere in the inheritance tree. Any post-init capability query must use either the static catalog or `DynamicCapabilityRegistry`.

There is one static capability gate on the base class:

```python
# ls.py:432–436
@classmethod
def supports_implementation_request(cls) -> bool:
    """Return whether this language server supports textDocument/implementation."""
    return False
```

This is a hardcoded `@classmethod` override pattern — subclasses override it to return `True`. It is the only per-method capability gate in solidlsp, and it is purely static.

### 1.2 Per-method param schemas in code

**File**: `vendor/serena/src/solidlsp/lsp_protocol_handler/lsp_requests.py`

This file is auto-generated from LSP 3.17 and defines typed request wrappers:

```python
async def implementation(
    self, params: lsp_types.ImplementationParams
) -> Union["lsp_types.Definition", list["lsp_types.LocationLink"], None]:
    return await self.send_request("textDocument/implementation", params)
```

Each method's param shape is a Python type from `lsp_types.py` — these are static dataclasses generated at build time. There is no runtime introspection of param schemas. Call sites in `ls.py` construct dicts inline:

```python
# ls.py:1495–1501 (_send_references_request)
return self.server.send.references(
    {
        "textDocument": {"uri": PathUtils.path_to_uri(...)},
        "position": {"line": line, "character": column},
        "context": {"includeDeclaration": False},
    }
)
```

The schema is implicit in each call site's dict literal. There is no registry mapping method names to their param constructors.

### 1.3 Where dynamic checks would hook in

Four natural seams:

1. **`SolidLanguageServer._start_server` / `override_initialize_params`** (ls.py:590–605): the `_initialize_with_override` wrapper intercepts the call just before send. Capturing the return value here would give the full `ServerCapabilities` dict at one chokepoint, before the subclass-specific `_start_server` body returns.

2. **`_handle_register_capability`** (ls.py:658–684): already fires on every `client/registerCapability` event. The current implementation extracts `method` and calls `DynamicCapabilityRegistry.register(sid, method)`. Extending this to also store `registerOptions` and `id` would be the minimal delta for full dynamic support.

3. **`build_capability_catalog`** (capabilities.py:219–287): currently calls `_get_initialize_params` (static) to extract `codeActionKind.valueSet`. A live alternative would call `registry.list_for(server_id)` for the running server's method set instead of walking adapter classes.

4. **`MultiServerCoordinator`** (multi_server.py): `_apply_priority` merges results from multiple servers. A per-server `supports(method)` predicate here would prevent dispatching to servers that don't support a method, instead of relying on empty-response handling after the fact.

### 1.4 DynamicCapabilityRegistry (v0.2.0 followup-01)

**File**: `vendor/serena/src/solidlsp/dynamic_capabilities.py`

```python
class DynamicCapabilityRegistry:
    """Append-only, thread-safe per-server registry."""

    def __init__(self) -> None:
        self._by_server: dict[str, list[str]] = {}
        self._lock = Lock()

    def register(self, server_id: str, method: str) -> None:
        with self._lock:
            existing = self._by_server.setdefault(server_id, [])
            if method not in existing:
                existing.append(method)

    def list_for(self, server_id: str) -> list[str]:
        with self._lock:
            return list(self._by_server.get(server_id, []))
```

**What it does**: Thread-safe append-only map from `server_id → [method, ...]`. Populated by `_handle_register_capability` in `ls.py`. Surfaced in `LanguageHealth.dynamic_capabilities` via `_build_language_health` in `scalpel_primitives.py`.

**What it's missing for dynamic-discovery**:

- **`registerOptions` not stored**: LSP `client/registerCapability` carries a `registerOptions` object per registration (e.g., `TextDocumentRegistrationOptions` with a `documentSelector`). The current code extracts only `reg["method"]`, discarding the options. A real capability gate needs the options to know *which documents* the registration applies to.
- **`id` not stored**: Each registration has a unique `id`. The `client/unregisterCapability` event references these ids. Without storing them, `_handle_unregister_capability` (ls.py:686–688) is a no-op — it ACKs but makes no change to the registry.
- **No `has(server_id, method)` predicate**: `list_for` returns a list; callers do `method in registry.list_for(sid)`, which is O(n). A `has(sid, method) -> bool` method would be the natural API for the `supports_method` gate needed in facades.
- **Server_id coverage is partial**: Only `BasedpyrightServer`, `PylspServer`, and `MarksmanServer` set `server_id` as a `ClassVar`. `RuffServer` and `RustAnalyzer` do not, so their dynamic registrations are silently dropped in `_handle_register_capability` (the `if sid:` guard fails).
- **No connection to the static catalog**: `LanguageHealth.dynamic_capabilities` is a separate tuple from `capabilities_advertised` on `ServerHealth`. There is no unified "is method X supported by server Y?" query that considers both.

---

## Part 2 — LSP-client landscape

### 2.1 VSCode lsp-client (TypeScript)

**Repo**: `microsoft/vscode-languageserver-node`, `client/src/common/`

**Capability-check pattern**: The client does not expose a `supports_method(name)` predicate. Instead, it uses a feature-plugin architecture. Each LSP method has a `DynamicFeature<RO>` implementation:

```typescript
export interface DynamicFeature<RO> {
  fillClientCapabilities(capabilities: ClientCapabilities): void;
  initialize(capabilities: ServerCapabilities,
    documentSelector: DocumentSelector | undefined): void;
  registrationType: RegistrationType<RO>;
  register(data: RegistrationData<RO>): void;
  unregister(id: string): void;
  clear(): void;
}
```

`initialize(capabilities, ...)` is called once after the server's init response arrives. The feature internally decides whether to activate by inspecting the specific capability key it cares about. Static registration (`implementationProvider: true` in init response) and dynamic registration (`client/registerCapability` for `textDocument/implementation`) both funnel through `feature.register(data)`.

**Dynamic registration**: The client routes `client/registerCapability` through a `Map<method, DynamicFeature>`. Each feature's `register(data)` stores the registration; `unregister(id)` removes it by id. The full `registerOptions` (including `documentSelector`) is preserved per registration.

**Is param schema ever introspected at runtime?** No. Each feature's call site constructs params using the TypeScript LSP types from `vscode-languageserver-protocol`. The schema is baked into client code.

### 2.2 Helix (Rust)

**Repo**: `helix-editor/helix`, `helix-lsp/src/client.rs`

**ServerCapabilities storage**: `OnceCell`, populated once from the init response:

```rust
pub(crate) capabilities: OnceCell<lsp::ServerCapabilities>,

pub fn capabilities(&self) -> &lsp::ServerCapabilities {
    self.capabilities
        .get()
        .expect("language server not yet initialized!")
}
```

**Capability check pattern**: A single `supports_feature(feature: LanguageServerFeature) -> bool` method with a match arm per feature:

```rust
pub fn supports_feature(&self, feature: LanguageServerFeature) -> bool {
    let capabilities = self.capabilities();
    use lsp::*;
    match feature {
        LanguageServerFeature::Format => matches!(
            capabilities.document_formatting_provider,
            Some(OneOf::Left(true) | OneOf::Right(_))
        ),
        LanguageServerFeature::GotoDefinition => matches!(
            capabilities.definition_provider,
            Some(OneOf::Left(true) | OneOf::Right(_))
        ),
        // ... 15+ more arms for GotoImplementation, Hover, CodeAction,
        // RenameSymbol, InlayHints, PullDiagnostics, CallHierarchy, etc.
    }
}
```

**Dynamic registration**: Explicitly opted out. The initialize params declare `dynamic_registration: Some(false)` for all capability groups. No `client/registerCapability` handler exists. This is a deliberate simplification — Helix treats capabilities as static after init.

**Is param schema ever introspected at runtime?** No. All param construction is hardcoded in Rust structs from the `lsp-types` crate.

### 2.3 Neovim built-in LSP (Lua)

**Repo**: `neovim/neovim`, `runtime/lua/vim/lsp/client.lua`

This is the most complete open implementation combining static + dynamic capability handling.

**ServerCapabilities storage**: Stored as a field on the `Client` object, resolved through `lsp.protocol.resolve_capabilities`:

```lua
rpc.request('initialize', init_params, function(init_err, result)
  self.server_capabilities =
    assert(lsp.protocol.resolve_capabilities(result.capabilities))
  self:_process_static_registrations()
end)
```

**Capability check — `supports_method`**:

```lua
function Client:supports_method(method, bufnr)
  local required_capability =
    lsp.protocol._request_name_to_server_capability[method]
  -- Static check: is the capability flag set in server_capabilities?
  if required_capability and
     vim.tbl_get(self.server_capabilities, unpack(required_capability)) then
    return true
  end
  -- Dynamic check: is there an active dynamic registration for this method?
  local provider = self:_registration_provider(method)
  local regs = self:_get_registrations(provider, bufnr)
  if lsp.protocol._method_supports_dynamic_registration[method]
     and not regs then
    return false
  end
  return required_capability == nil or is_self_mapping
end
```

The key data structure is `_request_name_to_server_capability`, a static table mapping method name strings to capability key paths (e.g., `"textDocument/implementation"` → `{"implementationProvider"}`).

**Dynamic registration**: Handled by `Client:_register(registrations)` which stores full `registerOptions` by provider, keyed by registration id, enabling unregistration:

```lua
function Client:_register(registrations)
  self:_register_dynamic(registrations)
  for _, reg in ipairs(registrations) do
    local method = reg.method
    if method == 'workspace/didChangeWatchedFiles' then
      lsp._watchfiles.register(reg, self.id)
    end
  end
end
```

**Is param schema ever introspected at runtime?** No. Param shapes for each method are hardcoded in `vim/lsp/buf.lua` and related files using the Lua LSP type library.

### 2.4 eglot (Emacs/Elisp)

**Repo**: `joaotavora/eglot`, `eglot.el`

**ServerCapabilities storage**: Stored as a slot on the `eglot-lsp-server` EIEIO class:

```elisp
(capabilities
 :initform nil
 :documentation "JSON object containing server capabilities."
 :accessor eglot--capabilities)
```

Populated after `initialize` completes: `(setf (eglot--capabilities server) capabilities)`.

**Capability check**: `eglot-server-capable` is a public function that walks the capability object with key navigation:

```elisp
(defun eglot-server-capable (&rest feats)
  "Determine if current server is capable of FEATS."
  (unless (cl-some (lambda (feat)
                     (memq feat eglot-ignored-server-capabilities))
                   feats)
    (cl-loop for caps = (eglot--capabilities (eglot--current-server-or-lose))
             ...)))
```

Feature code calls `(eglot-server-capable-or-lose :implementationProvider)` which signals an error if unsupported, allowing callers to skip gracefully. The argument is a keyword matching the LSP capability key name directly — no mapping table is needed because elisp just walks the parsed JSON as a plist.

**Dynamic registration**: eglot has partial support — it handles `client/registerCapability` for `workspace/didChangeWatchedFiles` but does not fully implement the dynamic feature lifecycle that VSCode does. Most capability checks are static-only.

**Is param schema ever introspected at runtime?** No. Param dicts are constructed inline in each eglot feature function.

---

## Patterns observed

- **Pattern A — OnceCell / field storage (Helix, Neovim, eglot)**: `ServerCapabilities` stored verbatim as a field after init. All post-init checks go through this field. Simple; breaks only if the server sends different capabilities across connections. Solidlsp has no equivalent — `init_response` is local to `_start_server` in adapters that capture it at all.

- **Pattern B — `supports_method(name) -> bool` with static dispatch table (Neovim)**: A static map `{method_name → capability_key_path}` drives the check. Static capabilities (from init) and dynamic registrations are both considered. This is the pattern most directly applicable to solidlsp facades: add `SolidLanguageServer.supports_method(method: str) -> bool` backed by stored `_server_capabilities` + `DynamicCapabilityRegistry`.

- **Pattern C — Feature plugin per method (VSCode)**: Each method is a `DynamicFeature<RO>` class instance. Capability check is implicit in whether `feature.register()` was called. Full `registerOptions` lifecycle (including unregister by id) is supported. More complex than B but also more extensible. Appropriate for a full-featured client; over-engineered for solidlsp's current surface.

- **Pattern D — Capability keyword navigation (eglot)**: No dispatch table. The caller passes the LSP capability key directly (`(eglot-server-capable :implementationProvider)`). Works because Elisp JSON is already a plist. Not applicable to Python without some analog; closest would be `server_capabilities.get("implementationProvider")`.

- **Pattern E — Static-only, opt-out dynamic (Helix)**: Explicitly disables `dynamicRegistration` in init params. Capabilities are fixed after init. Simplest possible model; works for editors with a small fixed feature set. Solidlsp's current `supports_implementation_request()` classmethod is this pattern applied to one method.

---

## Open questions for the synthesis pair

1. **Capture point**: Should `_server_capabilities` be stored in `SolidLanguageServer.__init__` via the `_initialize_with_override` wrapper (intercept the return value) or should each adapter call a `_on_initialize_complete(capabilities)` hook? The wrapper approach is a single chokepoint; the hook approach gives adapters a place to do per-server fixups (e.g., rust-analyzer's completionProvider assert).

2. **`_request_name_to_server_capability` equivalent**: Neovim has a static map `{method → capability_key_path[]}`. For solidlsp, this would need to cover at minimum: `textDocument/implementation → ["implementationProvider"]`, `textDocument/rename → ["renameProvider"]`, `textDocument/codeAction → ["codeActionProvider"]`, `textDocument/formatting → ["documentFormattingProvider"]`. Should this live in `ls.py` or in `capabilities.py`?

3. **`registerOptions` in `DynamicCapabilityRegistry`**: The current registry discards `registerOptions`. For the Pyright `textDocument/implementation` gap specifically, we only need the method name (it either registered or it didn't). But for `documentSelector`-scoped registrations the options matter. Is scope needed at MVP or can we defer?

4. **`server_id` gap**: `RuffServer` and `RustAnalyzer` have no `server_id` ClassVar, so their `client/registerCapability` events are silently dropped. These should be wired before any dynamic-discovery work is trusted as complete.

5. **Static catalog vs live query**: `build_capability_catalog` currently walks adapter classes at import time. If we store `_server_capabilities` on the live server, should the catalog be rebuilt post-init from actual server responses, or remain a static baseline with the live data used only for the `supports_method` gate?

---

## Citations

- `vendor/serena/src/solidlsp/ls.py` — base class: `_handle_register_capability` (line 658), `override_initialize_params` (line 907), `supports_implementation_request` (line 432)
- `vendor/serena/src/solidlsp/dynamic_capabilities.py` — `DynamicCapabilityRegistry` full class
- `vendor/serena/src/solidlsp/language_servers/rust_analyzer.py:780–783` — init_response local capture pattern
- `vendor/serena/src/solidlsp/language_servers/basedpyright_server.py:131–145` — init response discarded
- `vendor/serena/src/serena/refactoring/capabilities.py` — `build_capability_catalog`, `_introspect_adapter_kinds`
- `vendor/serena/src/serena/tools/scalpel_primitives.py:737–788` — `_build_language_health`
- `vendor/serena/src/serena/tools/scalpel_schemas.py:215–225` — `LanguageHealth.dynamic_capabilities`
- GitHub: `microsoft/vscode-languageserver-node`/`client/src/common/client.ts` + `features.ts` — `DynamicFeature<RO>` interface, `doRegisterCapability`, `_dynamicFeatures` Map — https://github.com/microsoft/vscode-languageserver-node
- GitHub: `helix-editor/helix`/`helix-lsp/src/client.rs` — `supports_feature`, `OnceCell<ServerCapabilities>` — https://github.com/helix-editor/helix
- GitHub: `neovim/neovim`/`runtime/lua/vim/lsp/client.lua` — `Client:supports_method`, `Client:_register`, `_request_name_to_server_capability` — https://github.com/neovim/neovim
- GitHub: `joaotavora/eglot`/`eglot.el` — `eglot-server-capable`, `eglot--capabilities` slot — https://github.com/joaotavora/eglot
