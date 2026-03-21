"""
Leo Health — Parser Test Suite
Tests all four parser modules: whoop, oura, fitbit, apple_health.
Run with: python -m pytest tests/
"""

import csv
import io
import json
import zipfile
import tempfile
from pathlib import Path

import pytest


# ── Whoop parser tests ────────────────────────────────────────────────────────

class TestWhoopParser:
    def test_iso_standard_format(self):
        from leo_health.parsers.whoop import _iso
        assert _iso("2024-01-15 08:23:44") == "2024-01-15T08:23:44"

    def test_iso_slash_format(self):
        from leo_health.parsers.whoop import _iso
        result = _iso("01/15/2024 08:23:44")
        assert "2024" in result and "01" in result

    def test_iso_empty_string(self):
        from leo_health.parsers.whoop import _iso
        assert _iso("") == ""

    def test_float_valid(self):
        from leo_health.parsers.whoop import _float
        assert _float("72.5") == 72.5

    def test_float_invalid_returns_none(self):
        from leo_health.parsers.whoop import _float
        assert _float("n/a") is None
        assert _float("") is None
        assert _float("  ") is None

    def test_float_zero_preserved(self):
        from leo_health.parsers.whoop import _float
        assert _float("0.0") == 0.0

    def test_coalesce_float_picks_first(self):
        from leo_health.parsers.whoop import _coalesce_float
        assert _coalesce_float("", "42.0", "99.0") == 42.0

    def test_coalesce_float_all_empty(self):
        from leo_health.parsers.whoop import _coalesce_float
        assert _coalesce_float("", "", "") is None

    def test_detect_csv_type_recovery(self):
        from leo_health.parsers.whoop import _detect_csv_type
        assert _detect_csv_type(["Cycle start time", "Recovery Score %", "HRV (ms)"]) == "recovery"

    def test_detect_csv_type_strain(self):
        from leo_health.parsers.whoop import _detect_csv_type
        assert _detect_csv_type(["Day Strain", "Calories"]) == "strain"

    def test_detect_csv_type_sleep(self):
        from leo_health.parsers.whoop import _detect_csv_type
        assert _detect_csv_type(["Sleep Performance %", "Time in Bed (hours)"]) == "sleep"

    def test_detect_csv_type_unknown(self):
        from leo_health.parsers.whoop import _detect_csv_type
        assert _detect_csv_type(["foo", "bar"]) == "unknown"

    def test_parse_recovery_row(self):
        from leo_health.parsers.whoop import _parse_recovery_row
        row = {
            "Cycle start time": "2024-01-15 08:00:00",
            "Recovery Score %": "78",
            "Heart Rate Variability (ms)": "55.2",
            "Resting Heart Rate (bpm)": "52",
            "SpO2 %": "98.0",
        }
        result = _parse_recovery_row(row)
        assert result is not None
        assert result["source"] == "whoop"
        assert result["recovery_score"] == 78.0
        assert result["hrv_ms"] == 55.2
        assert result["resting_heart_rate"] == 52.0

    def test_parse_recovery_row_missing_date(self):
        from leo_health.parsers.whoop import _parse_recovery_row
        assert _parse_recovery_row({"Recovery Score %": "78"}) is None

    def test_parse_strain_row(self):
        from leo_health.parsers.whoop import _parse_strain_row
        row = {
            "Cycle start time": "2024-01-15 08:00:00",
            "Day Strain": "14.2",
            "Calories": "2800",
            "Max Heart Rate (bpm)": "172",
            "Average Heart Rate (bpm)": "95",
        }
        result = _parse_strain_row(row)
        assert result is not None
        assert result["day_strain"] == 14.2
        assert result["calories"] == 2800.0

    def test_parse_sleep_row(self):
        from leo_health.parsers.whoop import _parse_sleep_row
        row = {
            "Cycle start time": "2024-01-15 00:00:00",
            "Sleep Performance %": "85",
            "Time in Bed (hours)": "7.5",
            "Light Sleep Duration (hours)": "3.2",
            "REM Sleep Duration (hours)": "1.8",
            "Slow Wave Sleep Duration (hours)": "1.5",
        }
        result = _parse_sleep_row(row)
        assert result is not None
        assert result["sleep_performance_pct"] == 85.0
        assert result["source"] == "whoop"

    def test_parse_from_csv_file(self, tmp_path):
        from leo_health.parsers.whoop import parse
        csv_path = tmp_path / "recovery.csv"
        csv_path.write_text(
            "Cycle start time,Recovery Score %,Heart Rate Variability (ms),Resting Heart Rate (bpm),SpO2 %\n"
            "2024-01-15 08:00:00,78,55.2,52,98.0\n"
            "2024-01-16 08:00:00,82,60.1,51,97.5\n"
        )
        result = parse(str(csv_path))
        assert len(result["recovery"]) == 2
        assert result["recovery"][0]["recovery_score"] == 78.0

    def test_parse_folder_skips_non_whoop(self, tmp_path):
        from leo_health.parsers.whoop import parse_folder
        # Valid Whoop CSV
        (tmp_path / "recovery.csv").write_text(
            "Cycle start time,Recovery Score %,Heart Rate Variability (ms),Resting Heart Rate (bpm),SpO2 %\n"
            "2024-01-15 08:00:00,78,55.2,52,98.0\n"
        )
        # Non-Whoop file that would previously crash with bare Exception
        (tmp_path / "notes.csv").write_text("not,a,whoop,file\nsome,random,data,here\n")
        result = parse_folder(str(tmp_path))
        assert isinstance(result["recovery"], list)


