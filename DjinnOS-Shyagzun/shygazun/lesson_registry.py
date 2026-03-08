from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence, cast

from shygazun.kernel.constants.byte_table import SHYGAZUN_BYTE_TABLE, byte_entry
from shygazun.kernel.policy.recombiner import frontier_for_akinenwun, frontier_to_obj, parse_akinenwun


@dataclass(frozen=True)
class LessonRecord:
    lesson_id: str
    payload: Mapping[str, Any]


@dataclass(frozen=True)
class ProjectionExample:
    source_text: str
    authoritative_projection: str
    lesson_id: str
    literal_gloss: str


@dataclass(frozen=True)
class ProjectionRule:
    lesson_id: str
    pattern: tuple[str, ...]
    english_template: str
    literal_gloss_template: str


@dataclass(frozen=True)
class ProjectionSlot:
    slot_name: str
    kind: str
    semantic_role: str | None = None
    person: int | None = None
    number: str | None = None
    required_features: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class ProjectionRegime:
    lesson_id: str
    regime_id: str
    slots: tuple[ProjectionSlot, ...]
    english_template: str
    literal_gloss_template: str


@dataclass(frozen=True)
class StructuralRegime:
    lesson_id: str
    regime_id: str
    source_tongues: tuple[str, ...]
    mediator_tongues: tuple[str, ...]
    validator_tongues: tuple[str, ...]
    applies_to_kinds: tuple[str, ...]
    description: str
    derived_features: Mapping[str, Any]
    required_features: Mapping[str, Any]


class LessonValidationError(ValueError):
    pass


