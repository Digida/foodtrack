"""Report Audit Tool — extracts numeric data points from reports and
verifies them against authoritative sources at configurable tolerance.

Features:
- Multi-pattern number extraction from free text
- Single/batch claim verification against authoritative sources
- Trend analysis over time windows (day/week/month)
- Data quality scoring
- Anomaly detection via Z-score
- Shipping/logistics-specific health checks
- Rate card extraction and validation
- Carrier/company coverage analysis
"""

from __future__ import annotations

import json
import logging
import math
import re
import statistics
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import httpx

from agent.base_tool import BaseTool

logger = logging.getLogger(__name__)

DEFAULT_TOLERANCE = 0.01


class Severity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditStatus(Enum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    SKIP = "skip"
    ERROR = "error"


class Confidence(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNVERIFIABLE = "unverifiable"


@dataclass
class AuditEntry:
    label: str = ""
    claimed_value: float = 0.0
    actual_value: float = 0.0
    unit: str = ""
    tolerance: float = DEFAULT_TOLERANCE
    deviation: float = 0.0
    status: str = AuditStatus.PASS.value
    confidence: str = Confidence.HIGH.value
    source: str = ""
    severity: str = Severity.INFO.value
    message: str = ""
    checks: List[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"label": self.label, "claimed_value": self.claimed_value,
                "actual_value": self.actual_value, "unit": self.unit,
                "tolerance": self.tolerance, "deviation": round(self.deviation, 6),
                "status": self.status, "confidence": self.confidence,
                "source": self.source, "severity": self.severity,
                "message": self.message, "checks": self.checks}


@dataclass
class AuditReport:
    entries: List[AuditEntry] = field(default_factory=list)
    total_checks: int = 0
    passed: int = 0
    failed: int = 0
    warnings: int = 0
    overall_status: str = AuditStatus.PASS.value
    confidence: str = Confidence.HIGH.value
    summary: str = ""
    score: float = 1.0

    def to_dict(self) -> dict:
        return {"entries": [e.to_dict() for e in self.entries],
                "total_checks": self.total_checks, "passed": self.passed,
                "failed": self.failed, "warnings": self.warnings,
                "overall_status": self.overall_status,
                "confidence": self.confidence, "summary": self.summary,
                "score": round(self.score, 4)}


@dataclass
class TrendPoint:
    timestamp: str = ""
    value: float = 0.0
    label: str = ""


@dataclass
class TrendAnalysis:
    metric: str = ""
    points: List[TrendPoint] = field(default_factory=list)
    direction: str = "stable"
    change_pct: float = 0.0
    mean: float = 0.0
    median: float = 0.0
    std_dev: float = 0.0
    min_val: float = 0.0
    max_val: float = 0.0
    anomaly_count: int = 0
    quality_score: float = 1.0

    def to_dict(self) -> dict:
        return {"metric": self.metric,
                "points": [{"timestamp": p.timestamp, "value": p.value, "label": p.label} for p in self.points],
                "direction": self.direction, "change_pct": round(self.change_pct, 4),
                "mean": round(self.mean, 4), "median": round(self.median, 4),
                "std_dev": round(self.std_dev, 4), "min_val": self.min_val,
                "max_val": self.max_val, "anomaly_count": self.anomaly_count,
                "quality_score": round(self.quality_score, 4)}


NUM_PATTERNS = [
    re.compile(r"([\d,]+\.?\d*)\s*(USD|EUR|GBP|UGX|KES|TZS|NGN|GHS|RWF|XOF|XAF|ZAR)", re.IGNORECASE),
    re.compile(r"\$([\d,]+\.?\d*)"),
    re.compile(r"([\d,]+\.?\d*)\s*(containers?|pallets?|boxes?|cartons?|pieces?|units?|items?|lots?)", re.IGNORECASE),
    re.compile(r"(?:rate|price|cost|fee|charge|total|amount|weight|volume|value)\s*:?\s*([\d,]+\.?\d*)", re.IGNORECASE),
    re.compile(r"([\d,]+\.?\d*)\s*%"),
    re.compile(r"([\d,]+\.?\d*)\s*(days?|hours?|weeks?|months?)", re.IGNORECASE),
    re.compile(r"([\d,]+\.?\d*)\s*(kg|kgs?|ton|t|lb|oz|m3|cbm|liters?|gallons?)", re.IGNORECASE),
    re.compile(r"([\d,]+\.?\d*)\s*(TEU|FEU)", re.IGNORECASE),
    re.compile(r"ETA\s*:?\s*([\d-]+\s*[\d:]*)"),
    re.compile(r"ETD\s*:?\s*([\d-]+\s*[\d:]*)"),
    re.compile(r"transit\s*:?\s*([\d,]+\.?\d*)\s*(days?)", re.IGNORECASE),
]


class ReportAudit:
    def extract_figures(self, text: str) -> List[dict]:
        figures = []
        seen = set()

        for pattern in NUM_PATTERNS:
            for match in pattern.finditer(text):
                raw = match.group(0).strip()
                if raw in seen:
                    continue
                seen.add(raw)

                val_str = match.group(1) if match.lastindex and match.lastindex >= 1 else match.group(0)
                value = self._parse_number(val_str)
                unit = match.group(2).upper() if match.lastindex and match.lastindex >= 2 else ""

                start = max(0, match.start() - 40)
                context = text[start:match.start()].strip()

                if not unit:
                    unit = self._infer_unit(raw, context)

                figures.append({
                    "value": round(value, 6),
                    "unit": unit or "units",
                    "raw": raw,
                    "context": context[-30:] if context else "",
                })

        return self._deduplicate_figures(figures)

    def _parse_number(self, s: str) -> float:
        s = s.strip().replace(",", "").replace("$", "").replace(" ", "")
        try:
            return float(s)
        except ValueError:
            return 0.0

    def _infer_unit(self, raw: str, context: str = "") -> str:
        upper = (raw + " " + context).upper()
        if "$" in raw:
            return "USD"
        if "%" in raw:
            return "%"
        for token in ["CONTAINER", "PALLET", "BOX", "CARTON", "PIECE", "UNIT", "ITEM", "LOT"]:
            if token in upper:
                return "units"
        for token in ["DAY", "HOUR", "WEEK", "MONTH"]:
            if token in upper:
                return "time"
        for token in ["KG", "TON", "LB", "M3", "CBM", "LITER", "GALLON"]:
            if token in upper:
                return "weight"
        for token in ["TEU", "FEU"]:
            if token in upper:
                return "container"
        return "units"

    def _deduplicate_figures(self, figures: List[dict]) -> List[dict]:
        if not figures:
            return []
        result = [figures[0]]
        for fig in figures[1:]:
            dup = False
            for existing in result:
                if abs(fig["value"] - existing["value"]) / max(abs(existing["value"]), 0.01) < 0.05 \
                   and fig["unit"] == existing["unit"]:
                    dup = True
                    break
            if not dup:
                result.append(fig)
        return result

    def verify_claim(self, claim: str, authoritative: dict,
                     tolerance: float = DEFAULT_TOLERANCE) -> AuditEntry:
        figures = self.extract_figures(claim)
        if not figures:
            return AuditEntry(label="claim", claimed_value=0, actual_value=0,
                              tolerance=tolerance, deviation=0,
                              status=AuditStatus.FAIL.value,
                              confidence=Confidence.LOW.value,
                              source=claim, severity=Severity.ERROR.value,
                              message="No extractable figures found in claim")

        best = figures[0]
        claimed = best["value"]
        unit = best["unit"].lower()

        actual = None
        matched_key = ""
        for key, val in authoritative.items():
            kl = key.lower()
            if unit in kl or kl in unit or str(claimed)[:4] in str(val):
                actual = val
                matched_key = key
                break

        if actual is None:
            for val in authoritative.values():
                if isinstance(val, (int, float)):
                    dev = abs(claimed - val) / max(abs(val), 0.01)
                    if dev <= tolerance:
                        actual = val
                        matched_key = str(val)
                        break

        if actual is None:
            actual = 0.0
            confidence = Confidence.LOW.value
        else:
            confidence = Confidence.HIGH.value if matched_key else Confidence.MEDIUM.value

        deviation = abs(claimed - actual) / max(abs(actual), 0.01)
        passed = deviation <= tolerance

        if passed:
            status = AuditStatus.PASS.value
            severity = Severity.INFO.value
            msg = f"Claim verified: {claimed} {best['unit']} (actual: {actual})"
        elif deviation <= tolerance * 3:
            status = AuditStatus.WARN.value
            severity = Severity.WARNING.value
            msg = f"Claim deviates by {deviation * 100:.1f}% (tolerance: {tolerance * 100:.1f}%)"
        else:
            status = AuditStatus.FAIL.value
            severity = Severity.ERROR.value
            msg = f"Claim deviates by {deviation * 100:.1f}% — exceeds tolerance of {tolerance * 100:.1f}%"

        return AuditEntry(label=matched_key or best["unit"] or "claim",
                          claimed_value=round(claimed, 6),
                          actual_value=round(actual, 6),
                          unit=best["unit"], tolerance=tolerance,
                          deviation=round(deviation, 6),
                          status=status, confidence=confidence,
                          source=claim, severity=severity, message=msg)

    def verify_batch(self, claims: List[str], authoritative: dict,
                     tolerance: float = DEFAULT_TOLERANCE) -> AuditReport:
        entries = [self.verify_claim(claim, authoritative, tolerance) for claim in claims]
        return self._aggregate_report(entries, "Batch verification")

    def verify_report(self, report_text: str, authoritative: dict,
                      tolerance: float = DEFAULT_TOLERANCE) -> AuditReport:
        figures = self.extract_figures(report_text)
        entries = [self._verify_figure(fig, authoritative, tolerance) for fig in figures]
        return self._aggregate_report(entries, "Report verification")

    def _verify_figure(self, figure: dict, authoritative: dict, tolerance: float) -> AuditEntry:
        claimed = figure["value"]
        unit = figure["unit"].lower()
        actual = None
        matched = ""

        for key, val in authoritative.items():
            kl = key.lower()
            if unit in kl or kl in unit:
                actual = val
                matched = key
                break

        if actual is None:
            for val in authoritative.values():
                if isinstance(val, (int, float)):
                    dev = abs(claimed - val) / max(abs(val), 0.01)
                    if dev <= tolerance:
                        actual = val
                        matched = str(val)
                        break

        if actual is None:
            actual = 0.0

        deviation = abs(claimed - actual) / max(abs(actual), 0.01)
        passed = deviation <= tolerance
        severity = Severity.INFO.value if passed else (Severity.WARNING.value if deviation <= tolerance * 3 else Severity.ERROR.value)
        status = AuditStatus.PASS.value if passed else (AuditStatus.WARN.value if deviation <= tolerance * 3 else AuditStatus.FAIL.value)

        return AuditEntry(label=matched or figure["unit"], claimed_value=round(claimed, 6),
                          actual_value=round(actual, 6), unit=figure["unit"],
                          tolerance=tolerance, deviation=round(deviation, 6),
                          status=status, severity=severity, source=figure["raw"])

    def analyze_trend(self, metric: str, data_points: List[dict],
                      value_key: str = "value", time_key: str = "timestamp") -> TrendAnalysis:
        if not data_points:
            return TrendAnalysis(metric=metric)

        values = [d.get(value_key, 0) for d in data_points]
        points = [TrendPoint(timestamp=d.get(time_key, ""), value=d.get(value_key, 0)) for d in data_points]

        n = len(values)
        mean = statistics.mean(values)
        median = statistics.median(values) if n >= 3 else mean
        std_dev = statistics.stdev(values) if n >= 2 else 0
        min_val = min(values)
        max_val = max(values)

        if n >= 3:
            first_half = values[:n // 2]
            second_half = values[n // 2:]
            dir_change = (sum(second_half) / len(second_half)) - (sum(first_half) / len(first_half)) if first_half and second_half else 0
            change_pct = dir_change / max(abs(mean), 0.01)

            if std_dev > abs(mean) * 0.5:
                direction = "volatile"
            elif change_pct > 0.05:
                direction = "rising"
            elif change_pct < -0.05:
                direction = "falling"
            else:
                direction = "stable"
        else:
            direction = "stable"
            change_pct = 0.0

        anomalies = 0
        quality_total = 0
        for v in values:
            if std_dev > 0:
                z = abs(v - mean) / std_dev
                if z > 2.0:
                    anomalies += 1
                quality_total += max(0, 1.0 - (z / 10.0))
            else:
                quality_total += 1.0

        quality_score = quality_total / max(n, 1)

        return TrendAnalysis(metric=metric, points=points, direction=direction,
                             change_pct=round(change_pct, 4), mean=round(mean, 4),
                             median=round(median, 4), std_dev=round(std_dev, 4),
                             min_val=min_val, max_val=max_val,
                             anomaly_count=anomalies, quality_score=round(quality_score, 4))

    def compare_periods(self, current: List[float], previous: List[float],
                        labels: Tuple[str, str] = ("current", "previous")) -> dict:
        if not current or not previous:
            return {"error": "Insufficient data"}

        cur_mean = statistics.mean(current)
        prev_mean = statistics.mean(previous)
        change = cur_mean - prev_mean
        change_pct = change / max(abs(prev_mean), 0.01)

        cur_volatility = statistics.stdev(current) / max(abs(cur_mean), 0.01) if len(current) >= 2 else 0
        prev_volatility = statistics.stdev(previous) / max(abs(prev_mean), 0.01) if len(previous) >= 2 else 0

        return {
            "current_period": labels[0], "previous_period": labels[1],
            "current_mean": round(cur_mean, 4), "previous_mean": round(prev_mean, 4),
            "absolute_change": round(change, 4), "change_pct": round(change_pct, 4),
            "direction": "up" if change > 0 else ("down" if change < 0 else "stable"),
            "current_volatility": round(cur_volatility, 4),
            "previous_volatility": round(prev_volatility, 4),
            "current_count": len(current), "previous_count": len(previous),
        }

    def validate_schema(self, data: dict, schema: dict) -> AuditReport:
        entries = []
        for field, rules in schema.items():
            actual = data.get(field)
            required = rules.get("required", False)
            expected_type = rules.get("type", "any")
            checks = []

            if required and actual is None:
                entries.append(AuditEntry(label=field, claimed_value=1, actual_value=0,
                                          status=AuditStatus.FAIL.value, severity=Severity.ERROR.value,
                                          source="schema", message=f"Required field missing: {field}"))
                continue

            if actual is None:
                entries.append(AuditEntry(label=field, claimed_value=0, actual_value=0,
                                          status=AuditStatus.SKIP.value, severity=Severity.INFO.value,
                                          source="schema", message=f"Optional field not present: {field}"))
                continue

            type_checks = {"number": (int, float), "string": (str,), "boolean": (bool,),
                           "list": (list,), "dict": (dict,)}
            if expected_type in type_checks:
                type_ok = isinstance(actual, type_checks[expected_type])
                checks.append({"check": f"type={expected_type}", "passed": type_ok,
                               "actual": type(actual).__name__})

            min_val = rules.get("min")
            max_val = rules.get("max")
            if min_val is not None and isinstance(actual, (int, float)):
                checks.append({"check": f">= {min_val}", "passed": actual >= min_val, "actual": actual})
            if max_val is not None and isinstance(actual, (int, float)):
                checks.append({"check": f"<= {max_val}", "passed": actual <= max_val, "actual": actual})

            pattern = rules.get("pattern")
            if pattern and isinstance(actual, str):
                matches = bool(re.match(pattern, actual))
                checks.append({"check": f"pattern={pattern}", "passed": matches, "actual": actual[:50]})

            enum_vals = rules.get("enum")
            if enum_vals:
                in_enum = actual in enum_vals
                checks.append({"check": f"in [{','.join(str(e) for e in enum_vals[:5])}]",
                               "passed": in_enum, "actual": actual})

            all_passed = all(c.get("passed") for c in checks)
            status = AuditStatus.PASS.value if all_passed else AuditStatus.FAIL.value
            severity = Severity.INFO.value if all_passed else Severity.ERROR.value

            entries.append(AuditEntry(label=field, claimed_value=1 if all_passed else 0,
                                      actual_value=1, unit="boolean", status=status,
                                      severity=severity, source="schema",
                                      message=f"{field}: {len([c for c in checks if c.get('passed')])}/{len(checks)} checks passed",
                                      checks=checks))

        return self._aggregate_report(entries, "Schema validation")

    def _aggregate_report(self, entries: List[AuditEntry], summary: str) -> AuditReport:
        total = len(entries)
        passed = sum(1 for e in entries if e.status == AuditStatus.PASS.value)
        failed = sum(1 for e in entries if e.status == AuditStatus.FAIL.value)
        warnings = sum(1 for e in entries if e.status == AuditStatus.WARN.value)

        if total == 0:
            return AuditReport(overall_status=AuditStatus.PASS.value, summary=f"{summary}: no checks", score=1.0)

        if failed > 0:
            overall = AuditStatus.FAIL.value
        elif warnings > 0:
            overall = AuditStatus.WARN.value
        else:
            overall = AuditStatus.PASS.value

        score = (passed + warnings * 0.5) / max(total, 1)

        high_conf = sum(1 for e in entries if e.confidence == Confidence.HIGH.value)
        conf_ratio = high_conf / max(total, 1)
        if conf_ratio >= 0.8:
            confidence = Confidence.HIGH.value
        elif conf_ratio >= 0.4:
            confidence = Confidence.MEDIUM.value
        else:
            confidence = Confidence.LOW.value

        return AuditReport(entries=entries, total_checks=total, passed=passed,
                           failed=failed, warnings=warnings,
                           overall_status=overall, confidence=confidence,
                           summary=f"{summary}: {passed}/{total} passed, {warnings} warnings, {failed} failed",
                           score=round(score, 4))

    def score_data_quality(self, data: dict, schema: dict) -> dict:
        report = self.validate_schema(data, schema)
        completeness = report.passed / max(report.total_checks, 1)
        return {"completeness": round(completeness, 4), "score": report.score,
                "passed": report.passed, "total": report.total_checks,
                "failed": report.failed, "summary": report.summary}

    def audit_shipping_health(self, shipping_data: dict) -> AuditReport:
        entries = []
        shipments = shipping_data.get("shipments", [])
        carriers = shipping_data.get("carriers", [])
        warehouses = shipping_data.get("warehouses", [])
        rates = shipping_data.get("rates", [])

        entries.append(AuditEntry(label="Total shipments", claimed_value=len(shipments),
                                  actual_value=len(shipments), unit="count",
                                  status=AuditStatus.PASS.value,
                                  source=f"{len(shipments)} shipments"))

        entries.append(AuditEntry(label="Active carriers", claimed_value=len(carriers),
                                  actual_value=len(carriers), unit="count",
                                  status=AuditStatus.PASS.value,
                                  source=f"{len(carriers)} carriers"))

        entries.append(AuditEntry(label="Warehouses", claimed_value=len(warehouses),
                                  actual_value=len(warehouses), unit="count",
                                  status=AuditStatus.PASS.value,
                                  source=f"{len(warehouses)} warehouses"))

        if rates:
            total_rates = len(rates)
            min_rate = min(r.get("amount", 0) for r in rates)
            max_rate = max(r.get("amount", 0) for r in rates)
            entries.append(AuditEntry(label="Rate cards", claimed_value=total_rates,
                                      actual_value=total_rates, unit="count",
                                      status=AuditStatus.PASS.value,
                                      source=f"{total_rates} rates (${min_rate:.2f}-${max_rate:.2f})"))

        if shipments:
            in_transit = sum(1 for s in shipments if s.get("status") == "in_transit")
            delivered = sum(1 for s in shipments if s.get("status") == "delivered")
            delayed = sum(1 for s in shipments if s.get("status") in ("exception", "delayed"))
            if shipments:
                delay_rate = delayed / len(shipments) * 100
                entries.append(AuditEntry(label="Delay rate", claimed_value=delay_rate,
                                          actual_value=delay_rate, unit="%",
                                          status=AuditStatus.WARN.value if delay_rate > 10 else AuditStatus.PASS.value,
                                          severity=Severity.WARNING.value if delay_rate > 10 else Severity.INFO.value,
                                          source=f"{delayed}/{len(shipments)} delayed ({delay_rate:.1f}%)"))

        return self._aggregate_report(entries, "Shipping health audit")

    def audit_rate_card(self, rate_data: dict, expected_currency: str = "USD") -> AuditReport:
        entries = []

        schema = {
            "origin": {"type": "string", "required": True},
            "destination": {"type": "string", "required": True},
            "amount": {"type": "number", "required": True, "min": 0},
            "currency": {"type": "string", "required": True, "enum": ["USD", "EUR", "GBP"]},
            "mode": {"type": "string", "required": True, "enum": ["ocean", "air", "truck", "rail", "courier"]},
            "valid_from": {"type": "string", "required": True},
            "valid_until": {"type": "string", "required": False},
        }

        report = self.validate_schema(rate_data, schema)
        entries.extend(report.entries)

        currency = rate_data.get("currency", "")
        if currency and currency != expected_currency:
            entries.append(AuditEntry(label="Currency check", claimed_value=1, actual_value=0,
                                      status=AuditStatus.WARN.value, severity=Severity.WARNING.value,
                                      source=f"Expected {expected_currency}, got {currency}",
                                      message=f"Rate currency mismatch"))

        return self._aggregate_report(entries, "Rate card audit")

    def rate_shipment(self, origin: str, destination: str, weight_kg: float,
                      mode: str = "ocean", rate_cards: List[dict] = None) -> dict:
        if not rate_cards:
            return {"status": "error", "error": "No rate cards available"}

        matching_rates = []
        for rate in rate_cards:
            if (rate.get("origin", "").lower() == origin.lower() and
                rate.get("destination", "").lower() == destination.lower() and
                rate.get("mode", "").lower() == mode.lower()):
                matching_rates.append(rate)

        if not matching_rates:
            return {"status": "error", "error": f"No rates found for {origin} -> {destination} ({mode})"}

        results = []
        for rate in matching_rates:
            base = rate.get("amount", 0)
            min_weight = rate.get("min_weight_kg", 0)
            rate_per_kg = rate.get("rate_per_kg", 0)
            effective_weight = max(weight_kg, min_weight)
            total = base + (effective_weight * rate_per_kg)
            results.append({
                "carrier": rate.get("carrier", "unknown"),
                "base_amount": base,
                "rate_per_kg": rate_per_kg,
                "total": round(total, 2),
                "currency": rate.get("currency", "USD"),
                "valid_until": rate.get("valid_until", ""),
            })

        results.sort(key=lambda r: r["total"])

        return {
            "status": "ok",
            "origin": origin,
            "destination": destination,
            "weight_kg": weight_kg,
            "mode": mode,
            "options": results,
            "best": results[0] if results else None,
        }

    def analyze_carrier_coverage(self, carriers: List[dict]) -> dict:
        if not carriers:
            return {"status": "error", "error": "No carrier data"}

        total = len(carriers)
        with_api = sum(1 for c in carriers if c.get("has_api", False))
        with_tracking = sum(1 for c in carriers if c.get("provides_tracking", False))
        with_rates = sum(1 for c in carriers if c.get("provides_rates", False))
        modes = {}
        for c in carriers:
            for m in c.get("modes", []):
                modes[m] = modes.get(m, 0) + 1

        return {
            "total_carriers": total,
            "api_integration_rate": round(with_api / total * 100, 1) if total else 0,
            "tracking_coverage": round(with_tracking / total * 100, 1) if total else 0,
            "rate_coverage": round(with_rates / total * 100, 1) if total else 0,
            "mode_distribution": modes,
            "carriers": carriers,
        }


class ReportAuditTool(BaseTool):
    name = "report_audit"
    description = (
        "Audit reports, extract figures, verify claims, analyze trends, "
        "and perform shipping/logistics health checks."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["extract", "verify", "trend", "shipping_health", "rate_shipment",
                         "carrier_coverage", "validate_schema", "data_quality"],
                "description": "Action to perform",
            },
            "text": {"type": "string", "description": "Text to analyze (for extract/verify)"},
            "data": {"type": "object", "description": "Data dict (for shipping_health, validate_schema)"},
            "claim": {"type": "string", "description": "Single claim to verify"},
            "authoritative": {"type": "object", "description": "Known correct values for verification"},
            "tolerance": {"type": "number", "description": "Max deviation fraction (default 0.01)"},
            "metric": {"type": "string", "description": "Metric name for trend analysis"},
            "data_points": {"type": "array", "description": "List of data point dicts for trend analysis"},
            "origin": {"type": "string", "description": "Origin location for rate calc"},
            "destination": {"type": "string", "description": "Destination location for rate calc"},
            "weight_kg": {"type": "number", "description": "Weight in kg for rate calc"},
            "mode": {"type": "string", "description": "Mode for rate calc (ocean/air/truck/rail/courier)"},
            "rate_cards": {"type": "array", "description": "Rate card dicts for rate calc"},
            "schema": {"type": "object", "description": "Schema definition for validation"},
            "carriers": {"type": "array", "description": "Carrier data for coverage analysis"},
        },
        "required": ["action"],
    }

    @classmethod
    def check_available(cls) -> bool:
        return True

    def execute(self, **kwargs: Any) -> str:
        auditor = ReportAudit()
        action = kwargs["action"]

        if action == "extract":
            result = auditor.extract_figures(kwargs.get("text", ""))
        elif action == "verify":
            result = auditor.verify_claim(
                kwargs.get("claim", ""),
                kwargs.get("authoritative", {}),
                kwargs.get("tolerance", DEFAULT_TOLERANCE),
            ).to_dict()
        elif action == "trend":
            result = auditor.analyze_trend(
                kwargs.get("metric", ""),
                kwargs.get("data_points", []),
            ).to_dict()
        elif action == "shipping_health":
            result = auditor.audit_shipping_health(kwargs.get("data", {})).to_dict()
        elif action == "rate_shipment":
            result = auditor.rate_shipment(
                kwargs.get("origin", ""),
                kwargs.get("destination", ""),
                kwargs.get("weight_kg", 0),
                kwargs.get("mode", "ocean"),
                kwargs.get("rate_cards", []),
            )
        elif action == "carrier_coverage":
            result = auditor.analyze_carrier_coverage(kwargs.get("carriers", []))
        elif action == "validate_schema":
            result = auditor.validate_schema(
                kwargs.get("data", {}),
                kwargs.get("schema", {}),
            ).to_dict()
        elif action == "data_quality":
            result = auditor.score_data_quality(
                kwargs.get("data", {}),
                kwargs.get("schema", {}),
            )
        else:
            result = {"status": "error", "error": f"Unknown action: {action}"}

        return json.dumps(result, ensure_ascii=False)