# ── Oura parser tests ─────────────────────────────────────────────────────────

class TestOuraParser:
    def test_iso_date_only(self):
        from leo_health.parsers.oura import _iso
        assert _iso("2024-01-15") == "2024-01-15T00:00:00"

    def test_iso_datetime(self):
        from leo_health.parsers.oura import _iso
        result = _iso("2024-01-15T23:30:00+00:00")
        assert result.startswith("2024-01-15")

    def test_iso_empty(self):
        from leo_health.parsers.oura import _iso
        assert _iso("") == ""

    def test_float_valid(self):
        from leo_health.parsers.oura import _float
        assert _float("88.5") == 88.5

    def test_float_invalid(self):
        from leo_health.parsers.oura import _float
        assert _float("") is None
        assert _float("N/A") is None

    def test_seconds_to_hours(self):
        from leo_health.parsers.oura import _seconds_to_hours
        assert _seconds_to_hours("3600") == 1.0
        assert _seconds_to_hours("5400") == 1.5
        assert _seconds_to_hours("") is None

    def test_normalize_header(self):
        from leo_health.parsers.oura import _normalize_header
        assert _normalize_header("Sleep Score (%)") == "sleep_score_pct"
        assert _normalize_header("HRV Balance") == "hrv_balance"

    def test_detect_csv_type_readiness(self):
        from leo_health.parsers.oura import _detect_csv_type
        assert _detect_csv_type(["date", "readiness_score", "recovery_index"]) == "readiness"

    def test_detect_csv_type_sleep(self):
        from leo_health.parsers.oura import _detect_csv_type
        assert _detect_csv_type(["date", "bedtime_start", "deep_sleep_duration"]) == "sleep"

    def test_detect_csv_type_activity(self):
        from leo_health.parsers.oura import _detect_csv_type
        assert _detect_csv_type(["date", "steps", "active_calories", "activity_score"]) == "activity"

    def test_detect_csv_type_unknown(self):
        from leo_health.parsers.oura import _detect_csv_type
        assert _detect_csv_type(["foo", "bar"]) == "unknown"

    def test_parse_readiness_row(self):
        from leo_health.parsers.oura import _parse_readiness_row
        row = {
            "date": "2024-01-15",
            "readiness_score": "82",
            "resting_heart_rate": "52",
            "hrv_balance": "48.5",
            "temperature_deviation": "0.1",
            "recovery_index": "90",
            "activity_balance": "75",
            "sleep_balance": "80",
        }
        result = _parse_readiness_row(row)
        assert result is not None
        assert result["readiness_score"] == 82.0
        assert result["resting_heart_rate"] == 52.0
        assert result["hrv_balance"] == 48.5
        assert result["source"] == "oura"

    def test_parse_readiness_row_missing_date(self):
        from leo_health.parsers.oura import _parse_readiness_row
        assert _parse_readiness_row({"readiness_score": "82"}) is None

    def test_parse_sleep_row_returns_triple(self):
        from leo_health.parsers.oura import _parse_sleep_row
        row = {
            "date": "2024-01-15",
            "bedtime_start": "2024-01-14T23:30:00",
            "bedtime_end": "2024-01-15T07:00:00",
            "time_in_bed": "27000",       # 7.5 hours in seconds
            "deep_sleep_duration": "5400", # 1.5 hours
            "light_sleep_duration": "9000",
            "rem_sleep_duration": "5400",
            "awake_duration": "1800",
            "efficiency": "90",
            "average_hrv": "45.0",
            "hr_lowest": "48",
        }
        sleep_rec, hr_rec, hrv_rec = _parse_sleep_row(row)
        assert sleep_rec is not None
        assert sleep_rec["source"] == "oura"
        assert sleep_rec["time_in_bed_hours"] == pytest.approx(7.5, abs=0.01)
        assert sleep_rec["sleep_performance_pct"] == 90.0
        assert hr_rec is not None and hr_rec["value"] == 48.0
        assert hrv_rec is not None and hrv_rec["metric"] == "hrv_rmssd"

    def test_parse_sleep_row_efficiency_fraction(self):
        from leo_health.parsers.oura import _parse_sleep_row
        row = {"date": "2024-01-15", "efficiency": "0.92"}
        sleep_rec, _, _ = _parse_sleep_row(row)
        assert sleep_rec["sleep_performance_pct"] == pytest.approx(92.0, abs=0.1)

    def test_parse_readiness_csv_file(self, tmp_path):
        from leo_health.parsers.oura import parse
        csv_path = tmp_path / "oura_readiness.csv"
        csv_path.write_text(
            "date,readiness_score,resting_heart_rate,hrv_balance,temperature_deviation\n"
            "2024-01-15,82,52,48.5,0.1\n"
            "2024-01-16,79,53,44.0,-0.2\n"
        )
        result = parse(str(csv_path))
        assert len(result["readiness"]) == 2
        assert result["readiness"][0]["readiness_score"] == 82.0

    def test_parse_folder_skips_non_oura(self, tmp_path):
        from leo_health.parsers.oura import parse_folder
        (tmp_path / "readiness.csv").write_text(
            "date,readiness_score,resting_heart_rate,hrv_balance\n"
            "2024-01-15,82,52,48.5\n"
        )
        (tmp_path / "garbage.csv").write_text("col1,col2\nval1,val2\n")
        result = parse_folder(str(tmp_path))
        assert isinstance(result["readiness"], list)
        assert len(result["readiness"]) >= 1


