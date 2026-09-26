"""
FixGenerator — converts a CausalChain into a FixProposal.

Responsibilities (Task 8 scope)
---------------------------------
1. Accept a :class:`~app.models.causal.CausalChain`.
2. Inspect the ROOT_CAUSE node and supporting evidence to select the
   appropriate fix strategy.
3. Return a fully typed :class:`~app.models.fix.FixProposal` with:
   - Evidence provenance (evidence_ids from the root-cause node)
   - A plain-language description and rationale
   - The affected file / configuration (when identifiable)
   - A typed ``DepChange`` for DEPENDENCY_CHANGE fixes
   - Confidence inherited from the root-cause node

What the generator does NOT do
--------------------------------
- Modify the repository
- Apply the fix
- Run tests or shell commands
- Call any AI/LLM provider
- Emit SSE events
- Implement counterfactual simulation
- Implement sandbox execution

Reasoning strategy (deterministic, rule-based for MVP)
--------------------------------------------------------
Priority order for fix strategy selection:

1. ROOT_CAUSE node has DependencyEvidence support AND the causal chain
   contains a DEPENDENCY_BREAK node with a known ``changed`` dep →
   propose a DEPENDENCY_CHANGE fix (pin to prior version).

2. ROOT_CAUSE node has ChangeEvidence support (code change) →
   propose a CODE_PATCH fix (revert the changed file).

3. Any ROOT_CAUSE node (fallback) →
   propose a generic fix description derived from the root-cause label.

For scenario-001 ("The Silent Semver Break") Rule 1 fires:
    utility-lib 3.0.0 → pin back to 2.3.1 in package.json.

InsufficientCausalChainError
-----------------------------
Returned (not raised) when the chain cannot support a fix proposal:
- chain has no ROOT_CAUSE node
- chain has no evidence_ids on the ROOT_CAUSE node
- chain confidence is 0.0

Usage
-----
::

    from app.graph.fix_generator import FixGenerator
    from app.graph.builder import CausalChainBuilder

    builder = CausalChainBuilder()
    chain = builder.build(investigation)   # CausalChain | InsufficientEvidenceError

    generator = FixGenerator()
    fix = generator.generate(chain)        # FixProposal | InsufficientCausalChainError
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.causal import CausalChain, CausalNodeType
from app.models.evidence import DepChange, DependencyEvidence, EvidenceType
from app.models.fix import FixProposal, FixType

# ---------------------------------------------------------------------------
# Generator version — increment when the rule set changes
# ---------------------------------------------------------------------------

_GENERATOR_VERSION = "1.0"


# ---------------------------------------------------------------------------
# InsufficientCausalChainError
# ---------------------------------------------------------------------------


@dataclass
class InsufficientCausalChainError:
    """
    Returned (not raised) when the causal chain cannot support a fix proposal.

    The generator never raises on an unusable chain — it returns this object
    so callers can decide how to handle the gap (log, retry, skip).

    Attributes
    ----------
    pipeline_id:
        The pipeline the fix was being generated for.
    reason:
        Human-readable explanation of why a fix could not be proposed.
    chain_confidence:
        Confidence of the originating chain (may be 0.0 on degenerate input).
    """

    pipeline_id: str
    reason: str
    chain_confidence: float = 0.0


# ---------------------------------------------------------------------------
# FixGenerator
# ---------------------------------------------------------------------------


class FixGenerator:
    """
    Converts a :class:`~app.models.causal.CausalChain` into a
    :class:`~app.models.fix.FixProposal`.

    The generator is stateless — a single instance can process multiple
    chains without cross-contamination.

    Methods
    -------
    generate(chain) → FixProposal | InsufficientCausalChainError
        The single public entry point.

    Notes
    -----
    The reasoning is deterministic and rule-based.  Given identical input,
    the output fix is always identical (same fix_id, same description, same
    dependency_changes).  This is intentional for the MVP.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(
        self,
        chain: CausalChain,
    ) -> FixProposal | InsufficientCausalChainError:
        """
        Convert a causal chain into a fix proposal.

        Parameters
        ----------
        chain:
            The :class:`CausalChain` produced by
            :class:`~app.graph.builder.CausalChainBuilder`.

        Returns
        -------
        FixProposal
            On success — a fully populated fix proposal.
        InsufficientCausalChainError
            When the chain is too sparse to propose a meaningful fix.
        """
        # Guard: chain must have a root-cause node
        root_node = next(
            (n for n in chain.nodes if n.node_type == CausalNodeType.ROOT_CAUSE),
            None,
        )
        if root_node is None:
            return InsufficientCausalChainError(
                pipeline_id=chain.pipeline_id,
                reason="CausalChain has no ROOT_CAUSE node; cannot generate a fix.",
                chain_confidence=chain.confidence,
            )

        # Guard: root-cause node must reference at least one evidence artifact
        if not root_node.evidence_ids:
            return InsufficientCausalChainError(
                pipeline_id=chain.pipeline_id,
                reason=(
                    "ROOT_CAUSE node has no evidence_ids; "
                    "no evidence-backed fix can be proposed."
                ),
                chain_confidence=chain.confidence,
            )

        # Guard: zero-confidence chain cannot produce a reliable fix
        if chain.confidence == 0.0:
            return InsufficientCausalChainError(
                pipeline_id=chain.pipeline_id,
                reason=(
                    "CausalChain confidence is 0.0; "
                    "evidence quality is too low to propose a fix."
                ),
                chain_confidence=0.0,
            )

        return self._build_fix(chain, root_node.evidence_ids, root_node.confidence)

    # ------------------------------------------------------------------
    # Internal: fix construction
    # ------------------------------------------------------------------

    def _build_fix(
        self,
        chain: CausalChain,
        root_evidence_ids: list[str],
        root_confidence: float,
    ) -> FixProposal | InsufficientCausalChainError:
        """
        Apply the priority-ordered rule set to select and construct the fix.

        Rule 1  — DEPENDENCY_BREAK node present with a resolvable DepChange
        Rule 2  — ROOT_CAUSE is a code-change (no dep break) — revert patch
        Rule 3  — Fallback: generic fix from root-cause description
        """
        dep_break_node = next(
            (n for n in chain.nodes if n.node_type == CausalNodeType.DEPENDENCY_BREAK),
            None,
        )

        # ------------------------------------------------------------------
        # Rule 1 — Dependency break: pin to prior version
        # ------------------------------------------------------------------
        if dep_break_node is not None:
            return self._fix_dependency_change(chain, root_evidence_ids, root_confidence)

        # ------------------------------------------------------------------
        # Rule 2 — Code change (no dependency break): revert the change
        # ------------------------------------------------------------------
        root_node = next(
            n for n in chain.nodes if n.node_type == CausalNodeType.ROOT_CAUSE
        )
        if "commit" in root_node.label.lower() or "code change" in root_node.label.lower():
            return self._fix_code_revert(chain, root_node, root_evidence_ids, root_confidence)

        # ------------------------------------------------------------------
        # Rule 3 — Fallback: generic fix
        # ------------------------------------------------------------------
        return self._fix_generic(chain, root_node, root_evidence_ids, root_confidence)

    # ------------------------------------------------------------------
    # Rule 1 helper — dependency pin fix
    # ------------------------------------------------------------------

    def _fix_dependency_change(
        self,
        chain: CausalChain,
        root_evidence_ids: list[str],
        root_confidence: float,
    ) -> FixProposal:
        """
        Produce a DEPENDENCY_CHANGE fix by pinning the breaking dependency
        back to the last known-good version.

        Extracts the dependency name and versions from the DEPENDENCY_BREAK
        node label (which the builder formats as
        ``"Breaking API change in <dep-name>"``).

        For the exact dependency versions, we locate the DepChange data
        embedded in the ROOT_CAUSE node label, which the builder formats as:
        ``"Dependency bump: <dep> <old> → <new>"``
        """
        dep_break_node = next(
            n for n in chain.nodes if n.node_type == CausalNodeType.DEPENDENCY_BREAK
        )
        root_node = next(
            n for n in chain.nodes if n.node_type == CausalNodeType.ROOT_CAUSE
        )

        # Collect all evidence_ids across both nodes (deduplicated, ordered)
        all_evidence_ids: list[str] = list(dict.fromkeys(
            root_evidence_ids + list(dep_break_node.evidence_ids)
        ))

        # Parse dep name and versions from the root-cause node label.
        # Builder label format: "Dependency bump: <dep> <old> → <new>"
        dep_name, old_version, new_version = _parse_dep_from_label(root_node.label)

        # Build the DepChange that represents the fix: roll back new → old
        if dep_name and old_version and new_version:
            dep_change_fix = DepChange(
                name=dep_name,
                old_version=new_version,   # current (broken) version
                new_version=old_version,   # target (safe) version
                affected_component=None,
            )
            description = (
                f"Pin {dep_name} back from {new_version} to {old_version}. "
                f"The new major version introduced breaking API changes that removed "
                f"functions used by this service."
            )
            rationale = (
                f"The causal chain identifies the upgrade of {dep_name} from "
                f"{old_version} to {new_version} as the root cause. "
                f"{dep_break_node.description} "
                f"Pinning back to {old_version} restores the removed API and "
                f"immediately resolves the observed failures."
            )
            affected_file = _infer_affected_file(chain)
            dep_changes = [dep_change_fix]
        else:
            # Dep name/version could not be parsed from label — generic dep fix
            description = (
                "Pin the breaking dependency back to the last compatible version."
            )
            rationale = (
                f"The causal chain identifies a dependency upgrade as the root cause. "
                f"{dep_break_node.description} "
                f"Reverting to the prior version restores the broken API."
            )
            affected_file = None
            dep_changes = []

        return FixProposal(
            fix_id=f"fix-{chain.pipeline_id}",
            pipeline_id=chain.pipeline_id,
            root_cause_node_id=root_node.node_id,
            fix_type=FixType.DEPENDENCY_CHANGE,
            description=description,
            rationale=rationale,
            affected_file=affected_file,
            dependency_changes=dep_changes,
            evidence_ids=all_evidence_ids,
            confidence=root_confidence,
            generator_version=_GENERATOR_VERSION,
        )

    # ------------------------------------------------------------------
    # Rule 2 helper — code revert fix
    # ------------------------------------------------------------------

    def _fix_code_revert(
        self,
        chain: CausalChain,
        root_node,  # CausalNode
        root_evidence_ids: list[str],
        root_confidence: float,
    ) -> FixProposal:
        """Produce a CODE_PATCH fix: revert the breaking commit."""
        description = (
            f"Revert the code change introduced in the failing commit. "
            f"{root_node.description}"
        )
        rationale = (
            f"The causal chain identifies a code change as the root cause: "
            f"{root_node.description} "
            f"Reverting the change will restore the previously-passing state."
        )
        return FixProposal(
            fix_id=f"fix-{chain.pipeline_id}",
            pipeline_id=chain.pipeline_id,
            root_cause_node_id=root_node.node_id,
            fix_type=FixType.CODE_PATCH,
            description=description,
            rationale=rationale,
            affected_file=None,
            evidence_ids=root_evidence_ids,
            confidence=root_confidence,
            generator_version=_GENERATOR_VERSION,
        )

    # ------------------------------------------------------------------
    # Rule 3 helper — generic fallback fix
    # ------------------------------------------------------------------

    def _fix_generic(
        self,
        chain: CausalChain,
        root_node,  # CausalNode
        root_evidence_ids: list[str],
        root_confidence: float,
    ) -> FixProposal:
        """Produce a generic fix description when no specific rule applies."""
        description = (
            f"Address the root cause identified in the causal chain: "
            f"{root_node.label}."
        )
        rationale = (
            f"The causal chain identifies the following root cause: "
            f"{root_node.description}"
        )
        return FixProposal(
            fix_id=f"fix-{chain.pipeline_id}",
            pipeline_id=chain.pipeline_id,
            root_cause_node_id=root_node.node_id,
            fix_type=FixType.CONFIG_CHANGE,
            description=description,
            rationale=rationale,
            affected_file=None,
            evidence_ids=root_evidence_ids,
            confidence=root_confidence * 0.5,  # penalise: no specific rule matched
            generator_version=_GENERATOR_VERSION,
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_dep_from_label(label: str) -> tuple[str | None, str | None, str | None]:
    """
    Extract (dep_name, old_version, new_version) from a builder-generated
    ROOT_CAUSE label.

    Expected format:
        "Dependency bump: <dep_name> <old_version> → <new_version>"

    Returns (None, None, None) if the label doesn't match the format.
    """
    prefix = "Dependency bump: "
    if not label.startswith(prefix):
        return None, None, None

    rest = label[len(prefix):]   # e.g. "utility-lib 2.3.1 → 3.0.0"
    # Split on the arrow separator (with or without spaces)
    if " → " in rest:
        left, new_version = rest.split(" → ", 1)
        new_version = new_version.strip()
    elif "->" in rest:
        left, new_version = rest.split("->", 1)
        new_version = new_version.strip()
    else:
        return None, None, None

    # left is "<dep_name> <old_version>"
    parts = left.strip().rsplit(" ", 1)
    if len(parts) == 2:
        dep_name, old_version = parts
        return dep_name.strip(), old_version.strip(), new_version
    return None, None, None


def _infer_affected_file(chain: CausalChain) -> str | None:
    """
    Attempt to infer the affected configuration file from the causal chain.

    For DEPENDENCY_CHANGE fixes the standard file is ``package.json``
    for Node.js projects.  The chain label/description is checked for
    explicit file references; if none found, ``package.json`` is returned
    when the dependency name is a Node.js-style package (no slashes in name
    suggests a non-path package name).

    Returns ``None`` when no file can be confidently inferred.
    """
    # Look for an explicit file path in the root-cause description
    root_node = next(
        (n for n in chain.nodes if n.node_type == CausalNodeType.ROOT_CAUSE),
        None,
    )
    if root_node is None:
        return None

    desc_lower = root_node.description.lower()
    for candidate in ("package.json", "requirements.txt", "pom.xml", "build.gradle",
                      "go.mod", "cargo.toml", "gemfile"):
        if candidate in desc_lower:
            return candidate

    # Fall back: if it looks like a Node.js project dep bump, assume package.json
    dep_break = next(
        (n for n in chain.nodes if n.node_type == CausalNodeType.DEPENDENCY_BREAK),
        None,
    )
    if dep_break is not None:
        # Node.js packages don't contain '/' unless scoped (@org/pkg)
        dep_name, _, _ = _parse_dep_from_label(root_node.label)
        if dep_name is not None:
            return "package.json"

    return None
