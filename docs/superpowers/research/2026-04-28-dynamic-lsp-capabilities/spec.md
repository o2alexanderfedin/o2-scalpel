# LSP Spec — Dynamic Capability + Parameter Discovery

**Researcher**: Agent A (LSP spec)
**Date**: 2026-04-28
**Spec version reviewed**: LSP 3.17
**metaModel source**: `https://raw.githubusercontent.com/microsoft/language-server-protocol/gh-pages/_specifications/lsp/3.17/metaModel/metaModel.json` (version `3.17.0`)

---

## TL;DR (3 bullets)

- `ServerCapabilities` in the `initialize` response is the primary discovery surface: every textDocument/* method we care about has a dedicated optional provider field (boolean or richer options object); absent = not supported, same as `false`.
- Dynamic registration (`client/registerCapability`) lets a server opt in to a method *after* initialization using a `Registration { id, method, registerOptions }` triple — the `method` field IS the LSP method name, so the id→method mapping is always explicit; ~37 methods support this.
- The spec has **no mechanism** for a server to self-describe parameter schemas at runtime; canonical param schemas live only in `metaModel.json` (build-time artifact); `executeCommand` is the closest analogue — it advertises command *names* only, never param shapes.

---

## 1. ServerCapabilities (initialize response)

**Spec ref**: [§Initialize](https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#initialize)

Every provider field is optional. Absence and `false` are normatively equivalent:

> "A missing property should be interpreted as an absence of the capability. If a missing property normally defines sub properties, all missing sub properties should be interpreted as an absence of the corresponding capability."

Key fields from `ServerCapabilities` (extracted from `metaModel.json`):

| Field | Type |
|---|---|
| `completionProvider` | `CompletionOptions` (object only — always structured) |
| `hoverProvider` | `boolean \| HoverOptions` |
| `definitionProvider` | `boolean \| DefinitionOptions` |
| `implementationProvider` | `boolean \| ImplementationOptions \| ImplementationRegistrationOptions` |
| `referencesProvider` | `boolean \| ReferenceOptions` |
| `documentSymbolProvider` | `boolean \| DocumentSymbolOptions` |
| `codeActionProvider` | `boolean \| CodeActionOptions` |
| `renameProvider` | `boolean \| RenameOptions` |
| `foldingRangeProvider` | `boolean \| FoldingRangeOptions \| FoldingRangeRegistrationOptions` |
| `documentLinkProvider` | `DocumentLinkOptions` |
| `workspaceSymbolProvider` | `boolean \| WorkspaceSymbolOptions` |
| `executeCommandProvider` | `ExecuteCommandOptions` |

The three-way union (`boolean | XOptions | XRegistrationOptions`) signals that the server may also use dynamic registration for that method. The `RegistrationOptions` variant includes a `documentSelector` filter and an optional static `id`, letting the server scope support to specific file types.

**Practical detection algorithm**: read `ServerCapabilities.<method>Provider` after `initialize`. If the field is truthy (any non-null, non-false value), the method is supported. If missing or `false`, do not call it.

---

## 2. Dynamic capability registration

**Spec ref**: [§client/registerCapability](https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#client_registerCapability)

The server sends `client/registerCapability` (a server-to-client *request*) carrying:

```typescript
interface RegistrationParams {
  registrations: Registration[];
}
interface Registration {
  id: string;            // opaque unique identifier chosen by server
  method: string;        // the LSP method being registered, e.g. "textDocument/implementation"
  registerOptions?: LSPAny; // method-specific options (DocumentSelector, etc.)
}
```

The `method` field is the full LSP method string — no secondary lookup needed. The `id` is only used later for `client/unregisterCapability` (`Unregistration { id, method }`).

**Prerequisite**: the client must have advertised `dynamicRegistration: true` in the matching `ClientCapabilities` sub-field (e.g. `textDocument.implementation.dynamicRegistration`). Without that flag, the spec says the server should not send dynamic registrations for that feature.

From `ImplementationClientCapabilities`:

> "Whether implementation supports dynamic registration. If this is set to `true` the client supports the new `ImplementationRegistrationOptions` return value for the corresponding server capability as well."

**~37 methods** support dynamic registration per metaModel, including all the core navigation methods: `textDocument/{definition,implementation,references,codeAction,rename,hover,completion,documentSymbol,foldingRange,documentLink}` and `workspace/symbol`.

**When do servers use it?** Typically when support depends on runtime conditions (project type detected after initialization, extension loaded lazily, or document-selector scoping). Basedpyright uses it for certain features to scope registration to Python files.

---

## 3. Parameter shapes

**No runtime self-description exists.** The spec provides no request or message for a server to describe the parameter schema of a method.

The closest analogue is `executeCommandProvider`:

```typescript
interface ExecuteCommandOptions {
  commands: string[];   // command names only — zero param schema info
}
```

The server advertises which command strings it handles; a client must know the param shapes out-of-band (documentation or code).

**Canonical source**: `metaModel.json` — the machine-readable schema for all LSP 3.17 structures and requests. It defines every request's `params` type, `result` type, and `registrationOptions` type. Example for `workspace/symbol`:

```json
{
  "method": "workspace/symbol",
  "params": { "kind": "reference", "name": "WorkspaceSymbolParams" },
  "registrationOptions": { "kind": "reference", "name": "WorkspaceSymbolRegistrationOptions" }
}
```

Where `WorkspaceSymbolParams` has a single required property `query: string` (plus mixin fields `workDoneToken` and `partialResultToken`).

**metaModel.json is a build-time artifact.** It is versioned with the spec and published at a stable URL. There is no LSP message for fetching it at runtime. A client that wants to validate params against it must bundle or fetch the JSON out-of-band.

---

## 4. Method support detection at runtime

**If you call an unsupported method**, the server returns a JSON-RPC error response. The relevant error codes:

```typescript
export namespace ErrorCodes {
  export const MethodNotFound: integer = -32601;  // method does not exist
  export const InvalidRequest: integer = -32600;
  export const InvalidParams: integer = -32602;
}
```

Servers that follow the spec return `-32601 MethodNotFound` for methods they do not implement.

**"Send and catch" as a discovery pattern**: technically works, but has significant failure modes:

1. **Side-effectful methods**: `textDocument/rename` or `workspace/applyEdit` are not safe to probe — they modify state. Only read-only requests (hover, definition, references) are safe to probe.
2. **Server divergence**: some servers (e.g. older pylsp builds) return `-32600 InvalidRequest` or a null result rather than `-32601` for unsupported methods. The error code is not reliably normalized.
3. **Latency cost**: each probe requires a round-trip.
4. **Race with dynamic registration**: a method might be `MethodNotFound` immediately after init but then become available once the server sends `client/registerCapability` a few hundred milliseconds later.

**Conclusion**: prefer `ServerCapabilities` inspection; use error-catching only as a last-resort fallback for legacy servers that mis-populate their capabilities, and only for idempotent read operations.

---

## 5. Notable quirks

**`codeActionProvider` dual type**: when `true`, the server handles code actions but advertises no detail. When `CodeActionOptions`, it may carry:
- `codeActionKinds?: CodeActionKind[]` — the subset of code action kinds the server produces
- `resolveProvider?: boolean` — whether `codeAction/resolve` is supported

A client that needs to filter by kind (e.g. only `source.fixAll`) must check the options object; a bare `true` means "unknown kinds."

**`renameProvider` dual type**: `RenameOptions` carries `prepareProvider?: boolean`. If `true`, the server supports `textDocument/prepareRename` — clients should use it to validate the rename target before committing. Calling `textDocument/prepareRename` against a server where `renameProvider` is `true` (not an options object, or options without `prepareProvider`) is undefined behavior.

**`implementationProvider` and the Pyright gap**: Pyright omits `implementationProvider` from its `ServerCapabilities` (the field is absent, not `false`). Per spec, absent = not supported. The correct behavior for o2-scalpel is to detect absence and fall back to `definitionProvider` — which Pyright does advertise. This is precisely what the static reference captures; dynamic checking confirms it without changing the conclusion.

**`workspaceSymbol` harness mismatch**: `WorkspaceSymbolParams.query` is a required `string` field. The o2-scalpel harness limitation that passes only `line/character` is a wrapper bug, not a spec ambiguity. The spec is unambiguous: `query` is the sole domain-specific parameter.

**`completionProvider`**: the only core provider that is always an options object (`CompletionOptions`), never a bare boolean. Its presence is the capability signal.

---

## Open questions for the synthesis pair

- Does the DynamicCapabilityRegistry in `vendor/serena` already persist the `method` string from `Registration`, making it possible to answer "is X registered?" at query time? If not, it is a one-field addition.
- For basedpyright's dynamic registrations: do they re-register the same methods as the static `ServerCapabilities` fields, or do they add *new* methods not present in static caps? The answer determines whether dynamic tracking is additive or corrective.
- Is there value in bundling `metaModel.json` as a vendored artifact so param schemas can be validated at integration-test time without a network fetch?
- For the "send and catch" fallback: is pylsp's error code behavior documented anywhere (GitHub issues), or is it empirically known from existing test runs?

---

## Citations

- LSP 3.17 spec — §Initialize / ServerCapabilities — https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#initialize
- LSP 3.17 spec — §client/registerCapability — https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#client_registerCapability
- LSP 3.17 spec — §Response Message / ErrorCodes — https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#responseMessage
- LSP 3.17 metaModel.json (machine-readable schema, version 3.17.0) — https://raw.githubusercontent.com/microsoft/language-server-protocol/gh-pages/_specifications/lsp/3.17/metaModel/metaModel.json
- LSP repo metaModel browser path — https://github.com/microsoft/language-server-protocol/blob/gh-pages/_specifications/lsp/3.17/metaModel/metaModel.json