# ── Fitbit parser tests ───────────────────────────────────────────────────────

class TestFitbitParser:
    def test_classify_file_heart(self):
        from leo_health.parsers.fitbit import _classify_file
        assert _classify_file("activities-heart-2024-01-15.json") == "heart"

    def test_classify_file_sleep(self):
        from leo_health.parsers.fitbit import _classify_file
        assert _classify_file("sleep-2024-01-15.json") == "sleep"

    def test_classify_file_hrv(self):
        from leo_health.parsers.fitbit import _classify_file
        assert _classify_file("hrv-2024-01-15.json") == "hrv"

    def test_classify_file_exercise(self):
        from leo_health.parsers.fitbit import _classify_file
        assert _classify_file("exercise-2024-01-15.json") == "exercise"

    def test_classify_file_unknown(self):
        from leo_health.parsers.fitbit import _classify_file
        assert _classify_file("personal-notes.json") == "unknown"
        assert _classify_file("activities-heart-2024-01-15-intraday.json") == "unknown"

    def test_parse_heart_file(self):
        from leo_health.parsers.fitbit import _parse_heart_file
        data = [
            {"dateTime": "2024-01-15", "value": {"restingHeartRate": 62, "customHeartRateZones": []}},
            {"dateTime": "2024-01-16", "value": {"restingHeartRate": 60}},
        ]
        result = _parse_heart_file(data)
        assert len(result) == 2
        assert result[0]["metric"] == "resting_heart_rate"
        assert result[0]["value"] == 62.0
        assert result[0]["source"] == "fitbit"

    def test_parse_heart_file_missing_rhr(self):
        from leo_health.parsers.fitbit import _parse_heart_file
        data = [{"dateTime": "2024-01-15", "value": {}}]
        assert _parse_heart_file(data) == []

    def test_parse_hrv_file(self):
        from leo_health.parsers.fitbit import _parse_hrv_file
        data = [{"hrv": [{"dateTime": "2024-01-15", "value": {"dailyRmssd": 42.8, "deepRmssd": 38.1}}]}]
        result = _parse_hrv_file(data)
        assert len(result) == 1
        assert result[0]["metric"] == "hrv_rmssd"
        assert result[0]["value"] == 42.8

    def test_parse_sleep_file(self):
        from leo_health.parsers.fitbit import _parse_sleep_file
        data = [{
            "dateOfSleep": "2024-01-15",
            "startTime": "2024-01-14T23:00:00.000",
            "endTime": "2024-01-15T07:00:00.000",
            "timeInBed": 480,
            "efficiency": 88,
            "minutesAsleep": 420,
            "minutesAwake": 60,
            "levels": {
                "summary": {
                    "deep": {"minutes": 90},
                    "light": {"minutes": 200},
                    "rem": {"minutes": 100},
                    "wake": {"minutes": 60},
                }
            },
        }]
        result = _parse_sleep_file(data)
        assert len(result) == 1
        rec = result[0]
        assert rec["source"] == "fitbit"
        assert rec["sleep_performance_pct"] == 88.0
        assert rec["time_in_bed_hours"] == pytest.approx(8.0, abs=0.01)
        assert rec["deep_sleep_hours"] == pytest.approx(1.5, abs=0.01)

    def test_normalize_activity(self):
        from leo_health.parsers.fitbit import _normalize_activity
        assert _normalize_activity("Running") == "running"
        assert _normalize_activity("Weight Training") == "strength_training"
        assert _normalize_activity("Bike Ride") == "cycling"
        assert _normalize_activity("HIIT Workout") == "hiit"

    def test_parse_from_zip(self, tmp_path):
        from leo_health.parsers.fitbit import parse
        heart_data = [{"dateTime": "2024-01-15", "value": {"restingHeartRate": 62}}]
        zip_path = tmp_path / "fitbit_export.zip"
        with zipfile.ZipFile(str(zip_path), "w") as zf:
            zf.writestr("activities-heart-2024-01-15.json", json.dumps(heart_data))
        result = parse(str(zip_path))
        assert len(result["heart_rate"]) == 1
        assert result["heart_rate"][0]["value"] == 62.0


