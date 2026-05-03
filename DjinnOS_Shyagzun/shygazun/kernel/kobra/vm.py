"""
shygazun/kernel/kobra/vm.py
============================
Kobra abstract machine — operational semantics for Aster and Grapevine.

This is the execution substrate the native evaluator runs on.  When
Kobra evaluates Kobra, it is this machine doing the work.  The Python
implementation is the scaffold; when the machine can run itself, the
scaffold removes itself.

Execution model
---------------
Token sequences execute left-to-right.  Each token is either:
  - A Mavo-name     → look up its definition in the namespace and execute
  - A terminal sym  → invoke its bound operation
  - A data value    → push to the value stack

Kyra (pipe)
  A Kyra B — the result of A is passed as the primary input to B.
  Kyra does not execute; it marks a continuation boundary.

KaelShi / KaelKe
  Operations produce either a KaelShi (success/coherent) or KaelKe
  (error/incoherent) result.  These are the only two result types at
  the operational level.

Kysha (consensus gate)
  Collects all results produced since the last gate reset.
  Proceeds (KaelShi) only if every result is KaelShi.
  Branches to KaelKe path otherwise.

Aster operations (bytes 128–155)
---------------------------------
  Si  — linear time    (iterator advance)
  Su  — loop time      (accumulator step)
  Os  — exponential time (branch multiply)
  Se  — logarithmic time (branch reduce)
  Sy  — fold time      (collapse branches)
  As  — frozen time    (checkpoint)
  Ep  — assign space   (bind name → value)
  Gwev— save space     (write to Sao/persistent)
  Ifa — parse space    (extract value from input by pattern)
  Ier — loop space     (iterate body over collection)
  San — push space     (accumulate onto stack-top list)
  Enno— delete space   (remove binding)
  Yl  — run space      (execute a deferred body)
  Hoz — unbind space   (unbind without deleting)

Grapevine operations (bytes 156–183)
--------------------------------------
  Sao  — persistent object  (create/access Sao store)
  Syr  — volatile buffer    (create/access Syr buffer)
  Seth — directory/bundle   (create/access Seth bundle)
  Mek  — call/emit          (call a named operation)
  Mekha— herald/gateway     (dispatch by type)
  Kyra — control token      (pipe continuation boundary)
  Kysha— consensus choir    (consensus gate)
  Kyl  — steward            (coordinate between operations)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


# ── Result types ──────────────────────────────────────────────────────────────

@dataclass
class KaelShi:
    """Coherent result — operation succeeded."""
    value: Any = None

    def __bool__(self) -> bool:
        return True


@dataclass
class KaelKe:
    """Incoherent result — operation failed or produced an error."""
    reason: str = ""
    value:  Any = None

    def __bool__(self) -> bool:
        return False


Result = KaelShi | KaelKe


# ── VM state ──────────────────────────────────────────────────────────────────

@dataclass
class VMFrame:
    """A single execution frame — one Lo-section or one function call."""
    env:       Dict[str, Any] = field(default_factory=dict)
    stack:     List[Any]      = field(default_factory=list)
    results:   List[Result]   = field(default_factory=list)  # Kysha accumulator
    sao:       Dict[str, Any] = field(default_factory=dict)  # persistent store

    def push(self, value: Any) -> None:
        self.stack.append(value)

    def pop(self) -> Any:
        return self.stack.pop() if self.stack else None

    def peek(self) -> Any:
        return self.stack[-1] if self.stack else None

    def top_list(self) -> List:
        """Return the top of stack as a list, creating one if needed."""
        if not self.stack or not isinstance(self.stack[-1], list):
            self.stack.append([])
        return self.stack[-1]

    def record(self, result: Result) -> None:
        self.results.append(result)

    def reset_gate(self) -> None:
        self.results.clear()


class KobraVM:
    """
    Kobra abstract machine.

    Executes token sequences produced by KobraEvaluator definitions.
    Each token is either a Mavo-name (looked up and executed recursively),
    a terminal operational symbol (dispatched to its bound operation),
    or a data value (pushed to the stack).

    Parameters
    ----------
    namespace : the Mavo namespace bootstrapped from Self-spec.ko
    """

    def __init__(self, namespace: Dict[str, Any]) -> None:
        self._ns = dict(namespace)
        # Wire bootstrap primitives: Mavo-prefixed callables must live in _ns
        # so _eval_token's Mavo-prefix check finds them.
        for name, fn in _OPS.items():
            if name.startswith("Mavo") and name not in self._ns:
                self._ns[name] = fn
        self._stack: List[VMFrame] = [VMFrame()]

    # ── Frame management ──────────────────────────────────────────────────

    @property
    def frame(self) -> VMFrame:
        return self._stack[-1]

    def push_frame(self) -> None:
        child = VMFrame(
            env = dict(self.frame.env),
            sao = self.frame.sao,
        )
        self._stack.append(child)

    def pop_frame(self) -> VMFrame:
        if len(self._stack) > 1:
            return self._stack.pop()
        return self._stack[0]

    # ── Execution ─────────────────────────────────────────────────────────

    def exec(self, tokens: List[str], input: Any = None) -> Result:
        """
        Execute a token sequence.

        Kyra tokens mark continuation boundaries: the result of everything
        before a Kyra is the input to everything after it.
        """
        if not tokens:
            return KaelShi(value=input)

        # Split on Kyra to build a pipeline
        segments = _split_kyra(tokens)

        value = input
        for segment in segments:
            result = self._exec_segment(segment, value)
            if isinstance(result, KaelKe):
                self.frame.record(result)
                return result
            value = result.value
            self.frame.record(result)

        return KaelShi(value=value)

    # Tokens that consume the NEXT token as a function reference rather than
    # evaluating it eagerly.  Ier is the primary example: [Ier MavoFn ...]
    # means "iterate over input applying MavoFn" — MavoFn is a reference, not
    # a call.
    _LOOKAHEAD_OPS: frozenset = frozenset({"Ier", "MavoStash", "MavoUnstash"})

    def _exec_segment(self, tokens: List[str], input: Any) -> Result:
        """Execute one Kyra-delimited segment."""
        value = input
        i = 0
        while i < len(tokens):
            tok = tokens[i]
            try:
                if tok in self._LOOKAHEAD_OPS and i + 1 < len(tokens):
                    # Consume the next token as a body reference without evaluating it
                    body_ref = tokens[i + 1]
                    i += 2
                    result = self._exec_with_ref(tok, body_ref, value)
                else:
                    result = self._eval_token(tok, value)
                    i += 1
                if isinstance(result, KaelKe):
                    return result
                value = result.value
            except Exception as exc:
                return KaelKe(reason=str(exc), value=tok)
        return KaelShi(value=value)

    def _exec_with_ref(self, op: str, ref: str, input: Any) -> Result:
        """Execute an operation that takes the next token as a function reference."""
        if op == "Ier":
            return self._ier_ref(ref, input)
        if op == "MavoStash":
            # Store current pipeline value in sao under the slot name
            self.frame.sao[ref] = input
            return KaelShi(value=input)
        if op == "MavoUnstash":
            # Retrieve value from sao slot
            val = self.frame.sao.get(ref)
            if val is None:
                return KaelKe(reason=f"MavoUnstash: slot '{ref}' is empty")
            return KaelShi(value=val)
        return KaelKe(reason=f"unknown lookahead op: {op}")

    def _ier_ref(self, ref: str, input: Any) -> Result:
        """Ier — filter-map: iterate input, apply ref to each item.
        KaelShi results are collected; KaelKe results are silently skipped."""
        if isinstance(input, str):
            iterable: Any = list(input)
        elif isinstance(input, (list, tuple)):
            iterable = input
        else:
            return KaelKe(reason=f"Ier: input is not iterable: {type(input)}")
        results = []
        for item in iterable:
            defn = self._ns.get(ref)
            if defn is None:
                op_fn = _OPS.get(ref)
                r = op_fn(self, item) if op_fn else KaelShi(value=item)
            elif isinstance(defn, list):
                self.push_frame()
                r = self.exec(defn, item)
                self.pop_frame()
            elif callable(defn):
                r = defn(self, item)
            else:
                r = KaelShi(value=defn)
            if isinstance(r, KaelShi):
                results.append(r.value)
            # KaelKe: silently skip — filter-map semantics
        return KaelShi(value=results)

    def _eval_token(self, tok: str, input: Any) -> Result:
        """Evaluate a single token."""
        # Mavo-name: look up definition and execute recursively
        if tok.startswith("Mavo"):
            defn = self._ns.get(tok)
            if defn is None:
                return KaelShi(value=tok)  # unresolved Mavo = opaque data
            if isinstance(defn, list):
                self.push_frame()
                # Input flows via exec's input parameter — do NOT push to stack.
                # Pushing would contaminate San's list accumulation.
                result = self.exec(defn, input)
                self.pop_frame()
                return result
            if callable(defn):
                return defn(self, input)
            return KaelShi(value=defn)

        # Terminal operational symbol
        op = _OPS.get(tok)
        if op is not None:
            return op(self, input)

        # Data: push to stack and return
        self.frame.push(tok)
        return KaelShi(value=tok)

    # ── Namespace ─────────────────────────────────────────────────────────

    def define(self, name: str, value: Any) -> None:
        self._ns[name]       = value
        self.frame.env[name] = value

    def lookup(self, name: str) -> Any:
        return self.frame.env.get(name) or self._ns.get(name)


# ── Kyra splitting ────────────────────────────────────────────────────────────

def _split_kyra(tokens: List[str]) -> List[List[str]]:
    """Split a token list into Kyra-delimited segments."""
    segments: List[List[str]] = []
    current:  List[str]       = []
    for tok in tokens:
        if tok == "Kyra":
            if current:
                segments.append(current)
            current = []
        else:
            current.append(tok)
    if current:
        segments.append(current)
    return segments if segments else [[]]


# ── Aster operations ──────────────────────────────────────────────────────────

def _op_ep(vm: KobraVM, input: Any) -> Result:
    """Ep — assign space: bind name → value.  Stack: [..., name, value] → [...]"""
    value = vm.frame.pop()
    name  = vm.frame.pop()
    if name is None:
        return KaelKe(reason="Ep: no name on stack")
    vm.define(str(name), value if value is not None else input)
    return KaelShi(value=value)


def _op_gwev(vm: KobraVM, input: Any) -> Result:
    """Gwev — save space: write input to Sao store under the top stack key."""
    key = vm.frame.pop()
    if key is None:
        return KaelKe(reason="Gwev: no key on stack")
    vm.frame.sao[str(key)] = input
    return KaelShi(value=input)


def _op_ifa(vm: KobraVM, input: Any) -> Result:
    """Ifa — parse space: parse input by pattern on stack.  Returns parsed value."""
    pattern = vm.frame.pop()
    if input is None:
        return KaelKe(reason="Ifa: no input")
    if isinstance(input, str):
        if pattern == "split":
            return KaelShi(value=input.split())
        if pattern == "lines":
            return KaelShi(value=input.splitlines())
        # Default: split by whitespace
        return KaelShi(value=input.split())
    if isinstance(input, list):
        return KaelShi(value=input)
    return KaelShi(value=str(input))


def _op_ier(vm: KobraVM, input: Any) -> Result:
    """Ier — loop space: iterate body (stack top) over collection (input)."""
    body = vm.frame.pop()
    if not isinstance(input, (list, tuple)):
        return KaelKe(reason="Ier: input is not iterable")
    results = []
    for item in input:
        if isinstance(body, list):
            vm.push_frame()
            vm.frame.push(item)
            r = vm.exec(body, item)
            vm.pop_frame()
        else:
            r = KaelShi(value=item)
        if isinstance(r, KaelKe):
            return r
        results.append(r.value)
    return KaelShi(value=results)


def _op_san(vm: KobraVM, input: Any) -> Result:
    """San — push space: append input to the top-of-stack list."""
    acc = vm.frame.top_list()
    acc.append(input)
    return KaelShi(value=acc)


def _op_enno(vm: KobraVM, input: Any) -> Result:
    """Enno — delete space: remove the top-of-stack name from the environment."""
    key = vm.frame.pop()
    if key:
        vm.frame.env.pop(str(key), None)
        vm._ns.pop(str(key), None)
    return KaelShi(value=None)


def _op_yl(vm: KobraVM, input: Any) -> Result:
    """Yl — run space: execute input as a token list."""
    body = input
    if isinstance(body, list):
        return vm.exec(body)
    return KaelShi(value=body)


def _op_hoz(vm: KobraVM, input: Any) -> Result:
    """Hoz — unbind space: unbind without deleting (shadow in local frame only)."""
    key = vm.frame.pop()
    if key:
        vm.frame.env[str(key)] = None
    return KaelShi(value=None)


def _op_si(vm: KobraVM, input: Any) -> Result:
    """Si — linear time: advance iterator one step."""
    if isinstance(input, list) and input:
        return KaelShi(value=input[0])
    return KaelShi(value=input)


def _op_su(vm: KobraVM, input: Any) -> Result:
    """Su — loop time: accumulate into the current loop state."""
    vm.frame.push(input)
    return KaelShi(value=input)


def _op_sy(vm: KobraVM, input: Any) -> Result:
    """Sy — fold time: collapse the stack into a single value."""
    items = list(vm.frame.stack)
    vm.frame.stack.clear()
    return KaelShi(value=items)


def _op_as(vm: KobraVM, input: Any) -> Result:
    """As — frozen time: checkpoint — record the current input unchanged."""
    vm.frame.record(KaelShi(value=input))
    return KaelShi(value=input)


def _op_os(vm: KobraVM, input: Any) -> Result:
    """Os — exponential time: branch multiply (push copies for each branch)."""
    n = vm.frame.pop()
    try:
        count = int(str(n))
    except (TypeError, ValueError):
        count = 2
    for _ in range(count):
        vm.frame.push(input)
    return KaelShi(value=input)


def _op_se(vm: KobraVM, input: Any) -> Result:
    """Se — logarithmic time: branch reduce (pop and merge N items from stack)."""
    n = vm.frame.pop()
    try:
        count = int(str(n))
    except (TypeError, ValueError):
        count = 2
    items = [vm.frame.pop() for _ in range(min(count, len(vm.frame.stack)))]
    return KaelShi(value=list(reversed(items)))


# ── Grapevine operations ──────────────────────────────────────────────────────

def _op_sao(vm: KobraVM, input: Any) -> Result:
    """Sao — persistent object: create or access a named Sao store."""
    key = vm.frame.pop()
    if key is None:
        return KaelShi(value=vm.frame.sao)
    k = str(key)
    if k not in vm.frame.sao:
        vm.frame.sao[k] = {}
    return KaelShi(value=vm.frame.sao[k])


def _op_syr(vm: KobraVM, input: Any) -> Result:
    """Syr — volatile buffer: create a mutable buffer holding input."""
    return KaelShi(value={"_syr": True, "value": input})


def _op_seth(vm: KobraVM, input: Any) -> Result:
    """Seth — directory/bundle: create or access a structured bundle."""
    key = vm.frame.pop()
    if key is None:
        return KaelShi(value=vm.frame.sao)
    k = str(key)
    if k not in vm.frame.sao:
        vm.frame.sao[k] = {}
    return KaelShi(value=vm.frame.sao[k])


def _op_mek(vm: KobraVM, input: Any) -> Result:
    """Mek — call/emit: call the named operation from the namespace."""
    name = vm.frame.pop()
    if name is None:
        return KaelKe(reason="Mek: no name")
    return vm._eval_token(str(name), input)


def _op_mekha(vm: KobraVM, input: Any) -> Result:
    """Mekha — herald/gateway: dispatch input to the right handler by type."""
    # Mekha reads the type of input and routes to the matching Mavo handler
    # In the minimal VM, type is determined by Python isinstance
    if isinstance(input, dict):
        handler = vm.lookup("MavoMekhaDict")
    elif isinstance(input, list):
        handler = vm.lookup("MavoMekhaList")
    elif isinstance(input, str):
        handler = vm.lookup("MavoMekhaStr")
    else:
        handler = None
    if handler and isinstance(handler, list):
        return vm.exec(handler, input)
    return KaelShi(value=input)


def _op_kysha(vm: KobraVM, input: Any) -> Result:
    """Kysha — consensus choir: gate that passes only if all recorded results are KaelShi."""
    results = list(vm.frame.results)
    vm.frame.reset_gate()
    if all(isinstance(r, KaelShi) for r in results):
        return KaelShi(value=input)
    failures = [r for r in results if isinstance(r, KaelKe)]
    reason = "; ".join(f.reason for f in failures) or "consensus failed"
    return KaelKe(reason=reason, value=input)


def _op_kyl(vm: KobraVM, input: Any) -> Result:
    """Kyl — steward: coordinate — pass input through without change, record as KaelShi."""
    vm.frame.record(KaelShi(value=input))
    return KaelShi(value=input)


def _op_ha(vm: KobraVM, input: Any) -> Result:
    """Ha — absolute positive: the True/Yes value."""
    vm.frame.record(KaelShi(value=True))
    return KaelShi(value=True)


def _op_ga(vm: KobraVM, input: Any) -> Result:
    """Ga — absolute negative: the False/No value."""
    vm.frame.record(KaelKe(reason="Ga", value=False))
    return KaelKe(reason="Ga", value=False)


def _op_na(vm: KobraVM, input: Any) -> Result:
    """Na — neutral/integration: merge top two stack values."""
    b = vm.frame.pop()
    a = vm.frame.pop()
    if isinstance(a, list) and isinstance(b, list):
        merged = a + b
    elif isinstance(a, dict) and isinstance(b, dict):
        merged = {**a, **b}
    else:
        merged = [v for v in (a, b) if v is not None]
    vm.frame.push(merged)
    return KaelShi(value=merged)


def _op_kael_shi(vm: KobraVM, input: Any) -> Result:
    """KaelShi — success cluster: collect results from the frame into a success bundle."""
    items = [r.value for r in vm.frame.results if isinstance(r, KaelShi)]
    vm.frame.reset_gate()
    return KaelShi(value=items)


def _op_kael_ke(vm: KobraVM, input: Any) -> Result:
    """KaelKe — error cluster: collect errors from the frame into an error bundle."""
    items = [(r.reason, r.value) for r in vm.frame.results if isinstance(r, KaelKe)]
    vm.frame.reset_gate()
    return KaelKe(reason="cluster", value=items)


# ── Bootstrap primitives (operations not yet expressible in Kobra) ────────────
# These live here until the native evaluator can express them in Kobra.

def _op_split_specs(vm: KobraVM, input: Any) -> Result:
    """MavoSplitSpecs — split a Lo-section body string into bracket-delimited spec strings."""
    if not isinstance(input, str):
        return KaelKe(reason="MavoSplitSpecs: input is not a string")
    specs: List[str] = []
    pos = 0
    while pos < len(input):
        while pos < len(input) and input[pos] in " \t\r\n":
            pos += 1
        if pos >= len(input):
            break
        if input[pos] != "[":
            pos += 1
            continue
        depth, end = 0, pos
        while end < len(input):
            if input[end] == "[":
                depth += 1
            elif input[end] == "]":
                depth -= 1
                if depth == 0:
                    break
            end += 1
        specs.append(input[pos + 1 : end].strip())
        pos = end + 1
    return KaelShi(value=specs)


def _op_find_mavo_key(vm: KobraVM, input: Any) -> Result:
    """MavoFindMavoKey — given a token list, return (key, defn_tokens) or KaelKe."""
    tokens = input if isinstance(input, list) else (input.split() if isinstance(input, str) else [])
    for i, tok in enumerate(tokens):
        if tok.startswith("Mavo"):
            key  = tok
            defn = [t for j, t in enumerate(tokens) if j != i]
            return KaelShi(value=(key, defn))
    return KaelKe(reason="MavoFindMavoKey: no Mavo-prefixed token found")


def _op_check_ta_shy_ma(vm: KobraVM, input: Any) -> Result:
    """MavoCheckTaShyMa — return the TaShyMa address if the spec is [TaShyMa(n)], else KaelKe."""
    text = input.strip() if isinstance(input, str) else ""
    if text.startswith("TaShyMa"):
        paren = text.find("(")
        if paren != -1:
            close = text.find(")", paren)
            if close != -1:
                return KaelShi(value=text[paren + 1 : close].strip())
    return KaelKe(reason="not TaShyMa", value=input)


def _op_filter_ta_shy_ma(vm: KobraVM, input: Any) -> Result:
    """MavoFilterTaShyMa — return KaelKe if the spec is TaShyMa (filter it out)."""
    text = input.strip() if isinstance(input, str) else ""
    if text.startswith("TaShyMa"):
        return KaelKe(reason="TaShyMa filtered", value=input)
    return KaelShi(value=input.split() if isinstance(input, str) else input)


def _op_spec_tokens(vm: KobraVM, input: Any) -> Result:
    """MavoSpecTokens — split a spec string into whitespace-delimited tokens."""
    if isinstance(input, str):
        return KaelShi(value=input.split())
    if isinstance(input, list):
        return KaelShi(value=input)
    return KaelKe(reason="MavoSpecTokens: unrecognised input type")


def _op_str_starts_mavo(vm: KobraVM, input: Any) -> Result:
    """MavoStrStartsMavo — KaelShi(input) if string starts with 'Mavo', else KaelKe."""
    if isinstance(input, str) and input.startswith("Mavo"):
        return KaelShi(value=input)
    return KaelKe(reason="not Mavo", value=input)


def _op_str_not_starts_mavo(vm: KobraVM, input: Any) -> Result:
    """MavoStrNotStartsMavo — KaelShi(input) if NOT starts with 'Mavo', else KaelKe."""
    if isinstance(input, str) and not input.startswith("Mavo"):
        return KaelShi(value=input)
    return KaelKe(reason="starts with Mavo", value=input)


def _op_str_not_starts_ta_shy_ma(vm: KobraVM, input: Any) -> Result:
    """MavoStrNotStartsTaShyMa — KaelShi(input) if NOT starts with 'TaShyMa', else KaelKe."""
    if isinstance(input, str) and not input.startswith("TaShyMa"):
        return KaelShi(value=input)
    return KaelKe(reason="starts with TaShyMa", value=input)


def _op_str_starts_ta_shy_ma(vm: KobraVM, input: Any) -> Result:
    """MavoStrStartsTaShyMa — KaelShi(input) if string starts with 'TaShyMa', else KaelKe."""
    if isinstance(input, str) and input.startswith("TaShyMa"):
        return KaelShi(value=input)
    return KaelKe(reason="not TaShyMa", value=input)


def _op_str_extract_paren(vm: KobraVM, input: Any) -> Result:
    """MavoStrExtractParen — extract content between the first '(' and matching ')'."""
    if not isinstance(input, str):
        return KaelKe(reason="MavoStrExtractParen: not a string")
    start = input.find("(")
    if start == -1:
        return KaelKe(reason="MavoStrExtractParen: no '(' found")
    depth, end = 0, start
    for i in range(start, len(input)):
        if input[i] == "(":
            depth += 1
        elif input[i] == ")":
            depth -= 1
            if depth == 0:
                end = i
                break
    return KaelShi(value=input[start + 1 : end].strip())


def _op_str_to_tokens(vm: KobraVM, input: Any) -> Result:
    """MavoStrToTokens — split a string on whitespace into a list of tokens."""
    if isinstance(input, str):
        tokens = input.split()
        return KaelShi(value=tokens) if tokens else KaelKe(reason="empty")
    if isinstance(input, list):
        return KaelShi(value=input)
    return KaelKe(reason="MavoStrToTokens: unrecognised type")


def _op_list_remove_first_mavo(vm: KobraVM, input: Any) -> Result:
    """MavoListRemoveFirstMavo — return list with the first Mavo-prefixed token removed."""
    if not isinstance(input, (list, tuple)):
        return KaelKe(reason="MavoListRemoveFirstMavo: not a list")
    result: List[Any] = []
    found = False
    for item in input:
        if not found and isinstance(item, str) and item.startswith("Mavo"):
            found = True  # skip only the first match
        else:
            result.append(item)
    return KaelShi(value=result)


def _op_list_head(vm: KobraVM, input: Any) -> Result:
    """MavoListHead — first element of a list."""
    if isinstance(input, (list, tuple)) and input:
        return KaelShi(value=input[0])
    return KaelKe(reason="MavoListHead: empty or not a list")


def _op_str_split_on_open(vm: KobraVM, input: Any) -> Result:
    """MavoStrSplitOnOpen — split string on '['; return all chunks after the first '['."""
    if not isinstance(input, str):
        return KaelKe(reason="MavoStrSplitOnOpen: not a string")
    parts = input.split("[")
    return KaelShi(value=parts[1:] if len(parts) > 1 else [])


def _op_str_before_close(vm: KobraVM, input: Any) -> Result:
    """MavoStrBeforeClose — return content of string before the first ']'."""
    if not isinstance(input, str):
        return KaelKe(reason="MavoStrBeforeClose: not a string", value=input)
    idx = input.find("]")
    if idx == -1:
        return KaelKe(reason="MavoStrBeforeClose: no ']' found", value=input)
    return KaelShi(value=input[:idx].strip())


def _op_str_trim(vm: KobraVM, input: Any) -> Result:
    """MavoStrTrim — trim leading/trailing whitespace from a string."""
    if isinstance(input, str):
        return KaelShi(value=input.strip())
    return KaelShi(value=input)


def _op_filter_empty(vm: KobraVM, input: Any) -> Result:
    """MavoFilterEmpty — remove empty or whitespace-only strings from a list."""
    if not isinstance(input, list):
        return KaelKe(reason="MavoFilterEmpty: not a list")
    return KaelShi(value=[s for s in input if str(s).strip()])


def _op_is_cannabis(vm: KobraVM, input: Any) -> Result:
    """MavoIsCannabis — KaelShi if input is a Cannabis akinen, KaelKe otherwise."""
    cannabis = {
        "At","Ar","Av","Azr","Af","An",
        "Od","Ox","Om","Soa",
        "It","Ir","Iv","Izr","If","In",
        "Ed","Ex","Em","Sei",
        "Yt","Yr","Yv","Yzr","Yf","Yn",
        "Ud","Ux","Um","Suy",
    }
    if str(input) in cannabis:
        return KaelShi(value=input)
    return KaelKe(reason="not Cannabis", value=input)


# ── Operation dispatch table ──────────────────────────────────────────────────

_OPS: Dict[str, Callable[[KobraVM, Any], Result]] = {
    # Aster — time modes
    "Si":   _op_si,
    "Su":   _op_su,
    "Os":   _op_os,
    "Se":   _op_se,
    "Sy":   _op_sy,
    "As":   _op_as,
    # Aster — space operations
    "Ep":   _op_ep,
    "Gwev": _op_gwev,
    "Ifa":  _op_ifa,
    "Ier":  _op_ier,
    "San":  _op_san,
    "Enno": _op_enno,
    "Yl":   _op_yl,
    "Hoz":  _op_hoz,
    # Grapevine — data
    "Sao":  _op_sao,
    "Syr":  _op_syr,
    "Seth": _op_seth,
    "Mek":  _op_mek,
    "Mekha":_op_mekha,
    # Grapevine — control
    "Kysha":_op_kysha,
    "Kyl":  _op_kyl,
    # Grapevine — consensus tokens
    "Kyra": lambda vm, inp: KaelShi(value=inp),  # Kyra handled by _split_kyra; no-op if reached
    # Rose — polarity
    "Ha":   _op_ha,
    "Ga":   _op_ga,
    "Na":   _op_na,
    # Result collection
    "KaelShi": _op_kael_shi,
    "KaelKe":  _op_kael_ke,
    # Bootstrap primitives (until Kobra can express these itself)
    # Irreducible string / list primitives
    "MavoStrStartsMavo":        _op_str_starts_mavo,
    "MavoStrNotStartsMavo":     _op_str_not_starts_mavo,
    "MavoStrNotStartsTaShyMa":  _op_str_not_starts_ta_shy_ma,
    "MavoStrStartsTaShyMa":     _op_str_starts_ta_shy_ma,
    "MavoStrExtractParen":      _op_str_extract_paren,
    "MavoStrToTokens":          _op_str_to_tokens,
    "MavoListHead":             _op_list_head,
    "MavoListRemoveFirstMavo":  _op_list_remove_first_mavo,
    "MavoStrSplitOnOpen":       _op_str_split_on_open,
    "MavoStrBeforeClose":  _op_str_before_close,
    "MavoStrTrim":         _op_str_trim,
    "MavoFilterEmpty":     _op_filter_empty,
    "MavoIsCannabis":      _op_is_cannabis,
}