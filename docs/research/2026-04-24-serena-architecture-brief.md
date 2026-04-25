# Serena Architecture Map: Focus on Refactoring & LSP Integration

## 1. Tool Registration & Dispatch

**Location:** `/src/serena/tools/tools_base.py` (lines 463–576)

Serena uses a **singleton registry** (`ToolRegistry`) that auto-discovers tool classes at startup via reflection. Key structure:

- **Discovery:** Scans all subclasses of `Tool` in `serena.tools.*` packages with `apply()` implementations (line 479).
- **Tool markers:** Classes decorated with `ToolMarkerSymbolicEdit`, `ToolMarkerSymbolicRead`, `ToolMarkerOptional`, `ToolMarkerBeta` control behavior.
- **Registry dict:** Maps tool names (snake_case) → `RegisteredTool` dataclass (line 450). Tool names are derived from class names (e.g., `ReplaceSymbolBodyTool` → `replace_symbol_body`).
- **MCP integration:** Tools are instantiated per request via `_iter_tools()` → `make_mcp_tool()` in `/src/serena/mcp.py` (lines 249–260).

**Design note:** No explicit plugin interface; new tools just subclass `Tool` and implement `apply()`. The registry auto-discovers them.

---

## 2. LSP Client Layer (`solidlsp`)

**Core:** `/src/solidlsp/ls.py` — `SolidLanguageServer` class wraps a language server process.

### LSP Communication
- **Process launch:** `LanguageServerProcess` (in `ls_process.py`) manages subprocess lifecycle.
- **Protocol handler:** `/src/solidlsp/lsp_protocol_handler/server.py` — thin wrapper around stdlib `jsonrpc`, routes LSP requests/responses via `self.server.send.*()` and `self.server.notify.*()`.
- **File buffers:** `LSPFileBuffer` (lines 73–150 in `ls.py`) tracks open files with version numbers, content caching, and change notification hooks.

### Currently Forwarded LSP Methods
From grep of `/src/solidlsp/language_servers/rust_analyzer.py` and `common.py`:
- `textDocument/didOpen`, `didChange`, `didClose` — automatic via `LSPFileBuffer._open_in_ls()` (line 110) / `close()` (line 122).
- `textDocument/documentSymbol` — used by symbol retriever (search via `find()`).
- `textDocument/definition` — cross-file navigation.
- `textDocument/references` — find referencing symbols.
- `textDocument/rename` — `request_rename_symbol_edit()` at line 2525.
- **NOT currently exposed:** `textDocument/codeAction`, `codeAction/resolve`, `workspace/executeCommand`.

### WorkspaceEdit & Document Change Operations
**Location:** `/src/serena/code_editor.py` (lines 317–348)

`_workspace_edit_to_edit_operations()` parses LSP `WorkspaceEdit`:
- **`changes` field:** Maps URI → `TextEdit[]`, wrapped in `EditOperationFileTextEdits`.
- **`documentChanges` field:** Supports both `TextDocumentEdit` (text edits) and file operations via `kind` field:
  - `"rename"` → `EditOperationRenameFile` (line 306).
  - No support for `"create"` or `"delete"` file ops (line 332 explicitly raises if unhandled).

**Architectural gap:** Creating/deleting files requires extending `EditOperation` interface with `EditOperationCreateFile` and `EditOperationDeleteFile` subclasses.

---

## 3. Language Server Configuration

**Location:** `/src/solidlsp/ls_config.py`

- **`Language` enum** (line 29): Lists 40+ supported languages (Rust, C++, Python, Java, etc.).
- **`FilenameMatcher`** (line 15): Uses fnmatch patterns to map extensions to languages.
- **`LanguageServerConfig`** (not fully shown): Holds per-language settings (initialization options, command overrides, etc.).

**Example: Rust (rust-analyzer)**
File: `/src/solidlsp/language_servers/rust_analyzer.py`
- `RustAnalyzer` subclass of `SolidLanguageServer` (line 24).
- Custom `DependencyProvider` (line 45) detects rustup and manages binary caching.
- Minimal initialization logic; most LSP defaults applied in base class.

**Example: C++ (clangd)**
File: `/src/solidlsp/language_servers/clangd_language_server.py`
- Similar pattern: subclass with language-specific initialization (compile flags, .clangd config handling).
- **Architectural note:** No unified refactoring pipeline; each language server's capabilities are used ad-hoc.

---

## 4. Symbol-Level Edit Primitives

All primitive edit operations route through `/src/serena/code_editor.py`:

### `replace_body()` (line 97)
- Finds symbol via `_find_unique_symbol()`.
- Gets body start/end positions.
- Deletes old text, inserts new text via `EditedFile` interface.