# ── Apple Health parser tests ─────────────────────────────────────────────────

class TestAppleHealthParser:
    def _make_export_zip(self, tmp_path: Path, xml_content: str) -> str:
        """Create a minimal Apple Health export.zip for testing."""
        zip_path = tmp_path / "export.zip"
        with zipfile.ZipFile(str(zip_path), "w") as zf:
            zf.writestr("apple_health_export/export.xml", xml_content)
        return str(zip_path)

    def test_iso_apple_format(self):
        from leo_health.parsers.apple_health import _iso
        result = _iso("2024-01-15 08:23:44 -0500")
        assert result.startswith("2024-01-15")

    def test_iso_empty(self):
        from leo_health.parsers.apple_health import _iso
        assert _iso("") == ""

    def test_parse_heart_rate_record(self, tmp_path):
        from leo_health.parsers.apple_health import parse
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<HealthData locale="en_US">
  <Record type="HKQuantityTypeIdentifierHeartRate"
          unit="count/min"
          value="72"
          startDate="2024-01-15 08:00:00 -0500"
          endDate="2024-01-15 08:00:00 -0500"
          sourceName="Apple Watch"/>
</HealthData>"""
        zip_path = self._make_export_zip(tmp_path, xml)
        result = parse(zip_path)
        assert len(result["heart_rate"]) == 1
        assert result["heart_rate"][0]["value"] == 72.0
        assert result["heart_rate"][0]["metric"] == "heart_rate"
        assert result["heart_rate"][0]["source"] == "apple_health"

    def test_parse_hrv_record(self, tmp_path):
        from leo_health.parsers.apple_health import parse
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<HealthData locale="en_US">
  <Record type="HKQuantityTypeIdentifierHeartRateVariabilitySDNN"
          unit="ms"
          value="45.3"
          startDate="2024-01-15 08:00:00 -0500"
          endDate="2024-01-15 08:00:00 -0500"
          sourceName="Apple Watch"/>
</HealthData>"""
        zip_path = self._make_export_zip(tmp_path, xml)
        result = parse(zip_path)
        assert len(result["hrv"]) == 1
        assert result["hrv"][0]["metric"] == "hrv_sdnn"
        assert result["hrv"][0]["value"] == pytest.approx(45.3, abs=0.01)

    def test_parse_sleep_record(self, tmp_path):
        from leo_health.parsers.apple_health import parse
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<HealthData locale="en_US">
  <Record type="HKCategoryTypeIdentifierSleepAnalysis"
          value="HKCategoryValueSleepAnalysisAsleepREM"
          startDate="2024-01-15 01:00:00 -0500"
          endDate="2024-01-15 02:30:00 -0500"
          sourceName="Apple Watch"/>
</HealthData>"""
        zip_path = self._make_export_zip(tmp_path, xml)
        result = parse(zip_path)
        assert len(result["sleep"]) == 1
        assert result["sleep"][0]["source"] == "apple_health"

    def test_parse_workout_record(self, tmp_path):
        from leo_health.parsers.apple_health import parse
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<HealthData locale="en_US">
  <Workout workoutActivityType="HKWorkoutActivityTypeRunning"
           duration="35.5"
           durationUnit="min"
           totalDistance="5.2"
           totalDistanceUnit="km"
           totalEnergyBurned="350"
           totalEnergyBurnedUnit="kcal"
           startDate="2024-01-15 07:00:00 -0500"
           endDate="2024-01-15 07:35:30 -0500"
           sourceName="Apple Watch"/>
</HealthData>"""
        zip_path = self._make_export_zip(tmp_path, xml)
        result = parse(zip_path)
        assert len(result["workouts"]) == 1
        assert result["workouts"][0]["activity"] == "running"

    def test_parse_empty_export(self, tmp_path):
        from leo_health.parsers.apple_health import parse
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<HealthData locale="en_US">
</HealthData>"""
        zip_path = self._make_export_zip(tmp_path, xml)
        result = parse(zip_path)
        assert result["heart_rate"] == []
        assert result["hrv"] == []
        assert result["sleep"] == []
        assert result["workouts"] == []