class LessonRegistry:
    def __init__(self, lessons: Sequence[LessonRecord]) -> None:
        self._lessons = tuple(lessons)
        self._by_id = {lesson.lesson_id: lesson for lesson in self._lessons}
        self._pronoun_aliases: dict[str, dict[str, Any]] = {}
        self._lexeme_aliases: dict[str, dict[str, Any]] = {}
        self._feature_aliases: dict[str, dict[str, Any]] = {}
        self._exact_projection_examples: dict[str, ProjectionExample] = {}
        self._projection_rules: list[ProjectionRule] = []
        self._projection_regimes: list[ProjectionRegime] = []
        self._structural_regimes: list[StructuralRegime] = []
        for lesson in self._lessons:
            payload = lesson.payload
            lesson_type = str(payload.get("lesson_type") or "")
            if lesson_type == "pronoun_paradigm":
                self._index_pronoun_lesson(lesson)
            elif lesson_type == "lexeme_aliases":
                self._index_lexeme_lesson(lesson)
            elif lesson_type == "feature_aliases":
                self._index_feature_lesson(lesson)
            elif lesson_type == "projection_discipline":
                self._index_projection_rules(lesson)
                self._index_projection_regimes(lesson)
            elif lesson_type == "structural_regime":
                self._index_structural_regimes(lesson)
            for example_obj in payload.get("projection_examples", []) if isinstance(payload.get("projection_examples"), list) else []:
                if not isinstance(example_obj, dict):
                    continue
                source_text = _normalize_text(str(example_obj.get("source_text") or ""))
                if not source_text:
                    continue
                self._exact_projection_examples[source_text] = ProjectionExample(
                    source_text=source_text,
                    authoritative_projection=str(example_obj.get("authoritative_projection") or ""),
                    lesson_id=lesson.lesson_id,
                    literal_gloss=str(example_obj.get("literal_gloss") or ""),
                )

    def lessons(self) -> Sequence[Mapping[str, Any]]:
        return tuple(lesson.payload for lesson in self._lessons)

    def lesson(self, lesson_id: str) -> Mapping[str, Any]:
        return self._by_id[lesson_id].payload

    def english_to_shygazun_lexicon(self) -> Mapping[str, str]:
        lexicon: dict[str, str] = {}
        for token, alias in self._pronoun_aliases.items():
            english_alias = str(alias.get("english_alias") or "").strip().lower()
            if english_alias:
                lexicon.setdefault(english_alias, token)
        for token, alias in self._lexeme_aliases.items():
            english_alias = str(alias.get("english_alias") or "").strip().lower()
            if english_alias:
                lexicon.setdefault(english_alias, token)
        for token, alias in self._feature_aliases.items():
            english_alias = str(alias.get("english_alias") or "").strip().lower()
            if english_alias:
                lexicon.setdefault(english_alias, token)
        return lexicon

    def shygazun_to_english_lexicon(self) -> Mapping[str, str]:
        lexicon: dict[str, str] = {}
        for token, alias in self._pronoun_aliases.items():
            english_alias = str(alias.get("english_alias") or "").strip()
            if english_alias:
                lexicon.setdefault(token.lower(), english_alias)
        for token, alias in self._lexeme_aliases.items():
            english_alias = str(alias.get("english_alias") or "").strip()
            if english_alias:
                lexicon.setdefault(token.lower(), english_alias)
        for token, alias in self._feature_aliases.items():
            english_alias = str(alias.get("english_alias") or "").strip()
            if english_alias:
                lexicon.setdefault(token.lower(), english_alias)
        return lexicon

    def english_projection_examples(self) -> Mapping[str, str]:
        examples: dict[str, str] = {}
        for example in self._exact_projection_examples.values():
            authoritative_projection = _normalize_text(example.authoritative_projection).lower()
            if authoritative_projection:
                examples.setdefault(authoritative_projection, example.source_text)
        return examples

    def shygazun_projection_examples(self) -> Mapping[str, str]:
        examples: dict[str, str] = {}
        for example in self._exact_projection_examples.values():
            source_text = _normalize_text(example.source_text)
            authoritative_projection = _normalize_text(example.authoritative_projection)
            if source_text and authoritative_projection:
                examples.setdefault(source_text.lower(), authoritative_projection)
        return examples

    def cobra_surface(self, source_text: str) -> dict[str, Any]:
        projection = self.project_text(source_text)
        return {
            "source_text": projection["source_text"],
            "authoritative_projection": projection.get("authoritative_projection"),
            "composed_features": projection["composed_features"],
            "byte_table_trace": projection["byte_table_trace"],
            "structural_verifications": projection["structural_verifications"],
            "code_surface": cast(Mapping[str, Any], projection["surface_lowerings"])["code_surface"],
            "placement_graph": cast(Mapping[str, Any], projection["surface_lowerings"])["placement_graph"],
            "trust_contract": projection["trust_contract"],
        }

    def project_text(self, source_text: str) -> dict[str, Any]:
        normalized = _normalize_text(source_text)
        if normalized == "":
            raise ValueError("source_text_required")

        tokens = normalized.split(" ")
        token_objects: list[dict[str, Any]] = []
        applied_lessons: set[str] = set()
        for token in tokens:
            alias = self._pronoun_aliases.get(token)
            if alias is not None:
                alias_decimals = _effective_decimals(alias)
                alias_symbols = _effective_symbols(alias)
                applied_lessons.add(str(alias["lesson_id"]))
                token_objects.append(
                    {
                        "token": token,
                        "kind": "pronoun_alias",
                        "lesson_id": alias["lesson_id"],
                        "person": alias["person"],
                        "number": alias["number"],
                        "distance_from_speaker_mind": alias["distance_from_speaker_mind"],
                        "english_alias": alias["english_alias"],
                        "bytes": alias_decimals,
                        "symbols": alias_symbols,
                        "semantic_trace": _semantic_trace_from_decimals(alias_decimals),
                        "authority_citations": list(alias["authority_citations"]),
                    }
                )
                continue

            lexeme = self._lexeme_aliases.get(token)
            if lexeme is not None:
                lexeme_decimals = _effective_decimals(lexeme)
                lexeme_symbols = _effective_symbols(lexeme)
                applied_lessons.add(str(lexeme["lesson_id"]))
                token_objects.append(
                    {
                        "token": token,
                        "kind": "lexeme_alias",
                        "lesson_id": lexeme["lesson_id"],
                        "semantic_role": lexeme["semantic_role"],
                        "english_alias": lexeme["english_alias"],
                        "literal_gloss": lexeme["literal_gloss"],
                        "bytes": lexeme_decimals,
                        "symbols": lexeme_symbols,
                        "semantic_trace": _semantic_trace_from_decimals(lexeme_decimals),
                        "authority_citations": list(lexeme["authority_citations"]),
                        "feature_bundle": dict(cast(Mapping[str, Any], lexeme["feature_bundle"])),
                    }
                )
                continue

            feature_alias = self._feature_aliases.get(token)
            if feature_alias is not None:
                feature_decimals = _effective_decimals(feature_alias)
                feature_symbols = _effective_symbols(feature_alias)
                applied_lessons.add(str(feature_alias["lesson_id"]))
                token_objects.append(
                    {
                        "token": token,
                        "kind": "feature_alias",
                        "lesson_id": feature_alias["lesson_id"],
                        "english_alias": feature_alias["english_alias"],
                        "literal_gloss": feature_alias["literal_gloss"],
                        "feature_bundle": dict(cast(Mapping[str, Any], feature_alias["feature_bundle"])),
                        "bytes": feature_decimals,
                        "symbols": feature_symbols,
                        "semantic_trace": _semantic_trace_from_decimals(feature_decimals),
                        "authority_citations": list(feature_alias["authority_citations"]),
                    }
                )
                continue

            try:
                frontier = frontier_for_akinenwun(token, mode="prose")
            except ValueError:
                token_objects.append(
                    {
                        "token": token,
                        "kind": "unresolved_surface",
                        "reason": "token_not_yet_covered_by_bilingual_lessons_or_recombiner",
                    }
                )
                continue

            token_objects.append(
                {
                    "token": token,
                    "kind": "akinenwun_surface",
                    "bytes": [int(decimal) for path in frontier.paths for decimal in path.decimals],
                    "symbols": [str(symbol) for path in frontier.paths for symbol in path.symbols],
                    "semantic_trace": _semantic_trace_from_decimals([int(decimal) for path in frontier.paths for decimal in path.decimals]),
                    "feature_bundle": _derive_intrinsic_feature_bundle([int(decimal) for path in frontier.paths for decimal in path.decimals]),
                    "frontier_hash": _frontier_hash_obj(frontier_to_obj(frontier)),
                    "frontier": frontier_to_obj(frontier),
                }
            )

        exact_example = self._exact_projection_examples.get(normalized)
        structural_verifications = self._verify_structural_regimes(token_objects)
        projection: dict[str, Any] = {
            "source_text": normalized,
            "tokens": token_objects,
            "applied_lessons": sorted(applied_lessons),
            "projection_mode": "lesson_constrained_bilingual",
            "byte_table_trace": _derive_byte_table_trace(token_objects),
            "structural_verifications": structural_verifications,
            "composed_features": _compose_feature_state(token_objects, structural_verifications),
        }
        projection["surface_lowerings"] = _derive_surface_lowerings(
            cast(Mapping[str, Any], projection["composed_features"]),
            token_objects,
        )
        pattern_projection = self._project_from_regimes(token_objects)
        if pattern_projection is None:
            pattern_projection = self._project_from_rules(token_objects)
        if pattern_projection is not None:
            applied_lessons.update(cast(Sequence[str], pattern_projection["applied_lessons"]))
            projection["applied_lessons"] = sorted(applied_lessons)
            projection["authoritative_projection"] = {
                "english": pattern_projection["english"],
                "literal_gloss": pattern_projection["literal_gloss"],
                "lesson_id": pattern_projection["lesson_id"],
                "authority_level": str(pattern_projection["authority_level"]),
            }
            if "pattern" in pattern_projection:
                projection["authoritative_projection"]["pattern"] = list(cast(Sequence[str], pattern_projection["pattern"]))
            if "regime_id" in pattern_projection:
                projection["authoritative_projection"]["regime_id"] = str(pattern_projection["regime_id"])

        if exact_example is not None:
            applied_lessons.add(exact_example.lesson_id)
            projection["applied_lessons"] = sorted(applied_lessons)
            projection["authoritative_projection"] = {
                "english": exact_example.authoritative_projection,
                "literal_gloss": exact_example.literal_gloss,
                "lesson_id": exact_example.lesson_id,
                "authority_level": "lesson_exact_match",
            }
        projection["trust_contract"] = _derive_trust_contract(projection)
        return projection

    def _index_pronoun_lesson(self, lesson: LessonRecord) -> None:
        payload = lesson.payload
        paradigm = payload.get("paradigm")
        if not isinstance(paradigm, list):
            return
        for entry_obj in paradigm:
            if not isinstance(entry_obj, dict):
                continue
            token = str(entry_obj.get("token") or "").strip()
            english_alias = str(entry_obj.get("english_alias") or "").strip()
            person = int(entry_obj.get("person")) if entry_obj.get("person") is not None else 0
            number = str(entry_obj.get("number") or "").strip()
            distance = str(entry_obj.get("distance_from_speaker_mind") or "").strip()
            if token == "" or english_alias == "" or person <= 0 or number == "":
                continue
            authority_citations = payload.get("authority", {}).get("citations", []) if isinstance(payload.get("authority"), dict) else []
            try:
                symbols = parse_akinenwun(token)
                decimals = _decimals_for_symbols(symbols)
            except ValueError:
                symbols = _loose_symbols_for_surface(token)
                decimals = _decimals_for_symbols(symbols) if symbols else []
            self._pronoun_aliases[token] = {
                "lesson_id": lesson.lesson_id,
                "english_alias": english_alias,
                "literal_gloss": english_alias,
                "person": person,
                "number": number,
                "distance_from_speaker_mind": distance,
                "bytes": decimals,
                "symbols": symbols,
                "authority_citations": authority_citations,
                "pattern_role": f"pronoun_p{person}_{number}",
            }

    def _index_lexeme_lesson(self, lesson: LessonRecord) -> None:
        payload = lesson.payload
        aliases = payload.get("aliases")
        if not isinstance(aliases, list):
            return
        for alias_obj in aliases:
            if not isinstance(alias_obj, dict):
                continue
            token = str(alias_obj.get("token") or "").strip()
            english_alias = str(alias_obj.get("english_alias") or "").strip()
            literal_gloss = str(alias_obj.get("literal_gloss") or english_alias).strip()
            semantic_role = str(alias_obj.get("semantic_role") or "").strip()
            feature_bundle = alias_obj.get("features")
            if token == "" or english_alias == "" or semantic_role == "":
                continue
            authority_citations = payload.get("authority", {}).get("citations", []) if isinstance(payload.get("authority"), dict) else []
            try:
                symbols = parse_akinenwun(token)
                decimals = _decimals_for_symbols(symbols)
            except ValueError:
                symbols = _loose_symbols_for_surface(token)
                decimals = _decimals_for_symbols(symbols) if symbols else []
            self._lexeme_aliases[token] = {
                "lesson_id": lesson.lesson_id,
                "english_alias": english_alias,
                "literal_gloss": literal_gloss,
                "semantic_role": semantic_role,
                "bytes": decimals,
                "symbols": symbols,
                "authority_citations": authority_citations,
                "pattern_role": semantic_role,
                "feature_bundle": dict(cast(Mapping[str, Any], feature_bundle)) if isinstance(feature_bundle, Mapping) else {},
            }

    def _index_feature_lesson(self, lesson: LessonRecord) -> None:
        payload = lesson.payload
        aliases = payload.get("aliases")
        if not isinstance(aliases, list):
            return
        for alias_obj in aliases:
            if not isinstance(alias_obj, dict):
                continue
            token = str(alias_obj.get("token") or "").strip()
            english_alias = str(alias_obj.get("english_alias") or token).strip()
            literal_gloss = str(alias_obj.get("literal_gloss") or english_alias).strip()
            feature_bundle = alias_obj.get("features")
            if token == "" or not isinstance(feature_bundle, dict) or len(feature_bundle) == 0:
                continue
            authority_citations = payload.get("authority", {}).get("citations", []) if isinstance(payload.get("authority"), dict) else []
            try:
                symbols = parse_akinenwun(token)
                decimals = _decimals_for_symbols(symbols)
            except ValueError:
                symbols = _loose_symbols_for_surface(token)
                decimals = _decimals_for_symbols(symbols) if symbols else []
            self._feature_aliases[token] = {
                "lesson_id": lesson.lesson_id,
                "english_alias": english_alias,
                "literal_gloss": literal_gloss,
                "feature_bundle": dict(cast(Mapping[str, Any], feature_bundle)),
                "bytes": decimals,
                "symbols": symbols,
                "authority_citations": authority_citations,
            }

    def _index_projection_rules(self, lesson: LessonRecord) -> None:
        payload = lesson.payload
        for rule_obj in payload.get("projection_rules", []) if isinstance(payload.get("projection_rules"), list) else []:
            if not isinstance(rule_obj, dict):
                continue
            pattern_obj = rule_obj.get("pattern")
            if not isinstance(pattern_obj, list) or len(pattern_obj) == 0:
                continue
            pattern = tuple(str(item).strip() for item in pattern_obj if str(item).strip())
            english_template = str(rule_obj.get("english_template") or "").strip()
            literal_gloss_template = str(rule_obj.get("literal_gloss_template") or "").strip()
            if len(pattern) == 0 or english_template == "" or literal_gloss_template == "":
                continue
            self._projection_rules.append(
                ProjectionRule(
                    lesson_id=lesson.lesson_id,
                    pattern=pattern,
                    english_template=english_template,
                    literal_gloss_template=literal_gloss_template,
                )
            )

    def _index_projection_regimes(self, lesson: LessonRecord) -> None:
        payload = lesson.payload
        regimes_obj = payload.get("projection_regimes")
        if not isinstance(regimes_obj, list):
            return
        for regime_obj in regimes_obj:
            if not isinstance(regime_obj, dict):
                continue
            regime_id = str(regime_obj.get("regime_id") or "").strip()
            slots_obj = regime_obj.get("slots")
            english_template = str(regime_obj.get("english_template") or "").strip()
            literal_gloss_template = str(regime_obj.get("literal_gloss_template") or "").strip()
            if regime_id == "" or not isinstance(slots_obj, list) or len(slots_obj) == 0:
                continue
            if english_template == "" or literal_gloss_template == "":
                continue
            slots: list[ProjectionSlot] = []
            for slot_obj in slots_obj:
                if not isinstance(slot_obj, dict):
                    continue
                slot_name = str(slot_obj.get("slot_name") or "").strip()
                kind = str(slot_obj.get("kind") or "").strip()
                semantic_role_obj = slot_obj.get("semantic_role")
                person_obj = slot_obj.get("person")
                number_obj = slot_obj.get("number")
                required_features_obj = slot_obj.get("required_features")
                if slot_name == "" or kind == "":
                    continue
                slot = ProjectionSlot(
                    slot_name=slot_name,
                    kind=kind,
                    semantic_role=str(semantic_role_obj).strip() if semantic_role_obj is not None else None,
                    person=int(person_obj) if person_obj is not None else None,
                    number=str(number_obj).strip() if number_obj is not None else None,
                    required_features=dict(cast(Mapping[str, Any], required_features_obj)) if isinstance(required_features_obj, Mapping) else None,
                )
                slots.append(slot)
            if len(slots) == 0:
                continue
            self._projection_regimes.append(
                ProjectionRegime(
                    lesson_id=lesson.lesson_id,
                    regime_id=regime_id,
                    slots=tuple(slots),
                    english_template=english_template,
                    literal_gloss_template=literal_gloss_template,
                )
            )

    def _index_structural_regimes(self, lesson: LessonRecord) -> None:
        payload = lesson.payload
        regimes_obj = payload.get("verification_regimes")
        if not isinstance(regimes_obj, list):
            return
        for regime_obj in regimes_obj:
            if not isinstance(regime_obj, dict):
                continue
            regime_id = str(regime_obj.get("regime_id") or "").strip()
            description = str(regime_obj.get("description") or "").strip()
            source_tongues = _string_tuple(regime_obj.get("source_tongues"))
            mediator_tongues = _string_tuple(regime_obj.get("mediator_tongues"))
            validator_tongues = _string_tuple(regime_obj.get("validator_tongues"))
            applies_to_kinds = _string_tuple(regime_obj.get("applies_to_kinds"))
            required_features = dict(cast(Mapping[str, Any], regime_obj.get("required_features"))) if isinstance(regime_obj.get("required_features"), Mapping) else {}
            if regime_id == "" or description == "":
                continue
            self._structural_regimes.append(
                StructuralRegime(
                    lesson_id=lesson.lesson_id,
                    regime_id=regime_id,
                    source_tongues=source_tongues,
                    mediator_tongues=mediator_tongues,
                    validator_tongues=validator_tongues,
                    applies_to_kinds=applies_to_kinds,
                    description=description,
                    derived_features=dict(cast(Mapping[str, Any], regime_obj.get("derived_features"))) if isinstance(regime_obj.get("derived_features"), Mapping) else {},
                    required_features=required_features,
                )
            )

    def _project_from_rules(self, token_objects: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
        if len(token_objects) == 0:
            return None
        token_roles = tuple(_pattern_role_for_token(token_obj) for token_obj in token_objects)
        token_map: dict[str, Mapping[str, Any]] = {}
        for token_obj in token_objects:
            role = _pattern_role_for_token(token_obj)
            if role:
                token_map[role] = token_obj

        for rule in self._projection_rules:
            if token_roles != rule.pattern:
                continue
            english = rule.english_template
            literal_gloss = rule.literal_gloss_template
            for role, token_obj in token_map.items():
                english = english.replace("{" + role + "}", str(token_obj.get("english_alias") or token_obj.get("token") or ""))
                literal_gloss = literal_gloss.replace(
                    "{" + role + "}",
                    str(token_obj.get("literal_gloss") or token_obj.get("english_alias") or token_obj.get("token") or ""),
                )
            return {
                "english": english,
                "literal_gloss": literal_gloss,
                "lesson_id": rule.lesson_id,
                "applied_lessons": [rule.lesson_id, *[str(obj.get("lesson_id") or "") for obj in token_objects if obj.get("lesson_id")]],
                "pattern": rule.pattern,
                "authority_level": "lesson_pattern_match",
            }
        return None

    def _project_from_regimes(self, token_objects: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
        if len(token_objects) == 0:
            return None
        for regime in self._projection_regimes:
            if len(token_objects) != len(regime.slots):
                continue
            slot_bindings: dict[str, Mapping[str, Any]] = {}
            matched = True
            for token_obj, slot in zip(token_objects, regime.slots):
                if not _token_matches_slot(token_obj, slot):
                    matched = False
                    break
                slot_bindings[slot.slot_name] = token_obj
            if not matched:
                continue

            english = regime.english_template
            literal_gloss = regime.literal_gloss_template
            for slot_name, token_obj in slot_bindings.items():
                english = english.replace("{" + slot_name + "}", str(token_obj.get("english_alias") or token_obj.get("token") or ""))
                literal_gloss = literal_gloss.replace(
                    "{" + slot_name + "}",
                    str(token_obj.get("literal_gloss") or token_obj.get("english_alias") or token_obj.get("token") or ""),
                )
            return {
                "english": english,
                "literal_gloss": literal_gloss,
                "lesson_id": regime.lesson_id,
                "applied_lessons": [regime.lesson_id, *[str(obj.get("lesson_id") or "") for obj in token_objects if obj.get("lesson_id")]],
                "regime_id": regime.regime_id,
                "authority_level": "lesson_regime_match",
            }
        return None

    def _verify_structural_regimes(self, token_objects: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
        verifications: list[dict[str, Any]] = []
        for regime in self._structural_regimes:
            matching_tokens = [
                token_obj
                for token_obj in token_objects
                if (len(regime.applies_to_kinds) == 0 or str(token_obj.get("kind") or "") in regime.applies_to_kinds)
                and _token_satisfies_required_features(token_obj, regime.required_features)
            ]
            tongues_seen = sorted(
                {
                    tongue
                    for token_obj in matching_tokens
                    for tongue in _token_tongues(token_obj)
                }
            )
            verified = (
                all(tongue in tongues_seen for tongue in regime.source_tongues)
                and all(tongue in tongues_seen for tongue in regime.mediator_tongues)
                and all(tongue in tongues_seen for tongue in regime.validator_tongues)
            )
            verifications.append(
                {
                    "lesson_id": regime.lesson_id,
                    "regime_id": regime.regime_id,
                    "description": regime.description,
                    "verified": verified,
                    "source_tongues": list(regime.source_tongues),
                    "mediator_tongues": list(regime.mediator_tongues),
                    "validator_tongues": list(regime.validator_tongues),
                    "derived_features": dict(regime.derived_features),
                    "tongues_seen": tongues_seen,
                    "matching_tokens": [str(token_obj.get("token") or "") for token_obj in matching_tokens],
                }
            )
        return verifications


def _normalize_text(text: str) -> str:
    return " ".join(text.strip().split())


def _string_tuple(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return tuple()
    out = [str(item).strip() for item in value if str(item).strip()]
    return tuple(out)


def _pattern_role_for_token(token_obj: Mapping[str, Any]) -> str:
    role = str(token_obj.get("pattern_role") or "")
    if role != "":
        return role
    kind = str(token_obj.get("kind") or "")
    if kind == "pronoun_alias":
        person = str(token_obj.get("person") or "")
        number = str(token_obj.get("number") or "")
        return f"pronoun_p{person}_{number}".replace(" ", "_")
    if kind == "lexeme_alias":
        return str(token_obj.get("semantic_role") or "")
    return ""


def _authority_decimals(token_obj: Mapping[str, Any]) -> list[int]:
    authority_citations = token_obj.get("authority_citations")
    if not isinstance(authority_citations, Sequence):
        return []
    decimals: list[int] = []
    for citation in authority_citations:
        if not isinstance(citation, Mapping):
            continue
        decimal = citation.get("decimal")
        if decimal is None:
            continue
        try:
            value = int(decimal)
        except (TypeError, ValueError):
            continue
        if value not in decimals:
            decimals.append(value)
    return decimals


def _effective_decimals(token_obj: Mapping[str, Any]) -> list[int]:
    bytes_obj = token_obj.get("bytes")
    decimals: list[int] = []
    if isinstance(bytes_obj, Sequence) and not isinstance(bytes_obj, (str, bytes, bytearray)):
        for item in bytes_obj:
            try:
                decimals.append(int(item))
            except (TypeError, ValueError):
                continue
    if decimals:
        return decimals
    return _authority_decimals(token_obj)


def _authority_symbols(token_obj: Mapping[str, Any]) -> list[str]:
    authority_citations = token_obj.get("authority_citations")
    if not isinstance(authority_citations, Sequence):
        return []
    symbols: list[str] = []
    for citation in authority_citations:
        if not isinstance(citation, Mapping):
            continue
        symbol = str(citation.get("symbol") or "").strip()
        if symbol and symbol not in symbols:
            symbols.append(symbol)
    return symbols


def _effective_symbols(token_obj: Mapping[str, Any]) -> list[str]:
    symbols_obj = token_obj.get("symbols")
    if isinstance(symbols_obj, Sequence) and not isinstance(symbols_obj, (str, bytes, bytearray)):
        symbols = [str(item).strip() for item in symbols_obj if str(item).strip()]
        if symbols:
            return symbols
    return _authority_symbols(token_obj)


def _token_feature_bundle(token_obj: Mapping[str, Any]) -> dict[str, Any]:
    bundle: dict[str, Any] = {}
    feature_bundle = token_obj.get("feature_bundle")
    if isinstance(feature_bundle, Mapping):
        bundle.update(dict(feature_bundle))
    decimals = _effective_decimals(token_obj)
    if decimals:
        intrinsic = _derive_intrinsic_feature_bundle(decimals)
        for key, value in intrinsic.items():
            bundle.setdefault(key, value)
    if str(token_obj.get("kind") or "") == "pronoun_alias":
        bundle.setdefault("person", token_obj.get("person"))
        bundle.setdefault("number", token_obj.get("number"))
        bundle.setdefault("distance_from_speaker_mind", token_obj.get("distance_from_speaker_mind"))
    return bundle


def _token_tongues(token_obj: Mapping[str, Any]) -> tuple[str, ...]:
    tongues: list[str] = []
    decimals = _effective_decimals(token_obj)
    if decimals:
        for item in decimals:
            try:
                entry = byte_entry(int(item))
            except Exception:
                continue
            tongue = str(entry["tongue"])
            if tongue not in tongues:
                tongues.append(tongue)
    return tuple(tongues)


def _token_satisfies_required_features(token_obj: Mapping[str, Any], required_features: Mapping[str, Any]) -> bool:
    if len(required_features) == 0:
        return True
    feature_bundle = _token_feature_bundle(token_obj)
    for key, value in required_features.items():
        current = feature_bundle.get(str(key))
        if isinstance(current, list):
            if value not in current:
                return False
        elif current != value:
            return False
    return True


def _compose_feature_state(
    token_objects: Sequence[Mapping[str, Any]],
    structural_verifications: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    composed: dict[str, Any] = {}
    feature_sources: list[dict[str, Any]] = []
    for token_obj in token_objects:
        feature_bundle = _token_feature_bundle(token_obj)
        if len(feature_bundle) == 0:
            continue
        feature_entry: dict[str, Any] = {
            "token": str(token_obj.get("token") or ""),
            "lesson_id": str(token_obj.get("lesson_id") or ""),
            "features": dict(feature_bundle),
        }
        feature_sources.append(feature_entry)
        for key, value in feature_bundle.items():
            existing = composed.get(str(key))
            if existing is None:
                composed[str(key)] = value
                continue
            if existing == value:
                continue
            if not isinstance(existing, list):
                composed[str(key)] = [existing, value]
            else:
                if value not in existing:
                    existing.append(value)
    for verification in structural_verifications or ():
        if not bool(verification.get("verified")):
            continue
        derived_features = verification.get("derived_features")
        if not isinstance(derived_features, Mapping) or len(derived_features) == 0:
            continue
        feature_sources.append(
            {
                "token": str(verification.get("regime_id") or ""),
                "lesson_id": str(verification.get("lesson_id") or ""),
                "features": dict(derived_features),
                "source": "structural_verification",
            }
        )
        for key, value in derived_features.items():
            existing = composed.get(str(key))
            if existing is None:
                composed[str(key)] = value
                continue
            if existing == value:
                continue
            if not isinstance(existing, list):
                composed[str(key)] = [existing, value]
            else:
                if value not in existing:
                    existing.append(value)
    if feature_sources:
        composed["_sources"] = feature_sources
    return composed


def _derive_surface_lowerings(
    composed_features: Mapping[str, Any],
    token_objects: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    tags: list[str] = []
    node_metadata: dict[str, Any] = {}
    for key, value in composed_features.items():
        if key == "_sources":
            continue
        node_metadata[key] = value
        if isinstance(value, list):
            for item in value:
                tags.append(f"{key}:{item}")
        else:
            tags.append(f"{key}:{value}")

    lexical_roles = [
        str(token_obj.get("semantic_role") or "")
        for token_obj in token_objects
        if str(token_obj.get("kind") or "") == "lexeme_alias" and str(token_obj.get("semantic_role") or "") != ""
    ]
    lexical_roles = [role for role in lexical_roles if role]

    code_surface = {
        "feature_tags": sorted(set(tags)),
        "lexical_roles": lexical_roles,
        "speaker_frame": {
            "person": composed_features.get("person"),
            "number": composed_features.get("number"),
            "distance_from_speaker_mind": composed_features.get("distance_from_speaker_mind"),
        },
        "entity_traits": {
            "animacy": composed_features.get("animacy"),
            "number": composed_features.get("number"),
            "embodiment": composed_features.get("embodiment"),
            "elemental_density": composed_features.get("elemental_density"),
            "processual": composed_features.get("processual"),
            "anatomy_derivation": composed_features.get("anatomy_derivation"),
            "validation_mode": composed_features.get("validation_mode"),
        },
    }

    placement_graph = {
        "node_metadata": node_metadata,
        "node_tags": sorted(set(tags)),
        "projection_hints": {
            "animate": composed_features.get("animacy") == "animate",
            "plural": (
                composed_features.get("number") == "plural"
                or (isinstance(composed_features.get("number"), list) and "plural" in cast(list[Any], composed_features.get("number")))
            ),
            "embodiment_axes": (
                cast(list[Any], composed_features.get("embodiment"))
                if isinstance(composed_features.get("embodiment"), list)
                else ([composed_features.get("embodiment")] if composed_features.get("embodiment") is not None else [])
            ),
            "anatomy_derivation": composed_features.get("anatomy_derivation"),
            "validation_mode": composed_features.get("validation_mode"),
        },
    }

    return {
        "code_surface": code_surface,
        "placement_graph": placement_graph,
    }


def _derive_trust_contract(projection: Mapping[str, Any]) -> dict[str, Any]:
    tokens_obj = projection.get("tokens")
    tokens = cast(Sequence[Mapping[str, Any]], tokens_obj) if isinstance(tokens_obj, Sequence) else tuple()
    authoritative_projection = projection.get("authoritative_projection")
    structural_obj = projection.get("structural_verifications")
    structural = cast(Sequence[Mapping[str, Any]], structural_obj) if isinstance(structural_obj, Sequence) else tuple()
    applicable_structural = tuple(
        item for item in structural
        if isinstance(item.get("matching_tokens"), list) and len(cast(list[Any], item.get("matching_tokens"))) > 0
    )
    composed_features_obj = projection.get("composed_features")
    composed_features = cast(Mapping[str, Any], composed_features_obj) if isinstance(composed_features_obj, Mapping) else {}

    total_tokens = len(tokens)
    unresolved_tokens = sum(1 for token in tokens if str(token.get("kind") or "") == "unresolved_surface")
    lesson_tokens = sum(
        1
        for token in tokens
        if str(token.get("kind") or "") in {"pronoun_alias", "lexeme_alias", "feature_alias"}
    )
    frontier_tokens = sum(1 for token in tokens if str(token.get("kind") or "") == "akinenwun_surface")
    verified_structures = sum(1 for item in applicable_structural if bool(item.get("verified")))
    structural_total = len(applicable_structural)
    authority_level = (
        str(cast(Mapping[str, Any], authoritative_projection).get("authority_level") or "none")
        if isinstance(authoritative_projection, Mapping)
        else "none"
    )

    score = 0.0
    if total_tokens > 0:
        score += 0.4 * (lesson_tokens / total_tokens)
        score += 0.15 * (frontier_tokens / total_tokens)
        score -= 0.35 * (unresolved_tokens / total_tokens)
    if authority_level == "lesson_exact_match":
        score += 0.25
    elif authority_level == "lesson_regime_match":
        score += 0.2
    elif authority_level == "lesson_pattern_match":
        score += 0.12
    if structural_total > 0:
        score += 0.2 * (verified_structures / structural_total)
    if composed_features.get("anatomy_derivation") is not None:
        score += 0.08
    if composed_features.get("validation_mode") is not None:
        score += 0.04

    normalized_score = max(0.0, min(1.0, round(score, 4)))
    grade = "low"
    if normalized_score >= 0.85:
        grade = "high"
    elif normalized_score >= 0.55:
        grade = "medium"

    return {
        "authority_level": authority_level,
        "coverage": {
            "total_tokens": total_tokens,
            "lesson_tokens": lesson_tokens,
            "frontier_tokens": frontier_tokens,
            "unresolved_tokens": unresolved_tokens,
        },
        "structural_verification": {
            "verified": verified_structures,
            "total": structural_total,
        },
        "score": normalized_score,
        "grade": grade,
        "downstream_readiness": {
            "code_surface_safe": unresolved_tokens == 0 and (
                authority_level in {"lesson_exact_match", "lesson_regime_match", "lesson_pattern_match"}
                or lesson_tokens == total_tokens
                or (structural_total > 0 and verified_structures == structural_total)
            ),
            "placement_graph_safe": unresolved_tokens == 0 and (structural_total == 0 or verified_structures == structural_total),
            "anatomy_surface_safe": unresolved_tokens == 0 and (
                total_tokens == 0
                or composed_features.get("anatomy_derivation") is not None
                or composed_features.get("anatomy_axes") is not None
                or composed_features.get("embodiment_mode") is not None
            ),
        },
    }


def _semantic_trace_from_decimals(decimals: Sequence[int]) -> list[dict[str, Any]]:
    trace: list[dict[str, Any]] = []
    for decimal in decimals:
        entry = byte_entry(int(decimal))
        trace.append(
            {
                "decimal": int(entry["decimal"]),
                "tongue": str(entry["tongue"]),
                "symbol": str(entry["symbol"]),
                "meaning": str(entry["meaning"]),
            }
        )
    return trace


def _derive_byte_table_trace(token_objects: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    tongue_counts: dict[str, int] = {}
    for token_obj in token_objects:
        for decimal in _effective_decimals(token_obj):
            try:
                entry = byte_entry(int(decimal))
            except Exception:
                continue
            tongue = str(entry["tongue"])
            tongue_counts[tongue] = tongue_counts.get(tongue, 0) + 1
            rows.append(
                {
                    "token": str(token_obj.get("token") or ""),
                    "decimal": int(entry["decimal"]),
                    "symbol": str(entry["symbol"]),
                    "tongue": tongue,
                    "meaning": str(entry["meaning"]),
                }
            )
    return {
        "rows": rows,
        "tongue_counts": tongue_counts,
    }


def _derive_intrinsic_feature_bundle(decimals: Sequence[int]) -> dict[str, Any]:
    features: dict[str, Any] = {}
    entries = [byte_entry(int(decimal)) for decimal in decimals]
    symbols = {str(entry["symbol"]) for entry in entries}
    meanings = [str(entry["meaning"]) for entry in entries]

    time_positive = "Y" in symbols
    time_negative = "U" in symbols
    sakura_time_symbols = {"By", "Dy", "Du", "Vu", "Vy"}
    aster_time_symbols = {"Si", "Su", "Os", "Se", "Sy", "As"}
    time_bearing = time_positive or time_negative or bool(symbols.intersection(sakura_time_symbols)) or bool(symbols.intersection(aster_time_symbols))
    if time_bearing:
        features["time_bearing"] = True
        features["stem_likelihood"] = "verbal"
        features["process_bias"] = "high"
        features["probable_verb_stem"] = True
        polarities: list[str] = []
        if time_positive:
            polarities.append("positive")
        if time_negative:
            polarities.append("negative")
        if polarities:
            features["time_polarity"] = polarities[0] if len(polarities) == 1 else polarities

    if "Wu" in symbols:
        features.setdefault("processual", True)
    if "Kael" in symbols:
        features.setdefault("cluster_logic", "explicit")
    if any("Whenever" in meaning or "Never" in meaning or "Now" in meaning for meaning in meanings):
        features.setdefault("temporal_frame", "active")
    return features


def _token_matches_slot(token_obj: Mapping[str, Any], slot: ProjectionSlot) -> bool:
    token_kind = str(token_obj.get("kind") or "")
    if token_kind != slot.kind:
        return False
    if slot.semantic_role is not None and str(token_obj.get("semantic_role") or "") != slot.semantic_role:
        return False
    if slot.person is not None:
        try:
            if int(token_obj.get("person")) != slot.person:
                return False
        except (TypeError, ValueError):
            return False
    if slot.number is not None and str(token_obj.get("number") or "") != slot.number:
        return False
    if slot.required_features is not None:
        feature_bundle = _token_feature_bundle(token_obj)
        for key, value in slot.required_features.items():
            current = feature_bundle.get(str(key))
            if isinstance(current, list):
                if value not in current:
                    return False
            elif current != value:
                return False
    return True


def _frontier_hash_obj(frontier_obj: Mapping[str, Any]) -> str:
    payload = json.dumps(frontier_obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    import hashlib

    return "h_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _decimals_for_symbols(symbols: Sequence[str]) -> tuple[int, ...]:
    decimals: list[int] = []
    for symbol in symbols:
        entries = tuple(entry for entry in SHYGAZUN_BYTE_TABLE.values() if entry["symbol"] == symbol)
        if len(entries) != 1:
            raise LessonValidationError(f"symbol '{symbol}' must resolve to exactly one byte row for lesson indexing")
        decimals.append(int(entries[0]["decimal"]))
    return tuple(decimals)


def _loose_symbols_for_surface(surface: str) -> tuple[str, ...]:
    remaining = surface.strip().lower()
    if remaining == "":
        return tuple()
    symbol_map = {
        str(entry["symbol"]).lower(): str(entry["symbol"])
        for entry in SHYGAZUN_BYTE_TABLE.values()
    }
    ordered_symbols = sorted(symbol_map.keys(), key=len, reverse=True)
    resolved: list[str] = []
    while remaining:
        matched = False
        for symbol_lower in ordered_symbols:
            if remaining.startswith(symbol_lower):
                resolved.append(symbol_map[symbol_lower])
                remaining = remaining[len(symbol_lower):]
                matched = True
                break
        if not matched:
            return tuple()
    return tuple(resolved)


def _validate_citations(citations: Iterable[Mapping[str, Any]]) -> None:
    for citation in citations:
        decimal = int(citation["decimal"])
        expected = byte_entry(decimal)
        for key in ("decimal", "binary", "tongue", "symbol", "meaning"):
            if citation.get(key) != expected[key]:
                raise LessonValidationError(
                    f"citation mismatch for byte {decimal} field '{key}': {citation.get(key)!r} != {expected[key]!r}"
                )


def _load_lesson_file(path: Path) -> LessonRecord:
    payload = json.loads(path.read_text(encoding="utf-8"))
    lesson_id = str(payload.get("lesson_id") or "").strip()
    if lesson_id == "":
        raise LessonValidationError(f"lesson file missing lesson_id: {path}")
    authority = payload.get("authority")
    if not isinstance(authority, dict):
        raise LessonValidationError(f"lesson file missing authority block: {path}")
    citations = authority.get("citations")
    if not isinstance(citations, list) or len(citations) == 0:
        raise LessonValidationError(f"lesson file missing citations: {path}")
    _validate_citations(cast(Sequence[Mapping[str, Any]], citations))
    return LessonRecord(lesson_id=lesson_id, payload=payload)


def validate_lesson_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    lesson_id = str(payload.get("lesson_id") or "").strip()
    if lesson_id == "":
        raise LessonValidationError("lesson_payload_missing_lesson_id")
    authority = payload.get("authority")
    if not isinstance(authority, Mapping):
        raise LessonValidationError(f"lesson '{lesson_id}' missing authority block")
    citations = authority.get("citations")
    if not isinstance(citations, list) or len(citations) == 0:
        raise LessonValidationError(f"lesson '{lesson_id}' missing citations")
    _validate_citations(cast(Sequence[Mapping[str, Any]], citations))
    lesson_type = str(payload.get("lesson_type") or "").strip()
    return {
        "lesson_id": lesson_id,
        "lesson_type": lesson_type,
        "citation_count": len(citations),
        "validated": True,
    }


def validate_lesson_payloads(payloads: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    validations = [validate_lesson_payload(payload) for payload in payloads]
    return {
        "validated": True,
        "count": len(validations),
        "lessons": validations,
    }


@lru_cache(maxsize=1)
def load_lesson_registry() -> LessonRegistry:
    lessons_root = Path(__file__).resolve().parent / "lessons" / "canonical"
    lesson_files = sorted(lessons_root.glob("*.lesson.json"))
    lessons = tuple(_load_lesson_file(path) for path in lesson_files)
    return LessonRegistry(lessons)