### `insert_before_symbol()` (line 174)
- Finds symbol, inserts at the line where symbol definition begins.
- Auto-adjusts leading/trailing newlines to maintain spacing conventions.

### `insert_after_symbol()` (line 133)
- Finds symbol body end, inserts at next line.
- Checks symbol kind to ensure it's a class/function/method (line 141).

### `delete_symbol()` (line 229)
- Finds symbol body span, deletes full range.

### `rename_symbol()` (line 350, `LanguageServerCodeEditor`)
- **Multi-file capability:** Calls LSP `textDocument/rename` (line 368), which returns a `WorkspaceEdit`.
- Applies edit via `_apply_workspace_edit()` (line 376).
- **Flow:** Symbol location → Language server → WorkspaceEdit → apply to all affected files.

**Implementation detail:** All edits go through `CodeEditor.EditedFile` abstraction:
- **LSP:** Uses `LSPFileBuffer` with per-change notifications (lines 252–271).
- **JetBrains:** Uses in-memory text manipulation + refresh callback (lines 387–421).

---

## 5. Extension Surface: Adding New Features

### Where to Add Rust-Specific Refactoring

**Option A: New Symbolic Edit Tools** (recommended for isolated operations)
1. Create file: `/src/serena/tools/rust_refactoring_tools.py`.
2. Subclass `Tool` with marker `ToolMarkerSymbolicEdit`.
3. Implement `apply()` using existing primitives:
   ```python
   class ExtractMethodTool(Tool, ToolMarkerSymbolicEdit):
       def apply(self, name_path: str, relative_path: str, new_method_name: str) -> str:
           code_editor = self.create_ls_code_editor()
           # Call rename_symbol, insert_after_symbol, replace_body as needed
   ```
4. Registry auto-discovers it.

**Option B: Facade Tools Orchestrating LSP CodeActions** (for complex refactorings)
1. Extend `SolidLanguageServer` to expose `textDocument/codeAction`.
2. Create tools that:
   - Call `server.send.code_action(params)` → get list of `CodeAction` objects.
   - Filter/select relevant actions.
   - Call `workspace/executeCommand` for those with `command` field (not `edit`).
   - Apply returned `WorkspaceEdit` via existing `_apply_workspace_edit()`.

**Option C: Direct LSP Command Execution** (for language-specific commands)
1. Extend `ls.py` with:
   ```python
   def execute_command(self, command: str, args: list) -> WorkspaceEdit | None:
       return self.server.send.execute_command({"command": command, "arguments": args})
   ```
2. Tools call this and apply the edit.

### Test Strategy

**Unit tests:** `/test/serena/test_symbol_editing.py`
- Snapshot tests using `syrupy` plugin.
- Compares before/after file content diffs.
- Language-agnostic; tests run across Python, Go, Rust, etc.

**Integration tests:** `/test/solidlsp/{language}/`
- Real language server; tests symbol retrieval, references, rename.
- Example: `/test/solidlsp/rust/test_rust_*.py`.

**To test new Rust refactoring:**
1. Add Rust test code to `/test/solidlsp/rust/fixtures/`.
2. Create `/test/serena/test_rust_refactoring.py` with snapshot tests.
3. Run against real `rust-analyzer` (auto-downloaded via `DependencyProvider`).

---

## 6. Language-Agnostic vs. Language-Specific Code Paths

### Layering (from generic → specific)

1. **`Tool` base class** (tools_base.py): Fully language-agnostic.
   - `apply()` signature agnostic; uses abstracted `CodeEditor` interface.

2. **`CodeEditor` hierarchy** (code_editor.py, lines 21–242):
   - Abstract `CodeEditor` base class with language-agnostic primitives.
   - `LanguageServerCodeEditor` (line 244): LSP-specific, wraps symbol retriever.
   - `JetBrainsCodeEditor` (line 387): IDE-specific, uses plugin client.

3. **`SolidLanguageServer`** (ls.py): Language-agnostic LSP wrapper.
   - Generic LSP protocol handling, file buffer management.
   - Per-language subclass (e.g., `RustAnalyzer`) only overrides initialization.

4. **Language-specific registration** (ls_config.py):
   - `Language` enum + `FilenameMatcher` → maps files to servers.
   - No language-specific symbol parsing; all delegated to LSP server.

### Where Rust-Specific Code Would Live

- **Symbol/refactoring understanding:** None needed; `rust-analyzer` LSP handles it.
- **Rust-specific tools:** New file `/src/serena/tools/rust_tools.py` (subclass `Tool`).
- **Rust-specific initialization:** Already in `/src/solidlsp/language_servers/rust_analyzer.py`.
- **Rust test fixtures:** `/test/solidlsp/rust/fixtures/` (existing).

**Key principle:** Serena avoids embedding language knowledge. Language servers own that; Serena orchestrates them via LSP.

---

## 7. Extension Points for rust-analyzer Refactorings

### Immediate Tasks

1. **Add `textDocument/codeAction` support**
   - **File:** `/src/solidlsp/ls.py`
   - **Add method (~10 lines):**
     ```python
     def request_code_actions(self, relative_path: str, range_: ls_types.Range, 
                              only: list[str] | None = None) -> list[LSPTypes.CodeAction]:
         params = CodeActionParams(textDocument=..., range=range_, only=only)
         with self.open_file(relative_path):
             return self.server.send.code_action(params) or []
     ```

2. **Add `codeAction/resolve` support**
   - **File:** `/src/solidlsp/ls.py`
   - **Add method (~5 lines):**
     ```python
     def resolve_code_action(self, action: CodeAction) -> CodeAction:
         return self.server.send.code_action_resolve(action)
     ```
   - Use when `CodeAction` has `data` field indicating server should resolve full edit.

3. **Add `workspace/executeCommand` support**
   - **File:** `/src/solidlsp/ls.py`
   - **Add method (~8 lines):**
     ```python
     def execute_command(self, command: str, args: list | None = None) -> Any:
         params = ExecuteCommandParams(command=command, arguments=args or [])
         return self.server.send.execute_command(params)
     ```
   - Return type: varies by command; may be `WorkspaceEdit`, `TextEdit[]`, or null.

4. **Create file operation edit handlers**
   - **File:** `/src/serena/code_editor.py`, extend `_workspace_edit_to_edit_operations()` (line 317)
   - **Add classes:**
     ```python
     class EditOperationCreateFile(EditOperation):
         def apply(self): os.makedirs(...); open(...).write(...)
     
     class EditOperationDeleteFile(EditOperation):
         def apply(self): os.remove(...)
     ```
   - **Update parser** (line 325): Handle `change["kind"] == "create"` and `"delete"`.

5. **Create facade tools for common Rust refactorings**
   - **File:** `/src/serena/tools/rust_refactoring_tools.py` (new)
   - **Tool 1: `InlineVariable`**
     ```python
     class InlineVariableTool(Tool, ToolMarkerSymbolicEdit):
         def apply(self, name_path: str, relative_path: str) -> str:
             symbol = find_unique_symbol(name_path, relative_path)
             actions = lang_server.request_code_actions(relative_path, symbol.range, only=["refactor.inline"])
             if not actions: return "No inline refactoring available"
             edit = actions[0].get("edit") or resolve_code_action(actions[0])["edit"]
             self._apply_workspace_edit(edit)
             return "Inlined successfully"
     ```
   - **Tool 2: `ExtractFunction`**
     ```python
     class ExtractFunctionTool(Tool, ToolMarkerSymbolicEdit):
         def apply(self, relative_path: str, start_line: int, end_line: int, fn_name: str) -> str:
             range_ = lines_to_range(start_line, end_line)
             actions = request_code_actions(..., only=["refactor.extract"])
             # Filter for function/method extraction
             # Execute selected action via executeCommand if needed
     ```

6. **Update tests**
   - **File:** `/test/serena/test_symbol_editing.py`
   - Add Rust-specific test cases using snapshot tests.
   - **File:** `/test/solidlsp/rust/test_rust_refactoring.py` (new)
   - Integration tests for each refactoring tool against real rust-analyzer.

### Architectural Debt & Surprises Found

1. **No file creation/deletion in WorkspaceEdit handler:** Currently raises ValueError (line 332). Quick fix needed.
2. **CodeActions not exposed:** rust-analyzer has mature codeAction support; Serena ignores it.
3. **No codeAction filtering:** Would be useful to expose only refactoring/fix actions in tools (via `only` parameter).
4. **Rename uses hardcoded multi-file application:** Works well, but other refactorings (e.g., move symbol) need custom handling.
5. **No async/await in tools:** All tool `apply()` methods are synchronous; LSP requests block. Fine for most cases, but large refactorings might be slow.

---

## Summary: Extension Path for Rust-analyzer Refactorings

1. **Add LSP primitives** to `SolidLanguageServer` (code_action, codeAction/resolve, executeCommand).
2. **Extend WorkspaceEdit parser** to handle file creation/deletion.
3. **Create tools** in new `rust_refactoring_tools.py` that:
   - Call `request_code_actions()` filtered by kind.
   - Optionally resolve code actions.
   - Execute commands or apply edits via existing `_apply_workspace_edit()`.
4. **Test** via snapshot tests + integration tests.

**Effort estimate:** 150–200 lines of code across ls.py, code_editor.py, and new tools file. No major architectural changes needed.
